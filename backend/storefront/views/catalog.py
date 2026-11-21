from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from catalogue.models import Category, Product
from storefront import selectors

PAGE_SIZE = 12
# Enough for the widest layout, 5 columns x 2 rows. app.css hides the extras on
# narrower screens so the grid only ever shows complete rows.
FEATURED_LIMIT = 10


def _decimal_or_none(raw):
    if raw in (None, ""):
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def _filters(request):
    return {
        "brand": request.GET.get("brand") or None,
        "price_min": _decimal_or_none(request.GET.get("price_min")),
        "price_max": _decimal_or_none(request.GET.get("price_max")),
        "in_stock": request.GET.get("in_stock") == "1",
        "sort": request.GET.get("sort") or "newest",
    }


def _paginate(request, queryset):
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    keep = {k: v for k, v in request.GET.items() if k != "page"}
    return page, (urlencode(keep) + "&" if keep else "")


def _brands_for(category=None):
    qs = Product.objects.filter(is_active=True)
    if category is not None:
        qs = qs.filter(category=category)
    return sorted(b for b in qs.values_list("brand", flat=True).distinct() if b)


def home(request):
    categories = Category.objects.filter(parent__isnull=True).order_by("name")
    return render(request, "storefront/home.html", {
        "categories": categories,
        "featured": selectors.featured_products(FEATURED_LIMIT),
        "active": "home",
    })


def category(request, slug):
    cat = get_object_or_404(Category, slug=slug)
    base = selectors.category_products(cat, **_filters(request))
    page, querystring = _paginate(request, base)
    return render(request, "storefront/category.html", {
        "category": cat, "page_obj": page, "querystring": querystring,
        "brands": _brands_for(cat),
    })


def search(request):
    query = (request.GET.get("q") or "").strip()
    base = selectors.search_products(query, **_filters(request))
    page, querystring = _paginate(request, base)
    return render(request, "storefront/search.html", {
        "query": query, "page_obj": page, "querystring": querystring,
        "brands": _brands_for(),
    })


def product_detail(request, slug):
    product = get_object_or_404(selectors.active_products(), slug=slug)
    return render(request, "storefront/product_detail.html", {
        "product": product,
        "images": list(product.images.all()),
        "variants": list(product.variants.all()),
        "related": selectors.related_products(product),
    })
