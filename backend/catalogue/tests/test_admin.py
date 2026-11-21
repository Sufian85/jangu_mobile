from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from catalogue.models import Category, Product


class CatalogueAdminAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.customer = User.objects.create_user(
            phone="0709876543", password="strongpass123", first_name="Grace", last_name="Hopper"
        )
        Category.objects.create(name="Phones")

    def test_staff_can_access_category_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:catalogue_category_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_access_product_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:catalogue_product_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_redirected_from_category_changelist(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("admin:catalogue_category_changelist"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_render_product_change_form_with_inlines(self):
        category = Category.objects.get(name="Phones")
        product = Product.objects.create(title="iPhone 15", category=category, brand="Apple")
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:catalogue_product_change", args=[product.pk]))
        self.assertEqual(response.status_code, 200)

    def test_product_form_does_not_ask_for_a_sku(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:catalogue_product_add"))
        self.assertContains(response, "variants-0-price")
        self.assertNotContains(response, "variants-0-sku")

    def test_adding_a_product_generates_a_readable_sku(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("admin:catalogue_product_add"),
            {
                "title": "Spark 10",
                "slug": "",
                "category": Category.objects.get(name="Phones").pk,
                "description": "",
                "brand": "Tecno",
                "is_active": "on",
                "variants-TOTAL_FORMS": "1",
                "variants-INITIAL_FORMS": "0",
                "variants-MIN_NUM_FORMS": "0",
                "variants-MAX_NUM_FORMS": "1000",
                "variants-0-attributes": '{"storage": "128GB", "color": "Black"}',
                "variants-0-price": "450000",
                "variants-0-stock_qty": "5",
                "images-TOTAL_FORMS": "0",
                "images-INITIAL_FORMS": "0",
                "images-MIN_NUM_FORMS": "0",
                "images-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(response.status_code, 302)
        variant = Product.objects.get(title="Spark 10").variants.get()
        self.assertEqual(variant.sku, "spark-10-128gb-black")
