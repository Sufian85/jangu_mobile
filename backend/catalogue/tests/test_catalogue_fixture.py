import io
import json
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import TestCase, override_settings

from catalogue.management.commands import load_catalogue
from catalogue.models import Category, Product, ProductImage, ProductVariant

from .helpers import make_test_image


def run(command):
    call_command(command, stdout=io.StringIO())


def counts():
    return (Category.objects.count(), Product.objects.count(),
            ProductVariant.objects.count(), ProductImage.objects.count())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class LoadCatalogueTests(TestCase):
    def test_loads_every_fixture_product_with_variants_and_images(self):
        run("load_catalogue")

        fixture = json.loads(load_catalogue.FIXTURE_PATH.read_text(encoding="utf-8"))
        n_products = sum(1 for row in fixture if row["model"] == "catalogue.product")
        self.assertEqual(Product.objects.count(), n_products)
        for product in Product.objects.all():
            self.assertTrue(product.description)
            self.assertTrue(product.variants.exists(), product.slug)
            self.assertEqual(product.images.filter(is_primary=True).count(), 1, product.slug)
        self.assertTrue(all(v.price > 0 for v in ProductVariant.objects.all()))
        for image in ProductImage.objects.all():
            self.assertTrue(default_storage.exists(image.image.name), image.image.name)

    def test_is_idempotent(self):
        run("load_catalogue")
        before = counts()
        run("load_catalogue")
        self.assertEqual(before, counts())

    def test_never_overwrites_existing_products(self):
        run("load_catalogue")
        variant = ProductVariant.objects.first()
        variant.price, variant.stock_qty = Decimal("1.00"), 0
        variant.save()
        product = variant.product
        product.images.all().delete()

        run("load_catalogue")

        variant.refresh_from_db()
        self.assertEqual((variant.price, variant.stock_qty), (Decimal("1.00"), 0))
        self.assertFalse(product.images.exists())

    def test_restores_a_deleted_product(self):
        run("load_catalogue")
        before = counts()
        Product.objects.first().delete()

        run("load_catalogue")

        self.assertEqual(before, counts())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DumpCatalogueTests(TestCase):
    def setUp(self):
        out_dir = Path(tempfile.mkdtemp())
        self.fixture_path = out_dir / "catalogue.json"
        self.media_dir = out_dir / "media"
        for name, value in (("FIXTURE_PATH", self.fixture_path),
                            ("FIXTURE_MEDIA_DIR", self.media_dir)):
            patcher = mock.patch.object(load_catalogue, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_dump_then_load_round_trips(self):
        category = Category.objects.create(name="Tablets")
        product = Product.objects.create(title="Galaxy Tab", category=category, brand="Samsung")
        ProductVariant.objects.create(product=product, sku="tab-64", price=Decimal("900000"),
                                      stock_qty=7)
        image = ProductImage.objects.create(product=product, image=make_test_image("tab.png"))

        run("dump_catalogue")

        rows = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        product_row = next(r for r in rows if r["model"] == "catalogue.product")
        self.assertNotIn("pk", product_row)
        self.assertEqual(product_row["fields"]["category"], ["tablets"])
        self.assertTrue((self.media_dir / image.image.name).is_file())

        default_storage.delete(image.image.name)
        Product.objects.all().delete()
        Category.objects.all().delete()

        run("load_catalogue")

        variant = ProductVariant.objects.get(sku="tab-64")
        self.assertEqual((variant.product.slug, variant.price, variant.stock_qty),
                         ("galaxy-tab", Decimal("900000"), 7))
        self.assertTrue(default_storage.exists(variant.product.images.get().image.name))
