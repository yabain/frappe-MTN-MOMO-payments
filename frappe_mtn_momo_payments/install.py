from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install() -> None:
    create_custom_fields(
        {
            "Customer": [
                {
                    "fieldname": "mtn_momo_mobile_number",
                    "label": "MTN MoMo Mobile Number",
                    "fieldtype": "Data",
                    "insert_after": "mobile_no",
                }
            ],
            "Supplier": [
                {
                    "fieldname": "mtn_momo_mobile_number",
                    "label": "MTN MoMo Mobile Number",
                    "fieldtype": "Data",
                    "insert_after": "mobile_no",
                }
            ],
        },
        update=True,
    )
    frappe.db.commit()
