import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from storefront.tests.factories import make_category, make_product


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class HomePageTests(TestCase):
    def test_renders_hero_and_categories(self):
        make_category("Smartphones")
        make_category("Gaming Gear")
        response = self.client.get(reverse("storefront:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Gadget. Our Priority.")
        self.assertContains(response, "Shop Smart · Live Better")
        self.assertContains(response, "Smartphones")
        self.assertContains(response, "Gaming Gear")

    def test_featured_grid_shows_in_stock_products(self):
        phones = make_category("Smartphones")
        make_product(title="Galaxy S23", category=phones, brand="Samsung", price="2800000", stock_qty=4)
        make_product(title="Sold Out", category=phones, brand="X", price="10000", stock_qty=0)
        response = self.client.get(reverse("storefront:home"))
        self.assertContains(response, "Galaxy S23")
        self.assertContains(response, "UGX 2,800,000")
        self.assertNotContains(response, "Sold Out")

    def test_featured_sends_enough_products_for_the_widest_layout(self):
        phones = make_category("Smartphones")
        for number in range(12):
            make_product(title=f"Phone {number}", category=phones)
        response = self.client.get(reverse("storefront:home"))
        self.assertEqual(len(response.context["featured"]), 10)

    def test_view_all_opens_every_product(self):
        make_category("Audio")
        response = self.client.get(reverse("storefront:home"))
        self.assertContains(response, f'<a href="{reverse("storefront:search")}">View All</a>')

    def test_uses_storefront_base(self):
        response = self.client.get(reverse("storefront:home"))
        self.assertTemplateUsed(response, "storefront/base.html")
        self.assertTemplateUsed(response, "storefront/home.html")
