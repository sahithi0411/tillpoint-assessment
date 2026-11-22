# NOTES

Fill in every field below before you submit. We read this file first: a submission with an empty field is not graded.
Write in your own words. If you did not fix something, set Status to `not fixed` and say what you found and tried; that still counts.
Status is one of: `fixed`, `partly fixed`, `not fixed`. Commits: the short hashes of the commits for this item, or `none`.

## 1. Report

> Finance says that on some days the revenue in the daily report is higher than what the payment provider paid out, and a few orders show more money received than their total.

Status: partly fixed

What I saw: When the same payment webhook event was received multiple times, the application could insert duplicate payment records for the same order. This caused the received amount and daily report revenue to become higher than expected.

Root cause: The payments table did not prevent duplicate event IDs. The webhook handler inserted a payment record every time it received an event, even when that event had already been processed.

Fix and why: Added a unique index on payments.event_id and used ON CONFLICT(event_id) DO NOTHING when inserting payments. This prevents the same webhook event from being counted more than once.

The application does not store payment-provider payout or transaction-fee information, so comparing the recorded revenue with the provider's net payout is still not supported.
How I verified it: Added test_duplicate_payment_event_is_not_counted_twice. It reproduced duplicate counting before the fix and passed after the fix. All 14 tests passed in the final test run.

Commits: d4545a5


## 2. Report

> Products show as sold out, or nearly, while the shelf is full. Staff say it gets worse on days when many customers abandon checkout.

Status: fixed

What I saw: Creating an order reserves stock immediately. When a pending order was cancelled, the reserved stock was not restored. Abandoned pending orders also continued holding stock, making products appear sold out even when the physical stock was available.

Root cause: The cancellation logic restored stock only for orders with paid status. There was also no mechanism to expire abandoned pending orders and release their reserved stock.

Fix and why: Updated the cancellation logic to restore stock for both pending and paid orders. Added a 15-minute expiry for pending orders. When a new order is created, the application checks for expired pending orders, restores their reserved stock, releases coupon usage, and marks those orders as cancelled. I chose 15 minutes because the report did not specify an expiry duration.

How I verified it: Added test_cancel_pending_order_restocks and test_expired_pending_order_restocks. These tests reproduced the stock-restoration problems before the fix and passed after the fix. All 14 tests passed in the final test run.

Commits: b09fe1d


## 3. Report

> Customers in taxed regions who used a coupon say the tax on their receipt is too high. Receipts without a coupon are right.

Status: fixed

What I saw: The application calculated sales tax using the original subtotal before applying the coupon discount. As a result, customers using coupons were charged tax on an amount higher than the discounted price.

Root cause: In pricing.py, the tax calculation happened before the coupon discount was subtracted from the subtotal.

Fix and why: Changed the calculation order so the coupon discount is subtracted first. Sales tax is now calculated on the discounted amount, and the final total is calculated by adding that tax to the discounted amount. This ensures customers are taxed on the correct amount.

How I verified it: Added test_coupon_tax_is_calculated_after_discount. Before the fix, the test failed because the tax was calculated on the original subtotal. After the fix, it passed with the expected discounted tax and total. All 14 tests passed in the final test run.

Commits: 6dd935f

## 4. Report

> Our shop in India (UTC+5:30) says sales taken in the morning do not appear in that day's report and turn up under the day before.

Status: fixed

What I saw: Transactions made during the early morning in India were not included in the correct local day's sales report because the report used UTC day boundaries instead of India local-time boundaries.

Root cause: The daily report calculation did not correctly apply the supplied UTC offset when determining the start and end of a business day.

Fix and why: Updated day_bounds_utc() in reports.py to convert the local day's start into UTC using the supplied offset. The end boundary is calculated as 24 hours after the start. This ensures transactions are grouped into the correct local business day.

How I verified it: Added test_daily_sales_uses_india_local_day. The test uses a transaction at 06:00 AM India time (00:30 UTC) and checks that it is included in the correct local day's report. It failed before the fix and passed after the fix. All 14 tests passed in the final test run.

Commits: 3ad13cf

## 5. Report

> Ever since we started running two server workers, we have sold more units of an item than we had, and its stock went negative.

Status: fixed

What I saw: The stock reservation logic could allow two order attempts to read the same available stock before either one updated it. This could result in more stock being reserved than was actually available.

Root cause: The application checked the available stock and then updated it in separate operations. The cached product information could also become outdated.

Fix and why: Updated Catalog.reserve() to use a conditional SQL UPDATE. The stock is decreased only when the database confirms that enough stock is available. If the update affects no rows, the application checks whether the product exists and raises OutOfStock when the requested quantity cannot be reserved. The product cache is also cleared after the reservation attempt to avoid stale stock information.

How I verified it: Added test_two_catalog_instances_cannot_oversell_stock. The test uses two Catalog instances with shared database access and checks that when only one item is available, the second reservation fails after the first reservation succeeds. It failed before the fix and passed after the fix. All 14 tests passed in the final test run.

Limitation: This test checks the conditional database update using two catalog instances, but it is not a full multi-process concurrency or load test.

Commits: d769ae1

## 6. Open question

> Open question from support, no single right answer: sometimes a customer really does pay twice for one order (two separate payments, not a retry of the same one). Today the system records both and says nothing. Decide what should happen, build the smallest version of your decision, and explain what it costs in `NOTES.md`.

My decision: Keep both successful payments in the payment records, mark the order as paid when the received amount reaches or exceeds the order total, and clearly report any extra amount as an overpayment for manual refund or reconciliation.

Why: Two separate successful payments are genuine transactions, not duplicate webhook deliveries. Keeping both records preserves the payment history and avoids losing financial information. Showing the overpaid amount helps staff identify orders that need attention.

What it costs: The application does not automatically refund the extra amount. Staff must manually review and reconcile overpayments. Automatic refunds would require payment-provider refund integration, which is outside the current implementation.

What I built: Added payment_summary() in payments.py to calculate the total amount received (paid_cents) and the extra amount received (overpaid_cents). Updated the payment webhook response to include this summary for successful payments.

How I verified it: Added test_two_genuine_payments_record_overpayment. The test sends two successful payments with different event IDs and checks that both payments are stored, the order is marked as paid, and the overpaid amount is returned correctly. All 14 tests passed in the final test run.

Commits: f9b1a5e


## Other things I noticed

1. Payment-provider payout amounts and transaction fees are not stored, so the application cannot fully reconcile recorded      payments with the provider's net payout.

2. Pending-order expiry is checked when a new order is created. It does not run automatically in the background.

3. Automatic refunds for genuine overpayments are not implemented because there is no payment-provider refund integration.

## Session logs

AI tools used: ChatGPT.

Session log files: TODO  add the actual full conversation export files inside session_logs/ and list each filename here.
