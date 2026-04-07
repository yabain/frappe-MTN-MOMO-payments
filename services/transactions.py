from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import now_datetime

from frappe_mtn_momo_payments.services.reconciliation import create_payment_entry_for_transaction
from frappe_mtn_momo_payments.utils.helpers import extract_request_status, next_poll_after, safe_json_dumps


def apply_status_payload(tx, payload: dict[str, Any], source: str = "poll"):
    status, reason = extract_request_status(payload)
    tx.db_set("momo_status", payload.get("status") or payload.get("financialTransactionStatus") or "", update_modified=False)
    tx.db_set("reason", reason, update_modified=False)
    tx.db_set("status_payload", safe_json_dumps(payload), update_modified=False)
    tx.db_set("last_polled_at", now_datetime(), update_modified=False)
    tx.db_set("status", status, update_modified=False)
    if status == "Success":
        create_payment_entry_for_transaction(tx.name)
    elif status in {"Pending", "Queued", "Processing"}:
        tx.db_set("next_poll_at", next_poll_after(10), update_modified=False)
    return status


def apply_callback_payload(tx, payload: dict[str, Any]):
    tx.db_set("webhook_payload", safe_json_dumps(payload), update_modified=False)
    return apply_status_payload(tx, payload, source="callback")
