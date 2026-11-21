from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders import services
from orders.exceptions import OrderNotCancellable
from orders.models import Order
from storefront.forms import AddressForm


@login_required
def index(request):
    return render(request, "storefront/account/index.html", {"active": "account"})


@login_required
def orders(request):
    page = Paginator(request.user.orders.all(), 10).get_page(request.GET.get("page"))
    return render(request, "storefront/account/orders.html", {"page_obj": page, "active": "account"})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, "storefront/account/order_detail.html", {"order": order, "active": "account"})


@require_POST
@login_required
def order_cancel(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    try:
        services.cancel_order(order)
    except OrderNotCancellable:
        messages.error(request, "This order can no longer be cancelled.")
    else:
        messages.success(request, f"Order {order.order_number} has been cancelled.")
    return redirect("storefront:account_order", order_number=order.order_number)


@login_required
def addresses(request):
    return render(request, "storefront/account/addresses.html", {
        "addresses": list(request.user.addresses.all()), "active": "account",
    })


@login_required
def address_add(request):
    form = AddressForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        address.save()
        messages.success(request, "Address added.")
        return redirect("storefront:addresses")
    return render(request, "storefront/account/address_form.html", {"form": form, "heading": "Add address"})


@login_required
def address_edit(request, pk):
    address = get_object_or_404(request.user.addresses, pk=pk)
    form = AddressForm(request.POST or None, instance=address)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Address updated.")
        return redirect("storefront:addresses")
    return render(request, "storefront/account/address_form.html", {"form": form, "heading": "Edit address"})


@require_POST
@login_required
def address_delete(request, pk):
    address = get_object_or_404(request.user.addresses, pk=pk)
    was_default = address.is_default
    with transaction.atomic():
        # Lock the user row so a concurrent add/delete can't race the
        # "promote a new default" step below (mirrors accounts.AddressViewSet).
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        address.delete()
        if was_default:
            replacement = request.user.addresses.order_by("-created_at").first()
            if replacement is not None:
                replacement.is_default = True
                replacement.save()
    messages.success(request, "Address deleted.")
    return redirect("storefront:addresses")


@require_POST
@login_required
def address_set_default(request, pk):
    address = get_object_or_404(request.user.addresses, pk=pk)
    address.is_default = True
    address.save()  # Address.save() unsets the previous default
    messages.success(request, "Default address updated.")
    return redirect("storefront:addresses")
