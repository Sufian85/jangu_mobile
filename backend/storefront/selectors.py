from django.db.models import Exists, Min, OuterRef, Prefetch, Q

from catalogue.models import Product, ProductImage, ProductVariant

_SORTS = {
    "price_asc": "min_price",
    "price_desc": "-min_price",
    "newest": "-created_at",
}


def active_products():
    """Base queryset: active products annotated with `min_price` and `in_stock`.

    `in_stock` is an `Exists` annotation (not a `variants__` aggregate) so it is
    readable off a `.get(...)` and does not perturb the `min_price` aggregate.
    """
    has_stock = ProductVariant.objects.filter(product=OuterRef("pk"), stock_qty__gt=0)
    return (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .annotate(min_price=Min("variants__price"), in_stock=Exists(has_stock))
        .prefetch_related(
            "variants",
            Prefetch("images", queryset=ProductImage.objects.order_by("-is_primary", "sort_order", "id")),
        )
    )


def _apply_filters(qs, *, brand=None, price_min=None, price_max=None, in_stock=None, sort=None):
    if brand:
        qs = qs.filter(brand__iexact=brand)
    if price_min not in (None, ""):
        qs = qs.filter(min_price__gte=price_min)
    if price_max not in (None, ""):
        qs = qs.filter(min_price__lte=price_max)
    if in_stock:
        qs = qs.filter(in_stock=True)
    return qs.order_by(_SORTS.get(sort, _SORTS["newest"]))


def category_products(category, **filters):
    return _apply_filters(active_products().filter(category=category), **filters)


def search_products(query, **filters):
    query = (query or "").strip()
    qs = active_products()
    if query:
        qs = qs.filter(
            Q(title__icontains=query) | Q(brand__icontains=query) | Q(description__icontains=query)
        )
    return _apply_filters(qs, **filters)


def related_products(product, limit=4):
    return list(
        active_products().filter(category=product.category).exclude(pk=product.pk)[:limit]
    )


def featured_products(limit=8):
    return list(
        active_products().filter(in_stock=True, images__isnull=False)
        .distinct().order_by("-created_at")[:limit]
    )
