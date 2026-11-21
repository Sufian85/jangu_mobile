from decimal import Decimal

from catalogue.models import Category, Product, ProductImage, ProductVariant
from catalogue.tests.helpers import make_test_image


def make_category(name="Smartphones"):
    return Category.objects.create(name=name)


def make_product(
    *, title="Galaxy S23", category=None, brand="Samsung", price="2800000",
    stock_qty=10, is_active=True, with_image=True, variants=None,
):
    category = category or make_category()
    product = Product.objects.create(
        title=title, category=category, brand=brand, is_active=is_active,
        description=f"{brand} {title} demo unit.",
    )
    specs = variants or [{"sku": f"{title}-A", "price": price, "stock_qty": stock_qty,
                          "attributes": {"storage": "128GB", "color": "Black"}}]
    for spec in specs:
        ProductVariant.objects.create(
            product=product, sku=spec["sku"], price=Decimal(str(spec["price"])),
            stock_qty=spec["stock_qty"], attributes=spec.get("attributes", {}),
        )
    if with_image:
        ProductImage.objects.create(product=product, image=make_test_image(f"{title}.png"))
    return product
