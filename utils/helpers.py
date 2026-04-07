from __future__ import annotations

import json
import re
import uuid
from typing import Any

import frappe
from frappe.utils import add_to_date, get_url, now_datetime


SUCCESS_STATUSES = {"SUCCESSFUL", "SUCCESS", "COMPLETED"}
FAILED_STATUSES = {"FAILED", "FAIL", "ERROR"}
REJECTED_STATUSES = {"REJECTED", "DECLINED", "CANCELLED"}
PENDING_STATUSES = {"PENDING", "ONGOING", "IN_PROGRESS", "PROCESSING"}
TIMEOUT_STATUSES = {"TIMEOUT", "TIMED_OUT"}


def make_uuid() -> str:
    return str(uuid.uuid4())


def safe_json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, default=str, ensure_ascii=False, indent=2)
    except Exception:
        return str(value)


def coerce_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    try:
        return json.loads(value)
    except Exception:
        return {"raw": str(value)}


def normalize_phone_number(phone: str | None, country_code: str = "237") -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return ""
    if digits.startswith(country_code):
        return digits
    if digits.startswith("00"):
        digits = digits[2:]
        if digits.startswith(country_code):
            return digits
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    if len(digits) <= 9:
        return f"{country_code}{digits}"
    return digits


def callback_token(settings_name: str) -> str:
    return frappe.generate_hash(f"mtn-callback-{settings_name}", 12)


def build_callback_url(settings_doc, route: str, reference_id: str) -> str:
    secret = settings_doc.get_password("callback_secret") or settings_doc.callback_secret or ""
    return (
        f"{get_url()}/api/method/{route}"
        f"?settings={settings_doc.name}&reference_id={reference_id}&token={secret}"
    )


def map_status(raw_status: str | None) -> str:
    status = (raw_status or "").strip().upper()
    if status in SUCCESS_STATUSES:
        return "Success"
    if status in FAILED_STATUSES:
        return "Failed"
    if status in REJECTED_STATUSES:
        return "Rejected"
    if status in TIMEOUT_STATUSES:
        return "Timeout"
    if status in PENDING_STATUSES:
        return "Pending"
    if not status:
        return "Pending"
    return status.title()


def status_needs_poll(status: str | None) -> bool:
    return (status or "").strip() in {"Queued", "Pending", "Processing"}


def next_poll_after(minutes: int = 10):
    return add_to_date(now_datetime(), minutes=minutes, as_datetime=True)


def get_enabled_settings(company: str | None = None):
    filters = {"enabled": 1}
    if company:
        filters["company"] = company
    name = frappe.db.get_value("MTN MoMo Settings", filters, "name")
    if not name:
        frappe.throw("No enabled MTN MoMo Settings found.")
    return frappe.get_doc("MTN MoMo Settings", name)


def extract_request_status(payload: dict[str, Any]) -> tuple[str, str]:
    for key in ("status", "financialTransactionStatus", "reason"):
        if key in payload:
            pass
    raw_status = payload.get("status") or payload.get("financialTransactionStatus") or payload.get("reason")
    reason = payload.get("reason") or payload.get("statusReason") or payload.get("message") or ""
    return map_status(raw_status), str(reason or "")
