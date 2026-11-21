from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.cart import SessionCart
from orders.models import Order, OrderItem
from orders.tests.factories import make_address, make_request, make_user, make_variant

User = get_user_model()


class AccountIndexTests(TestCase):
    def test_requires_login(self):
        r = self.client.get(reverse("storefront:account"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])

    def test_renders_greeting_and_tiles(self):
        user = User.objects.create_user(
            phone="+256772000001", password="s3cure-pass-99", first_name="Ada", last_name="L"
        )
        self.client.force_login(user)
        r = self.client.get(reverse("storefront:account"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Hi Ada")
        self.assertContains(r, reverse("storefront:account_orders"))
        self.assertContains(r, reverse("storefront:addresses"))
        self.assertContains(r, reverse("storefront:logout"))


class OrderHistoryTests(TestCase):
    def setUp(self):
        self.user = make_user(phone="+256772000001")
        self.other = make_user(phone="+256772000002")
        self.client.force_login(self.user)

    def _order(self, owner, number, status=Order.Status.PAID):
        order = Order.objects.create(
            user=owner, order_number=number, status=status,
            subtotal=Decimal("1000000"), total=Decimal("1000000"),
            recipient_name="Ada", recipient_phone="+256772000009",
            city_district="Kampala", street_area="Kololo",
        )
        OrderItem.objects.create(
            order=order, variant=make_variant(sku=number), product_title="Phone X",
            variant_label="128GB", quantity=1, unit_price=Decimal("1000000"),
        )
        return order

    def test_history_lists_only_own_orders(self):
        self._order(self.user, "JNG-20260906-0001")
        self._order(self.other, "JNG-20260906-0002")
        r = self.client.get(reverse("storefront:account_orders"))
        self.assertContains(r, "JNG-20260906-0001")
        self.assertNotContains(r, "JNG-20260906-0002")

    def test_history_requires_login(self):
        self.client.logout()
        r = self.client.get(reverse("storefront:account_orders"))
        self.assertIn("/login/", r["Location"])

    def test_detail_shows_items_and_total(self):
        order = self._order(self.user, "JNG-20260906-0003")
        r = self.client.get(reverse("storefront:account_order", args=[order.order_number]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Phone X")
        self.assertContains(r, "UGX 1,000,000")

    def test_detail_404_for_another_users_order(self):
        order = self._order(self.other, "JNG-20260906-0004")
        r = self.client.get(reverse("storefront:account_order", args=[order.order_number]))
        self.assertEqual(r.status_code, 404)


class OrderCancelTests(TestCase):
    def setUp(self):
        self.user = make_user(phone="+256772000001")
        self.address = make_address(self.user)
        self.v = make_variant(sku="A", price="1000000", stock_qty=10)
        self.client.force_login(self.user)

    def _place(self, qty=3):
        cart = SessionCart(make_request())
        cart.add(self.v, qty)
        from orders import services
        return services.create_order_from_cart(user=self.user, cart=cart, address=self.address)

    def test_cancel_restores_stock_and_sets_cancelled(self):
        order = self._place(3)
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 7)
        r = self.client.post(reverse("storefront:account_order_cancel", args=[order.order_number]))
        self.assertRedirects(r, reverse("storefront:account_order", args=[order.order_number]))
        order.refresh_from_db(); self.v.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.v.stock_qty, 10)

    def test_cancel_requires_post(self):
        order = self._place(1)
        r = self.client.get(reverse("storefront:account_order_cancel", args=[order.order_number]))
        self.assertEqual(r.status_code, 405)

    def test_cancel_another_users_order_404(self):
        other = make_user(phone="+256772000099")
        cart = SessionCart(make_request())
        v = make_variant(sku="Z", stock_qty=5)
        cart.add(v, 1)
        from orders import services
        order = services.create_order_from_cart(user=other, cart=cart, address=make_address(other))
        r = self.client.post(reverse("storefront:account_order_cancel", args=[order.order_number]))
        self.assertEqual(r.status_code, 404)

    def test_cancel_shipped_order_shows_error(self):
        order = self._place(1)
        order.status = Order.Status.SHIPPED
        order.save()
        r = self.client.post(reverse("storefront:account_order_cancel", args=[order.order_number]), follow=True)
        self.assertContains(r, "no longer be cancelled")

    def test_detail_hides_cancel_for_shipped(self):
        order = self._place(1)
        order.status = Order.Status.SHIPPED
        order.save()
        r = self.client.get(reverse("storefront:account_order", args=[order.order_number]))
        self.assertNotContains(r, "Cancel order")

    def test_detail_shows_cancel_for_paid(self):
        order = self._place(1)
        r = self.client.get(reverse("storefront:account_order", args=[order.order_number]))
        self.assertContains(r, "Cancel order")


class AddressBookTests(TestCase):
    def setUp(self):
        self.user = make_user(phone="+256772000001")
        self.other = make_user(phone="+256772000002")
        self.client.force_login(self.user)

    def test_list_shows_only_own_addresses_with_default_badge(self):
        mine = make_address(self.user)  # first address -> is_default
        make_address(self.other)
        r = self.client.get(reverse("storefront:addresses"))
        self.assertContains(r, mine.recipient_name)
        self.assertContains(r, "Default")

    def test_add_creates_address_and_normalises_phone(self):
        r = self.client.post(reverse("storefront:address_add"), {
            "recipient_name": "Ada L", "recipient_phone": "0770000000",
            "city_district": "Jinja", "street_area": "Main St", "landmark": "",
        })
        self.assertRedirects(r, reverse("storefront:addresses"))
        a = self.user.addresses.get()
        self.assertEqual(a.recipient_phone, "+256770000000")
        self.assertTrue(a.is_default)

    def test_edit_is_owner_scoped(self):
        mine = make_address(self.user)
        r = self.client.post(reverse("storefront:address_edit", args=[mine.pk]), {
            "recipient_name": "New Name", "recipient_phone": mine.recipient_phone,
            "city_district": mine.city_district, "street_area": mine.street_area, "landmark": "",
        })
        self.assertRedirects(r, reverse("storefront:addresses"))
        mine.refresh_from_db()
        self.assertEqual(mine.recipient_name, "New Name")
        theirs = make_address(self.other)
        self.assertEqual(self.client.get(reverse("storefront:address_edit", args=[theirs.pk])).status_code, 404)

    def test_set_default_switches_and_unsets_previous(self):
        a1 = make_address(self.user)   # default
        a2 = make_address(self.user)   # not default
        r = self.client.post(reverse("storefront:address_set_default", args=[a2.pk]))
        self.assertRedirects(r, reverse("storefront:addresses"))
        a1.refresh_from_db(); a2.refresh_from_db()
        self.assertFalse(a1.is_default)
        self.assertTrue(a2.is_default)

    def test_delete_promotes_a_replacement_default(self):
        a1 = make_address(self.user)   # default
        a2 = make_address(self.user)
        r = self.client.post(reverse("storefront:address_delete", args=[a1.pk]))
        self.assertRedirects(r, reverse("storefront:addresses"))
        self.assertFalse(self.user.addresses.filter(pk=a1.pk).exists())
        a2.refresh_from_db()
        self.assertTrue(a2.is_default)

    def test_delete_requires_post_and_is_owner_scoped(self):
        mine = make_address(self.user)
        self.assertEqual(self.client.get(reverse("storefront:address_delete", args=[mine.pk])).status_code, 405)
        theirs = make_address(self.other)
        self.assertEqual(self.client.post(reverse("storefront:address_delete", args=[theirs.pk])).status_code, 404)
