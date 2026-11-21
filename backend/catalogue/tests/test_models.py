import tempfile

from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings

from catalogue.models import Category, Product, ProductImage, ProductVariant
from catalogue.tests.helpers import make_test_image


class CategoryModelTests(TestCase):
    def test_slug_auto_generated_from_name(self):
        category = Category.objects.create(name="Mobile Phones")
        self.assertEqual(category.slug, "mobile-phones")

    def test_slug_collision_appends_suffix(self):
        Category.objects.create(name="Phones")
        second = Category.objects.create(name="Phones")
        self.assertEqual(second.slug, "phones-2")

    def test_explicit_slug_is_preserved(self):
        category = Category.objects.create(name="Tablets", slug="custom-slug")
        self.assertEqual(category.slug, "custom-slug")

    def test_nested_parent_child_relationship(self):
        electronics = Category.objects.create(name="Electronics")
        phones = Category.objects.create(name="Phones", parent=electronics)
        smartphones = Category.objects.create(name="Smartphones", parent=phones)
        self.assertEqual(smartphones.parent, phones)
        self.assertEqual(smartphones.parent.parent, electronics)

    def test_children_related_name(self):
        electronics = Category.objects.create(name="Electronics")
        phones = Category.objects.create(name="Phones", parent=electronics)
        self.assertIn(phones, electronics.children.all())


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")

    def test_slug_auto_generated_from_title(self):
        product = Product.objects.create(
            title="Tecno Spark 10", category=self.category, brand="Tecno"
        )
        self.assertEqual(product.slug, "tecno-spark-10")

    def test_slug_collision_appends_suffix(self):
        Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        second = Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        self.assertEqual(second.slug, "spark-10-2")

    def test_is_active_defaults_to_true(self):
        product = Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        self.assertTrue(product.is_active)

    def test_category_protected_on_delete(self):
        Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        with self.assertRaises(ProtectedError):
            self.category.delete()


class ProductVariantModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )

    def test_attributes_default_to_empty_dict(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00"
        )
        self.assertEqual(variant.attributes, {})

    def test_attributes_json_roundtrip(self):
        variant = ProductVariant.objects.create(
            product=self.product,
            sku="SPARK10-128-BLK",
            price="450000.00",
            attributes={"storage": "128GB", "color": "Black"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.attributes, {"storage": "128GB", "color": "Black"})

    def test_stock_qty_defaults_to_zero(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00"
        )
        self.assertEqual(variant.stock_qty, 0)

    def test_in_stock_property(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00", stock_qty=5
        )
        self.assertTrue(variant.in_stock)
        variant.stock_qty = 0
        self.assertFalse(variant.in_stock)

    def test_sku_unique(self):
        ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00"
        )
        with self.assertRaises(IntegrityError):
            ProductVariant.objects.create(
                product=self.product, sku="SPARK10-128-BLK", price="450000.00"
            )

    def test_blank_sku_is_built_from_product_and_attributes(self):
        variant = ProductVariant.objects.create(
            product=self.product,
            price="450000.00",
            attributes={"storage": "256GB", "color": "Cosmic Orange"},
        )
        self.assertEqual(variant.sku, "spark-10-256gb-cosmic-orange")

    def test_generated_sku_does_not_depend_on_stored_key_order(self):
        variant = ProductVariant.objects.create(
            product=self.product,
            price="450000.00",
            attributes={"ram": "16GB", "color": "Grey", "storage": "512GB", "processor": "Core i5"},
        )
        self.assertEqual(variant.sku, "spark-10-core-i5-16gb-512gb-grey")

    def test_generated_sku_without_attributes_is_the_product_slug(self):
        variant = ProductVariant.objects.create(product=self.product, price="450000.00")
        self.assertEqual(variant.sku, "spark-10")

    def test_generated_sku_is_unique(self):
        attributes = {"storage": "128GB"}
        first = ProductVariant.objects.create(
            product=self.product, price="450000.00", attributes=attributes
        )
        second = ProductVariant.objects.create(
            product=self.product, price="450000.00", attributes=attributes
        )
        self.assertEqual(first.sku, "spark-10-128gb")
        self.assertEqual(second.sku, "spark-10-128gb-2")

    def test_generated_sku_fits_the_field_for_long_names(self):
        product = Product.objects.create(title="Phone " * 30, category=self.category, brand="Tecno")
        attributes = {"storage": "128GB"}
        first = ProductVariant.objects.create(product=product, price="450000.00", attributes=attributes)
        second = ProductVariant.objects.create(product=product, price="450000.00", attributes=attributes)
        self.assertLessEqual(len(first.sku), 64)
        self.assertLessEqual(len(second.sku), 64)
        self.assertNotEqual(first.sku, second.sku)

    def test_given_sku_is_kept(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00"
        )
        self.assertEqual(variant.sku, "SPARK10-128-BLK")

    def test_sku_stays_the_same_when_attributes_change(self):
        variant = ProductVariant.objects.create(
            product=self.product, price="450000.00", attributes={"color": "Black"}
        )
        variant.attributes = {"color": "Blue"}
        variant.save()
        variant.refresh_from_db()
        self.assertEqual(variant.sku, "spark-10-black")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProductImageModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )

    def test_first_image_is_auto_primary(self):
        image = ProductImage.objects.create(product=self.product, image=make_test_image())
        self.assertTrue(image.is_primary)

    def test_new_primary_unsets_previous_primary(self):
        first = ProductImage.objects.create(
            product=self.product, image=make_test_image("a.png")
        )
        second = ProductImage.objects.create(
            product=self.product, image=make_test_image("b.png"), is_primary=True
        )
        first.refresh_from_db()
        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)

    def test_sort_order_defaults_to_zero(self):
        image = ProductImage.objects.create(product=self.product, image=make_test_image())
        self.assertEqual(image.sort_order, 0)
