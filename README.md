<h1 align="center">Frappe MTN MoMo Payments (Cameroon)</h1>

<p align="center">
  <br>
  <img src="https://momo.mtn.com/wp-content/uploads/sites/15/2022/07/Group-360.png?w=360 360w, https://momo.mtn.com/wp-content/uploads/sites/15/2022/07/Group-360.png?w=150 150w, https://momo.mtn.com/wp-content/uploads/sites/15/2022/07/Group-360.png?w=300 300w" alt="logo" width="20%" />
  <br><br>
  <i>A custom Frappe / ERPNext application for <b>MTN Mobile Money Cameroon</b> built in the spirit of the
`frappe-mpsa-payments` app, but adapted to the <b>MTN MoMo Open API</b> flow.
    <br>...</i>

  <br>
</p>

<p align="center">
  <img src="https://payments.digikuntz.com/assets/img/resources/logo_gic_0.png" alt="logo Yaba-In" width="10%" />
  <img src="https://payments.digikuntz.com/assets/img/resources/logo_yaba-in.png" alt="logo Yaba-In" width="20%" />
</p>
<p align="center">By:
  <a href="https://gic.cm"><strong>GIC Promote Ltd</strong></a> & <a href="https://yaba-in.com"><strong>Yaba-In</strong></a>
  <br>
</p>


<hr>

## Documentation

Get started with ERPNext, learn the fundamentals and explore advanced topics on documentation website.

- [Getting started](https://school.frappe.io/lms/courses/introduction-to-erpnext/learn/1-1)
- [ERPNext Essentials: A Complete Training Program](https://school.frappe.io/lms/courses/erpnext-training)


## What is included

### Phase 1 — Collections
- Request To Pay (collection) from:
  - Sales Invoice
  - Sales Order
  - Payment Request
  - POS invoices (through Sales Invoice UI)
  - Website checkout page
- Collection callback endpoint
- Scheduled polling for pending payments
- Optional auto creation of ERPNext Payment Entries
- Delivery notification helper

### Phase 2 — Checkout / POS / Website
- Desk actions on Sales Invoice / Sales Order / Payment Request
- Simple website checkout page at `/mtn-momo-checkout`
- Generic whitelisted API you can call from a custom storefront

### Phase 3 — Disbursement / Refund / Reconciliation
- Transfer / payout batch doctype
- Per-row transfer initiation
- Transfer status polling
- Refund initiation and refund status polling
- Account balance helpers
- Transaction ledger doctype for auditability

## Important notes
- This app is **production-oriented scaffolding** and a strong functional baseline.
- It was built against the published MTN MoMo API patterns and the public architecture visible in
  `navariltd/frappe-mpsa-payments`, but it **has not been live-certified against your real MTN Cameroon merchant account**.
- MTN production onboarding details can vary by account, country approval, and product entitlement.
  That is why the base URLs, target environment, callback host and keys are configurable in the settings doctype.
- You must configure **HTTPS callback URLs** reachable publicly.

## Installation

```bash
cd $BENCH_PATH/apps
unzip /path/to/frappe_mtn_momo_payments.zip -d .
cd $BENCH_PATH
bench --site your-site.local install-app frappe_mtn_momo_payments
bench --site your-site.local migrate
bench restart
```

If you prefer a classic git workflow, unzip the project somewhere, move the folder into `apps/`, then install the app.

## First setup
1. Open **MTN MoMo Settings**.
2. Create one record for your Cameroon business.
3. Fill:
   - Company
   - Target Environment (`sandbox` or your production environment string from MTN)
   - Collection Subscription Key
   - Disbursement Subscription Key
   - API User
   - API Key
   - Callback host
   - Collection / Disbursement base URLs
   - Accounts and Mode of Payment
4. Save.
5. Use the helper buttons to refresh tokens / test balance.

## Default endpoints assumed by the app
The settings doctype ships with sandbox defaults:
- `https://sandbox.momodeveloper.mtn.com`

Production values are intentionally configurable because MTN production activation can differ by region/account.

## Website checkout
Visit:
- `/mtn-momo-checkout`

The page posts to the whitelisted method:
- `frappe_mtn_momo_payments.api.collections.start_web_checkout`

## Main API methods
- `frappe_mtn_momo_payments.api.collections.request_payment_for_reference`
- `frappe_mtn_momo_payments.api.collections.request_payment`
- `frappe_mtn_momo_payments.api.collections.get_collection_status`
- `frappe_mtn_momo_payments.api.disbursement.transfer_for_reference`
- `frappe_mtn_momo_payments.api.disbursement.get_disbursement_status`
- `frappe_mtn_momo_payments.api.disbursement.refund_transaction`
- `frappe_mtn_momo_payments.api.webhooks.collection_callback`
- `frappe_mtn_momo_payments.api.webhooks.disbursement_callback`
- `frappe_mtn_momo_payments.api.webhooks.refund_callback`

## What you will still likely tailor in production
- The exact `target_environment` string for Cameroon production
- Account mapping rules for your chart of accounts
- Payment Entry policy for Sales Orders / advances
- Website storefront integration specifics
- MTN production callback / entitlement validation

## License note
This project is delivered as an original app inspired by the public structure and feature ideas of the referenced M-Pesa app.
You should still perform your own legal review before distributing commercially.



## Stay in touch

- Author -  [GIC Promote Ltd ](https://gic.cm/) & [Yaba-In](https://yaba-in.com/)
- Website GIC Promote Ltd- [https://gic.cm/](https://gic.cm/)
- Website Yaba-In- [https://yaba-in.com/](https://yaba-in.com/)


**Your software solution compagny.**