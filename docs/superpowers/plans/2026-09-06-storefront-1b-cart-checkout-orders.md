# Jangu Storefront — Phase 1b (Cart, Checkout, Orders) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A shopper can add gadgets to a cart, register/log in, choose a delivery address, "pay" via a simulated gateway, and see an order confirmation — with durable `Order`/`OrderItem` records and transactional stock handling.

**Architecture:** New `orders` Django app owns the domain: `Order`/`OrderItem`/`DailyOrderSequence` models, a `SessionCart` over `request.session`, a transactional service layer, and admin. The `storefront` app gets cart / auth / checkout / payment / confirmation views + templates that call `orders.services`. No REST API this phase. Payment is simulated (method choice + a "Pay" button; a `?simulate=fail` affordance for tests).

**Tech Stack:** Django 5.2 templates + `django.contrib.auth` session auth over the existing phone-keyed `accounts.User`; `orders` service layer with `@transaction.atomic`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-06-storefront-milestone-1-design.md` — this plan covers phase **1b** from §12. Phase 1a is merged to `main`. Phase 1c (account dashboard, order history, standalone address book) gets its own plan.

**Deviations from spec (intentional, decided while planning):**
- **Auth pages move from 1c to 1b.** Checkout is `@login_required` and needs a real login/register path, so `register` / `login` / `logout` views + templates ship here. 1c keeps the account dashboard, order history + cancel, and the standalone address book.
- **`order_number` uses a `DailyOrderSequence` counter row with `select_for_update`** (spec §5.2's stated acceptable alternative), not the retry-on-`IntegrityError` loop — a failed INSERT inside `transaction.atomic()` poisons the transaction on Postgres, and the counter row is simpler and race-safe on every backend.
- **Payment-failure simulation raises *before* any DB work** (`services.place_order` early-raises on `simulate_fail`), so "creates no order" also means the cart and stock are untouched — no mid-transaction rollback of a session mutation.
- **`variant_label` string is duplicated** (one line) in `orders.services` rather than importing `storefront.templatetags`, to keep `orders` free of a `storefront` dependency.
- Checkout uses an inline `AddressForm` + a radio list of existing addresses on one page; no separate address-book page in 1b (that's 1c).

Every command assumes: `cd /Users/mac/projects/jango_mobileapp && source .venv/bin/activate`; `manage.py` runs from `backend/`.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/orders/apps.py` | `OrdersConfig` |
| `backend/orders/models.py` | `Order`, `OrderItem`, `DailyOrderSequence`, `Order.Status` |
| `backend/orders/migrations/0001_initial.py` | generated schema |
| `backend/orders/exceptions.py` | `EmptyCartError`, `InsufficientStockError`, `AddressOwnershipError`, `PaymentSimulatedFailure`, `OrderNotCancellable` |
| `backend/orders/cart.py` | `SessionCart` — session-backed cart with live pricing |
| `backend/orders/services.py` | `create_order_from_cart`, `mark_paid`, `cancel_order`, `place_order` |
| `backend/orders/admin.py` | `OrderAdmin` + `OrderItemInline` |
| `backend/orders/tests/factories.py` | `make_user`, `make_variant`, `make_address`, `make_request` |
| `backend/orders/tests/test_models.py` | model behavior |
| `backend/orders/tests/test_cart.py` | `SessionCart` |
| `backend/orders/tests/test_services.py` | service layer |
| `backend/orders/tests/test_admin.py` | admin smoke |
| `backend/storefront/forms.py` | `AddToCartForm`, `UpdateCartForm`, `RegisterForm`, `PhoneAuthenticationForm`, `AddressForm` |
| `backend/storefront/views/cart.py` | `detail`, `add`, `update`, `remove` |
| `backend/storefront/views/auth.py` | `register`, `StorefrontLoginView`, `logout_view` |
| `backend/storefront/views/checkout.py` | `checkout`, `payment`, `order_confirmation` |
| `backend/storefront/context_processors.py` | upgrade `cart_summary` to `SessionCart` (`cart_count` + `cart_subtotal`) |
| `backend/storefront/urls.py` | + cart / auth / checkout routes |
| `backend/storefront/templates/storefront/` | `cart.html`, `checkout.html`, `payment.html`, `order_confirmation.html`, `auth/login.html`, `auth/register.html`, `partials/order_summary.html` |
| `backend/storefront/templates/storefront/product_detail.html` | wire the real Add-to-Cart form |
| `backend/storefront/templates/storefront/partials/{header,bottom_nav}.html` | repoint Cart / Account links |
| `backend/storefront/tests/{test_cart,test_auth,test_checkout}.py` | storefront-level flows |
| `backend/backend/settings.py` | `INSTALLED_APPS += "orders"` |

---

## Task 1: Branch + `orders` app skeleton + config

**Files:** Create `backend/orders/{__init__,apps}.py`, `backend/orders/tests/__init__.py`. Modify `backend/backend/settings.py`.

- [ ] **Step 1: Branch**
```bash
cd /Users/mac/projects/jango_mobileapp
git switch -c storefront/milestone-1b
```
Expected: `Switched to a new branch 'storefront/milestone-1b'`

- [ ] **Step 2: Create package files**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
mkdir -p orders/tests
touch orders/__init__.py orders/tests/__init__.py
```

- [ ] **Step 3: `backend/orders/apps.py`**
```python
from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "orders"
```

- [ ] **Step 4: `backend/orders/models.py`** (temporary stub so the app imports; real models in Task 2)
```python
# Models are added in Task 2.
```

- [ ] **Step 5: settings** — add `"orders"` to `INSTALLED_APPS` immediately after `"storefront"`:
```python
    "catalogue",
    "storefront",
    "orders",
]
```

- [ ] **Step 6: Verify**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py check
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `check` clean; `Ran 160 tests` / `OK`.

- [ ] **Step 7: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add -A
git commit -m "feat(orders): scaffold app, register in INSTALLED_APPS"
```

---

## Task 2: `orders` models + migration

**Files:** Modify `backend/orders/models.py`. Create `backend/orders/tests/factories.py`, `backend/orders/tests/test_models.py`, `backend/orders/migrations/` (generated).

- [ ] **Step 1: `backend/orders/tests/factories.py`**
```python
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
```

- [ ] **Step 2: Write the failing test** — `backend/orders/tests/test_models.py`
```python
from decimal import Decimal

from django.test import TestCase

from orders.models import DailyOrderSequence, Order, OrderItem
from orders.tests.factories import make_address, make_user, make_variant


class OrderModelTests(TestCase):
    def _order(self, **kw):
        user = kw.pop("user", None) or make_user()
        defaults = dict(
            user=user, order_number="JNG-20260906-0001", subtotal=Decimal("0"),
            total=Decimal("0"), recipient_name="Ada", recipient_phone="+256772000009",
            city_district="Kampala", street_area="Kololo",
        )
        defaults.update(kw)
        return Order.objects.create(**defaults)

    def test_str_is_order_number(self):
        self.assertEqual(str(self._order()), "JNG-20260906-0001")

    def test_status_defaults_to_pending(self):
        self.assertEqual(self._order().status, Order.Status.PENDING)

    def test_delivery_fee_defaults_to_zero(self):
        self.assertEqual(self._order().delivery_fee, Decimal("0"))

    def test_order_number_is_unique(self):
        self._order()
        with self.assertRaises(Exception):
            self._order(user=make_user(phone="+256772000002"))

    def test_orders_ordered_newest_first(self):
        a = self._order(order_number="JNG-20260906-0001")
        b = self._order(order_number="JNG-20260906-0002", user=make_user(phone="+256772000002"))
        self.assertEqual(list(Order.objects.all()), [b, a])


class OrderItemModelTests(TestCase):
    def test_line_total_is_unit_price_times_quantity(self):
        user = make_user()
        order = Order.objects.create(
            user=user, order_number="JNG-20260906-0009", subtotal=Decimal("0"),
            total=Decimal("0"), recipient_name="Ada", recipient_phone="+256772000009",
            city_district="Kampala", street_area="Kololo",
        )
        variant = make_variant(price="1500000")
        item = OrderItem.objects.create(
            order=order, variant=variant, product_title="Widget", variant_label="128GB / Black",
            quantity=3, unit_price=Decimal("1500000"),
        )
        self.assertEqual(item.line_total, Decimal("4500000"))


class DailyOrderSequenceTests(TestCase):
    def test_date_is_unique(self):
        import datetime
        DailyOrderSequence.objects.create(date=datetime.date(2026, 9, 6))
        with self.assertRaises(Exception):
            DailyOrderSequence.objects.create(date=datetime.date(2026, 9, 6))
```

