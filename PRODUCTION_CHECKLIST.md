# Production checklist — MTN MoMo Cameroon

## Before first live transaction
- Confirm your MTN MoMo business account is enabled for the required products:
  - Collections / Request To Pay
  - Disbursement / Transfer
  - Refund (if needed)
- Confirm the exact production `target_environment` string supplied by MTN.
- Confirm the exact production base URLs supplied/approved for your account.
- Confirm your callback domain is public and HTTPS.
- Confirm firewall rules allow inbound callback traffic.
- Confirm your ERPNext chart of accounts mapping for:
  - received_account
  - disbursement_account
  - Mode of Payment

## Recommended first tests
1. Sandbox token generation
2. Sandbox Request To Pay
3. Sandbox callback delivery
4. Sandbox polling fallback
5. Successful Payment Entry creation
6. Sandbox disbursement test
7. Sandbox refund test

## Cameroon-specific items to verify with MTN
- Production environment code for Cameroon
- Any account-level restrictions on collection vs disbursement
- Phone number formatting expected in production
- Callback IP / hostname allow-list requirements
- Refund eligibility rules
- Balance endpoint access on your profile

## Suggested hardening tasks after installation
- Add server-side signature or IP verification if MTN provides it for your tenant
- Add rate limiting around public callback endpoints
- Add dedicated custom roles for finance / treasury users
- Add custom reports and dashboards on top of `MTN MoMo Transaction`
- Add retry policies for transfer failures based on your business rules
