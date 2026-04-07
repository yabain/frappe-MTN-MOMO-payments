from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt

from mtn_momo_payments.services.client import MTNMoMoClient
from mtn_momo_payments.services.transactions import apply_status_payload
from mtn_momo_payments.utils.helpers import (
    build_callback_url,
    get_enabled_settings,
    make_uuid,
    next_poll_after,
    normalize_phone_number,
    safe_json_dumps,
)


def _make_transfer_tx(settings_doc, amount, phone_number, reference_doctype=None, reference_name=None, party_type=None, party=None, company=None, batch=None):
    tx = frappe.new_doc("MTN MoMo Transaction")
    tx.update(
        {
            "settings": settings_doc.name,
            "transaction_type": "Transfer",
            "direction": "Out",
            "status": "Queued",
            "amount": flt(amount),
            "currency": settings_doc.currency,
            "payee_party_id_type": "MSISDN",
            "payee_party_id": phone_number,
            "request_reference_id": make_uuid(),
            "external_id": make_uuid(),
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "party_type": party_type,
            "party": party,
            "mode_of_payment": settings_doc.mode_of_payment,
            "company": company or settings_doc.company,
            "sandbox": settings_doc.is_sandbox,
            "disbursement_batch": batch,
            "next_poll_at": next_poll_after(5),
        }
    )
    tx.insert(ignore_permissions=True)
    return tx


def _transfer(tx, payer_message: str = "ERPNext payout", payee_note: str = "ERPNext payout"):
    settings_doc = frappe.get_doc("MTN MoMo Settings", tx.settings)
    client = MTNMoMoClient(settings_doc)
    callback_url = build_callback_url(
        settings_doc,
        "mtn_momo_payments.api.webhooks.disbursement_callback",
        tx.request_reference_id,
    )
    payload = {
        "amount": str(tx.amount),
        "currency": tx.currency,
        "externalId": tx.external_id,
        "payee": {
            "partyIdType": tx.payee_party_id_type or "MSISDN",
            "partyId": tx.payee_party_id,
        },
        "payerMessage": payer_message,
        "payeeNote": payee_note,
    }
    response = client.transfer(tx.request_reference_id, payload, callback_url=callback_url)
    tx.db_set("api_response", safe_json_dumps(response), update_modified=False)
    tx.db_set("status", "Pending", update_modified=False)
    tx.db_set("next_poll_at", next_poll_after(5), update_modified=False)
    return tx


@frappe.whitelist()
def transfer_for_reference(
    settings: str | None = None,
    reference_doctype: str | None = None,
    reference_name: str | None = None,
    phone_number: str | None = None,
    amount: float | None = None,
    party_type: str | None = None,
    party: str | None = None,
    payer_message: str | None = None,
    payee_note: str | None = None,
):
    company = None
    if reference_doctype and reference_name:
        ref = frappe.get_doc(reference_doctype, reference_name)
        company = getattr(ref, "company", None)
        if reference_doctype in {"Purchase Invoice", "Purchase Order"}:
            party_type = party_type or "Supplier"
            party = party or getattr(ref, "supplier", None)
            if not phone_number and party:
                phone_number = (
                    frappe.db.get_value("Supplier", party, "mtn_momo_mobile_number")
                    or frappe.db.get_value("Supplier", party, "mobile_no")
                )
        amount = flt(amount or getattr(ref, "outstanding_amount", None) or getattr(ref, "grand_total", None))
    settings_doc = frappe.get_doc("MTN MoMo Settings", settings) if settings else get_enabled_settings(company)
    phone_number = normalize_phone_number(phone_number, settings_doc.country_code)
    if not phone_number:
        frappe.throw("A valid beneficiary mobile number is required.")
    if flt(amount) <= 0:
        frappe.throw("Amount must be greater than zero.")
    tx = _make_transfer_tx(
        settings_doc,
        amount,
        phone_number,
        reference_doctype=reference_doctype,
        reference_name=reference_name,
        party_type=party_type,
        party=party,
        company=company,
    )
    _transfer(tx, payer_message or "ERPNext payout", payee_note or "MTN MoMo disbursement")
    return {"transaction": tx.name, "reference_id": tx.request_reference_id, "status": "Pending"}


def _poll_disbursement_transaction(tx):
    settings_doc = frappe.get_doc("MTN MoMo Settings", tx.settings)
    client = MTNMoMoClient(settings_doc)
    payload = client.get_transfer_status(tx.request_reference_id)
    return apply_status_payload(tx, payload)


@frappe.whitelist()
def get_disbursement_status(transaction: str):
    tx = frappe.get_doc("MTN MoMo Transaction", transaction)
    status = _poll_disbursement_transaction(tx)
    tx.reload()
    return {"status": status, "reason": tx.reason, "payment_entry": tx.payment_entry}


@frappe.whitelist()
def refund_transaction(transaction_name: str, amount: float | None = None, payer_message: str | None = None, payee_note: str | None = None):
    original = frappe.get_doc("MTN MoMo Transaction", transaction_name)
    if original.status != "Success":
        frappe.throw("Only successful transactions can be refunded.")
    settings_doc = frappe.get_doc("MTN MoMo Settings", original.settings)
    refund_tx = frappe.new_doc("MTN MoMo Transaction")
    refund_tx.update(
        {
            "settings": settings_doc.name,
            "transaction_type": "Refund",
            "direction": "Out",
            "status": "Queued",
            "amount": flt(amount or original.amount),
            "currency": original.currency or settings_doc.currency,
            "request_reference_id": make_uuid(),
            "external_id": make_uuid(),
            "reference_doctype": original.reference_doctype,
            "reference_name": original.reference_name,
            "refund_reference_id": original.request_reference_id,
            "party_type": original.party_type,
            "party": original.party,
            "mode_of_payment": original.mode_of_payment,
            "company": original.company,
            "sandbox": settings_doc.is_sandbox,
            "next_poll_at": next_poll_after(5),
        }
    )
    refund_tx.insert(ignore_permissions=True)
    client = MTNMoMoClient(settings_doc)
    callback_url = build_callback_url(
        settings_doc,
        "mtn_momo_payments.api.webhooks.refund_callback",
        refund_tx.request_reference_id,
    )
    payload = {
        "amount": str(refund_tx.amount),
        "currency": refund_tx.currency,
        "externalId": refund_tx.external_id,
        "payerMessage": payer_message or "ERPNext refund",
        "payeeNote": payee_note or "MTN MoMo refund",
        "referenceIdToRefund": original.request_reference_id,
    }
    response = client.refund(refund_tx.request_reference_id, payload, callback_url=callback_url)
    refund_tx.db_set("api_response", safe_json_dumps(response), update_modified=False)
    refund_tx.db_set("status", "Pending", update_modified=False)
    return {"transaction": refund_tx.name, "reference_id": refund_tx.request_reference_id, "status": "Pending"}


def _poll_refund_transaction(tx):
    settings_doc = frappe.get_doc("MTN MoMo Settings", tx.settings)
    client = MTNMoMoClient(settings_doc)
    payload = client.get_refund_status(tx.request_reference_id)
    return apply_status_payload(tx, payload)
