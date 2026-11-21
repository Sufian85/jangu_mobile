from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from orders import services
from orders.cart import SessionCart
from orders.exceptions import (
    AddressOwnershipError,
    EmptyCartError,
    InsufficientStockError,
    PaymentSimulatedFailure,
)
from orders.models import Order
from storefront.forms import AddressForm

PAYMENT_METHODS = {"mtn_momo": "MTN MoMo", "airtel_money": "Airtel Money", "card": "Card"}
SESSION_ADDRESS_KEY = "checkout_address_id"


@login_required
def checkout(request):
    cart = SessionCart(request)
    if len(cart) == 0:
        messages.info(request, "Your cart is empty.")
        return redirect("storefront:cart")

    addresses = list(request.user.addresses.all())
    form = AddressForm(request.POST or None)

    if request.method == "POST":
        address_id = request.POST.get("address_id")
        if address_id:
            address = get_object_or_404(request.user.addresses, pk=address_id)
        elif form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
        else:
            return render(request, "storefront/checkout.html", {
                "addresses": addresses, "form": form, "lines": list(cart), "subtotal": cart.subtotal,
            })
        request.session[SESSION_ADDRESS_KEY] = address.id
        return redirect("storefront:payment")

    return render(request, "storefront/checkout.html", {
        "addresses": addresses, "form": form, "lines": list(cart), "subtotal": cart.subtotal,
    })


@login_required
def payment(request):
    cart = SessionCart(request)
    if len(cart) == 0:
        return redirect("storefront:cart")
    address_id = request.session.get(SESSION_ADDRESS_KEY)
    if not address_id:
        return redirect("storefront:checkout")
    address = get_object_or_404(request.user.addresses, pk=address_id)

    if request.method == "POST":
        method = request.POST.get("method")
        if method not in PAYMENT_METHODS:
            messages.error(request, "Choose a payment method.")
        else:
            simulate_fail = request.GET.get("simulate") == "fail"
            try:
                order = services.place_order(
                    user=request.user, cart=cart, address=address,
                    method=method, simulate_fail=simulate_fail,
                )
            except PaymentSimulatedFailure:
                messages.error(request, "Payment failed. Please try again.")
            except EmptyCartError:
                return redirect("storefront:cart")
            except AddressOwnershipError:
                return redirect("storefront:checkout")
            except InsufficientStockError as exc:
                for s in exc.shortfalls:
                    messages.error(request, f"Only {s['available']} of {s['variant'].product.title} left.")
                return redirect("storefront:cart")
            else:
                request.session.pop(SESSION_ADDRESS_KEY, None)
                return redirect("storefront:order_confirmation", order_number=order.order_number)

    return render(request, "storefront/payment.html", {
        "address": address, "lines": list(cart), "subtotal": cart.subtotal,
        "methods": PAYMENT_METHODS,
    })


@login_required
def order_confirmation(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, "storefront/order_confirmation.html", {"order": order})
