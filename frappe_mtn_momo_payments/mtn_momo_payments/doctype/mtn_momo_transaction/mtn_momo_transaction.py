from __future__ import annotations

import frappe
from frappe.model.document import Document


class MTNMoMoTransaction(Document):
    def autoname(self):
        self.name = f"MTN-TXN-{frappe.generate_hash(length=10).upper()}"
