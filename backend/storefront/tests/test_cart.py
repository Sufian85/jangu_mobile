import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from orders.tests.factories import make_variant


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CartFlowTests(TestCase):
    def setUp(self):
        self.v = make_variant(sku="A", price="1000000", stock_qty=5,
                              attributes={"storage": "128GB"}, title="Phone")

    def test_add_sets_session_and_redirects_to_cart(self):
        r = self.client.post(reverse("storefront:cart_add"),
                             {"variant_id": self.v.id, "quantity": 2})
        self.assertRedirects(r, reverse("storefront:cart"))
        self.assertEqual(self.client.session["cart"], {str(self.v.id): 2})

    def test_add_same_variant_increments(self):
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 2})
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 1})
        self.assertEqual(self.client.session["cart"], {str(self.v.id): 3})

    def test_over_stock_add_is_rejected_with_message(self):
        r = self.client.post(reverse("storefront:cart_add"),
                             {"variant_id": self.v.id, "quantity": 9}, follow=True)
        self.assertContains(r, "in stock")
        self.assertNotIn("cart", self.client.session)

    def test_update_to_zero_removes(self):
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 2})
        self.client.post(reverse("storefront:cart_update"), {"variant_id": self.v.id, "quantity": 0})
        self.assertEqual(self.client.session["cart"], {})

    def test_remove(self):
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 2})
        self.client.post(reverse("storefront:cart_remove"), {"variant_id": self.v.id})
        self.assertEqual(self.client.session["cart"], {})

    def test_cart_page_shows_lines_and_totals(self):
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 2})
        r = self.client.get(reverse("storefront:cart"))
        self.assertContains(r, "Phone-A")
        self.assertContains(r, "UGX 2,000,000")

    def test_badge_count_via_context_processor(self):
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 2})
        r = self.client.get(reverse("storefront:home"))
        self.assertContains(r, 'class="cart-badge">2<')
