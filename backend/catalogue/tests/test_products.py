import tempfile
from decimal import Decimal

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalogue.models import Category, Product, ProductImage, ProductVariant
from catalogue.tests.helpers import make_test_image


class ProductListViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("product-list")
        self.phones = Category.objects.create(name="Phones")
        self.laptops = Category.objects.create(name="Laptops")

    def _make_product(self, title, category, brand, price, stock_qty=5, is_active=True):
        product = Product.objects.create(
            title=title, category=category, brand=brand, is_active=is_active
        )
        ProductVariant.objects.create(
            product=product, sku=f"{title}-SKU", price=Decimal(price), stock_qty=stock_qty
        )
        return product

    def test_excludes_inactive_products(self):
        self._make_product("Spark 10", self.phones, "Tecno", "450000.00", is_active=False)
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 0)

    def test_category_filter(self):
        self._make_product("Spark 10", self.phones, "Tecno", "450000.00")
        self._make_product("ThinkPad", self.laptops, "Lenovo", "2000000.00")
        response = self.client.get(self.url, {"category": self.phones.slug})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Spark 10")

    def test_search_matches_title(self):
        self._make_product("Spark 10", self.phones, "Tecno", "450000.00")
        response = self.client.get(self.url, {"search": "spark"})
        self.assertEqual(response.data["count"], 1)

    def test_search_matches_brand(self):
        self._make_product("Spark 10", self.phones, "Tecno", "450000.00")
        response = self.client.get(self.url, {"search": "tecno"})
        self.assertEqual(response.data["count"], 1)

    def test_ordering_by_price_ascending(self):
        self._make_product("Cheap Phone", self.phones, "Tecno", "100000.00")
        self._make_product("Pricey Phone", self.phones, "Apple", "3000000.00")
        response = self.client.get(self.url, {"ordering": "price_from"})
        titles = [row["title"] for row in response.data["results"]]
        self.assertEqual(titles, ["Cheap Phone", "Pricey Phone"])

    def test_ordering_by_price_descending(self):
        self._make_product("Cheap Phone", self.phones, "Tecno", "100000.00")
        self._make_product("Pricey Phone", self.phones, "Apple", "3000000.00")
        response = self.client.get(self.url, {"ordering": "-price_from"})
        titles = [row["title"] for row in response.data["results"]]
        self.assertEqual(titles, ["Pricey Phone", "Cheap Phone"])

    def test_out_of_stock_variant_still_visible_but_flagged(self):
        self._make_product("Spark 10", self.phones, "Tecno", "450000.00", stock_qty=0)
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 1)
        self.assertFalse(response.data["results"][0]["in_stock"])

    def test_price_from_is_minimum_variant_price(self):
        product = self._make_product("Spark 10", self.phones, "Tecno", "450000.00")
        ProductVariant.objects.create(
            product=product, sku="SPARK10-256", price=Decimal("500000.00"), stock_qty=3
        )
        response = self.client.get(self.url)
        self.assertEqual(response.data["results"][0]["price_from"], "450000.00")

    def test_pagination_page_size(self):
        for i in range(25):
            self._make_product(f"Phone {i}", self.phones, "Tecno", "100000.00")
        response = self.client.get(self.url)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_primary_image_returns_absolute_url(self):
        product = self._make_product("Spark 10", self.phones, "Tecno", "450000.00")
        ProductImage.objects.create(product=product, image=make_test_image())
        response = self.client.get(self.url)
        primary_image = response.data["results"][0]["primary_image"]
        self.assertIsNotNone(primary_image)
        self.assertIn("/media/", primary_image)

    def test_zero_variant_product_has_null_price_and_not_in_stock(self):
        Product.objects.create(title="No Variants", category=self.phones, brand="Tecno")
        response = self.client.get(self.url)
        self.assertIsNone(response.data["results"][0]["price_from"])
        self.assertFalse(response.data["results"][0]["in_stock"])


class ProductDetailViewTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128", price=Decimal("450000.00"), stock_qty=0
        )
        self.url = reverse("product-detail", args=[self.product.slug])

    def test_returns_full_detail_with_variants(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["variants"]), 1)
        self.assertEqual(response.data["variants"][0]["sku"], "SPARK10-128")

    def test_out_of_stock_variant_flagged_in_detail(self):
        response = self.client.get(self.url)
        self.assertFalse(response.data["variants"][0]["in_stock"])

    def test_inactive_product_returns_404(self):
        self.product.is_active = False
        self.product.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