- [ ] **Step 3: Run — verify it fails**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test orders.tests.test_models -v 2
```
Expected: import error — `orders.models` has no `Order`.

- [ ] **Step 4: Implement** — `backend/orders/models.py`
```python
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
        ordering = ["-created_at"]

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
```

- [ ] **Step 5: Make + apply migration**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py makemigrations orders
python manage.py migrate orders
```
Expected: creates `orders/migrations/0001_initial.py`; `migrate` applies it.

- [ ] **Step 6: Run — verify it passes**
```bash
python manage.py test orders.tests.test_models -v 2
```
Expected: `Ran 8 tests` … `OK`.

- [ ] **Step 7: Full suite**
```bash
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `Ran 168 tests` / `OK`.

- [ ] **Step 8: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/orders/models.py backend/orders/migrations backend/orders/tests
git commit -m "feat(orders): Order, OrderItem, DailyOrderSequence models"
```

---

## Task 3: `orders/exceptions.py` + `orders/cart.py` (SessionCart)

**Files:** Create `backend/orders/exceptions.py`, `backend/orders/cart.py`, `backend/orders/tests/test_cart.py`.

- [ ] **Step 1: `backend/orders/exceptions.py`**
```python
class OrdersError(Exception):
    """Base class for orders domain errors."""


class EmptyCartError(OrdersError):
    pass


class InsufficientStockError(OrdersError):
    """Carries a list of {'variant', 'requested', 'available'} dicts."""

    def __init__(self, shortfalls):
        self.shortfalls = shortfalls
        super().__init__(f"{len(shortfalls)} line(s) exceed available stock")


class AddressOwnershipError(OrdersError):
    pass


class PaymentSimulatedFailure(OrdersError):
    pass


class OrderNotCancellable(OrdersError):
    pass
```

- [ ] **Step 2: Write the failing test** — `backend/orders/tests/test_cart.py`
```python
from decimal import Decimal

from django.test import TestCase

from orders.cart import SessionCart
from orders.exceptions import InsufficientStockError
from orders.tests.factories import make_request, make_variant


class SessionCartTests(TestCase):
    def setUp(self):
        self.request = make_request()
        self.cart = SessionCart(self.request)
        self.v = make_variant(sku="A", price="1000000", stock_qty=5)

    def test_add_then_increment(self):
        self.cart.add(self.v, 2)
        self.cart.add(self.v, 1)
        self.assertEqual(len(self.cart), 3)

    def test_add_replace_sets_absolute(self):
        self.cart.add(self.v, 2)
        self.cart.add(self.v, 1, replace=True)
        self.assertEqual(len(self.cart), 1)

    def test_add_over_stock_raises_and_does_not_mutate(self):
        with self.assertRaises(InsufficientStockError):
            self.cart.add(self.v, 6)
        self.assertEqual(len(self.cart), 0)

    def test_set_quantity_absolute_and_zero_removes(self):
        self.cart.add(self.v, 2)
        self.cart.set_quantity(self.v.id, 4)
        self.assertEqual(len(self.cart), 4)
        self.cart.set_quantity(self.v.id, 0)
        self.assertEqual(len(self.cart), 0)

    def test_set_quantity_over_stock_raises(self):
        self.cart.add(self.v, 1)
        with self.assertRaises(InsufficientStockError):
            self.cart.set_quantity(self.v.id, 99)

    def test_remove_and_clear(self):
        self.cart.add(self.v, 2)
        self.cart.remove(self.v.id)
        self.assertEqual(len(self.cart), 0)
        self.cart.add(self.v, 1)
        self.cart.clear()
        self.assertEqual(len(self.cart), 0)

    def test_iter_yields_live_pricing_and_line_totals(self):
        self.cart.add(self.v, 3)
        (line,) = list(self.cart)
        self.assertEqual(line["variant"], self.v)
        self.assertEqual(line["quantity"], 3)
        self.assertEqual(line["unit_price"], Decimal("1000000"))
        self.assertEqual(line["line_total"], Decimal("3000000"))
        self.assertEqual(self.cart.subtotal, Decimal("3000000"))

    def test_iter_prunes_deleted_variant_ids(self):
        self.cart.add(self.v, 1)
        gone = make_variant(sku="B", stock_qty=1)
        self.request.session["cart"][str(gone.id)] = 1
        gone_id = gone.id
        gone.delete()
        lines = list(self.cart)
        self.assertEqual([l["variant"].id for l in lines], [self.v.id])
        self.assertNotIn(str(gone_id), self.request.session["cart"])
        self.assertTrue(self.request.session.modified)

    def test_marks_session_modified_on_write(self):
        self.request.session.modified = False
        self.cart.add(self.v, 1)
        self.assertTrue(self.request.session.modified)
```

- [ ] **Step 3: Run — verify it fails**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test orders.tests.test_cart -v 2
```
Expected: import error for `orders.cart`.

- [ ] **Step 4: Implement** — `backend/orders/cart.py`
```python
from decimal import Decimal

from catalogue.models import ProductVariant

from .exceptions import InsufficientStockError

SESSION_KEY = "cart"


class SessionCart:
    """A shopping cart persisted in ``request.session[SESSION_KEY]`` as
    ``{"<variant_id>": <int quantity>}``. Prices are always resolved live."""

    def __init__(self, request):
        self.session = request.session
        # `.get`, not `.setdefault` — reading a cart on a page that never
        # mutates it (admin, API, every catalogue page) must not write an
        # empty "cart" key into that visitor's session.
        self._items = dict(self.session.get(SESSION_KEY) or {})

    # -- mutation -----------------------------------------------------------
    def _touch(self):
        self.session[SESSION_KEY] = self._items
        self.session.modified = True

    def add(self, variant, qty=1, *, replace=False):
        key = str(variant.id)
        new_qty = qty if replace else self._items.get(key, 0) + qty
        if new_qty > variant.stock_qty:
            raise InsufficientStockError(
                [{"variant": variant, "requested": new_qty, "available": variant.stock_qty}]
            )
        self._items[key] = new_qty
        self._touch()

    def set_quantity(self, variant_id, qty):
        key = str(variant_id)
        if qty <= 0:
            self.remove(variant_id)
            return
        variant = ProductVariant.objects.filter(id=variant_id).first()
        if variant is None:
            self.remove(variant_id)
            return
        if qty > variant.stock_qty:
            raise InsufficientStockError(
                [{"variant": variant, "requested": qty, "available": variant.stock_qty}]
            )
        self._items[key] = qty
        self._touch()

    def remove(self, variant_id):
        if self._items.pop(str(variant_id), None) is not None:
            self._touch()

    def clear(self):
        self._items = {}
        self._touch()

    # -- reads ------------------------------------------------------------
    def __iter__(self):
        ids = [int(k) for k in self._items]
        variants = {v.id: v for v in ProductVariant.objects.filter(id__in=ids)}
        pruned = False
        for key in list(self._items):
            variant = variants.get(int(key))
            if variant is None:
                del self._items[key]
                pruned = True
                continue
            qty = self._items[key]
            yield {
                "variant": variant,
                "quantity": qty,
                "unit_price": variant.price,
                "line_total": variant.price * qty,
            }
        if pruned:
            self._touch()

    def __len__(self):
        return sum(self._items.values())

    @property
    def subtotal(self):
        return sum((line["line_total"] for line in self), Decimal("0"))
