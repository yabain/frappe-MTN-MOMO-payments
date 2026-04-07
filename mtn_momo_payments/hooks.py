app_name = "mtn_momo_payments"
app_title = "MTN MoMo Payments"
app_publisher = "OpenAI"
app_description = "MTN Mobile Money Cameroon integration for ERPNext"
app_email = "support@example.com"
app_license = "mit"
required_apps = ["erpnext"]

after_install = "mtn_momo_payments.install.after_install"
after_migrate = "mtn_momo_payments.migrate.after_migrate"

doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
    "Sales Order": "public/js/sales_order.js",
    "Payment Request": "public/js/payment_request.js",
}

scheduler_events = {
    "cron": {
        "*/10 * * * *": [
            "mtn_momo_payments.services.scheduler.poll_pending_transactions",
            "mtn_momo_payments.services.scheduler.poll_pending_payout_batches",
        ]
    }
}

add_to_apps_screen = [
    {
        "name": "mtn_momo_payments",
        "logo": "/assets/mtn_momo_payments/images/icon.svg",
        "title": "MTN MoMo Payments",
        "route": "/app/mtn-momo-payments",
    }
]
