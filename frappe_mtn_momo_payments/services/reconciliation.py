from __future__ import annotations

import frappe
from frappe.utils import flt, nowdate


def _erpnext_available() -> bool:
    try:
        import erpnext  # noqa: F401
        return True
    except Exception:
        return False


def _resolve_party_from_reference(tx):
    if tx.party_type and tx.party:
        return tx.party_type, tx.party
    if not tx.reference_doctype or not tx.reference_name:
        return None, None
    ref = frappe.get_doc(tx.reference_doctype, tx.reference_name)
    if tx.reference_doctype in {"Sales Invoice", "Sales Order"}:
        return "Customer", getattr(ref, "customer", None)
    if tx.reference_doctype in {"Purchase Invoice", "Purchase Order"}:
        return "Supplier", getattr(ref, "supplier", None)
    return None, None


def _build_manual_payment_entry(tx, settings_doc, payment_type: str):
    pe = frappe.new_doc("Payment Entry")
    pe.payment_type = payment_type
    pe.company = tx.company or settings_doc.company
    pe.mode_of_payment = tx.mode_of_payment or settings_doc.mode_of_payment
    pe.reference_no = tx.request_reference_id
    pe.reference_date = nowdate()
    pe.party_type, pe.party = _resolve_party_from_reference(tx)
    amount = flt(tx.amount)

    if payment_type == "Receive":
        pe.paid_amount = amount
        pe.received_amount = amount
        pe.paid_to = settings_doc.received_account
        if not pe.party_type:
            pe.party_type = "Customer"
    else:
        pe.paid_amount = amount
        pe.received_amount = amount
        pe.paid_from = settings_doc.disbursement_account
        if not pe.party_type:
            pe.party_type = "Supplier"

    if tx.reference_doctype and tx.reference_name and tx.reference_doctype in {"Sales Invoice", "Purchase Invoice"}:
        pe.append(
            "references",
            {
                "reference_doctype": tx.reference_doctype,
                "reference_name": tx.reference_name,
                "allocated_amount": amount,
                "total_amount": amount,
                "outstanding_amount": amount,
            },
        )
    return pe


def create_payment_entry_for_transaction(tx_name: str) -> str | None:
    if not _erpnext_available():
        return None

    tx = frappe.get_doc("MTN MoMo Transaction", tx_name)
    if tx.payment_entry or tx.status != "Success":
        return tx.payment_entry

    settings_doc = frappe.get_doc("MTN MoMo Settings", tx.settings)
    if not settings_doc.auto_create_payment_entry:
        return None

    try:
        payment_type = "Receive" if tx.direction == "In" else "Pay"
        pe = _build_manual_payment_entry(tx, settings_doc, payment_type)
        pe.insert(ignore_permissions=True)
        pe.submit()
        tx.db_set("payment_entry", pe.name, update_modified=False)
        tx.db_set("is_reconciled", 1, update_modified=False)
        return pe.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "MTN MoMo Payment Entry Creation")
        return None