```

- [ ] **Step 5: Run — verify it passes**
```bash
python manage.py test orders.tests.test_cart -v 2
```
Expected: `Ran 9 tests` … `OK`.

- [ ] **Step 6: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/orders/exceptions.py backend/orders/cart.py backend/orders/tests/test_cart.py
git commit -m "feat(orders): SessionCart + domain exceptions"
```

---

## Task 4: `orders/services.py`

**Files:** Create `backend/orders/services.py`, `backend/orders/tests/test_services.py`.

- [ ] **Step 1: Write the failing test** — `backend/orders/tests/test_services.py`
```python
from decimal import Decimal

from django.test import TestCase

from orders import services
from orders.cart import SessionCart
from orders.exceptions import (
    AddressOwnershipError,
    EmptyCartError,
    InsufficientStockError,
    OrderNotCancellable,
    PaymentSimulatedFailure,
)
from orders.models import Order, OrderItem
from orders.tests.factories import make_address, make_request, make_user, make_variant


class CreateOrderFromCartTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)
        self.request = make_request()
        self.cart = SessionCart(self.request)
        self.v = make_variant(sku="A", price="1000000", stock_qty=10,
                              attributes={"storage": "128GB", "color": "Black"})

    def test_happy_path_creates_order_clears_cart_decrements_stock(self):
        self.cart.add(self.v, 3)
        order = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.subtotal, Decimal("3000000"))
        self.assertEqual(order.total, Decimal("3000000"))
        self.assertTrue(order.order_number.startswith("JNG-"))
        item = order.items.get()
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.unit_price, Decimal("1000000"))
        self.assertEqual(item.variant_label, "128GB / Black")
        self.assertEqual(item.product_title, self.v.product.title)
        self.assertEqual(len(self.cart), 0)
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 7)

    def test_snapshots_are_frozen(self):
        self.cart.add(self.v, 1)
        order = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.v.price = Decimal("9999999"); self.v.save()
        self.address.recipient_name = "Someone Else"; self.address.save()
        order.refresh_from_db()
        self.assertEqual(order.items.get().unit_price, Decimal("1000000"))
        self.assertEqual(order.recipient_name, "Ada L")

    def test_empty_cart_raises(self):
        with self.assertRaises(EmptyCartError):
            services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)

    def test_insufficient_stock_raises_and_persists_nothing(self):
        self.cart.add(self.v, 5)
        self.v.stock_qty = 2; self.v.save()
        with self.assertRaises(InsufficientStockError) as ctx:
            services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.assertEqual(ctx.exception.shortfalls[0]["available"], 2)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_foreign_address_raises(self):
        other = make_address(make_user(phone="+256772000077"))
        self.cart.add(self.v, 1)
        with self.assertRaises(AddressOwnershipError):
            services.create_order_from_cart(user=self.user, cart=self.cart, address=other)

    def test_order_numbers_increment_same_day(self):
        self.cart.add(self.v, 1)
        o1 = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.cart.add(self.v, 1)
        o2 = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.assertNotEqual(o1.order_number, o2.order_number)
        self.assertTrue(o2.order_number.endswith("0002"))


class MarkPaidTests(TestCase):
    def _pending(self):
        user = make_user()
        return Order.objects.create(
            user=user, order_number="JNG-20260906-0001", subtotal=Decimal("0"),
            total=Decimal("0"), recipient_name="Ada", recipient_phone="+256772000009",
            city_district="Kampala", street_area="Kololo",
        )

    def test_marks_paid_and_sets_fields(self):
        order = services.mark_paid(self._pending(), method="mtn_momo")
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.payment_method, "mtn_momo")
        self.assertTrue(order.payment_reference.startswith("SIM-"))
        self.assertIsNotNone(order.paid_at)

    def test_fail_true_raises_and_leaves_pending(self):
        order = self._pending()
        with self.assertRaises(PaymentSimulatedFailure):
            services.mark_paid(order, method="card", fail=True)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_second_call_is_noop(self):
        order = services.mark_paid(self._pending(), method="card")
        ref = order.payment_reference
        again = services.mark_paid(order, method="mtn_momo")
        self.assertEqual(again.payment_reference, ref)
        self.assertEqual(again.payment_method, "card")


class CancelOrderTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)
        self.request = make_request()
        self.cart = SessionCart(self.request)
        self.v = make_variant(price="500000", stock_qty=10)

    def test_cancel_restores_stock_and_sets_cancelled(self):
        self.cart.add(self.v, 4)
        order = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 6)
        services.cancel_order(order)
        order.refresh_from_db(); self.v.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.v.stock_qty, 10)

    def test_cancel_non_cancellable_status_raises(self):
        self.cart.add(self.v, 1)
        order = services.create_order_from_cart(user=self.user, cart=self.cart, address=self.address)
        order.status = Order.Status.SHIPPED; order.save()
        with self.assertRaises(OrderNotCancellable):
            services.cancel_order(order)


class PlaceOrderTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.address = make_address(self.user)
        self.request = make_request()
        self.cart = SessionCart(self.request)
        self.v = make_variant(price="1000000", stock_qty=10)

    def test_place_order_creates_paid_order(self):
        self.cart.add(self.v, 2)
        order = services.place_order(user=self.user, cart=self.cart, address=self.address,
                                     method="airtel_money")
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(len(self.cart), 0)
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 8)

    def test_simulate_fail_creates_nothing_and_keeps_cart(self):
        self.cart.add(self.v, 2)
        with self.assertRaises(PaymentSimulatedFailure):
            services.place_order(user=self.user, cart=self.cart, address=self.address,
                                 method="card", simulate_fail=True)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(len(self.cart), 2)
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 10)
```

- [ ] **Step 2: Run — verify it fails**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test orders.tests.test_services -v 2
```
Expected: import error for `orders.services`.

- [ ] **Step 3: Implement** — `backend/orders/services.py`
```python
import secrets
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from catalogue.models import ProductVariant

from .exceptions import (
    AddressOwnershipError,
    EmptyCartError,
    InsufficientStockError,
    OrderNotCancellable,
    PaymentSimulatedFailure,
)
from .models import DailyOrderSequence, Order, OrderItem


