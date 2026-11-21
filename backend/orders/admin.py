from django.contrib import admin

from .models import DailyOrderSequence, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["variant", "product_title", "variant_label", "quantity", "unit_price"]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user", "status", "total", "payment_method", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["order_number", "recipient_phone", "recipient_name"]
    readonly_fields = [
        "order_number", "user", "subtotal", "delivery_fee", "total", "address",
        "recipient_name", "recipient_phone", "city_district", "street_area", "landmark",
        "payment_method", "payment_reference", "created_at", "paid_at",
    ]
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product_title", "variant_label", "quantity", "unit_price"]
    search_fields = ["order__order_number", "product_title"]


@admin.register(DailyOrderSequence)
class DailyOrderSequenceAdmin(admin.ModelAdmin):
    list_display = ["date", "last_value"]
