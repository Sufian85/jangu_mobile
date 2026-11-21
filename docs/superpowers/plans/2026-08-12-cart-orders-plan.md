# Cart & Orders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `orders` app — `Cart`/`CartItem`/`Order`/`OrderItem` models, and the customer-facing cart + order API (add/update/remove cart items, create an order from the cart, view/cancel own orders) — per `docs/superpowers/specs/2026-08-12-cart-orders-design.md`.

**Architecture:** One new Django app, `orders`, layered like `accounts`/`catalogue`: models → serializers → views → urls → admin. Every endpoint requires `IsAuthenticated` and is scoped to `request.user`'s own `Cart`/`Order`s — no staff API in this sub-project (unlike `catalogue`), staff use Django Admin in the meantime.

**Tech Stack:** Django 5.2, DRF — no new third-party dependencies. Reuses the project-wide `DEFAULT_PAGINATION_CLASS` (set in the catalogue sub-project) for order history pagination. No git commands in any step (matches this project's existing convention — do not run `git add`/`git commit`).

**Paths used throughout:**
- Venv: `/Users/mac/projects/jango_mobileapp/.venv`
- Django project root (where `manage.py` lives): `/Users/mac/projects/jango_mobileapp/backend`
- App package: `/Users/mac/projects/jango_mobileapp/backend/orders`

---

### Task 1: Orders app skeleton + Cart + CartItem models (TDD, first migration)

**Files:**
- Create: `backend/orders/__init__.py`
- Create: `backend/orders/apps.py`
- Create: `backend/orders/models.py`
- Create: `backend/orders/tests/__init__.py`
- Create: `backend/orders/tests/test_models.py`
- Modify: `backend/backend/settings.py`

- [ ] **Step 1: Write the failing tests**

`orders/tests/test_models.py`:
```python
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import User
from catalogue.models import Category, Product, ProductVariant
from orders.models import Cart, CartItem


class CartModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )

    def test_cart_created_for_user(self):
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(cart.user, self.user)

    def test_one_cart_per_user(self):
        Cart.objects.create(user=self.user)
        with self.assertRaises(IntegrityError):
            Cart.objects.create(user=self.user)


class CartItemModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.cart = Cart.objects.create(user=self.user)
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128", price="450000.00", stock_qty=10
        )

    def test_default_quantity_is_one(self):
        item = CartItem.objects.create(cart=self.cart, variant=self.variant)
        self.assertEqual(item.quantity, 1)

    def test_duplicate_variant_in_same_cart_raises_integrity_error(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=1)
        with self.assertRaises(IntegrityError):
            CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)

    def test_quantity_must_be_at_least_one(self):
        from django.core.exceptions import ValidationError

        item = CartItem(cart=self.cart, variant=self.variant, quantity=0)
        with self.assertRaises(ValidationError):
            item.full_clean()
```

`orders/__init__.py`, `orders/tests/__init__.py`: empty files.

- [ ] **Step 2: Add orders to INSTALLED_APPS, run tests to verify they fail**

`orders/apps.py`:
```python
from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orders"
```

Modify `settings.py` `INSTALLED_APPS`, adding `"orders",` after `"catalogue",`.

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders`
Expected: FAIL with `ModuleNotFoundError: No module named 'orders.models'`.

- [ ] **Step 3: Write the implementation**

`orders/models.py`:
```python
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from catalogue.models import ProductVariant


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart({self.user})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("cart", "variant")]

    def __str__(self):
        return f"{self.variant.sku} x{self.quantity}"
```

`Cart.user` is a `OneToOneField` (one cart per user, auto-created on first API access — no explicit "create cart" endpoint). `CartItem.variant` is `CASCADE`, not `PROTECT`: a cart is not a historical record, so removing a variant from the catalogue should simply drop it from any cart that had it — contrast with `OrderItem.variant` below, which does need `PROTECT`.

- [ ] **Step 4: Create and run the migration**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py makemigrations orders`
Expected: creates `orders/migrations/0001_initial.py` defining `Cart` and `CartItem`.

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py migrate`
Expected: applies the new migration with no errors.

- [ ] **Step 5: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders`
Expected: `OK` (5 tests pass).

---

### Task 2: Order + OrderItem models with order-number generation (TDD, migration)

