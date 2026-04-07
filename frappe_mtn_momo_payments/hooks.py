app_name = "frappe_mtn_momo_payments"
app_title = "MTN MoMo Payments"
app_publisher = "OpenAI"
app_description = "MTN Mobile Money Cameroon integration for ERPNext"
app_email = "support@example.com"
app_license = "mit"
required_apps = ["erpnext"]

after_install = "frappe_mtn_momo_payments.install.after_install"

doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
    "Sales Order": "public/js/sales_order.js",
    "Payment Request": "public/js/payment_request.js",
}

scheduler_events = {
    "cron": {
        "*/10 * * * *": [
            "frappe_mtn_momo_payments.services.scheduler.poll_pending_transactions",
            "frappe_mtn_momo_payments.services.scheduler.poll_pending_payout_batches",
        ]
    }
}
