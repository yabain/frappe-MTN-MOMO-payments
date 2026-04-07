from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from mtn_momo_payments.api.disbursement import _poll_disbursement_transaction, _transfer
from mtn_momo_payments.utils.helpers import normalize_phone_number


class MTNMoMoPayoutBatch(Document):
    def autoname(self):
        self.name = f"MTN-PAYOUT-{frappe.generate_hash(length=8).upper()}"

    def validate(self):
        total = 0
        for row in self.references:
            total += flt(row.amount)
        self.total_amount = total

    def on_submit(self):
        if self.auto_submit_on_submit:
            self.initiate_transfers()

    @frappe.whitelist()
    def initiate_transfers(self):
        settings_doc = frappe.get_doc("MTN MoMo Settings", self.settings)
        success = 0
        failed = 0
        for row in self.references:
            if row.transaction:
                continue
            try:
                tx = frappe.new_doc("MTN MoMo Transaction")
                tx.update(
                    {
                        "settings": settings_doc.name,
                        "transaction_type": "Transfer",
                        "direction": "Out",
                        "status": "Queued",
                        "amount": row.amount,
                        "currency": row.currency or settings_doc.currency,
                        "payee_party_id_type": "MSISDN",
                        "payee_party_id": normalize_phone_number(row.recipient_mobile, settings_doc.country_code),
                        "request_reference_id": frappe.generate_hash(length=36),
                        "external_id": row.external_id or frappe.generate_hash(length=10),
                        "reference_doctype": row.reference_doctype,
                        "reference_name": row.reference_name,
                        "party_type": row.party_type,
                        "party": row.party,
                        "mode_of_payment": self.mode_of_payment or settings_doc.mode_of_payment,
                        "company": self.company or settings_doc.company,
                        "sandbox": settings_doc.is_sandbox,
                        "disbursement_batch": self.name,
                    }
                )
                tx.insert(ignore_permissions=True)
                _transfer(tx, payer_message=self.remarks or "ERPNext payout batch", payee_note=row.recipient_name or "Payout")
                row.db_set("transaction", tx.name, update_modified=False)
                row.db_set("status", "Pending", update_modified=False)
                success += 1
            except Exception:
                failed += 1
                row.db_set("status", "Failed", update_modified=False)
                row.db_set("reason", frappe.get_traceback(), update_modified=False)
                frappe.log_error(frappe.get_traceback(), f"MTN MoMo Payout Row {row.name}")
        self.db_set("status", "Pending" if success and not failed else "Partial" if success else "Failed", update_modified=False)
        self.db_set("last_sync_at", now_datetime(), update_modified=False)
        return {"success": success, "failed": failed}

    @frappe.whitelist()
    def update_transfer_statuses(self):
        paid = 0
        failed = 0
        pending = 0
        for row in self.references:
            if not row.transaction:
                pending += 1
                continue
            tx = frappe.get_doc("MTN MoMo Transaction", row.transaction)
            if tx.status in {"Queued", "Pending", "Processing"}:
                _poll_disbursement_transaction(tx)
                tx.reload()
            row.db_set("status", tx.status, update_modified=False)
            row.db_set("reason", tx.reason, update_modified=False)
            row.db_set("payment_entry", tx.payment_entry, update_modified=False)
            if tx.status == "Success":
                paid += 1
            elif tx.status in {"Failed", "Rejected", "Timeout"}:
                failed += 1
            else:
                pending += 1
        if paid and not failed and not pending:
            status = "Paid"
        elif paid and (failed or pending):
            status = "Partial"
        elif failed and not paid and not pending:
            status = "Failed"
        else:
            status = "Pending"
        self.db_set("status", status, update_modified=False)
        self.db_set("last_sync_at", now_datetime(), update_modified=False)
        return status