def _variant_label(attributes):
    # Mirrors storefront_extras.variant_label; kept local so `orders` has no
    # `storefront` dependency.
    if not isinstance(attributes, dict):
        return "Standard"
    parts = [str(v) for v in attributes.values() if v not in (None, "")]
    return " / ".join(parts) if parts else "Standard"


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
            variant_label=_variant_label(v.attributes),
            quantity=line["quantity"], unit_price=v.price,
        )
        v.stock_qty -= line["quantity"]
        v.save(update_fields=["stock_qty"])

    cart.clear()
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
    written and the cart is left intact (the raise happens before any DB work)."""
    if simulate_fail:
        raise PaymentSimulatedFailure("Simulated payment failure.")
    with transaction.atomic():
        order = create_order_from_cart(user=user, cart=cart, address=address)
        return mark_paid(order, method=method)
```

- [ ] **Step 4: Run — verify it passes**
```bash
python manage.py test orders.tests.test_services -v 2
```
Expected: `Ran 14 tests` … `OK`.

- [ ] **Step 5: Full suite**
```bash
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `Ran 182 tests` / `OK`.

- [ ] **Step 6: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/orders/services.py backend/orders/tests/test_services.py
git commit -m "feat(orders): order service layer (create, pay, cancel, place)"
```

---

## Task 5: `orders` admin

**Files:** Create `backend/orders/admin.py`, `backend/orders/tests/test_admin.py`.

- [ ] **Step 1: Write the failing test** — `backend/orders/tests/test_admin.py`
```python
from django.test import TestCase
from django.urls import reverse

from orders.tests.factories import make_user


class OrderAdminTests(TestCase):
    def setUp(self):
        admin = make_user(phone="+256772000100", is_staff=True, is_superuser=True)
        self.client.force_login(admin)

    def test_order_changelist_loads(self):
        r = self.client.get(reverse("admin:orders_order_changelist"))
        self.assertEqual(r.status_code, 200)

    def test_orderitem_changelist_loads(self):
        r = self.client.get(reverse("admin:orders_orderitem_changelist"))
        self.assertEqual(r.status_code, 200)
```

- [ ] **Step 2: Run — verify it fails**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test orders.tests.test_admin -v 2
```
Expected: `NoReverseMatch` for `admin:orders_order_changelist`.

- [ ] **Step 3: Implement** — `backend/orders/admin.py`
```python
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
```

- [ ] **Step 4: Run — verify it passes**
```bash
python manage.py test orders.tests.test_admin -v 2
```
Expected: `Ran 2 tests` … `OK`.

- [ ] **Step 5: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/orders/admin.py backend/orders/tests/test_admin.py
git commit -m "feat(orders): admin registration for Order/OrderItem"
```

---

## Task 6: Context processor upgrade + cart forms

**Files:** Modify `backend/storefront/context_processors.py`. Create `backend/storefront/forms.py`, `backend/storefront/tests/test_forms.py`.

- [ ] **Step 1: Write the failing test** — `backend/storefront/tests/test_forms.py`
```python
from django.test import TestCase

from orders.tests.factories import make_variant
from storefront.forms import AddToCartForm, UpdateCartForm


class AddToCartFormTests(TestCase):
    def test_valid_for_active_variant(self):
        v = make_variant(sku="A", stock_qty=5)
        form = AddToCartForm(data={"variant_id": v.id, "quantity": 2})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["variant"], v)
        self.assertEqual(form.cleaned_data["quantity"], 2)

    def test_rejects_unknown_variant(self):
        form = AddToCartForm(data={"variant_id": 999999, "quantity": 1})
        self.assertFalse(form.is_valid())
        self.assertIn("variant_id", form.errors)

    def test_rejects_inactive_product_variant(self):
        v = make_variant(sku="B", stock_qty=5)
        v.product.is_active = False
        v.product.save()
        form = AddToCartForm(data={"variant_id": v.id, "quantity": 1})
        self.assertFalse(form.is_valid())

    def test_quantity_must_be_positive(self):
        v = make_variant(sku="C", stock_qty=5)
        self.assertFalse(AddToCartForm(data={"variant_id": v.id, "quantity": 0}).is_valid())


class UpdateCartFormTests(TestCase):
    def test_allows_zero_for_removal(self):
        v = make_variant(sku="D", stock_qty=5)
        form = UpdateCartForm(data={"variant_id": v.id, "quantity": 0})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["quantity"], 0)

    def test_rejects_negative(self):
        v = make_variant(sku="E", stock_qty=5)
        self.assertFalse(UpdateCartForm(data={"variant_id": v.id, "quantity": -1}).is_valid())
```

- [ ] **Step 2: Run — verify it fails**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_forms -v 2
```
Expected: import error for `storefront.forms`.

- [ ] **Step 3: Implement** — `backend/storefront/forms.py`
```python
from django import forms

from catalogue.models import ProductVariant


class _VariantMixin(forms.Form):
    variant_id = forms.IntegerField(min_value=1)

    def clean_variant_id(self):
        vid = self.cleaned_data["variant_id"]
        variant = (
            ProductVariant.objects.filter(id=vid, product__is_active=True)
            .select_related("product")
            .first()
        )
        if variant is None:
            raise forms.ValidationError("That product is unavailable.")
        self.cleaned_data["variant"] = variant
        return vid


class AddToCartForm(_VariantMixin):
    quantity = forms.IntegerField(min_value=1, initial=1)


class UpdateCartForm(_VariantMixin):
    quantity = forms.IntegerField(min_value=0)
```

- [ ] **Step 4: Upgrade the context processor** — replace `backend/storefront/context_processors.py` with:
```python
from orders.cart import SessionCart


def cart_summary(request):
    """Cart badge + subtotal for every template. One extra query when the
    cart is non-empty (SessionCart resolves live prices); zero when empty."""
    cart = SessionCart(request)
    return {"cart_count": len(cart), "cart_subtotal": cart.subtotal}
```

- [ ] **Step 5: Run — verify forms pass + full suite green**
```bash
python manage.py test storefront.tests.test_forms -v 2
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `Ran 6 tests` OK for the forms; full suite `Ran 190 tests` / `OK`. (The 1a `test_home`/`test_catalog` still pass — they never assert on `cart_subtotal`, and `cart_count` is still provided.)

- [ ] **Step 6: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront/forms.py backend/storefront/context_processors.py backend/storefront/tests/test_forms.py
git commit -m "feat(storefront): SessionCart-backed context processor + cart forms"
```

---

## Task 7: Cart views, templates, and real Add-to-Cart

**Files:** Create `backend/storefront/views/cart.py`, `backend/storefront/templates/storefront/cart.html`, `backend/storefront/tests/test_cart.py`. Modify `backend/storefront/urls.py`, `backend/storefront/templates/storefront/product_detail.html`, `.../partials/header.html`, `.../partials/bottom_nav.html`.

- [ ] **Step 1: `backend/storefront/views/cart.py`**
```python
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
```

- [ ] **Step 2: `backend/storefront/templates/storefront/cart.html`**
```html
{% extends "storefront/base.html" %}
{% load static storefront_extras %}
{% block title %}Your Cart — Jangu Mobile{% endblock %}
{% block content %}
<section class="section">
  <h2>Your Cart</h2>
  {% if lines %}
  <table class="cart-table">
    <tbody>
    {% for line in lines %}
      <tr>
        <td>
          {% with img=line.variant.product.images.all|first %}
          <img class="cart-thumb" src="{% if img %}{{ img.image.url }}{% else %}{% static 'storefront/img/placeholder.svg' %}{% endif %}" alt="">
          {% endwith %}
        </td>
        <td>
          <a href="{% url 'storefront:product' line.variant.product.slug %}">{{ line.variant.product.title }}</a>
          <div class="muted">{{ line.variant.attributes|variant_label }}</div>
        </td>
        <td>{{ line.unit_price|ugx }}</td>
        <td>
          <form method="post" action="{% url 'storefront:cart_update' %}" class="qty" data-qty>
            {% csrf_token %}
            <input type="hidden" name="variant_id" value="{{ line.variant.id }}">
            <button type="button" data-step="down">−</button>
            <input type="number" name="quantity" value="{{ line.quantity }}" min="0" aria-label="Quantity">
            <button type="button" data-step="up">+</button>
            <button class="btn btn-navy" type="submit">Update</button>
          </form>
        </td>
        <td>{{ line.line_total|ugx }}</td>
        <td>
          <form method="post" action="{% url 'storefront:cart_remove' %}">
            {% csrf_token %}
            <input type="hidden" name="variant_id" value="{{ line.variant.id }}">
            <button class="btn" type="submit">Remove</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  <div class="cart-summary">
    <div>Subtotal <b>{{ subtotal|ugx }}</b></div>
    <div>Delivery <b>{{ 0|ugx }}</b></div>
    <div>Total <b>{{ subtotal|ugx }}</b></div>
    <a class="btn btn-primary btn-block" href="{% url 'storefront:checkout' %}">Proceed to Checkout</a>
  </div>
  {% else %}
  <p>Your cart is empty.</p>
  <a class="btn btn-primary" href="{% url 'storefront:home' %}">Start Shopping</a>
  {% endif %}
</section>
{% endblock %}
```

- [ ] **Step 3: Append to `backend/storefront/static/storefront/css/app.css`**
```css

/* cart */
.cart-table{width:100%;border-collapse:collapse;margin:16px 0}
.cart-table td{border-bottom:1px solid var(--line);padding:10px;vertical-align:middle}
.cart-thumb{width:56px;height:56px;object-fit:cover;border-radius:8px}
.cart-summary{max-width:320px;margin-left:auto;background:var(--card);border:1px solid var(--line);
  border-radius:var(--radius);padding:16px;display:grid;gap:8px}
.cart-summary>div{display:flex;justify-content:space-between}
.cart-summary .btn{margin-top:8px}
.pay-methods{display:grid;gap:10px;margin:16px 0}
.pay-methods label{display:flex;align-items:center;gap:10px;border:1px solid var(--line);
  border-radius:10px;padding:12px 14px;cursor:pointer}
.addr-list{display:grid;gap:10px;margin:12px 0}
.addr-list label{display:block;border:1px solid var(--line);border-radius:10px;padding:12px 14px;cursor:pointer}
.confirm{max-width:560px;margin:24px auto;text-align:center}
.confirm .tick{width:64px;height:64px;border-radius:50%;background:#e6f4ec;color:#186a3b;
  display:flex;align-items:center;justify-content:center;font-size:2rem;margin:0 auto 12px}
.status-badge{display:inline-block;padding:2px 10px;border-radius:999px;background:var(--bg);font-size:.8rem;font-weight:700}
```

- [ ] **Step 4: Wire the real Add-to-Cart form** in `backend/storefront/templates/storefront/product_detail.html`

Replace the block from `{% if variants %}` through the closing of the `data-add-btn` button and the "next update" paragraph with:
```html
    <form method="post" action="{% url 'storefront:cart_add' %}">
      {% csrf_token %}
      {% if variants %}
      <label for="variant">Option</label>
      <select id="variant" name="variant_id" data-variant-select>
        {% for v in variants %}
          <option value="{{ v.id }}" data-price="{{ v.price|ugx|cut:'UGX ' }}" data-in-stock="{% if v.stock_qty > 0 %}1{% else %}0{% endif %}">
            {{ v.attributes|variant_label }} — {{ v.price|ugx }}{% if v.stock_qty == 0 %} (Out of stock){% endif %}
          </option>
        {% endfor %}
      </select>
      {% else %}
      <input type="hidden" name="variant_id" value="">
      {% endif %}

      <div class="qty" data-qty>
        <button type="button" data-step="down">−</button>
        <input type="number" name="quantity" value="1" min="1" aria-label="Quantity">
        <button type="button" data-step="up">+</button>
      </div>

      <button class="btn btn-primary btn-block" type="submit" data-add-btn {% if not product.in_stock %}disabled{% endif %}>
        Add to Cart
      </button>
    </form>
```
(Leave the rest of the template — gallery, description, related — unchanged.)

- [ ] **Step 5: Repoint links**

`backend/storefront/templates/storefront/partials/header.html` — change the cart link `href="{% url 'storefront:home' %}"` on the `cart-link` anchor to `href="{% url 'storefront:cart' %}"`, and add a subtotal title:
```html
      <a class="cart-link" href="{% url 'storefront:cart' %}">Cart
        {% if cart_count %}<span class="cart-badge">{{ cart_count }}</span>{% endif %}
      </a>
```

`backend/storefront/templates/storefront/partials/bottom_nav.html` — change the Cart entry's `href` to `{% url 'storefront:cart' %}` and give it `class="{% if active == 'cart' %}active{% endif %}"`.

- [ ] **Step 6: `backend/storefront/urls.py`** — add the cart routes (keep the existing four):
```python
from django.urls import path

from storefront.views import cart, catalog

app_name = "storefront"

urlpatterns = [
    path("", catalog.home, name="home"),
    path("c/<slug:slug>/", catalog.category, name="category"),
    path("search/", catalog.search, name="search"),
    path("p/<slug:slug>/", catalog.product_detail, name="product"),
    path("cart/", cart.detail, name="cart"),
    path("cart/add/", cart.add, name="cart_add"),
    path("cart/update/", cart.update, name="cart_update"),
    path("cart/remove/", cart.remove, name="cart_remove"),
]
```

- [ ] **Step 7: Write tests** — `backend/storefront/tests/test_cart.py`
```python
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from orders.tests.factories import make_variant


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CartFlowTests(TestCase):
    def setUp(self):
        self.v = make_variant(sku="A", price="1000000", stock_qty=5,
                              attributes={"storage": "128GB"}, title="Phone")

    def test_add_sets_session_and_redirects_to_cart(self):
        r = self.client.post(reverse("storefront:cart_add"),
                             {"variant_id": self.v.id, "quantity": 2})
        self.assertRedirects(r, reverse("storefront:cart"))
        self.assertEqual(self.client.session["cart"], {str(self.v.id): 2})

    def test_add_same_variant_increments(self):
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 2})
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 1})
        self.assertEqual(self.client.session["cart"], {str(self.v.id): 3})

    def test_over_stock_add_is_rejected_with_message(self):
        r = self.client.post(reverse("storefront:cart_add"),
                             {"variant_id": self.v.id, "quantity": 9}, follow=True)
        self.assertContains(r, "in stock")
        self.assertNotIn("cart", self.client.session)

    def test_update_to_zero_removes(self):
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 2})
        self.client.post(reverse("storefront:cart_update"), {"variant_id": self.v.id, "quantity": 0})
        self.assertEqual(self.client.session["cart"], {})

    def test_remove(self):
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 2})
        self.client.post(reverse("storefront:cart_remove"), {"variant_id": self.v.id})
        self.assertEqual(self.client.session["cart"], {})

    def test_cart_page_shows_lines_and_totals(self):
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 2})
        r = self.client.get(reverse("storefront:cart"))
        self.assertContains(r, "Phone-A")
        self.assertContains(r, "UGX 2,000,000")

    def test_badge_count_via_context_processor(self):
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": 2})
        r = self.client.get(reverse("storefront:home"))
        self.assertContains(r, 'class="cart-badge">2<')
```

- [ ] **Step 8: Run**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_cart -v 2
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `Ran 7 tests` OK; full suite `Ran 197 tests` / `OK`.

- [ ] **Step 9: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront
git commit -m "feat(storefront): cart page + add/update/remove + real Add to Cart"
```

---

## Task 8: Auth — register / login / logout

**Files:** Modify `backend/storefront/forms.py`. Create `backend/storefront/views/auth.py`, `backend/storefront/templates/storefront/auth/login.html`, `.../auth/register.html`, `backend/storefront/tests/test_auth.py`. Modify `backend/storefront/urls.py`, `.../partials/header.html`, `.../partials/bottom_nav.html`.

- [ ] **Step 1: Append to `backend/storefront/forms.py`**
```python
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from accounts.validators import normalize_uganda_phone

User = get_user_model()


class PhoneAuthenticationForm(AuthenticationForm):
    """Login form: relabel the username field and normalise the phone so a
    number typed as ``0771…`` matches the stored ``+256771…`` value."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Phone"
        self.fields["username"].widget.attrs.update({"placeholder": "+2567…"})

    def clean(self):
        raw = self.cleaned_data.get("username")
        if raw:
            try:
                self.cleaned_data["username"] = normalize_uganda_phone(raw)
            except DjangoValidationError:
                pass
        return super().clean()


