import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from orders.models import Order
from orders.tests.factories import make_address, make_variant

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256771234567", password="s3cure-pass-99", first_name="Ada", last_name="L"
        )
        self.address = make_address(self.user, is_default=True)
        self.v = make_variant(sku="A", price="1000000", stock_qty=5, title="Phone")

    def _fill_cart(self, qty=2):
        self.client.force_login(self.user)
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": qty})

    def test_anonymous_checkout_redirects_to_login(self):
        r = self.client.get(reverse("storefront:checkout"))
        self.assertIn("/login/", r["Location"])
        self.assertIn("next=", r["Location"])

    def test_empty_cart_checkout_redirects_to_cart(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("storefront:checkout"))
        self.assertRedirects(r, reverse("storefront:cart"))

    def test_checkout_lists_addresses(self):
        self._fill_cart()
        r = self.client.get(reverse("storefront:checkout"))
        self.assertContains(r, self.address.recipient_name)

    def test_checkout_selecting_address_advances_to_payment(self):
        self._fill_cart()
        r = self.client.post(reverse("storefront:checkout"), {"address_id": self.address.id})
        self.assertRedirects(r, reverse("storefront:payment"))
        self.assertEqual(self.client.session["checkout_address_id"], self.address.id)

    def test_payment_creates_paid_order_clears_cart_decrements_stock(self):
        self._fill_cart(2)
        self.client.post(reverse("storefront:checkout"), {"address_id": self.address.id})
        r = self.client.post(reverse("storefront:payment"), {"method": "mtn_momo"})
        order = Order.objects.get()
        self.assertRedirects(r, reverse("storefront:order_confirmation", args=[order.order_number]))
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.total, order.subtotal)
        self.assertEqual(self.client.session.get("cart", {}), {})
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 3)

    def test_simulate_fail_creates_no_order(self):
        self._fill_cart(2)
        self.client.post(reverse("storefront:checkout"), {"address_id": self.address.id})
        r = self.client.post(reverse("storefront:payment") + "?simulate=fail",
                             {"method": "card"}, follow=True)
        self.assertContains(r, "Payment failed")
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.client.session["cart"], {str(self.v.id): 2})

    def test_confirmation_404_for_other_user(self):
        self._fill_cart(1)
        self.client.post(reverse("storefront:checkout"), {"address_id": self.address.id})
        self.client.post(reverse("storefront:payment"), {"method": "card"})
        number = Order.objects.get().order_number
        other = User.objects.create_user(phone="+256772229999", password="x", first_name="B", last_name="C")
        self.client.force_login(other)
        self.assertEqual(
            self.client.get(reverse("storefront:order_confirmation", args=[number])).status_code, 404
        )

    def test_checkout_can_add_new_address_inline(self):
        self._fill_cart(1)
        r = self.client.post(reverse("storefront:checkout"), {
            "recipient_name": "New Person", "recipient_phone": "0770000000",
            "city_district": "Jinja", "street_area": "Main St", "landmark": "",
        })
        self.assertRedirects(r, reverse("storefront:payment"))
        self.assertEqual(self.user.addresses.count(), 2)
