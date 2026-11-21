from decimal import Decimal

from django.test import TestCase

from orders.models import DailyOrderSequence, Order, OrderItem
from orders.tests.factories import make_address, make_user, make_variant


class OrderModelTests(TestCase):
    def _order(self, **kw):
        user = kw.pop("user", None) or make_user()
        defaults = dict(
            user=user, order_number="JNG-20260906-0001", subtotal=Decimal("0"),
            total=Decimal("0"), recipient_name="Ada", recipient_phone="+256772000009",
            city_district="Kampala", street_area="Kololo",
        )
        defaults.update(kw)
        return Order.objects.create(**defaults)

    def test_str_is_order_number(self):
        self.assertEqual(str(self._order()), "JNG-20260906-0001")

    def test_status_defaults_to_pending(self):
        self.assertEqual(self._order().status, Order.Status.PENDING)

    def test_delivery_fee_defaults_to_zero(self):
        self.assertEqual(self._order().delivery_fee, Decimal("0"))

    def test_order_number_is_unique(self):
        self._order()
        with self.assertRaises(Exception):
            self._order(user=make_user(phone="+256772000002"))

    def test_orders_ordered_newest_first(self):
        a = self._order(order_number="JNG-20260906-0001")
        b = self._order(order_number="JNG-20260906-0002", user=make_user(phone="+256772000002"))
        self.assertEqual(list(Order.objects.all()), [b, a])


class OrderItemModelTests(TestCase):
    def test_line_total_is_unit_price_times_quantity(self):
        user = make_user()
        order = Order.objects.create(
            user=user, order_number="JNG-20260906-0009", subtotal=Decimal("0"),
            total=Decimal("0"), recipient_name="Ada", recipient_phone="+256772000009",
            city_district="Kampala", street_area="Kololo",
        )
        variant = make_variant(price="1500000")
        item = OrderItem.objects.create(
            order=order, variant=variant, product_title="Widget", variant_label="128GB / Black",
            quantity=3, unit_price=Decimal("1500000"),
        )
        self.assertEqual(item.line_total, Decimal("4500000"))


class DailyOrderSequenceTests(TestCase):
    def test_date_is_unique(self):
        import datetime
        DailyOrderSequence.objects.create(date=datetime.date(2026, 9, 6))
        with self.assertRaises(Exception):
            DailyOrderSequence.objects.create(date=datetime.date(2026, 9, 6))