class RegisterForm(forms.Form):
    phone = forms.CharField(max_length=20)
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean_phone(self):
        try:
            normalized = normalize_uganda_phone(self.cleaned_data["phone"])
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages)
        if User.objects.filter(phone=normalized).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return normalized

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        if p1:
            try:
                validate_password(p1)
            except DjangoValidationError as exc:
                self.add_error("password1", exc.messages)
        return cleaned

    def save(self):
        return User.objects.create_user(
            phone=self.cleaned_data["phone"],
            password=self.cleaned_data["password1"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
        )
```

- [ ] **Step 2: `backend/storefront/views/auth.py`**
```python
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from storefront.forms import PhoneAuthenticationForm, RegisterForm


class StorefrontLoginView(LoginView):
    template_name = "storefront/auth/login.html"
    authentication_form = PhoneAuthenticationForm
    redirect_authenticated_user = True


def register(request):
    if request.user.is_authenticated:
        return redirect("storefront:home")
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)
            return redirect("storefront:home")
    else:
        form = RegisterForm()
    return render(request, "storefront/auth/register.html", {"form": form, "next": next_url})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("storefront:home")
```

- [ ] **Step 3: `backend/storefront/templates/storefront/auth/login.html`**
```html
{% extends "storefront/base.html" %}
{% block title %}Log in — Jangu Mobile{% endblock %}
{% block content %}
<section class="section" style="max-width:420px;margin:0 auto">
  <h2>Log in</h2>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <input type="hidden" name="next" value="{{ next }}">
    <button class="btn btn-primary btn-block" type="submit">Log in</button>
  </form>
  <p style="margin-top:12px">New here? <a href="{% url 'storefront:register' %}?next={{ next|urlencode }}">Create an account</a></p>