**Files:**
- Modify: `backend/orders/models.py`
- Modify: `backend/orders/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

Change the import block at the top of `orders/tests/test_models.py` to:
```python
from decimal import Decimal

from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from accounts.models import User
from catalogue.models import Category, Product, ProductVariant
from orders.models import Cart, CartItem, Order, OrderItem
```

Append to `orders/tests/test_models.py`:
```python
class OrderModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )

    def _make_order(self):
        return Order.objects.create(
            user=self.user,
            subtotal=Decimal("450000.00"),
            total=Decimal("450000.00"),
            recipient_name="Ada Lovelace",
            recipient_phone="+256771234567",
            city_district="Kampala",
            street_area="Kololo",
        )

    def test_order_number_auto_generated(self):
        order = self._make_order()
        self.assertTrue(order.order_number.startswith("JNG-"))

    def test_order_number_increments_within_same_day(self):
        first = self._make_order()
        second = self._make_order()
        self.assertNotEqual(first.order_number, second.order_number)
        first_seq = int(first.order_number.split("-")[-1])
        second_seq = int(second.order_number.split("-")[-1])
        self.assertEqual(second_seq, first_seq + 1)

    def test_status_defaults_to_pending(self):
        order = self._make_order()
        self.assertEqual(order.status, Order.STATUS_PENDING)

    def test_str_returns_order_number(self):
        order = self._make_order()
        self.assertEqual(str(order), order.order_number)


class OrderItemModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128", price=Decimal("450000.00"), stock_qty=10
        )
        self.order = Order.objects.create(
            user=self.user,
            subtotal=Decimal("450000.00"),
            total=Decimal("450000.00"),
            recipient_name="Ada Lovelace",
            recipient_phone="+256771234567",
            city_district="Kampala",
            street_area="Kololo",
        )

    def test_variant_protected_on_delete(self):
        OrderItem.objects.create(
            order=self.order, variant=self.variant, quantity=1, unit_price=Decimal("450000.00")
        )
        with self.assertRaises(ProtectedError):
            self.variant.delete()

    def test_unit_price_is_stored_independently_of_variant_price(self):
        item = OrderItem.objects.create(
            order=self.order, variant=self.variant, quantity=1, unit_price=Decimal("450000.00")
        )
        self.variant.price = Decimal("500000.00")
        self.variant.save()
        item.refresh_from_db()
        self.assertEqual(item.unit_price, Decimal("450000.00"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_models.OrderModelTests`
Expected: FAIL with `ImportError: cannot import name 'Order' from 'orders.models'`.

- [ ] **Step 3: Write the implementation**

Change the top import line of `orders/models.py` from `from django.db import models` to:
```python
from datetime import date

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction

from catalogue.models import ProductVariant
```

Append to `orders/models.py`:
```python
def _generate_order_number():
    today_str = date.today().strftime("%Y%m%d")
    prefix = f"JNG-{today_str}-"
    with transaction.atomic():
        count = (
            Order.objects.select_for_update()
            .filter(order_number__startswith=prefix)
            .count()
        )
    return f"{prefix}{count + 1:04d}"


class Order(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_PAID = "PAID"
    STATUS_PROCESSING = "PROCESSING"
    STATUS_SHIPPED = "SHIPPED"
    STATUS_DELIVERED = "DELIVERED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=13)
    city_district = models.CharField(max_length=100)
    street_area = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True)
    address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = _generate_order_number()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="order_items"
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.variant.sku} x{self.quantity}"
```

`_generate_order_number` is defined before `Order` but only *calls* `Order.objects` inside its body, which isn't evaluated until the function actually runs (by which point the module has finished loading and `Order` exists) — this is the standard, safe way to have same-module forward references in Python, avoiding the circular-import problem a separate `utils.py` would have (a module-level helper needing to query the very model that would need to import that helper). The `select_for_update()` inside `transaction.atomic()` makes the per-day counter race-safe under concurrent order creation. `OrderItem.variant` uses `on_delete=models.PROTECT` — mirrors the existing `Product.category` PROTECT precedent from the catalogue sub-project: staff cannot delete a variant that has order history.

- [ ] **Step 4: Create and run the migration**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py makemigrations orders`
Expected: creates `orders/migrations/0002_order_orderitem.py` (exact filename may vary slightly — Django auto-names it from the new models).

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py migrate`
Expected: applies the new migration with no errors.

- [ ] **Step 5: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders`
Expected: `OK` (11 tests pass).

---

### Task 3: Django Admin registration (TDD)

**Files:**
- Create: `backend/orders/admin.py`
- Create: `backend/orders/tests/test_admin.py`

- [ ] **Step 1: Write the failing tests**

`orders/tests/test_admin.py`:
```python
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from orders.models import Cart


class OrdersAdminAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.customer = User.objects.create_user(
            phone="0709876543", password="strongpass123", first_name="Grace", last_name="Hopper"
        )
        Cart.objects.create(user=self.staff_user)

    def test_staff_can_access_cart_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:orders_cart_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_access_order_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:orders_order_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_redirected_from_order_changelist(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("admin:orders_order_changelist"))
        self.assertEqual(response.status_code, 302)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_admin`
Expected: FAIL with `NoReverseMatch` (models not registered in admin).

- [ ] **Step 3: Write the implementation**

`orders/admin.py`:
```python
from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at"]
    search_fields = ["user__phone"]
    inlines = [CartItemInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user", "status", "total", "created_at"]
    list_filter = ["status"]
    search_fields = ["order_number", "user__phone"]
    inlines = [OrderItemInline]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_admin`
Expected: `OK` (3 tests pass).

---

### Task 4: Cart retrieve API — GET /api/cart/ (TDD)

**Files:**
- Create: `backend/orders/serializers.py`
- Create: `backend/orders/views.py`
- Create: `backend/orders/urls.py`
- Create: `backend/orders/tests/test_cart.py`
- Modify: `backend/backend/urls.py`

- [ ] **Step 1: Write the failing tests**

`orders/tests/test_cart.py`:
```python
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from catalogue.models import Category, Product, ProductVariant
from orders.models import Cart, CartItem


class CartViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128", price=Decimal("450000.00"), stock_qty=10
        )
        self.url = reverse("cart-detail")

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_creates_cart_if_missing(self):
        self.assertFalse(Cart.objects.filter(user=self.user).exists())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Cart.objects.filter(user=self.user).exists())

    def test_empty_cart_has_zero_subtotal(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["subtotal"], "0.00")

    def test_cart_reflects_live_variant_price(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=2)
        response = self.client.get(self.url)
        self.assertEqual(response.data["subtotal"], "900000.00")
        self.variant.price = Decimal("500000.00")
        self.variant.save()
        response = self.client.get(self.url)
        self.assertEqual(response.data["subtotal"], "1000000.00")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_cart`
Expected: FAIL with `NoReverseMatch: 'cart-detail' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

`orders/serializers.py`:
```python
from decimal import Decimal

from rest_framework import serializers

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    unit_price = serializers.DecimalField(
        source="variant.price", max_digits=10, decimal_places=2, read_only=True
    )
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "variant", "sku", "quantity", "unit_price", "line_total"]
        read_only_fields = ["id"]

    def get_line_total(self, obj):
        return str(obj.variant.price * obj.quantity)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "subtotal"]

    def get_subtotal(self, obj):
        total = sum(
            (item.variant.price * item.quantity for item in obj.items.all()),
            Decimal("0.00"),
        )
        return str(total)
```

`unit_price`/`line_total`/`subtotal` are always computed from the variant's *current* price at read time — a `CartItem` stores no price of its own, so a product's price change is reflected immediately in every cart that contains it (contrast with `OrderItem.unit_price`, a real snapshot). `get_line_total`/`get_subtotal` return `str(...)` to match this project's existing convention of rendering monetary values as decimal strings (the same shape a real `DecimalField` produces).

`orders/views.py`:
```python
from rest_framework import generics, permissions

from .models import Cart
from .serializers import CartSerializer


