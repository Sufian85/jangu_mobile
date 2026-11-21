from decimal import Decimal

from django.test import TestCase

from orders import services
from orders.cart import SessionCart
from orders.exceptions import (
    AddressOwnershipError,
    EmptyCartError,
    InsufficientStockError,
    OrderNotCancellable,
    PaymentSimulatedFailure,
)
from orders.models import Order, OrderItem
from orders.tests.factories import make_address, make_request, make_user, make_variant


class CreateOrderFromCartTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)
        self.request = make_request()
        self.cart = SessionCart(self.request)
        self.v = make_variant(sku="A", price="1000000", stock_qty=10,
                              attributes={"storage": "128GB", "color": "Black"})

    def test_happy_path_creates_order_and_decrements_stock(self):
        self.cart.add(self.v, 3)
        order = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.subtotal, Decimal("3000000"))
        self.assertEqual(order.total, Decimal("3000000"))
        self.assertTrue(order.order_number.startswith("JNG-"))
        item = order.items.get()
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.unit_price, Decimal("1000000"))
        self.assertEqual(item.variant_label, "128GB / Black")
        self.assertEqual(item.product_title, self.v.product.title)
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 7)

    def test_snapshots_are_frozen(self):
        self.cart.add(self.v, 1)
        order = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.v.price = Decimal("9999999"); self.v.save()
        self.address.recipient_name = "Someone Else"; self.address.save()
        order.refresh_from_db()
        self.assertEqual(order.items.get().unit_price, Decimal("1000000"))
        self.assertEqual(order.recipient_name, "Ada L")

    def test_empty_cart_raises(self):
        with self.assertRaises(EmptyCartError):
            services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)

    def test_insufficient_stock_raises_and_persists_nothing(self):
        self.cart.add(self.v, 5)
        self.v.stock_qty = 2; self.v.save()
        with self.assertRaises(InsufficientStockError) as ctx:
            services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.assertEqual(ctx.exception.shortfalls[0]["available"], 2)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_foreign_address_raises(self):
        other = make_address(make_user(phone="+256772000077"))
        self.cart.add(self.v, 1)
        with self.assertRaises(AddressOwnershipError):
            services.create_order_from_cart(user=self.user, cart=self.cart, address=other)

    def test_order_numbers_increment_same_day(self):
        self.cart.add(self.v, 1)
        o1 = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.cart.add(self.v, 1)
        o2 = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.assertNotEqual(o1.order_number, o2.order_number)
        self.assertTrue(o2.order_number.endswith("0002"))


class MarkPaidTests(TestCase):
    def _pending(self):
        user = make_user()
        return Order.objects.create(
            user=user, order_number="JNG-20260906-0001", subtotal=Decimal("0"),
            total=Decimal("0"), recipient_name="Ada", recipient_phone="+256772000009",
            city_district="Kampala", street_area="Kololo",
        )

    def test_marks_paid_and_sets_fields(self):
        order = services.mark_paid(self._pending(), method="mtn_momo")
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.payment_method, "mtn_momo")
        self.assertTrue(order.payment_reference.startswith("SIM-"))
        self.assertIsNotNone(order.paid_at)

    def test_fail_true_raises_and_leaves_pending(self):
        order = self._pending()
        with self.assertRaises(PaymentSimulatedFailure):
            services.mark_paid(order, method="card", fail=True)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_second_call_is_noop(self):
        order = services.mark_paid(self._pending(), method="card")
        ref = order.payment_reference
        again = services.mark_paid(order, method="mtn_momo")
        self.assertEqual(again.payment_reference, ref)
        self.assertEqual(again.payment_method, "card")


class CancelOrderTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)
        self.request = make_request()
        self.cart = SessionCart(self.request)
        self.v = make_variant(price="500000", stock_qty=10)

    def test_cancel_restores_stock_and_sets_cancelled(self):
        self.cart.add(self.v, 4)
        order = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 6)
        services.cancel_order(order)
        order.refresh_from_db(); self.v.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.v.stock_qty, 10)

    def test_cancel_non_cancellable_status_raises(self):
        self.cart.add(self.v, 1)
        order = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        order.status = Order.Status.SHIPPED; order.save()
        with self.assertRaises(OrderNotCancellable):
            services.cancel_order(order)


class PlaceOrderTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)
        self.request = make_request()
        self.cart = SessionCart(self.request)
        self.v = make_variant(price="1000000", stock_qty=10)

    def test_place_order_creates_paid_order(self):
        self.cart.add(self.v, 2)
        order = services.place_order(user=self.user, cart=self.cart, address=self.address,
                                     method="airtel_money")
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(len(self.cart), 0)
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 8)

    def test_simulate_fail_creates_nothing_and_keeps_cart(self):
        self.cart.add(self.v, 2)
        with self.assertRaises(PaymentSimulatedFailure):
            services.place_order(user=self.user, cart=self.cart, address=self.address,
                                 method="card", simulate_fail=True)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(len(self.cart), 2)
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 10)
