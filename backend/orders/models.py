from decimal import Decimal

from django.conf import settings
from django.db import models


class DailyOrderSequence(models.Model):
    """Per-day counter for order numbers; one row per calendar date."""

    date = models.DateField(unique=True)
    last_value = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.date:%Y%m%d}: {self.last_value}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        PROCESSING = "PROCESSING", "Processing"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=20, blank=True)
    payment_reference = models.CharField(max_length=40, blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=12, decimal_places=2)

    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=13)
    city_district = models.CharField(max_length=100)
    street_area = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True)
    address = models.ForeignKey(
        "accounts.Address", null=True, blank=True, on_delete=models.SET_NULL
    )

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # -id tiebreaker: two orders placed in the same microsecond would
        # otherwise fall back to DB insert order, making pagination unstable.
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("catalogue.ProductVariant", on_delete=models.PROTECT)
    product_title = models.CharField(max_length=200)
    variant_label = models.CharField(max_length=120, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} × {self.product_title}"
