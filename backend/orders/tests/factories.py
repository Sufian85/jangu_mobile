from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import HttpRequest

from accounts.models import Address
from catalogue.models import Category, Product, ProductVariant


def make_user(phone="+256772000001", **kw):
    return get_user_model().objects.create_user(
        phone=phone, password="pass12345", first_name="Ada", last_name="Lovelace", **kw
    )


def make_variant(*, sku="SKU-1", price="1000000", stock_qty=10, attributes=None, title="Widget"):
    cat = Category.objects.create(name=f"Cat-{sku}")
    product = Product.objects.create(title=f"{title}-{sku}", category=cat, brand="ACME")
    return ProductVariant.objects.create(
        product=product, sku=sku, price=Decimal(str(price)),
        stock_qty=stock_qty, attributes=attributes if attributes is not None else {"storage": "128GB", "color": "Black"},
    )


def make_address(user, **kw):
    defaults = dict(
        recipient_name="Ada L", recipient_phone="+256772000009",
        city_district="Kampala", street_area="Kololo", landmark="",
    )
    defaults.update(kw)
    return Address.objects.create(user=user, **defaults)


def make_request():
    """A bare request with a working in-memory session (no DB hit)."""
    from django.contrib.sessions.backends.db import SessionStore
    request = HttpRequest()
    request.session = SessionStore()
    return request