</section>
{% endblock %}
```

- [ ] **Step 4: `backend/storefront/templates/storefront/auth/register.html`**
```html
{% extends "storefront/base.html" %}
{% block title %}Create account — Jangu Mobile{% endblock %}
{% block content %}
<section class="section" style="max-width:420px;margin:0 auto">
  <h2>Create your account</h2>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <input type="hidden" name="next" value="{{ next }}">
    <button class="btn btn-primary btn-block" type="submit">Create account</button>
  </form>
  <p style="margin-top:12px">Already have an account? <a href="{% url 'storefront:login' %}?next={{ next|urlencode }}">Log in</a></p>
</section>
{% endblock %}
```

- [ ] **Step 5: `backend/storefront/urls.py`** — add auth routes:
```python
from django.urls import path

from storefront.views import auth, cart, catalog

app_name = "storefront"

urlpatterns = [
    path("", catalog.home, name="home"),
    path("c/<slug:slug>/", catalog.category, name="category"),
    path("search/", catalog.search, name="search"),
    path("p/<slug:slug>/", catalog.product_detail, name="product"),
    path("cart/", cart.detail, name="cart"),
    path("cart/add/", cart.add, name="cart_add"),
    path("cart/update/", cart.update, name="cart_update"),
    path("cart/remove/", cart.remove, name="cart_remove"),
    path("register/", auth.register, name="register"),
    path("login/", auth.StorefrontLoginView.as_view(), name="login"),
    path("logout/", auth.logout_view, name="logout"),
]
```

- [ ] **Step 6: Repoint the Account link** in `partials/header.html` and `partials/bottom_nav.html`

`header.html` — replace the Account anchor with:
```html
      {% if user.is_authenticated %}
      <a href="{% url 'storefront:home' %}">{{ user.first_name|default:user.phone }}</a>
      <form method="post" action="{% url 'storefront:logout' %}" style="display:inline">{% csrf_token %}<button class="btn" type="submit">Log out</button></form>
      {% else %}
      <a href="{% url 'storefront:login' %}">Account</a>
      {% endif %}
```
`bottom_nav.html` — point the Account entry's `href` to `{% url 'storefront:login' %}` (it becomes the account hub in 1c).

- [ ] **Step 7: Write tests** — `backend/storefront/tests/test_auth.py`
```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegisterTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        r = self.client.post(reverse("storefront:register"), {
            "phone": "0771234567", "first_name": "Ada", "last_name": "Lovelace",
            "password1": "s3cure-pass-99", "password2": "s3cure-pass-99",
        })
        self.assertRedirects(r, reverse("storefront:home"))
        user = User.objects.get()
        self.assertEqual(user.phone, "+256771234567")
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_duplicate_phone_shows_error(self):
        User.objects.create_user(phone="+256771234567", password="x", first_name="A", last_name="B")
        r = self.client.post(reverse("storefront:register"), {
            "phone": "+256771234567", "first_name": "Ada", "last_name": "L",
            "password1": "s3cure-pass-99", "password2": "s3cure-pass-99",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "already exists")

    def test_weak_password_rejected(self):
        r = self.client.post(reverse("storefront:register"), {
            "phone": "0771234567", "first_name": "Ada", "last_name": "L",
            "password1": "12345678", "password2": "12345678",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "too common")

    def test_password_mismatch_rejected(self):
        r = self.client.post(reverse("storefront:register"), {
            "phone": "0771234567", "first_name": "Ada", "last_name": "L",
            "password1": "s3cure-pass-99", "password2": "different-99",
        })
        self.assertContains(r, "do not match", status_code=200)


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256771234567", password="s3cure-pass-99", first_name="Ada", last_name="L"
        )

    def test_login_with_local_format_phone(self):
        r = self.client.post(reverse("storefront:login"),
                             {"username": "0771234567", "password": "s3cure-pass-99"})
        self.assertRedirects(r, reverse("storefront:home"))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("storefront:logout")).status_code, 405)
        r = self.client.post(reverse("storefront:logout"))
        self.assertRedirects(r, reverse("storefront:home"))
        self.assertNotIn("_auth_user_id", self.client.session)
```

- [ ] **Step 8: Run**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_auth -v 2
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `Ran 7 tests` OK; full suite `Ran 204 tests` / `OK`.

- [ ] **Step 9: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront
git commit -m "feat(storefront): session auth — register, login, logout"
```

---

## Task 9: Checkout, simulated payment, order confirmation

**Files:** Modify `backend/storefront/forms.py`. Create `backend/storefront/views/checkout.py`, `backend/storefront/templates/storefront/{checkout,payment,order_confirmation}.html`, `.../partials/order_summary.html`, `backend/storefront/tests/test_checkout.py`. Modify `backend/storefront/urls.py`.

- [ ] **Step 1: Append `AddressForm` to `backend/storefront/forms.py`**
```python
from accounts.models import Address


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["recipient_name", "recipient_phone", "city_district", "street_area", "landmark"]

    def clean_recipient_phone(self):
        value = self.cleaned_data["recipient_phone"]
        try:
            return normalize_uganda_phone(value)
        except DjangoValidationError as exc:
            raise forms.ValidationError(exc.messages)
```

- [ ] **Step 2: `backend/storefront/views/checkout.py`**
```python
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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
```

