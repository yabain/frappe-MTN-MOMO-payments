from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

WORKSPACE_TITLE = "MTN MoMo Payments"
WORKSPACE_MODULE = "MTN MoMo Payments"
APP_NAME = "mtn_momo_payments"


def after_install() -> None:
    ensure_custom_fields()
    ensure_workspace()
    frappe.db.commit()


def ensure_custom_fields() -> None:
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


def _workspace_content() -> str:
    blocks = [
        {"type": "header", "data": {"text": "Configuration", "level": 4, "col": 12}},
        {"type": "shortcut", "data": {"shortcut_name": "MTN MoMo Settings", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "MTN MoMo Transaction", "col": 4}},
        {"type": "shortcut", "data": {"shortcut_name": "MTN MoMo Payout Batch", "col": 4}},
        {"type": "spacer", "data": {"col": 12}},
        {"type": "header", "data": {"text": "Operations", "level": 4, "col": 12}},
        {"type": "card", "data": {"card_name": "MTN MoMo", "col": 4}},
    ]
    return json.dumps(blocks)


def _workspace_links() -> list[dict]:
    return [
        {
            "label": "MTN MoMo",
            "type": "Card Break",
            "hidden": 0,
            "is_query_report": 0,
            "link_count": 0,
            "onboard": 0,
        },
        {
            "label": "MTN MoMo Settings",
            "type": "Link",
            "link_type": "DocType",
            "link_to": "MTN MoMo Settings",
            "hidden": 0,
            "is_query_report": 0,
            "link_count": 0,
            "onboard": 0,
            "dependencies": "",
        },
        {
            "label": "MTN MoMo Transaction",
            "type": "Link",
            "link_type": "DocType",
            "link_to": "MTN MoMo Transaction",
            "hidden": 0,
            "is_query_report": 0,
            "link_count": 0,
            "onboard": 0,
            "dependencies": "",
        },
        {
            "label": "MTN MoMo Payout Batch",
            "type": "Link",
            "link_type": "DocType",
            "link_to": "MTN MoMo Payout Batch",
            "hidden": 0,
            "is_query_report": 0,
            "link_count": 0,
            "onboard": 0,
            "dependencies": "",
        },
    ]


def ensure_workspace() -> None:
    if not frappe.db.exists("DocType", "Workspace"):
        return

    meta = frappe.get_meta("Workspace")
    fieldnames = {df.fieldname for df in meta.fields}

    values = {
        "label": WORKSPACE_TITLE,
        "title": WORKSPACE_TITLE,
        "module": WORKSPACE_MODULE,
        "public": 1,
        "is_hidden": 0,
        "content": _workspace_content(),
        "sequence_id": 90,
        "for_user": "",
        "parent_page": "",
        "restrict_to_domain": "",
        "icon": "payment-gateway",
        "app": APP_NAME,
    }

    if frappe.db.exists("Workspace", WORKSPACE_TITLE):
        doc = frappe.get_doc("Workspace", WORKSPACE_TITLE)
    else:
        doc = frappe.new_doc("Workspace")
        doc.name = WORKSPACE_TITLE

    for key, value in values.items():
        if key in fieldnames:
            setattr(doc, key, value)

    if "links" in fieldnames:
        doc.set("links", [])
        for link in _workspace_links():
            doc.append("links", link)

    if not getattr(doc, "name", None):
        doc.name = WORKSPACE_TITLE

    if getattr(doc, "is_new", lambda: False)():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

    frappe.clear_cache()
