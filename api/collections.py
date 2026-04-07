from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt

from frappe_mtn_momo_payments.services.client import MTNMoMoClient
from frappe_mtn_momo_payments.services.transactions import apply_status_payload
from frappe_mtn_momo_payments.utils.helpers import (
    build_callback_url,
    get_enabled_settings,
    make_uuid,
    next_poll_after,
    normalize_phone_number,
    safe_json_dumps,
)


def _make_collection_tx(settings_doc, amount, phone_number, reference_doctype=None, reference_name=None, party_type=None, party=None, mode_of_payment=None, company=None):
    tx = frappe.new_doc("MTN MoMo Transaction")
    tx.update(
        {
            "settings": settings_doc.name,
            "transaction_type": "Collection",
            "direction": "In",
            "status": "Queued",
            "amount": flt(amount),
            "currency": settings_doc.currency,
            "payer_party_id_type": "MSISDN",
            "payer_party_id": phone_number,
            "request_reference_id": make_uuid(),
            "external_id": make_uuid(),
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "party_type": party_type,
            "party": party,
            "mode_of_payment": mode_of_payment or settings_doc.mode_of_payment,
            "company": company or settings_doc.company,
            "sandbox": settings_doc.is_sandbox,
            "next_poll_at": next_poll_after(5),
        }
    )
    tx.insert(ignore_permissions=True)
    return tx


def _resolve_reference(reference_doctype: str | None, reference_name: str | None):
    if not reference_doctype or not reference_name:
        return None
    return frappe.get_doc(reference_doctype, reference_name)


def _reference_context(reference_doctype: str | None, reference_name: str | None) -> dict[str, Any]:
    ref = _resolve_reference(reference_doctype, reference_name)
    if not ref:
        return {}
    out = {
        "company": getattr(ref, "company", None),
        "party_type": None,
        "party": None,
        "amount": getattr(ref, "outstanding_amount", None)
        or getattr(ref, "rounded_total", None)
        or getattr(ref, "grand_total", None)
        or getattr(ref, "base_grand_total", None),
        "phone_number": None,
    }
    if reference_doctype in {"Sales Invoice", "Sales Order"}:
        out["party_type"] = "Customer"
        out["party"] = getattr(ref, "customer", None)
        customer = out["party"]
        if customer:
            out["phone_number"] = (
                frappe.db.get_value("Customer", customer, "mtn_momo_mobile_number")
                or frappe.db.get_value("Customer", customer, "mobile_no")
            )
    if reference_doctype == "Payment Request":
        out["party_type"] = getattr(ref, "party_type", None) or "Customer"
        out["party"] = getattr(ref, "party", None)
        out["amount"] = getattr(ref, "grand_total", None) or getattr(ref, "outstanding_amount", None)
    return out


def _request_to_pay(tx, payer_message: str = "ERPNext payment request", payee_note: str = "ERPNext payment request"):
    settings_doc = frappe.get_doc("MTN MoMo Settings", tx.settings)
    client = MTNMoMoClient(settings_doc)
    callback_url = build_callback_url(
        settings_doc,
        "frappe_mtn_momo_payments.api.webhooks.collection_callback",
        tx.request_reference_id,
    )
    payload = {
        "amount": str(tx.amount),
        "currency": tx.currency,
        "externalId": tx.external_id,
        "payer": {
            "partyIdType": tx.payer_party_id_type or "MSISDN",
            "partyId": tx.payer_party_id,
        },
        "payerMessage": payer_message,
        "payeeNote": payee_note,
    }
    response = client.request_to_pay(tx.request_reference_id, payload, callback_url=callback_url)
    tx.db_set("api_response", safe_json_dumps(response), update_modified=False)
    tx.db_set("status", "Pending", update_modified=False)
    tx.db_set("next_poll_at", next_poll_after(5), update_modified=False)
    return tx


@frappe.whitelist()
def request_payment_for_reference(
    settings: str | None = None,
    reference_doctype: str | None = None,
    reference_name: str | None = None,
    phone_number: str | None = None,
    amount: float | None = None,
    payer_message: str | None = None,
    payee_note: str | None = None,
):
    ctx = _reference_context(reference_doctype, reference_name)
    settings_doc = frappe.get_doc("MTN MoMo Settings", settings) if settings else get_enabled_settings(ctx.get("company"))
    phone_number = normalize_phone_number(phone_number or ctx.get("phone_number"), settings_doc.country_code)
    if not phone_number:
        frappe.throw("A valid customer mobile number is required.")
    amount = flt(amount or ctx.get("amount"))
    if amount <= 0:
        frappe.throw("Amount must be greater than zero.")
    tx = _make_collection_tx(
        settings_doc,
        amount,
        phone_number,
        reference_doctype=reference_doctype,
        reference_name=reference_name,
        party_type=ctx.get("party_type"),
        party=ctx.get("party"),
        company=ctx.get("company"),
    )
    _request_to_pay(tx, payer_message or "ERPNext payment request", payee_note or "MTN MoMo collection")
    return {
        "transaction": tx.name,
        "reference_id": tx.request_reference_id,
        "status": "Pending",
    }


@frappe.whitelist()
def request_payment(
    settings: str,
    phone_number: str,
    amount: float,
    reference_doctype: str | None = None,
    reference_name: str | None = None,
    party_type: str | None = None,
    party: str | None = None,
    payer_message: str | None = None,
    payee_note: str | None = None,
):
    settings_doc = frappe.get_doc("MTN MoMo Settings", settings)
    phone_number = normalize_phone_number(phone_number, settings_doc.country_code)
    tx = _make_collection_tx(
        settings_doc,
        amount,
        phone_number,
        reference_doctype=reference_doctype,
        reference_name=reference_name,
        party_type=party_type,
        party=party,
    )
    _request_to_pay(tx, payer_message or "ERPNext payment request", payee_note or "MTN MoMo collection")
    return {"transaction": tx.name, "reference_id": tx.request_reference_id, "status": "Pending"}


@frappe.whitelist(allow_guest=True)
def start_web_checkout(**kwargs):
    return request_payment(**kwargs)


def _poll_collection_transaction(tx):
    settings_doc = frappe.get_doc("MTN MoMo Settings", tx.settings)
    client = MTNMoMoClient(settings_doc)
    payload = client.get_request_to_pay_status(tx.request_reference_id)
    return apply_status_payload(tx, payload)


@frappe.whitelist()
def get_collection_status(transaction: str):
    tx = frappe.get_doc("MTN MoMo Transaction", transaction)
    status = _poll_collection_transaction(tx)
    tx.reload()
    return {"status": status, "reason": tx.reason, "payment_entry": tx.payment_entry}


@frappe.whitelist()
def send_delivery_notification(transaction: str, notification_message: str):
    tx = frappe.get_doc("MTN MoMo Transaction", transaction)
    settings_doc = frappe.get_doc("MTN MoMo Settings", tx.settings)
    client = MTNMoMoClient(settings_doc)
    return client.send_delivery_notification(tx.request_reference_id, notification_message)
