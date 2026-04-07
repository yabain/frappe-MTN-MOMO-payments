from __future__ import annotations

import base64
from typing import Any

import requests
import frappe
from frappe.utils import add_to_date, now_datetime

from frappe_mtn_momo_payments.utils.helpers import safe_json_dumps


class MTNMoMoClient:
    def __init__(self, settings_doc):
        self.settings = settings_doc
        self.timeout = 45

    def _base_url(self, product: str) -> str:
        if product == "collection":
            return (self.settings.collection_base_url or "https://sandbox.momodeveloper.mtn.com").rstrip("/")
        if product == "disbursement":
            return (self.settings.disbursement_base_url or "https://sandbox.momodeveloper.mtn.com").rstrip("/")
        return (self.settings.provisioning_base_url or "https://sandbox.momodeveloper.mtn.com").rstrip("/")

    def _target_environment(self) -> str:
        return (self.settings.target_environment or ("sandbox" if self.settings.is_sandbox else "")).strip()

    def _subscription_key(self, product: str) -> str:
        if product == "collection":
            return self.settings.get_password("collection_subscription_key") or self.settings.collection_subscription_key or ""
        return self.settings.get_password("disbursement_subscription_key") or self.settings.disbursement_subscription_key or ""

    def _api_user(self) -> str:
        return (self.settings.api_user or "").strip()

    def _api_key(self) -> str:
        return self.settings.get_password("api_key") or self.settings.api_key or ""

    def _headers(self, product: str, include_auth: bool = True, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": self._subscription_key(product),
        }
        env = self._target_environment()
        if env:
            headers["X-Target-Environment"] = env
        if include_auth:
            headers["Authorization"] = f"Bearer {self.get_access_token(product)}"
        if extra:
            headers.update({k: v for k, v in extra.items() if v is not None and v != ""})
        return headers

    def _request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        auth: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers or {},
                json=payload,
                auth=auth,
                timeout=self.timeout,
            )
            try:
                data = response.json() if response.text else {}
            except Exception:
                data = {"raw": response.text}
            if response.status_code >= 400:
                frappe.throw(
                    f"MTN MoMo API error {response.status_code}: {safe_json_dumps(data)}"
                )
            return data
        except requests.RequestException as exc:
            frappe.throw(f"Unable to reach MTN MoMo API: {exc}")

    def provision_api_user(self, reference_id: str) -> dict[str, Any]:
        payload = {"providerCallbackHost": self.settings.provider_callback_host}
        headers = {
            "X-Reference-Id": reference_id,
            "Ocp-Apim-Subscription-Key": self._subscription_key("collection"),
            "Content-Type": "application/json",
        }
        return self._request(
            "POST",
            f"{self._base_url('provisioning')}/v1_0/apiuser",
            headers=headers,
            payload=payload,
        )

    def provision_api_key(self, api_user: str | None = None) -> dict[str, Any]:
        api_user = api_user or self._api_user()
        headers = {
            "Ocp-Apim-Subscription-Key": self._subscription_key("collection"),
        }
        return self._request(
            "POST",
            f"{self._base_url('provisioning')}/v1_0/apiuser/{api_user}/apikey",
            headers=headers,
        )

    def get_access_token(self, product: str) -> str:
        now = now_datetime()
        if product == "collection":
            token = self.settings.collection_access_token
            expires = self.settings.collection_token_expires_at
        else:
            token = self.settings.disbursement_access_token
            expires = self.settings.disbursement_token_expires_at
        if token and expires and expires > now:
            return token

        auth = (self._api_user(), self._api_key())
        headers = {
            "Ocp-Apim-Subscription-Key": self._subscription_key(product),
        }
        data = self._request(
            "POST",
            f"{self._base_url(product)}/{product}/token/",
            headers=headers,
            auth=auth,
        )
        token = data.get("access_token")
        expires_in = int(data.get("expires_in") or 3600)
        expires_at = add_to_date(now, seconds=max(60, expires_in - 60), as_datetime=True)
        if product == "collection":
            self.settings.db_set("collection_access_token", token, update_modified=False)
            self.settings.db_set("collection_token_expires_at", expires_at, update_modified=False)
        else:
            self.settings.db_set("disbursement_access_token", token, update_modified=False)
            self.settings.db_set("disbursement_token_expires_at", expires_at, update_modified=False)
        return token

    def request_to_pay(self, reference_id: str, payload: dict[str, Any], callback_url: str | None = None) -> dict[str, Any]:
        headers = self._headers(
            "collection",
            extra={
                "X-Reference-Id": reference_id,
                "X-Callback-Url": callback_url or "",
            },
        )
        return self._request(
            "POST",
            f"{self._base_url('collection')}/collection/v1_0/requesttopay",
            headers=headers,
            payload=payload,
        )

    def get_request_to_pay_status(self, reference_id: str) -> dict[str, Any]:
        headers = self._headers("collection")
        return self._request(
            "GET",
            f"{self._base_url('collection')}/collection/v1_0/requesttopay/{reference_id}",
            headers=headers,
        )

    def send_delivery_notification(self, reference_id: str, notification_message: str) -> dict[str, Any]:
        headers = self._headers("collection")
        return self._request(
            "POST",
            f"{self._base_url('collection')}/collection/v1_0/requesttopay/{reference_id}/deliverynotification",
            headers=headers,
            payload={"notificationMessage": notification_message},
        )

    def transfer(self, reference_id: str, payload: dict[str, Any], callback_url: str | None = None) -> dict[str, Any]:
        headers = self._headers(
            "disbursement",
            extra={
                "X-Reference-Id": reference_id,
                "X-Callback-Url": callback_url or "",
            },
        )
        return self._request(
            "POST",
            f"{self._base_url('disbursement')}/disbursement/v1_0/transfer",
            headers=headers,
            payload=payload,
        )

    def get_transfer_status(self, reference_id: str) -> dict[str, Any]:
        headers = self._headers("disbursement")
        return self._request(
            "GET",
            f"{self._base_url('disbursement')}/disbursement/v1_0/transfer/{reference_id}",
            headers=headers,
        )

    def refund(self, reference_id: str, payload: dict[str, Any], callback_url: str | None = None) -> dict[str, Any]:
        headers = self._headers(
            "disbursement",
            extra={
                "X-Reference-Id": reference_id,
                "X-Callback-Url": callback_url or "",
            },
        )
        return self._request(
            "POST",
            f"{self._base_url('disbursement')}/disbursement/v1_0/refund",
            headers=headers,
            payload=payload,
        )

    def get_refund_status(self, reference_id: str) -> dict[str, Any]:
        headers = self._headers("disbursement")
        return self._request(
            "GET",
            f"{self._base_url('disbursement')}/disbursement/v1_0/refund/{reference_id}",
            headers=headers,
        )

    def get_balance(self, product: str = "collection") -> dict[str, Any]:
        headers = self._headers(product)
        return self._request(
            "GET",
            f"{self._base_url(product)}/{product}/v1_0/account/balance",
            headers=headers,
        )
