import secrets
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from catalogue.models import ProductVariant
from catalogue.utils import variant_label

from .exceptions import (
    AddressOwnershipError,
    EmptyCartError,
    InsufficientStockError,
    OrderNotCancellable,
    PaymentSimulatedFailure,
)
from .models import DailyOrderSequence, Order, OrderItem


def _next_order_number():
    today = timezone.localdate()
    seq, _ = DailyOrderSequence.objects.select_for_update().get_or_create(date=today)
    seq.last_value += 1
    seq.save(update_fields=["last_value"])
    return f"JNG-{today:%Y%m%d}-{seq.last_value:04d}"


@transaction.atomic
def create_order_from_cart(*, user, cart, address):
    if address.user_id != user.id:
        raise AddressOwnershipError("Address does not belong to this user.")

    lines = list(cart)
    if not lines:
        raise EmptyCartError("Cart is empty.")

    ids = [line["variant"].id for line in lines]
    locked = {v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=ids)}

    shortfalls = []
    for line in lines:
        v = locked.get(line["variant"].id)
        if v is None or line["quantity"] > v.stock_qty:
            shortfalls.append({
                "variant": line["variant"],
                "requested": line["quantity"],
                "available": v.stock_qty if v else 0,
            })
    if shortfalls:
        raise InsufficientStockError(shortfalls)

    subtotal = sum((locked[l["variant"].id].price * l["quantity"] for l in lines), Decimal("0"))
    order = Order.objects.create(
        user=user,
        order_number=_next_order_number(),
        subtotal=subtotal,
        delivery_fee=Decimal("0"),
        total=subtotal,
        address=address,
        recipient_name=address.recipient_name,
        recipient_phone=address.recipient_phone,
        city_district=address.city_district,
        street_area=address.street_area,
        landmark=address.landmark,
    )
    for line in lines:
        v = locked[line["variant"].id]
        OrderItem.objects.create(
            order=order, variant=v, product_title=v.product.title,
            variant_label=variant_label(v.attributes),
            quantity=line["quantity"], unit_price=v.price,
        )
        v.stock_qty -= line["quantity"]
        v.save(update_fields=["stock_qty"])

    return order


@transaction.atomic
def mark_paid(order, *, method, fail=False):
    if fail:
        raise PaymentSimulatedFailure("Simulated payment failure.")
    if order.status != Order.Status.PENDING:
        return order
    order.status = Order.Status.PAID
    order.payment_method = method
    order.payment_reference = "SIM-" + secrets.token_hex(4).upper()
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "payment_method", "payment_reference", "paid_at"])
    return order


@transaction.atomic
def cancel_order(order):
    if order.status not in (Order.Status.PENDING, Order.Status.PAID):
        raise OrderNotCancellable(f"Cannot cancel an order in status {order.status}.")
    for item in order.items.select_related("variant"):
        variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
        variant.stock_qty += item.quantity
        variant.save(update_fields=["stock_qty"])
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status"])
    return order


def place_order(*, user, cart, address, method, simulate_fail=False):
    """Create + pay for an order as one unit. On ``simulate_fail`` nothing is
    written and the cart is left intact (the raise happens before any DB work).
    The cart is cleared only after the transaction commits."""
    if simulate_fail:
        raise PaymentSimulatedFailure("Simulated payment failure.")
    with transaction.atomic():
        order = create_order_from_cart(user=user, cart=cart, address=address)
        mark_paid(order, method=method)
    cart.clear()
    return order
