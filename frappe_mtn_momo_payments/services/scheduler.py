from __future__ import annotations

import frappe
from frappe.utils import now_datetime

from frappe_mtn_momo_payments.api.collections import _poll_collection_transaction
from frappe_mtn_momo_payments.api.disbursement import _poll_disbursement_transaction, _poll_refund_transaction


def poll_pending_transactions() -> None:
    names = frappe.get_all(
        "MTN MoMo Transaction",
        filters={
            "status": ["in", ["Queued", "Pending", "Processing"]],
            "next_poll_at": ["<=", now_datetime()],
        },
        pluck="name",
        limit=100,
    )
    for name in names:
        try:
            tx = frappe.get_doc("MTN MoMo Transaction", name)
            if tx.transaction_type == "Collection":
                _poll_collection_transaction(tx)
            elif tx.transaction_type == "Transfer":
                _poll_disbursement_transaction(tx)
            elif tx.transaction_type == "Refund":
                _poll_refund_transaction(tx)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"MTN MoMo Poll Transaction {name}")


def poll_pending_payout_batches() -> None:
    names = frappe.get_all(
        "MTN MoMo Payout Batch",
        filters={"docstatus": 1, "status": ["in", ["Queued", "Partial", "Pending"]]},
        pluck="name",
        limit=50,
    )
    for name in names:
        try:
            doc = frappe.get_doc("MTN MoMo Payout Batch", name)
            doc.update_transfer_statuses()
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"MTN MoMo Poll Batch {name}")