class CartView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer

    def get_object(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart
```

`orders/urls.py`:
```python
from django.urls import path

from .views import CartView

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart-detail"),
]
```

Modify `backend/urls.py` to add one line, `path("api/", include("orders.urls")),`, right after the existing `path("api/", include("catalogue.urls")),` line (Django tries multiple `include()`s under the same prefix in order — `catalogue.urls` and `orders.urls` define disjoint paths, `categories/`/`products/` vs `cart/`/`orders/`, so there's no collision):
```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("catalogue.urls")),
    path("api/", include("orders.urls")),
    path("api/staff/catalogue/", include("catalogue.staff_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_cart`
Expected: `OK` (4 tests pass).

---

### Task 5: CartItem add/update/remove API (TDD)

**Files:**
- Modify: `backend/orders/serializers.py`
- Modify: `backend/orders/views.py`
- Modify: `backend/orders/urls.py`
- Modify: `backend/orders/tests/test_cart.py`

- [ ] **Step 1: Write the failing tests**

Change the import block at the top of `orders/tests/test_cart.py` to:
```python
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from catalogue.models import Category, Product, ProductVariant
from orders.models import Cart, CartItem
```
(unchanged — already correct from Task 4, no edit needed if it already matches this exactly).

Append to `orders/tests/test_cart.py`:
```python
class CartItemAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.other_user = User.objects.create_user(
            phone="0709876543", password="strongpass123", first_name="Grace", last_name="Hopper"
        )
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128", price=Decimal("450000.00"), stock_qty=5
        )
        self.list_url = reverse("cart-item-list")

    def test_add_item_creates_cart_item(self):
        response = self.client.post(self.list_url, {"variant": self.variant.id, "quantity": 2})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CartItem.objects.get(variant=self.variant).quantity, 2)

    def test_adding_same_variant_twice_increments_quantity(self):
        self.client.post(self.list_url, {"variant": self.variant.id, "quantity": 2})
        self.client.post(self.list_url, {"variant": self.variant.id, "quantity": 1})
        self.assertEqual(CartItem.objects.get(variant=self.variant).quantity, 3)

    def test_add_item_exceeding_stock_returns_400(self):
        response = self.client.post(self.list_url, {"variant": self.variant.id, "quantity": 10})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_updates_quantity(self):
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        detail_url = reverse("cart-item-detail", args=[item.pk])
        response = self.client.patch(detail_url, {"quantity": 3})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

    def test_patch_exceeding_stock_returns_400(self):
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        detail_url = reverse("cart-item-detail", args=[item.pk])
        response = self.client.patch(detail_url, {"quantity": 10})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_removes_item(self):
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        detail_url = reverse("cart-item-detail", args=[item.pk])
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())

    def test_cannot_modify_another_users_cart_item(self):
        other_cart = Cart.objects.create(user=self.other_user)
        other_item = CartItem.objects.create(cart=other_cart, variant=self.variant, quantity=1)
        detail_url = reverse("cart-item-detail", args=[other_item.pk])
        response = self.client.patch(detail_url, {"quantity": 3})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.list_url, {"variant": self.variant.id, "quantity": 1})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_cart.CartItemAPITests`
Expected: FAIL with `NoReverseMatch: 'cart-item-list' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Append to `orders/serializers.py`:
```python
class CartItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["id", "variant", "quantity"]
        read_only_fields = ["id"]
```

Replace `orders/views.py` with:
```python
from rest_framework import generics, mixins, permissions, serializers, viewsets

from .models import Cart, CartItem
from .serializers import CartItemWriteSerializer, CartSerializer


class CartView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer

    def get_object(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart


class CartItemViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartItemWriteSerializer

    def get_queryset(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return CartItem.objects.filter(cart=cart)

    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        variant = serializer.validated_data["variant"]
        existing = CartItem.objects.filter(cart=cart, variant=variant).first()
        if existing:
            new_quantity = existing.quantity + serializer.validated_data["quantity"]
            self._validate_stock(variant, new_quantity)
            existing.quantity = new_quantity
            existing.save()
            serializer.instance = existing
        else:
            self._validate_stock(variant, serializer.validated_data["quantity"])
            serializer.save(cart=cart)

    def perform_update(self, serializer):
        new_quantity = serializer.validated_data.get("quantity", serializer.instance.quantity)
        self._validate_stock(serializer.instance.variant, new_quantity)
        serializer.save()

    def _validate_stock(self, variant, quantity):
        if quantity > variant.stock_qty:
            raise serializers.ValidationError({"quantity": "Not enough stock available."})
```

`CartItemViewSet` deliberately mixes in only Create/Update/Destroy — no List/Retrieve — since the spec calls for `POST`/`PATCH`/`DELETE` on `/cart/items/` only (`GET /cart/` from Task 4 already shows items nested). The router (below) will only generate routes for actions the viewset actually has. `perform_create` merges into an existing line (incrementing quantity) rather than erroring on a duplicate variant — matches `CartItem`'s `unique_together` constraint and the spec's "increments quantity if the variant's already present" behavior. Both create and update re-validate stock against the *target* quantity (soft check, not a reservation — matches Task 4's live-pricing philosophy: nothing about the cart is locked in).

Replace `orders/urls.py` with:
```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CartItemViewSet, CartView

router = DefaultRouter()
router.register("cart/items", CartItemViewSet, basename="cart-item")

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart-detail"),
    path("", include(router.urls)),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_cart`
Expected: `OK` (12 tests pass).

---

### Task 6: Order creation API — POST /api/orders/ (TDD)

**Files:**
- Modify: `backend/orders/serializers.py`
- Modify: `backend/orders/views.py`
- Modify: `backend/orders/urls.py`
- Create: `backend/orders/tests/test_orders.py`

- [ ] **Step 1: Write the failing tests**

`orders/tests/test_orders.py`:
```python
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Address, User
from catalogue.models import Category, Product, ProductVariant
from orders.models import Cart, CartItem, Order


class OrderCreateViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.other_user = User.objects.create_user(
            phone="0709876543", password="strongpass123", first_name="Grace", last_name="Hopper"
        )
        self.client.force_authenticate(user=self.user)
        self.address = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128", price=Decimal("450000.00"), stock_qty=5
        )
        self.cart = Cart.objects.create(user=self.user)
        self.url = reverse("order-list")

    def test_create_order_from_cart(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)
        response = self.client.post(self.url, {"address_id": self.address.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["total"], "900000.00")
        self.assertEqual(len(response.data["items"]), 1)

    def test_create_order_clears_cart(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)
        self.client.post(self.url, {"address_id": self.address.id})
        self.assertEqual(self.cart.items.count(), 0)

    def test_create_order_decrements_stock(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)
        self.client.post(self.url, {"address_id": self.address.id})
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 3)

    def test_create_order_snapshots_address(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=1)
        self.client.post(self.url, {"address_id": self.address.id})
        order = Order.objects.get(user=self.user)
        self.address.street_area = "Nakasero"
        self.address.save()
        order.refresh_from_db()
        self.assertEqual(order.street_area, "Kololo")

    def test_create_order_with_empty_cart_returns_400(self):
        response = self.client.post(self.url, {"address_id": self.address.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_with_insufficient_stock_returns_400_and_creates_nothing(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=10)
        response = self.client.post(self.url, {"address_id": self.address.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 5)

    def test_create_order_with_another_users_address_returns_400(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=1)
        other_address = Address.objects.create(
            user=self.other_user,
            recipient_name="Grace Hopper",
            recipient_phone="0709876543",
            city_district="Entebbe",
            street_area="Main St",
        )
        response = self.client.post(self.url, {"address_id": other_address.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {"address_id": self.address.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_orders`
Expected: FAIL with `NoReverseMatch: 'order-list' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Change the top of `orders/serializers.py` to:
```python
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from accounts.models import Address
from catalogue.models import ProductVariant

from .models import Cart, CartItem, Order, OrderItem
```

Append to `orders/serializers.py`:
```python
class OrderItemSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_title = serializers.CharField(source="variant.product.title", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "variant", "sku", "product_title", "quantity", "unit_price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "status", "subtotal", "delivery_fee", "total",
            "recipient_name", "recipient_phone", "city_district", "street_area",
            "landmark", "created_at", "items",
        ]


class OrderCreateSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()

    def validate_address_id(self, value):
        request = self.context["request"]
        try:
            address = Address.objects.get(pk=value, user=request.user)
        except Address.DoesNotExist:
            raise serializers.ValidationError("Address not found.")
        return address

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        address = validated_data["address_id"]
        cart = get_object_or_404(Cart, user=user)
        items = list(cart.items.select_related("variant").all())
        if not items:
            raise serializers.ValidationError({"cart": "Cart is empty."})

        with transaction.atomic():
            variant_ids = [item.variant_id for item in items]
            locked_variants = {
                v.pk: v
                for v in ProductVariant.objects.select_for_update().filter(pk__in=variant_ids)
            }
            insufficient = [
                item for item in items if item.quantity > locked_variants[item.variant_id].stock_qty
            ]
            if insufficient:
                raise serializers.ValidationError(
                    {
                        "items": [
                            f"{item.variant.sku}: only "
                            f"{locked_variants[item.variant_id].stock_qty} in stock."
                            for item in insufficient
                        ]
                    }
                )

            subtotal = sum(
                (locked_variants[item.variant_id].price * item.quantity for item in items),
                Decimal("0.00"),
            )
            order = Order.objects.create(
                user=user,
                subtotal=subtotal,
                total=subtotal,
                recipient_name=address.recipient_name,
                recipient_phone=address.recipient_phone,
                city_district=address.city_district,
                street_area=address.street_area,
                landmark=address.landmark,
                address=address,
            )
            for item in items:
                variant = locked_variants[item.variant_id]
                OrderItem.objects.create(
                    order=order, variant=variant, quantity=item.quantity, unit_price=variant.price
                )
                variant.stock_qty -= item.quantity
                variant.save()
            cart.items.all().delete()
        return order
```

`validate_address_id` returns the resolved `Address` *instance*, not the raw id — DRF stores whatever a field-level `validate_<field>` returns into `validated_data`, so `create()` gets a ready-to-use object. Scoping the lookup to `user=request.user` means an `address_id` belonging to another user 404s into a clean "not found" `ValidationError` rather than ever touching someone else's data. Stock is re-validated (the real reservation moment — no payment gateway to hook a later reservation to) under `select_for_update()` on the specific variants involved, inside the same transaction as the order/items/decrement/cart-clear — any failure (insufficient stock) raises before anything is written, and any failure after that point rolls back the whole transaction, so a request never leaves a partial order behind.

Replace the top of `orders/views.py` with:
```python
from rest_framework import generics, mixins, permissions, serializers, status, viewsets
from rest_framework.response import Response

from .models import Cart, CartItem
from .serializers import (
    CartItemWriteSerializer,
    CartSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)
```

Append to `orders/views.py`:
```python
class OrderCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
```

Modify `orders/urls.py`:
```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CartItemViewSet, CartView, OrderCreateView

router = DefaultRouter()
router.register("cart/items", CartItemViewSet, basename="cart-item")

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart-detail"),
    path("orders/", OrderCreateView.as_view(), name="order-list"),
    path("", include(router.urls)),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_orders`
Expected: `OK` (8 tests pass).

---

### Task 7: Order list/detail API (TDD)

**Files:**
- Modify: `backend/orders/views.py`
- Modify: `backend/orders/urls.py`
- Modify: `backend/orders/tests/test_orders.py`

- [ ] **Step 1: Write the failing tests**

Append to `orders/tests/test_orders.py`:
```python
class OrderListDetailTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.other_user = User.objects.create_user(
            phone="0709876543", password="strongpass123", first_name="Grace", last_name="Hopper"
        )
        self.client.force_authenticate(user=self.user)

    def _make_order(self, user):
        return Order.objects.create(
            user=user,
            subtotal=Decimal("450000.00"),
            total=Decimal("450000.00"),
            recipient_name="Ada Lovelace",
            recipient_phone="+256771234567",
            city_district="Kampala",
            street_area="Kololo",
        )

    def test_list_returns_only_own_orders(self):
        self._make_order(self.user)
        self._make_order(self.other_user)
        response = self.client.get(reverse("order-list"))
        self.assertEqual(response.data["count"], 1)

    def test_detail_returns_own_order(self):
        order = self._make_order(self.user)
        response = self.client.get(reverse("order-detail", args=[order.order_number]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order_number"], order.order_number)

    def test_cannot_view_another_users_order(self):
        order = self._make_order(self.other_user)
        response = self.client.get(reverse("order-detail", args=[order.order_number]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_ordered_newest_first(self):
        first = self._make_order(self.user)
        second = self._make_order(self.user)
        response = self.client.get(reverse("order-list"))
        self.assertEqual(response.data["results"][0]["order_number"], second.order_number)

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("order-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_orders.OrderListDetailTests`
Expected: FAIL with `NoReverseMatch: 'order-detail' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Replace `OrderCreateView` in `orders/views.py` with `OrderViewSet` (change the top import line from `from .models import Cart, CartItem` to `from .models import Cart, CartItem, Order`, keep everything else at the top of the file the same):
```python
from rest_framework import generics, mixins, permissions, serializers, status, viewsets
from rest_framework.response import Response

from .models import Cart, CartItem, Order
from .serializers import (
    CartItemWriteSerializer,
    CartSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)
```

Remove the `OrderCreateView` class from `orders/views.py` and replace it with:
```python
class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "order_number"

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
```

`OrderViewSet` supersedes Task 6's standalone `OrderCreateView` now that list/retrieve need to live on the same `orders/` URL — `lookup_field = "order_number"` makes `/orders/{order_number}/` the detail URL instead of a numeric pk. `get_queryset` scopes every action (list, retrieve, *and* the object lookup `create`'s sibling actions would use) to `request.user`'s own orders, so another user's order 404s rather than 403s — same pattern used throughout `accounts`/`catalogue`. List pagination comes from the project-wide `DEFAULT_PAGINATION_CLASS` (no override needed) and "newest first" from `Order.Meta.ordering` (set in Task 2) — both already in place, nothing extra needed here.

Replace `orders/urls.py` with:
```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CartItemViewSet, CartView, OrderViewSet

router = DefaultRouter()
router.register("cart/items", CartItemViewSet, basename="cart-item")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart-detail"),
    path("", include(router.urls)),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_orders`
Expected: `OK` (13 tests pass).

---

### Task 8: Order cancel API (TDD)

**Files:**
- Modify: `backend/orders/views.py`
- Modify: `backend/orders/tests/test_orders.py`

- [ ] **Step 1: Write the failing tests**

Change the import block at the top of `orders/tests/test_orders.py` to:
```python
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Address, User
from catalogue.models import Category, Product, ProductVariant
from orders.models import Cart, CartItem, Order, OrderItem
```

Append to `orders/tests/test_orders.py`:
```python
class OrderCancelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128", price=Decimal("450000.00"), stock_qty=3
        )
        self.order = Order.objects.create(
            user=self.user,
            subtotal=Decimal("450000.00"),
            total=Decimal("450000.00"),
            recipient_name="Ada Lovelace",
            recipient_phone="+256771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        OrderItem.objects.create(
            order=self.order, variant=self.variant, quantity=2, unit_price=Decimal("450000.00")
        )
        self.url = reverse("order-cancel", args=[self.order.order_number])

    def test_cancel_pending_order_restores_stock(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 5)

    def test_cancel_pending_order_sets_status_cancelled(self):
        self.client.post(self.url)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_CANCELLED)

    def test_cannot_cancel_non_pending_order(self):
        self.order.status = Order.STATUS_PAID
        self.order.save()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_qty, 3)

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_orders.OrderCancelTests`
Expected: FAIL with `NoReverseMatch: 'order-cancel' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Change the top of `orders/views.py` to:
```python
from django.db import transaction
from rest_framework import generics, mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from catalogue.models import ProductVariant
from .models import Cart, CartItem, Order
from .serializers import (
    CartItemWriteSerializer,
    CartSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)
```

Append to the `OrderViewSet` class in `orders/views.py` (add this method inside the existing class, after `create`):
```python
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, order_number=None):
        order = self.get_object()
        if order.status != Order.STATUS_PENDING:
            return Response(
                {"detail": "Only pending orders can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            variant_ids = [item.variant_id for item in order.items.all()]
            locked_variants = {
                v.pk: v
                for v in ProductVariant.objects.select_for_update().filter(pk__in=variant_ids)
            }
            for item in order.items.all():
                variant = locked_variants[item.variant_id]
                variant.stock_qty += item.quantity
                variant.save()
            order.status = Order.STATUS_CANCELLED
            order.save()
        return Response(OrderSerializer(order).data)
```

`self.get_object()` reuses `get_queryset`'s user-scoping, so cancelling another user's order 404s the same way viewing one does. Stock is restored under the same `select_for_update()` pattern used for order creation, inside one transaction with the status flip — no separate "partially cancelled" state is reachable.

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test orders.tests.test_orders`
Expected: `OK` (17 tests pass).

---

### Task 9: Full test suite run

**Files:** none

- [ ] **Step 1: Run the entire suite**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test`
Expected: `OK` — 163 tests total (120 pre-existing from `core`/`accounts`/`catalogue` + 43 new from `orders`: 5 Cart/CartItem model + 6 Order/OrderItem model + 3 admin + 4 cart retrieve + 8 cart item API + 8 order create + 5 order list/detail + 4 order cancel).

- [ ] **Step 2: Final config sanity check**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py check`
Expected: `System check identified no issues (0 silenced).`
