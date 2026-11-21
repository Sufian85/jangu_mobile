from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from orders.cart import SessionCart
from orders.exceptions import InsufficientStockError
from storefront.forms import AddToCartForm, UpdateCartForm


def detail(request):
    cart = SessionCart(request)
    lines = list(cart)
    return render(request, "storefront/cart.html", {
        "lines": lines, "subtotal": cart.subtotal, "active": "cart",
    })


@require_POST
def add(request):
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Could not add that item to your cart.")
        return redirect(request.META.get("HTTP_REFERER", "storefront:home"))
    variant = form.cleaned_data["variant"]
    try:
        SessionCart(request).add(variant, form.cleaned_data["quantity"])
    except InsufficientStockError as exc:
        avail = exc.shortfalls[0]["available"]
        messages.error(request, f"Only {avail} of {variant.product.title} in stock.")
        return redirect("storefront:product", slug=variant.product.slug)
    messages.success(request, f"Added {variant.product.title} to your cart.")
    return redirect("storefront:cart")


@require_POST
def update(request):
    form = UpdateCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Could not update your cart.")
        return redirect("storefront:cart")
    try:
        SessionCart(request).set_quantity(form.cleaned_data["variant_id"], form.cleaned_data["quantity"])
    except InsufficientStockError as exc:
        messages.error(request, f"Only {exc.shortfalls[0]['available']} in stock.")
    return redirect("storefront:cart")


@require_POST
def remove(request):
    try:
        SessionCart(request).remove(int(request.POST.get("variant_id", "")))
    except (TypeError, ValueError):
        pass
    return redirect("storefront:cart")
