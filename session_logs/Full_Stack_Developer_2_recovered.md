# Full Stack Developer (2) — Recovered Conversation Excerpt

## 1. Inspecting the original payments.py

User:
git --no-pager show HEAD:tillpoint/payments.py

Original code:

"""Payment provider webhooks. The provider retries a delivery until it gets a 2xx, so events can repeat."""
from . import db

class PaymentError(Exception):
    pass

class Payments:
    def __init__(self, conn):
        self.conn = conn

    def handle_event(self, event, now=None):
        """event: dict(id, type, order_id, amount_cents). Returns the order's status after the event."""
        if event.get("type") != "payment.succeeded":
            return None
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (event["order_id"],)).fetchone()
        if order is None:
            raise PaymentError(f"payment for unknown order {event['order_id']}")
        if order["status"] == "cancelled":
            raise PaymentError(f"order {order['id']} is cancelled")
        self.conn.execute(
            "INSERT INTO payments (order_id, event_id, amount_cents, received_at) VALUES (?, ?, ?, ?)",
            (order["id"], event["id"], event["amount_cents"], db.to_iso(now or db.utcnow())),
        )
        if order["status"] == "pending" and self.paid_cents(order["id"]) >= order["total_cents"]:
            self.conn.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order["id"],))
            return "paid"
        return order["status"]

    def paid_cents(self, order_id):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) AS paid FROM payments WHERE order_id = ?", (order_id,)
        ).fetchone()
        return row["paid"]

## 2. Backing up and restoring the original files

User:
Copy-Item tillpoint\payments.py payments_fixed_backup.py
Copy-Item tillpoint\db.py db_fixed_backup.py

git show HEAD:tillpoint/payments.py | Set-Content -Encoding utf8 tillpoint\payments.py
git show HEAD:tillpoint/db.py | Set-Content -Encoding utf8 tillpoint\db.py

python -m unittest discover -s tests -p "test_orders.py" -v

Result:
test_cancel_paid_order_restocks ... ok
test_coupon_takes_ten_percent ... ok
test_daily_sales ... ok
test_duplicate_payment_event_is_not_counted_twice ... FAIL
test_order_totals_with_tax ... ok
test_out_of_stock ... ok
test_payment_marks_order_paid ... ok
test_price_change ... ok

Failure:
self.assertEqual(self.app.payments.paid_cents(order["id"]), 1200)
AssertionError: 2400 != 1200

## 3. Root cause analysis

Assistant:
Excellent! You have successfully reproduced Report 1's bug.

What the test proved:
- First delivery: 1200 paise recorded.
- Second delivery with the same event ID: another 1200 paise recorded.
- Expected total: 1200 paise.
- Actual total: 2400 paise.

Root cause:
The original payments.py does not check whether a payment event was already processed. Therefore, when the provider retries the same event, the application records it twice.

## 4. Restore the fixed files

Assistant instructed:

Copy-Item payments_fixed_backup.py tillpoint\payments.py -Force
Copy-Item db_fixed_backup.py tillpoint\db.py -Force

Then run:

python -m unittest discover -s tests -p "test_orders.py" -v

Expected result: All 8 tests should pass.

The assistant asked the user to send the test output before reviewing the database uniqueness constraint and duplicate-event handling.

Note: This is a recovered excerpt, not the complete original chat transcript.
