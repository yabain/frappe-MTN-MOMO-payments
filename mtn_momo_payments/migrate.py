from __future__ import annotations

import frappe

from mtn_momo_payments.install import ensure_workspace


def after_migrate() -> None:
    ensure_workspace()
    frappe.db.commit()
