from __future__ import annotations

import frappe

from mtn_momo_payments.services.transactions import apply_callback_payload
from mtn_momo_payments.utils.helpers import coerce_json


def _validate_token(settings_name: str, token: str | None):
    settings_doc = frappe.get_doc("MTN MoMo Settings", settings_name)
    expected = settings_doc.get_password("callback_secret") or settings_doc.callback_secret or ""
    if expected and token != expected:
        frappe.throw("Invalid callback token.")
    return settings_doc


def _payload_from_request() -> dict:
    data = frappe.request.get_data() or b""
    payload = coerce_json(data)
    if not payload:
        payload = coerce_json(frappe.local.form_dict)
    return payload


def _callback(settings: str, reference_id: str, token: str | None):
    _validate_token(settings, token)
    tx_name = frappe.db.get_value("MTN MoMo Transaction", {"request_reference_id": reference_id}, "name")
    if not tx_name:
        frappe.response["http_status_code"] = 404
        return {"ok": False, "message": "Transaction not found"}
    tx = frappe.get_doc("MTN MoMo Transaction", tx_name)
    payload = _payload_from_request()
    status = apply_callback_payload(tx, payload)
    return {"ok": True, "status": status, "transaction": tx.name}


@frappe.whitelist(allow_guest=True)
def collection_callback(settings: str, reference_id: str, token: str | None = None, **kwargs):
    return _callback(settings, reference_id, token)


@frappe.whitelist(allow_guest=True)
def disbursement_callback(settings: str, reference_id: str, token: str | None = None, **kwargs):
    return _callback(settings, reference_id, token)


@frappe.whitelist(allow_guest=True)
def refund_callback(settings: str, reference_id: str, token: str | None = None, **kwargs):
    return _callback(settings, reference_id, token)
