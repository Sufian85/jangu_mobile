"""Write the catalogue in the database back to catalogue/fixtures/.

Dumps categories, products, variants and images to fixtures/catalogue.json
(rows point at each other by slug/SKU, not by id) and copies every image they
use from media storage into fixtures/media/. Commit both; the next deploy's
`load_catalogue` picks up any products that are not live yet.
"""

import shutil

from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import BaseCommand

from catalogue.models import Category, Product, ProductImage

from . import load_catalogue


class Command(BaseCommand):
    help = "Dump the catalogue to fixtures/catalogue.json and copy its images alongside."

    def handle(self, *args, **options):
        fixture_path = load_catalogue.FIXTURE_PATH
        media_dir = load_catalogue.FIXTURE_MEDIA_DIR

        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        call_command(
            "dumpdata",
            "catalogue.Category", "catalogue.Product",
            "catalogue.ProductVariant", "catalogue.ProductImage",
            natural_foreign=True, natural_primary=True, indent=2,
            output=str(fixture_path), verbosity=0,
        )

        names = [n for n in Category.objects.values_list("image", flat=True) if n]
        names += ProductImage.objects.values_list("image", flat=True)
        for name in names:
            target = media_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with default_storage.open(name, "rb") as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)

        self.stdout.write(self.style.SUCCESS(
            f"dump_catalogue: wrote {Product.objects.count()} products to {fixture_path} "
            f"and {len(names)} images to {media_dir}."))
