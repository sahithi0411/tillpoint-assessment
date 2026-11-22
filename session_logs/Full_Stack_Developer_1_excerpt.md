# Full Stack Developer (1) — pasted conversation excerpt

> Scope: This file contains only the conversation excerpt pasted into ChatGPT on 22 November 2026. It is not a complete export of the original chat and must not be presented as a full session log.

## User

```python
import unittest
from datetime import datetime, timezone

from tillpoint import db, reports
from tillpoint.api import App
from tillpoint.catalog import OutOfStock


class OrderDeskTest(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect()
        self.app = App(self.conn)
        self.app.catalog.add_product("MUG", "Mug", 1200, stock=10)
        self.app.catalog.add_product("TEE", "T-shirt", 2500, stock=3)
        self.conn.execute("INSERT INTO coupons (code, kind, value) VALUES ('TEN', 'percent', 10)")

    def test_order_totals_with_tax(self):
        order = self.app.orders.create("ana", [("MUG", 2), ("TEE", 1)], region="CA")
        self.assertEqual(order["subtotal_cents"], 4900)
        self.assertEqual(order["tax_cents"], 355)
        self.assertEqual(order["total_cents"], 5255)
        self.assertEqual(self.app.catalog.get_product("MUG").stock, 8)

    def test_coupon_takes_ten_percent(self):
        order = self.app.orders.create("ana", [("MUG", 1)], coupon_code="TEN")
        self.assertEqual(order["discount_cents"], 120)
        self.assertEqual(order["total_cents"], 1080)

    def test_out_of_stock(self):
        with self.assertRaises(OutOfStock):
            self.app.orders.create("ana", [("TEE", 4)])
        self.assertEqual(self.app.catalog.get_product("TEE").stock, 3)

    def test_payment_marks_order_paid(self):
        order = self.app.orders.create("ana", [("MUG", 1)])
        event = {
            "id": "evt_duplicate",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 1200
        }

        self.app.payments.handle_event(event)
        self.app.payments.handle_event(event)

        self.assertEqual(self.app.payments.paid_cents(order["id"]), 1200)

        payment_count = self.conn.execute(
            "SELECT COUNT(*) FROM payments WHERE order_id = ?",
            (order["id"],)
        ).fetchone()[0]

        self.assertEqual(payment_count, 1)
        status, payload = self.app.handle("POST", "/webhooks/payments", {
            "id": "evt_1", "type": "payment.succeeded", "order_id": order["id"], "amount_cents": 1200})
        self.assertEqual((status, payload["status"]), (200, "paid"))

    def test_cancel_paid_order_restocks(self):
        order = self.app.orders.create("ana", [("TEE", 2)])
        self.app.payments.handle_event(
            {"id": "evt_2", "type": "payment.succeeded", "order_id": order["id"], "amount_cents": 5000})
        self.app.orders.cancel(order["id"])
        self.assertEqual(self.app.catalog.get_product("TEE").stock, 3)

    def test_daily_sales(self):
        order = self.app.orders.create("ana", [("MUG", 1)])
        noon = datetime(2025, 3, 10, 12, 0, tzinfo=timezone.utc)
        self.app.payments.handle_event(
            {"id": "evt_3", "type": "payment.succeeded", "order_id": order["id"], "amount_cents": 1200}, now=noon)
        self.assertEqual(reports.daily_sales(self.conn, "2025-03-10"),
                         {"day": "2025-03-10", "revenue_cents": 1200, "orders": 1})

    def test_price_change(self):
        self.app.handle("PUT", "/products/MUG", {"price_cents": 1500})
        self.assertEqual(self.app.catalog.get_product("MUG").price_cents, 1500)


if __name__ == "__main__":
    unittest.main()
```

## Assistant

You're very close! Your new test code is correct, but there is one small issue: you placed the duplicate-payment test inside the existing `test_payment_marks_order_paid()` method.

We need two separate test methods so Python can count them independently.

### Step 1: Replace your current `test_payment_marks_order_paid()` method

Replace that entire method with these two separate methods:

```python
    def test_payment_marks_order_paid(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        status, payload = self.app.handle("POST", "/webhooks/payments", {
            "id": "evt_1",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 1200
        })

        self.assertEqual((status, payload["status"]), (200, "paid"))

    def test_duplicate_payment_event_is_not_counted_twice(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        event = {
            "id": "evt_duplicate",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 1200
        }

        self.app.payments.handle_event(event)
        self.app.payments.handle_event(event)

        self.assertEqual(self.app.payments.paid_cents(order["id"]), 1200)

        payment_count = self.conn.execute(
            "SELECT COUNT(*) FROM payments WHERE order_id = ?",
            (order["id"],)
        ).fetchone()[0]

        self.assertEqual(payment_count, 1)
```

### Step 2: Save the file

Press `Ctrl + S`.

### Step 3: Run all tests

```powershell
python -m unittest discover -s tests -v
```

Expected at that stage: 8 tests passed.

Send the output. Then we'll test the separate-payment scenario, where two different event IDs are received for the same order.

## User

The user pasted the revised `test_orders.py` with `test_payment_marks_order_paid()` and `test_duplicate_payment_event_is_not_counted_twice()` as separate methods.

## Assistant

Excellent! Your `test_orders.py` is now structured correctly. You have separated the two tests:

- `test_payment_marks_order_paid` checks that a successful payment marks the order as paid.
- `test_duplicate_payment_event_is_not_counted_twice` checks that sending the same payment event twice records it only once.

Next step: run the tests.

Open PowerShell in your project root folder and execute:

```powershell
python -m unittest discover -s tests -v
```

You should see 8 tests if everything passes.

Please share the complete output here. Don't change any other files yet. After we verify the result, we'll investigate Report 1 and identify its actual root cause before making a fix.