- [ ] **Step 3: `backend/storefront/templates/storefront/partials/order_summary.html`**
```html
{% load storefront_extras %}
<table class="cart-table">
  <tbody>
  {% for line in lines %}
    <tr>
      <td>{{ line.variant.product.title }}<div class="muted">{{ line.variant.attributes|variant_label }}</div></td>
      <td>× {{ line.quantity }}</td>
      <td>{{ line.line_total|ugx }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
<div class="cart-summary">
  <div>Subtotal <b>{{ subtotal|ugx }}</b></div>
  <div>Delivery <b>{{ 0|ugx }}</b></div>
  <div>Total <b>{{ subtotal|ugx }}</b></div>
</div>
```

- [ ] **Step 4: `backend/storefront/templates/storefront/checkout.html`**
```html
{% extends "storefront/base.html" %}
{% block title %}Checkout — Jangu Mobile{% endblock %}
{% block content %}
<section class="section" style="max-width:640px;margin:0 auto">
  <h2>Delivery address</h2>
  <form method="post">
    {% csrf_token %}
    {% if addresses %}
    <div class="addr-list">
      {% for a in addresses %}
      <label>
        <input type="radio" name="address_id" value="{{ a.id }}" {% if a.is_default %}checked{% endif %}>
        {{ a.recipient_name }} — {{ a.recipient_phone }}<br>{{ a.street_area }}, {{ a.city_district }}
        {% if a.landmark %} ({{ a.landmark }}){% endif %}
      </label>
      {% endfor %}
    </div>
    <p class="muted">…or add a new address below (leave the radios unselected):</p>
    {% endif %}
    {{ form.as_p }}
    <h3 style="margin-top:20px">Order summary</h3>
    {% include "storefront/partials/order_summary.html" %}
    <button class="btn btn-primary btn-block" type="submit">Continue to Payment</button>
  </form>
</section>
{% endblock %}
```

- [ ] **Step 5: `backend/storefront/templates/storefront/payment.html`**
```html
{% extends "storefront/base.html" %}
{% load storefront_extras %}
{% block title %}Payment — Jangu Mobile{% endblock %}
{% block content %}
<section class="section" style="max-width:560px;margin:0 auto">
  <h2>Payment</h2>
  <p>Deliver to: <b>{{ address.recipient_name }}</b>, {{ address.street_area }}, {{ address.city_district }}</p>
  {% include "storefront/partials/order_summary.html" %}
  <form method="post">
    {% csrf_token %}
    <div class="pay-methods">
      {% for value, label in methods.items %}
      <label><input type="radio" name="method" value="{{ value }}" {% if forloop.first %}checked{% endif %}> {{ label }}</label>
      {% endfor %}
    </div>
    <button class="btn btn-primary btn-block" type="submit">Pay {{ subtotal|ugx }}</button>
  </form>
  <p class="muted" style="margin-top:8px">Payment is simulated — no real charge is made.</p>
</section>
{% endblock %}
```

- [ ] **Step 6: `backend/storefront/templates/storefront/order_confirmation.html`**
```html
{% extends "storefront/base.html" %}
{% load storefront_extras %}
{% block title %}Order {{ order.order_number }} — Jangu Mobile{% endblock %}
{% block content %}
<section class="confirm">
  <div class="tick">✓</div>
  <h2>Thank you! Your order is confirmed.</h2>
  <p>Order <b>{{ order.order_number }}</b> · <span class="status-badge">{{ order.get_status_display }}</span></p>
</section>
<section class="section" style="max-width:560px;margin:0 auto">
  <table class="cart-table"><tbody>
  {% for item in order.items.all %}
    <tr><td>{{ item.product_title }}<div class="muted">{{ item.variant_label }}</div></td>
        <td>× {{ item.quantity }}</td><td>{{ item.line_total|ugx }}</td></tr>
  {% endfor %}
  </tbody></table>
  <div class="cart-summary">
    <div>Total <b>{{ order.total|ugx }}</b></div>
    <div>Paid via <b>{{ order.get_payment_method_display|default:order.payment_method }}</b></div>
    <div>Ref <b>{{ order.payment_reference }}</b></div>
  </div>
  <p style="margin-top:16px">Delivering to {{ order.recipient_name }}, {{ order.street_area }}, {{ order.city_district }}.</p>
  <a class="btn btn-navy" href="{% url 'storefront:home' %}">Continue shopping</a>
</section>
{% endblock %}
```
Note: `order.get_payment_method_display` only works if `payment_method` has `choices`; it does not in the model, so this falls back via `|default:order.payment_method`. Acceptable — shows `mtn_momo` etc. (1c can prettify).

- [ ] **Step 7: `backend/storefront/urls.py`** — add checkout routes:
```python
from storefront.views import auth, cart, catalog, checkout
```
and inside `urlpatterns` (after the auth routes):
```python
    path("checkout/", checkout.checkout, name="checkout"),
    path("checkout/payment/", checkout.payment, name="payment"),
    path("orders/<str:order_number>/", checkout.order_confirmation, name="order_confirmation"),
```

- [ ] **Step 8: Write tests** — `backend/storefront/tests/test_checkout.py`
```python
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from orders.models import Order
from orders.tests.factories import make_address, make_variant

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256771234567", password="s3cure-pass-99", first_name="Ada", last_name="L"
        )
        self.address = make_address(self.user, is_default=True)
        self.v = make_variant(sku="A", price="1000000", stock_qty=5, title="Phone")

    def _fill_cart(self, qty=2):
        self.client.force_login(self.user)
        self.client.post(reverse("storefront:cart_add"), {"variant_id": self.v.id, "quantity": qty})

    def test_anonymous_checkout_redirects_to_login(self):
        r = self.client.get(reverse("storefront:checkout"))
        self.assertIn("/login/", r["Location"])
        self.assertIn("next=", r["Location"])

    def test_empty_cart_checkout_redirects_to_cart(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("storefront:checkout"))
        self.assertRedirects(r, reverse("storefront:cart"))

    def test_checkout_lists_addresses(self):
        self._fill_cart()
        r = self.client.get(reverse("storefront:checkout"))
        self.assertContains(r, self.address.recipient_name)

    def test_checkout_selecting_address_advances_to_payment(self):
        self._fill_cart()
        r = self.client.post(reverse("storefront:checkout"), {"address_id": self.address.id})
        self.assertRedirects(r, reverse("storefront:payment"))
        self.assertEqual(self.client.session["checkout_address_id"], self.address.id)

    def test_payment_creates_paid_order_clears_cart_decrements_stock(self):
        self._fill_cart(2)
        self.client.post(reverse("storefront:checkout"), {"address_id": self.address.id})
        r = self.client.post(reverse("storefront:payment"), {"method": "mtn_momo"})
        order = Order.objects.get()
        self.assertRedirects(r, reverse("storefront:order_confirmation", args=[order.order_number]))
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.total, order.subtotal)
        self.assertEqual(self.client.session.get("cart", {}), {})
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 3)

    def test_simulate_fail_creates_no_order(self):
        self._fill_cart(2)
        self.client.post(reverse("storefront:checkout"), {"address_id": self.address.id})
        r = self.client.post(reverse("storefront:payment") + "?simulate=fail",
                             {"method": "card"}, follow=True)
        self.assertContains(r, "Payment failed")
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.client.session["cart"], {str(self.v.id): 2})

    def test_confirmation_404_for_other_user(self):
        self._fill_cart(1)
        self.client.post(reverse("storefront:checkout"), {"address_id": self.address.id})
        self.client.post(reverse("storefront:payment"), {"method": "card"})
        number = Order.objects.get().order_number
        other = User.objects.create_user(phone="+256772229999", password="x", first_name="B", last_name="C")
        self.client.force_login(other)
        self.assertEqual(
            self.client.get(reverse("storefront:order_confirmation", args=[number])).status_code, 404
        )

    def test_checkout_can_add_new_address_inline(self):
        self._fill_cart(1)
        r = self.client.post(reverse("storefront:checkout"), {
            "recipient_name": "New Person", "recipient_phone": "0770000000",
            "city_district": "Jinja", "street_area": "Main St", "landmark": "",
        })
        self.assertRedirects(r, reverse("storefront:payment"))
        self.assertEqual(self.user.addresses.count(), 2)
```

