from __future__ import annotations

import frappe
from frappe.model.document import Document

from mtn_momo_payments.services.client import MTNMoMoClient
from mtn_momo_payments.utils.helpers import callback_token


class MTNMoMoSettings(Document):
    def validate(self):
        self.currency = self.currency or "XAF"
        self.country_code = self.country_code or "237"
        self.collection_base_url = self.collection_base_url or "https://sandbox.momodeveloper.mtn.com"
        self.disbursement_base_url = self.disbursement_base_url or "https://sandbox.momodeveloper.mtn.com"
        self.provisioning_base_url = self.provisioning_base_url or "https://sandbox.momodeveloper.mtn.com"
        self.target_environment = self.target_environment or ("sandbox" if self.is_sandbox else self.target_environment)
        self.provider_callback_host = (self.provider_callback_host or frappe.utils.get_url()).replace("https://", "").replace("http://", "").split("/")[0]
        if not self.callback_secret:
            self.callback_secret = callback_token(self.name or self.gateway_name or "mtn-momo")

    def on_update(self):
        self.ensure_mode_of_payment()

    def ensure_mode_of_payment(self):
        if not self.mode_of_payment:
            mop_name = f"MTN MoMo - {self.gateway_name}"
            if not frappe.db.exists("Mode of Payment", mop_name):
                mop = frappe.get_doc(
                    {
                        "doctype": "Mode of Payment",
                        "mode_of_payment": mop_name,
                        "type": "Phone",
                        "enabled": 1,
                    }
                )
                if self.company and self.received_account:
                    mop.append(
                        "accounts",
                        {
                            "company": self.company,
                            "default_account": self.received_account,
                        },
                    )
                mop.insert(ignore_permissions=True)
            self.db_set("mode_of_payment", mop_name, update_modified=False)

    @frappe.whitelist()
    def provision_sandbox_api_user(self):
        client = MTNMoMoClient(self)
        reference_id = frappe.generate_hash(length=36)
        response = client.provision_api_user(reference_id)
        self.db_set("api_user", reference_id, update_modified=False)
        return response

    @frappe.whitelist()
    def provision_sandbox_api_key(self):
        client = MTNMoMoClient(self)
        response = client.provision_api_key(self.api_user)
        api_key = response.get("apiKey") if isinstance(response, dict) else None
        if api_key:
            self.db_set("api_key", api_key, update_modified=False)
        return response

    @frappe.whitelist()
    def refresh_collection_token(self):
        return {"access_token": MTNMoMoClient(self).get_access_token("collection")}

    @frappe.whitelist()
    def refresh_disbursement_token(self):
        return {"access_token": MTNMoMoClient(self).get_access_token("disbursement")}

    @frappe.whitelist()
    def get_collection_balance(self):
        payload = MTNMoMoClient(self).get_balance("collection")
        self.db_set("last_balance_payload", frappe.as_json(payload), update_modified=False)
        return payload

    @frappe.whitelist()
    def get_disbursement_balance(self):
        payload = MTNMoMoClient(self).get_balance("disbursement")
        self.db_set("last_balance_payload", frappe.as_json(payload), update_modified=False)
        return payload
