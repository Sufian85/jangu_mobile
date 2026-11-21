from decimal import Decimal

from django.test import TestCase

from orders.cart import SessionCart
from orders.exceptions import InsufficientStockError
from orders.tests.factories import make_request, make_variant


class SessionCartTests(TestCase):
    def setUp(self):
        self.request = make_request()
        self.cart = SessionCart(self.request)
        self.v = make_variant(sku="A", price="1000000", stock_qty=5)

    def test_add_then_increment(self):
        self.cart.add(self.v, 2)
        self.cart.add(self.v, 1)
        self.assertEqual(len(self.cart), 3)

    def test_add_replace_sets_absolute(self):
        self.cart.add(self.v, 2)
        self.cart.add(self.v, 1, replace=True)
        self.assertEqual(len(self.cart), 1)

    def test_add_over_stock_raises_and_does_not_mutate(self):
        with self.assertRaises(InsufficientStockError):
            self.cart.add(self.v, 6)
        self.assertEqual(len(self.cart), 0)

    def test_set_quantity_absolute_and_zero_removes(self):
        self.cart.add(self.v, 2)
        self.cart.set_quantity(self.v.id, 4)
        self.assertEqual(len(self.cart), 4)
        self.cart.set_quantity(self.v.id, 0)
        self.assertEqual(len(self.cart), 0)

    def test_set_quantity_over_stock_raises(self):
        self.cart.add(self.v, 1)
        with self.assertRaises(InsufficientStockError):
            self.cart.set_quantity(self.v.id, 99)

    def test_remove_and_clear(self):
        self.cart.add(self.v, 2)
        self.cart.remove(self.v.id)
        self.assertEqual(len(self.cart), 0)
        self.cart.add(self.v, 1)
        self.cart.clear()
        self.assertEqual(len(self.cart), 0)

    def test_iter_yields_live_pricing_and_line_totals(self):
        self.cart.add(self.v, 3)
        (line,) = list(self.cart)
        self.assertEqual(line["variant"], self.v)
        self.assertEqual(line["quantity"], 3)
        self.assertEqual(line["unit_price"], Decimal("1000000"))
        self.assertEqual(line["line_total"], Decimal("3000000"))
        self.assertEqual(self.cart.subtotal, Decimal("3000000"))

    def test_iter_prunes_deleted_variant_ids(self):
        self.cart.add(self.v, 1)
        gone = make_variant(sku="B", stock_qty=1)
        self.request.session["cart"][str(gone.id)] = 1
        gone_id = gone.id
        gone.delete()
        lines = list(self.cart)
        self.assertEqual([l["variant"].id for l in lines], [self.v.id])
        self.assertNotIn(str(gone_id), self.request.session["cart"])
        self.assertTrue(self.request.session.modified)

    def test_marks_session_modified_on_write(self):
        self.request.session.modified = False
        self.cart.add(self.v, 1)
        self.assertTrue(self.request.session.modified)