- [ ] **Step 9: Run**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_checkout -v 2
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `Ran 8 tests` OK; full suite `Ran 212 tests` / `OK`.

- [ ] **Step 10: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront
git commit -m "feat(storefront): checkout, simulated payment, order confirmation"
```

---

## Task 10: Phase 1b verification gate

**Files:** none (verification only).

- [ ] **Step 1: Full suite**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `OK`, 0 failures (≈212 tests).

- [ ] **Step 2: Deploy check**
```bash
DEBUG=False SECRET_KEY=verify-only-1234567890 python manage.py check --deploy 2>&1 | grep -E "W0|ERROR|identified"
```
Expected: only `security.W004`/`W008`/`W009`, no `ERROR`.

- [ ] **Step 3: End-to-end purchase under `gunicorn` / `DEBUG=False`**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
rm -f db.sqlite3 && rm -rf staticfiles media
export DEBUG=False SECRET_KEY=verify-only-1234567890 ALLOWED_HOSTS=127.0.0.1,localhost DJANGO_SETTINGS_MODULE=backend.settings
python manage.py collectstatic --no-input >/dev/null
python manage.py migrate >/dev/null
python manage.py seed_demo
../.venv/bin/gunicorn backend.wsgi:application --bind 127.0.0.1:8128 --workers 2 --pid /tmp/g8128.pid >/tmp/g8128.log 2>&1 &
sleep 6
python - <<'PY'
import re, urllib.request, http.cookiejar
base = "http://127.0.0.1:8128"
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPRedirectHandler())
def get(p): return op.open(base+p).read().decode()
def token(html): return re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
def post(p, data, ref):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(base+p, body, {"Referer": base+ref, "Content-Type":"application/x-www-form-urlencoded"})
    return op.open(req).read().decode()
import urllib.parse
# register
h = get("/register/"); post("/register/", {"csrfmiddlewaretoken":token(h),"phone":"0772345678","first_name":"Ada","last_name":"L","password1":"s3cure-pass-77","password2":"s3cure-pass-77","next":""}, "/register/")
# product slug + a variant id
pd = get("/p/samsung-galaxy-s23/")
vid = re.search(r'<option value="(\d+)"', pd).group(1)
post("/cart/add/", {"csrfmiddlewaretoken":token(pd),"variant_id":vid,"quantity":"1"}, "/p/samsung-galaxy-s23/")
cart = get("/cart/"); assert "UGX" in cart, "cart empty"
co = get("/checkout/")
post("/checkout/", {"csrfmiddlewaretoken":token(co),"recipient_name":"Ada L","recipient_phone":"0770000000","city_district":"Kampala","street_area":"Kololo","landmark":""}, "/checkout/")
pay = get("/checkout/payment/")
conf = post("/checkout/payment/", {"csrfmiddlewaretoken":token(pay),"method":"mtn_momo"}, "/checkout/payment/")
assert "order is confirmed" in conf, conf[:400]
assert re.search(r"JNG-\d{8}-\d{4}", conf), "no order number"
print("PURCHASE FLOW OK:", re.search(r"JNG-\d{8}-\d{4}", conf).group(0))
PY
kill "$(cat /tmp/g8128.pid)"; rm -f /tmp/g8128.pid /tmp/g8128.log
rm -f db.sqlite3 && rm -rf staticfiles media
```
Expected: `PURCHASE FLOW OK: JNG-YYYYMMDD-0001`.

- [ ] **Step 4: Admin check**
Run `python manage.py runserver` after `seed_demo` + a superuser; open `/admin/orders/order/` and confirm the placed order shows with its items inline, navy theme.

- [ ] **Step 5: Report**
Summarise commits (`orders` scaffold → models → cart → services → admin → context/forms → cart UI → auth → checkout), full suite green, end-to-end purchase verified under `DEBUG=False`. Phase 1b is deployable. Next: push/merge to deploy, or write the Phase 1c plan (account dashboard, order history + cancel, address book).

---

## Self-Review

**Spec coverage (§5 + §6 cart/checkout portions + §12 "1b"):**
- §5.1 `Order`/`OrderItem` models + `line_total` — Task 2. `DailyOrderSequence` (deviation from §5.2 retry loop, documented) — Task 2.
- §5.2 `order_number` `JNG-YYYYMMDD-NNNN` + per-day increment — Task 4 (`_next_order_number`), tested in `test_services.test_order_numbers_increment_same_day`.
- §5.3 `SessionCart` (add/replace/set_quantity/remove/clear/`__iter__` live pricing + prune/`__len__`/`subtotal`/`session.modified`) — Task 3.
- §5.4 `create_order_from_cart`, `mark_paid`, `cancel_order` + all five exceptions — Tasks 3 (exceptions) + 4. `place_order` composition added for the view.
- §5.5 model/cart/service/admin tests — Tasks 2/3/4/5.
- §6.2 routes `cart`, `cart_add/update/remove`, `checkout`, `payment`, `order_confirmation`, `register`, `login`, `logout` — Tasks 7/8/9. (Account-area + address-book routes are Phase 1c.)
- §6.4 cart / checkout / payment / order_confirmation / auth pages — Tasks 7/8/9. Owner-scoped `order_confirmation` 404s for other users — tested.
- §6.5 `AddToCartForm`/`UpdateCartForm` (Task 6), `RegisterForm`/`PhoneAuthenticationForm` (Task 8), `AddressForm` (Task 9). `CheckoutAddressForm` — folded into the `checkout` view's address_id-or-`AddressForm` branch rather than a dedicated form (simpler; documented).
- §6.6 context processor → `cart_count` + `cart_subtotal` via `SessionCart` — Task 6.
- §6.8 cart tests (add/increment/zero-removes/over-stock/totals/badge) — Task 7; checkout tests (anon→login, empty→cart, addresses, payment creates PAID + clears + decrements, `?simulate=fail` no order, confirmation 404) — Task 9; auth tests (register+login, dup phone, weak password, login, logout POST-only) — Task 8.
- **Not in 1b (Phase 1c):** `/account/` dashboard, `/account/orders/` history + detail + cancel, `/account/addresses/` book. Order model supports cancel (`services.cancel_order`, tested) — the UI lands in 1c.

**Placeholder scan:** none. Every step has full file content or an exact, unambiguous edit. Task 7 Step 4 and Task 8 Step 6 describe replacements against known 1a template text.

**Type/name consistency:** `SessionCart` API (`add`/`set_quantity`/`remove`/`clear`/`subtotal`/`__len__`/`__iter__`) identical across `cart.py`, `services.py`, views, and every test. Service names (`create_order_from_cart`, `mark_paid`, `cancel_order`, `place_order`) consistent across `services.py`, views, tests. Exception names identical across `exceptions.py`, `services.py`, `cart.py`, views, tests. `Order.Status.{PENDING,PAID,CANCELLED}` used consistently. URL names (`cart`, `cart_add`, `cart_update`, `cart_remove`, `register`, `login`, `logout`, `checkout`, `payment`, `order_confirmation`) consistent across `urls.py`, templates, views, tests. Session keys `"cart"` (from `orders.cart.SESSION_KEY`) and `"checkout_address_id"` (`checkout.SESSION_ADDRESS_KEY`) consistent. `PAYMENT_METHODS` keys (`mtn_momo`/`airtel_money`/`card`) match the model's documented values and the templates.
