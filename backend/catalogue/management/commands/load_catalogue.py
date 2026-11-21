"""Load the shop catalogue from catalogue/fixtures/. Safe to run on every deploy.

Only adds what is missing. A product whose slug is already in the database is
left exactly as it is (price, stock, description, images), so edits made in
the admin are never overwritten. New products are created together with their
variants and images, and each image file is copied from fixtures/media/ into
media storage (local disk or S3) if it is not there yet.

To change the catalogue: edit it in the admin and run `dump_catalogue`, or
edit fixtures/catalogue.json by hand. Commit the result.
"""

from collections import Counter
from pathlib import Path

from django.core import serializers
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalogue.models import Category, Product, ProductImage, ProductVariant

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"
FIXTURE_PATH = FIXTURES_DIR / "catalogue.json"
FIXTURE_MEDIA_DIR = FIXTURES_DIR / "media"


class Command(BaseCommand):
    help = "Add catalogue rows from fixtures/catalogue.json that are not in the database yet."

    def handle(self, *args, **options):
        added = Counter()
        new_product_ids = set()
        deferred = []

        with transaction.atomic(), FIXTURE_PATH.open(encoding="utf-8") as fh:
            for obj in serializers.deserialize("json", fh, handle_forward_references=True):
                instance = obj.object
                if isinstance(instance, (ProductVariant, ProductImage)):
                    if instance.product_id not in new_product_ids:
                        continue
                    if isinstance(instance, ProductImage):
                        instance.pk = None  # fixture ids may clash with live rows
                    elif instance.pk is not None:
                        continue  # SKU already belongs to another product
                elif instance.pk is not None:
                    continue  # slug matched an existing row; leave it alone

                obj.save()
                added[type(instance)] += 1
                if obj.deferred_fields:
                    deferred.append(obj)
                if isinstance(instance, Product):
                    new_product_ids.add(instance.pk)
                image = getattr(instance, "image", None)
                if image:
                    self._copy_image(image.name)

            for obj in deferred:
                obj.save_deferred_fields()

        self.stdout.write(self.style.SUCCESS(
            f"load_catalogue: added {added[Category]} categories, {added[Product]} products, "
            f"{added[ProductVariant]} variants, {added[ProductImage]} images."))

    def _copy_image(self, name):
        if default_storage.exists(name):
            return
        source = FIXTURE_MEDIA_DIR / name
        if not source.is_file():
            raise CommandError(
                f"load_catalogue: fixture references {name} but {source} does not exist.")
        with source.open("rb") as fh:
            default_storage.save(name, File(fh))
