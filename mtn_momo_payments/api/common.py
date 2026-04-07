from __future__ import annotations

import frappe

from mtn_momo_payments.utils.helpers import get_enabled_settings


@frappe.whitelist()
def get_active_settings(company: str | None = None):
    doc = get_enabled_settings(company)
    return {
        "name": doc.name,
        "company": doc.company,
        "currency": doc.currency,
        "mode_of_payment": doc.mode_of_payment,
        "country_code": doc.country_code,
    }
