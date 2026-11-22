
import unittest
from datetime import datetime, timezone

from tillpoint import db, reports
from tillpoint.api import App
from tillpoint.catalog import Catalog, OutOfStock


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

    def test_cancel_paid_order_restocks(self):
        order = self.app.orders.create("ana", [("TEE", 2)])
        self.app.payments.handle_event(
            {"id": "evt_2", "type": "payment.succeeded", "order_id": order["id"], "amount_cents": 5000}
        )
        self.app.orders.cancel(order["id"])
        self.assertEqual(self.app.catalog.get_product("TEE").stock, 3)

    def test_cancel_pending_order_restocks(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        self.assertEqual(self.app.catalog.get_product("MUG").stock, 9)

        self.app.orders.cancel(order["id"])

        self.assertEqual(self.app.catalog.get_product("MUG").stock, 10)

    def test_expired_pending_order_restocks(self):
        created_at = datetime(2026, 11, 22, 10, 0, tzinfo=timezone.utc)
        expired_at = datetime(2026, 11, 22, 10, 16, tzinfo=timezone.utc)

        order = self.app.orders.create(
            "ana",
            [("MUG", 1)],
            now=created_at
        )

        self.assertEqual(self.app.catalog.get_product("MUG").stock, 9)

        self.app.orders.create(
            "bob",
            [("MUG", 1)],
            now=expired_at
        )

        self.assertEqual(self.app.orders.get(order["id"])["status"], "cancelled")
        self.assertEqual(self.app.catalog.get_product("MUG").stock, 9)

    def test_daily_sales(self):
        order = self.app.orders.create("ana", [("MUG", 1)])
        noon = datetime(2025, 3, 10, 12, 0, tzinfo=timezone.utc)
        self.app.payments.handle_event(
            {"id": "evt_3", "type": "payment.succeeded", "order_id": order["id"], "amount_cents": 1200},
            now=noon
        )
        self.assertEqual(
            reports.daily_sales(self.conn, "2025-03-10"),
            {"day": "2025-03-10", "revenue_cents": 1200, "orders": 1}
        )

    def test_price_change(self):
        self.app.handle("PUT", "/products/MUG", {"price_cents": 1500})
        self.assertEqual(self.app.catalog.get_product("MUG").price_cents, 1500)

    def test_coupon_tax_is_calculated_after_discount(self):
        order = self.app.orders.create(
        "ana",
        [("MUG", 1)],
        region="CA",
        coupon_code="TEN"
        )

        self.assertEqual(order["subtotal_cents"], 1200)
        self.assertEqual(order["discount_cents"], 120)
        self.assertEqual(order["tax_cents"], 78)
        self.assertEqual(order["total_cents"], 1158)

    def test_daily_sales_uses_india_local_day(self):
        order = self.app.orders.create("ana", [("MUG", 1)])
        morning_ist = datetime(2025, 3, 10, 0, 30, tzinfo=timezone.utc)
        self.app.payments.handle_event(
            {
                "id": "evt_india_morning",
                "type": "payment.succeeded",
                "order_id": order["id"],
                "amount_cents": 1200
            },
            now=morning_ist
        )
        self.assertEqual(
            reports.daily_sales(self.conn, "2025-03-10", utc_offset_minutes=330),
            {"day": "2025-03-10", "revenue_cents": 1200, "orders": 1}
        )

    def test_two_catalog_instances_cannot_oversell_stock(self):
        self.app.catalog.add_product("LIMITED", "Limited Item", 500, stock=1)
        worker_one = Catalog(self.conn)
        worker_two = Catalog(self.conn)
        self.assertEqual(worker_one.get_product("LIMITED").stock, 1)
        self.assertEqual(worker_two.get_product("LIMITED").stock, 1)
        worker_one.reserve("LIMITED", 1)
        with self.assertRaises(OutOfStock):
            worker_two.reserve("LIMITED", 1)
        row = self.conn.execute(
            "SELECT stock FROM products WHERE sku = ?",
            ("LIMITED",)
        ).fetchone()

        self.assertEqual(row["stock"], 0)

if __name__ == "__main__":
    unittest.main()
