# Full Stack Developer (3) — Recovered Conversation Excerpt

## 1. Existing test_orders.py

User shared the existing tests from tests/test_orders.py, including:
- test_order_totals_with_tax
- test_coupon_takes_ten_percent
- test_out_of_stock
- test_payment_marks_order_paid
- test_duplicate_payment_event_is_not_counted_twice
- test_cancel_paid_order_restocks
- test_daily_sales
- test_price_change

The duplicate payment test checks that processing the same event twice records only one payment.

## 2. Investigating Report 2

Assistant:
Your existing tests confirm that paid orders return stock when cancelled, but there is no test for cancelling a pending order.

That is the missing scenario we need to investigate. An abandoned checkout can leave an order in pending status, so let's write a regression test first.

## 3. Regression test to add

Add this test above test_cancel_paid_order_restocks in tests/test_orders.py:

    def test_cancel_pending_order_restocks(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        self.assertEqual(self.app.catalog.get_product("MUG").stock, 9)

        self.app.orders.cancel(order["id"])

        self.assertEqual(self.app.catalog.get_product("MUG").stock, 10)

## 4. Run the test

Command:

python -m unittest tests.test_orders.OrderDeskTest.test_cancel_pending_order_restocks -v

Expected result:
The test should fail because the current cancel() method returns stock only for paid orders.

Assistant instruction:
Do not change orders.py yet. Share the test output to confirm the failure before fixing it.

Note: This is a recovered excerpt, not the complete original chat transcript.
