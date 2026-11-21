# Jangu Storefront — Phase 1c (Account Area) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a logged-in shopper an account area: a dashboard, their order history with detail + self-cancel, and an address book (list / add / edit / delete / set-default).

**Architecture:** One new view module `storefront/views/account.py` (all `@login_required`, owner-scoped 404s), five `account/` templates + one shared `partials/order_receipt.html`, reusing `orders.services.cancel_order`, the existing `storefront.forms.AddressForm`, and `accounts.Address`'s `save()` default-handling. No model changes, no new dependencies.

**Tech Stack:** Django 5.2 templates + `django.contrib.auth` session auth (register/login/logout already shipped in Phase 1b).

**Spec:** `docs/superpowers/specs/2026-09-06-storefront-milestone-1-design.md` — this plan covers phase **1c** from §12 (the "register/login/logout" part of 1c already shipped in 1b). Phases 1a + 1b are merged to `main`; full suite is at 218 tests.

**Deviations from spec (intentional):**
- **`address_set_default` route added** (`/account/addresses/<pk>/set-default/`, POST) — the spec's route list is illustrative and doesn't include it, but the "default badge" feature needs a way to change the default, and `accounts.AddressViewSet` already establishes exactly this pattern (a dedicated `set-default` action; `is_default` is deliberately not a writable form field, so turning it off can't strand a user with zero defaults).
- **`address_delete` mirrors `accounts.AddressViewSet.perform_destroy`** — locks the user row, deletes, and promotes the most-recent remaining address to default if the deleted one was the default. Without this, deleting the default leaves the user with none.
- **`partials/order_receipt.html` extracted** from the 1b `order_confirmation.html` so the confirmation page and the new order-detail page share one receipt block instead of drifting.

Every command assumes: `cd /Users/mac/projects/jango_mobileapp && source .venv/bin/activate`; `manage.py` runs from `backend/`.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/storefront/views/account.py` | `index`, `orders`, `order_detail`, `order_cancel`, `addresses`, `address_add`, `address_edit`, `address_delete`, `address_set_default` — all `@login_required` |
| `backend/storefront/templates/storefront/account/index.html` | dashboard: greeting + tiles + logout |
| `backend/storefront/templates/storefront/account/orders.html` | paginated order list |
| `backend/storefront/templates/storefront/account/order_detail.html` | one order + receipt + cancel button |
| `backend/storefront/templates/storefront/account/addresses.html` | address list with default badge + per-row actions |
| `backend/storefront/templates/storefront/account/address_form.html` | add / edit form |
| `backend/storefront/templates/storefront/partials/order_receipt.html` | shared items table + totals + delivery snapshot |
| `backend/storefront/templates/storefront/order_confirmation.html` | *(modify)* use the shared receipt partial |
| `backend/storefront/templates/storefront/partials/header.html` | *(modify)* authed link → `storefront:account` |
| `backend/storefront/templates/storefront/partials/bottom_nav.html` | *(modify)* Account link → account or login |
| `backend/storefront/urls.py` | *(modify)* + 9 account routes |
| `backend/storefront/static/storefront/css/app.css` | *(modify)* small account styles |
| `backend/storefront/tests/test_account.py` | all account-area tests |

`storefront/views/account.py` will hold ~9 short views for one cohesive section — comparable in size to `views/checkout.py` (94 lines); no split needed.

---

## Task 1: `account.py` skeleton + dashboard + routes + nav

**Files:** Create `backend/storefront/views/account.py`, `backend/storefront/templates/storefront/account/index.html`, `backend/storefront/tests/test_account.py`. Modify `backend/storefront/urls.py`, `.../partials/header.html`, `.../partials/bottom_nav.html`, `.../static/storefront/css/app.css`.

- [ ] **Step 1: Branch**
```bash
cd /Users/mac/projects/jango_mobileapp
git switch -c storefront/milestone-1c
```
Expected: `Switched to a new branch 'storefront/milestone-1c'`

- [ ] **Step 2: `backend/storefront/views/account.py`** — real `index`, harmless stubs for the rest (replaced in Tasks 2–4; the routes must all exist now so `index.html` can `{% url %}` them)
```python
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render


@login_required
def index(request):
    return render(request, "storefront/account/index.html", {"active": "account"})


@login_required
def orders(request):  # Task 2
    return HttpResponse("orders (stub)")


@login_required
def order_detail(request, order_number):  # Task 2
    return HttpResponse("order detail (stub)")


@login_required
def order_cancel(request, order_number):  # Task 3
    return HttpResponse("order cancel (stub)")


@login_required
def addresses(request):  # Task 4
    return HttpResponse("addresses (stub)")


@login_required
def address_add(request):  # Task 4
    return HttpResponse("address add (stub)")


@login_required
def address_edit(request, pk):  # Task 4
    return HttpResponse("address edit (stub)")


@login_required
def address_delete(request, pk):  # Task 4
    return HttpResponse("address delete (stub)")


@login_required
def address_set_default(request, pk):  # Task 4
    return HttpResponse("address set default (stub)")
```

- [ ] **Step 3: `backend/storefront/templates/storefront/account/index.html`**
```html
{% extends "storefront/base.html" %}
{% block title %}My Account — Jangu Mobile{% endblock %}
{% block content %}
<section class="section" style="max-width:640px;margin:0 auto">
  <h2>Hi {{ user.first_name|default:user.phone }}</h2>
  <p class="muted">{{ user.phone }}</p>
  <div class="account-tiles">
    <a class="account-tile" href="{% url 'storefront:account_orders' %}"><b>My Orders</b><span>Track and manage your orders</span></a>
    <a class="account-tile" href="{% url 'storefront:addresses' %}"><b>Delivery Addresses</b><span>Manage where your orders go</span></a>
  </div>
  <form method="post" action="{% url 'storefront:logout' %}" style="margin-top:16px">
    {% csrf_token %}<button class="btn" type="submit">Log out</button>
  </form>
</section>
{% endblock %}
```

- [ ] **Step 4: `backend/storefront/urls.py`** — change the import to `from storefront.views import account, auth, cart, catalog, checkout` and append these to `urlpatterns` (after the `order_confirmation` route):
```python
    path("account/", account.index, name="account"),
    path("account/orders/", account.orders, name="account_orders"),
    path("account/orders/<str:order_number>/", account.order_detail, name="account_order"),
    path("account/orders/<str:order_number>/cancel/", account.order_cancel, name="account_order_cancel"),
    path("account/addresses/", account.addresses, name="addresses"),
    path("account/addresses/add/", account.address_add, name="address_add"),
    path("account/addresses/<int:pk>/edit/", account.address_edit, name="address_edit"),
    path("account/addresses/<int:pk>/delete/", account.address_delete, name="address_delete"),
    path("account/addresses/<int:pk>/set-default/", account.address_set_default, name="address_set_default"),
```

- [ ] **Step 5: Repoint nav**

`backend/storefront/templates/storefront/partials/header.html` — the authenticated user link currently reads
`<a href="{% url 'storefront:home' %}">{{ user.first_name|default:user.phone }}</a>`. Change its href to `{% url 'storefront:account' %}`.

`backend/storefront/templates/storefront/partials/bottom_nav.html` — the Account entry currently reads
`<a href="{% url 'storefront:login' %}">👤<span>Account</span></a>`. Replace it with:
```html
  <a href="{% if user.is_authenticated %}{% url 'storefront:account' %}{% else %}{% url 'storefront:login' %}{% endif %}" class="{% if active == 'account' %}active{% endif %}">👤<span>Account</span></a>
```

- [ ] **Step 6: Append to `backend/storefront/static/storefront/css/app.css`**
```css

/* account */
.account-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}
.account-tile{display:block;padding:16px;border:1px solid var(--line);border-radius:var(--radius);background:var(--card);box-shadow:var(--shadow);color:inherit}
.account-tile:hover{border-color:var(--orange)}
.account-tile b{display:block}
.account-tile span{font-size:.85rem;color:var(--muted)}
.order-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;border:1px solid var(--line);border-radius:var(--radius);background:var(--card);padding:14px;margin-bottom:10px}
.order-row a{font-weight:700}
.addr-card{border:1px solid var(--line);border-radius:var(--radius);background:var(--card);padding:14px;margin-bottom:10px}
.addr-card .badge{display:inline-block;background:var(--navy);color:#fff;font-size:.7rem;font-weight:700;padding:2px 8px;border-radius:999px;margin-left:6px}
.addr-card .row{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
```

- [ ] **Step 7: Write the failing test** — `backend/storefront/tests/test_account.py`
```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AccountIndexTests(TestCase):
    def test_requires_login(self):
        r = self.client.get(reverse("storefront:account"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])

    def test_renders_greeting_and_tiles(self):
        user = User.objects.create_user(
            phone="+256772000001", password="s3cure-pass-99", first_name="Ada", last_name="L"
        )
        self.client.force_login(user)
        r = self.client.get(reverse("storefront:account"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Hi Ada")
        self.assertContains(r, reverse("storefront:account_orders"))
        self.assertContains(r, reverse("storefront:addresses"))
        self.assertContains(r, reverse("storefront:logout"))
```

- [ ] **Step 8: Run**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_account -v 2
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `Ran 2 tests` OK; full suite `Ran 220 tests` / `OK`.

- [ ] **Step 9: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront
git commit -m "feat(storefront): account dashboard + routes + nav"
```

---

## Task 2: Order history (list + detail) + shared receipt partial

**Files:** Modify `backend/storefront/views/account.py`, `backend/storefront/templates/storefront/order_confirmation.html`, `backend/storefront/tests/test_account.py`. Create `backend/storefront/templates/storefront/partials/order_receipt.html`, `.../account/orders.html`, `.../account/order_detail.html`.

- [ ] **Step 1: `backend/storefront/templates/storefront/partials/order_receipt.html`** (lift the receipt block out of the current `order_confirmation.html`)
```html
{% load storefront_extras %}
<table class="cart-table"><tbody>
{% for item in order.items.all %}
  <tr><td>{{ item.product_title }}<div class="muted">{{ item.variant_label }}</div></td>
      <td>× {{ item.quantity }}</td><td>{{ item.line_total|ugx }}</td></tr>
{% endfor %}
</tbody></table>
<div class="cart-summary">
  <div>Total <b>{{ order.total|ugx }}</b></div>
  <div>Paid via <b>{{ order.payment_method|default:"—" }}</b></div>
  <div>Ref <b>{{ order.payment_reference|default:"—" }}</b></div>
</div>
<p style="margin-top:16px">Delivering to {{ order.recipient_name }}, {{ order.street_area }}, {{ order.city_district }}.</p>
```

- [ ] **Step 2: Rewrite `backend/storefront/templates/storefront/order_confirmation.html`** to use the partial
```html
{% extends "storefront/base.html" %}
{% block title %}Order {{ order.order_number }} — Jangu Mobile{% endblock %}
{% block content %}
<section class="confirm">
  <div class="tick">✓</div>
  <h2>Thank you! Your order is confirmed.</h2>
  <p>Order <b>{{ order.order_number }}</b> · <span class="status-badge">{{ order.get_status_display }}</span></p>
</section>
<section class="section" style="max-width:560px;margin:0 auto">
  {% include "storefront/partials/order_receipt.html" %}
  <a class="btn btn-navy" href="{% url 'storefront:home' %}">Continue shopping</a>
</section>
{% endblock %}
```

- [ ] **Step 3: `backend/storefront/templates/storefront/account/orders.html`**
```html
{% extends "storefront/base.html" %}
{% load storefront_extras %}
{% block title %}My Orders — Jangu Mobile{% endblock %}
{% block content %}
<section class="section" style="max-width:720px;margin:0 auto">
  <h2>My Orders</h2>
  {% if page_obj.object_list %}
    {% for order in page_obj.object_list %}
    <div class="order-row">
      <div>
        <a href="{% url 'storefront:account_order' order.order_number %}">{{ order.order_number }}</a>
        <div class="muted">{{ order.created_at|date:"j M Y" }} · {{ order.items.count }} item{{ order.items.count|pluralize }}</div>
      </div>
      <span class="status-badge">{{ order.get_status_display }}</span>
      <b>{{ order.total|ugx }}</b>
    </div>
    {% endfor %}
    {% include "storefront/partials/pagination.html" %}
  {% else %}
    <p>You have no orders yet.</p>
    <a class="btn btn-primary" href="{% url 'storefront:home' %}">Start Shopping</a>
  {% endif %}
</section>
{% endblock %}
```

- [ ] **Step 4: `backend/storefront/templates/storefront/account/order_detail.html`** (cancel button is added in Task 3)
```html
{% extends "storefront/base.html" %}
{% block title %}Order {{ order.order_number }} — Jangu Mobile{% endblock %}
{% block content %}
<section class="section" style="max-width:560px;margin:0 auto">
  <p><a href="{% url 'storefront:account_orders' %}">‹ All orders</a></p>
  <h2>Order {{ order.order_number }}</h2>
  <p>Placed {{ order.created_at|date:"j M Y" }} · <span class="status-badge">{{ order.get_status_display }}</span></p>
  {% include "storefront/partials/order_receipt.html" %}
</section>
{% endblock %}
```

- [ ] **Step 5: Replace the `orders` and `order_detail` stubs in `backend/storefront/views/account.py`**

Add to the imports at the top:
```python
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from orders.models import Order
```
Replace the two stubs with:
```python
@login_required
def orders(request):
    page = Paginator(request.user.orders.all(), 10).get_page(request.GET.get("page"))
    return render(request, "storefront/account/orders.html", {"page_obj": page, "active": "account"})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, "storefront/account/order_detail.html", {"order": order, "active": "account"})
```
(Keep `from django.shortcuts import render` working — if the file already imports `render`, merge rather than duplicate.)

- [ ] **Step 6: Add tests to `backend/storefront/tests/test_account.py`**
```python
from decimal import Decimal

from orders.models import Order, OrderItem
from orders.tests.factories import make_user, make_variant


class OrderHistoryTests(TestCase):
    def setUp(self):
        self.user = make_user(phone="+256772000001")
        self.other = make_user(phone="+256772000002")
        self.client.force_login(self.user)

    def _order(self, owner, number, status=Order.Status.PAID):
        order = Order.objects.create(
            user=owner, order_number=number, status=status,
            subtotal=Decimal("1000000"), total=Decimal("1000000"),
            recipient_name="Ada", recipient_phone="+256772000009",
            city_district="Kampala", street_area="Kololo",
        )
        OrderItem.objects.create(
            order=order, variant=make_variant(sku=number), product_title="Phone X",
            variant_label="128GB", quantity=1, unit_price=Decimal("1000000"),
        )
        return order

    def test_history_lists_only_own_orders(self):
        self._order(self.user, "JNG-20260906-0001")
        self._order(self.other, "JNG-20260906-0002")
        r = self.client.get(reverse("storefront:account_orders"))
        self.assertContains(r, "JNG-20260906-0001")
        self.assertNotContains(r, "JNG-20260906-0002")

    def test_history_requires_login(self):
        self.client.logout()
        r = self.client.get(reverse("storefront:account_orders"))
        self.assertIn("/login/", r["Location"])

    def test_detail_shows_items_and_total(self):
        order = self._order(self.user, "JNG-20260906-0003")
        r = self.client.get(reverse("storefront:account_order", args=[order.order_number]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Phone X")
        self.assertContains(r, "UGX 1,000,000")

    def test_detail_404_for_another_users_order(self):
        order = self._order(self.other, "JNG-20260906-0004")
        r = self.client.get(reverse("storefront:account_order", args=[order.order_number]))
        self.assertEqual(r.status_code, 404)
```

- [ ] **Step 7: Run**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_account storefront.tests.test_checkout -v 2 2>&1 | grep -E "^Ran |^OK$|^FAILED"
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `test_account` + `test_checkout` all pass (the confirmation-page rewrite doesn't break `test_checkout`'s 200/404 assertions); full suite `Ran 224 tests` / `OK`.

- [ ] **Step 8: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront
git commit -m "feat(storefront): order history list + detail; shared order-receipt partial"
```

---

## Task 3: Order self-cancel

**Files:** Modify `backend/storefront/views/account.py`, `backend/storefront/templates/storefront/account/order_detail.html`, `backend/storefront/tests/test_account.py`.

- [ ] **Step 1: Replace the `order_cancel` stub in `backend/storefront/views/account.py`**

Add to the imports (merge `redirect` into the existing `from django.shortcuts import …` line rather than adding a second one):
```python
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders import services
from orders.exceptions import OrderNotCancellable
```
Replace the stub with:
```python
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
```

- [ ] **Step 2: Add the cancel button to `backend/storefront/templates/storefront/account/order_detail.html`**

Immediately before the closing `</section>`, add:
```html
  {% if order.status == "PENDING" or order.status == "PAID" %}
  <form method="post" action="{% url 'storefront:account_order_cancel' order.order_number %}" style="margin-top:16px">
    {% csrf_token %}
    <button class="btn" type="submit">Cancel order</button>
  </form>
  {% endif %}
```

- [ ] **Step 3: Add tests to `backend/storefront/tests/test_account.py`**
```python
from orders.cart import SessionCart
from orders.tests.factories import make_address, make_request


class OrderCancelTests(TestCase):
    def setUp(self):
        self.user = make_user(phone="+256772000001")
        self.address = make_address(self.user)
        self.v = make_variant(sku="A", price="1000000", stock_qty=10)
        self.client.force_login(self.user)

    def _place(self, qty=3):
        cart = SessionCart(make_request())
        cart.add(self.v, qty)
        from orders import services
        return services.create_order_from_cart(user=self.user, cart=cart, address=self.address)

    def test_cancel_restores_stock_and_sets_cancelled(self):
        order = self._place(3)
        self.v.refresh_from_db()
        self.assertEqual(self.v.stock_qty, 7)
        r = self.client.post(reverse("storefront:account_order_cancel", args=[order.order_number]))
        self.assertRedirects(r, reverse("storefront:account_order", args=[order.order_number]))
        order.refresh_from_db(); self.v.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.v.stock_qty, 10)

    def test_cancel_requires_post(self):
        order = self._place(1)
        r = self.client.get(reverse("storefront:account_order_cancel", args=[order.order_number]))
        self.assertEqual(r.status_code, 405)

    def test_cancel_another_users_order_404(self):
        other = make_user(phone="+256772000099")
        cart = SessionCart(make_request())
        v = make_variant(sku="Z", stock_qty=5)
        cart.add(v, 1)
        from orders import services
        order = services.create_order_from_cart(user=other, cart=cart, address=make_address(other))
        r = self.client.post(reverse("storefront:account_order_cancel", args=[order.order_number]))
        self.assertEqual(r.status_code, 404)

    def test_cancel_shipped_order_shows_error(self):
        order = self._place(1)
        order.status = Order.Status.SHIPPED
        order.save()
        r = self.client.post(reverse("storefront:account_order_cancel", args=[order.order_number]), follow=True)
        self.assertContains(r, "no longer be cancelled")

    def test_detail_hides_cancel_for_shipped(self):
        order = self._place(1)
        order.status = Order.Status.SHIPPED
        order.save()
        r = self.client.get(reverse("storefront:account_order", args=[order.order_number]))
        self.assertNotContains(r, "Cancel order")

    def test_detail_shows_cancel_for_paid(self):
        order = self._place(1)
        r = self.client.get(reverse("storefront:account_order", args=[order.order_number]))
        self.assertContains(r, "Cancel order")
```

- [ ] **Step 4: Run**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_account -v 2 2>&1 | grep -E "^Ran |^OK$|^FAILED"
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `test_account` all pass; full suite `Ran 230 tests` / `OK`.

- [ ] **Step 5: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront
git commit -m "feat(storefront): self-service order cancellation"
```

---

## Task 4: Address book

**Files:** Modify `backend/storefront/views/account.py`, `backend/storefront/tests/test_account.py`. Create `backend/storefront/templates/storefront/account/addresses.html`, `.../account/address_form.html`.

- [ ] **Step 1: Replace the address stubs in `backend/storefront/views/account.py`**

Add to the imports:
```python
from django.contrib.auth import get_user_model
from django.db import transaction

from storefront.forms import AddressForm
```
After this task every stub is gone, so also **remove the now-unused `from django.http import HttpResponse`** line added in Task 1.

Replace the five stubs (`addresses`, `address_add`, `address_edit`, `address_delete`, `address_set_default`) with:
```python
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
```

- [ ] **Step 2: `backend/storefront/templates/storefront/account/addresses.html`**
```html
{% extends "storefront/base.html" %}
{% block title %}Delivery Addresses — Jangu Mobile{% endblock %}
{% block content %}
<section class="section" style="max-width:640px;margin:0 auto">
  <div class="section-head"><h2>Delivery Addresses</h2><a href="{% url 'storefront:address_add' %}">+ Add address</a></div>
  {% for a in addresses %}
  <div class="addr-card">
    <b>{{ a.recipient_name }}</b>{% if a.is_default %}<span class="badge">Default</span>{% endif %}
    <div class="muted">{{ a.recipient_phone }} · {{ a.street_area }}, {{ a.city_district }}{% if a.landmark %} ({{ a.landmark }}){% endif %}</div>
    <div class="row">
      <a class="btn" href="{% url 'storefront:address_edit' a.pk %}">Edit</a>
      {% if not a.is_default %}
      <form method="post" action="{% url 'storefront:address_set_default' a.pk %}">{% csrf_token %}<button class="btn" type="submit">Make default</button></form>
      {% endif %}
      <form method="post" action="{% url 'storefront:address_delete' a.pk %}">{% csrf_token %}<button class="btn" type="submit">Delete</button></form>
    </div>
  </div>
  {% empty %}
  <p>You have no saved addresses.</p>
  {% endfor %}
</section>
{% endblock %}
```

- [ ] **Step 3: `backend/storefront/templates/storefront/account/address_form.html`**
```html
{% extends "storefront/base.html" %}
{% block title %}{{ heading }} — Jangu Mobile{% endblock %}
{% block content %}
<section class="section" style="max-width:480px;margin:0 auto">
  <h2>{{ heading }}</h2>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button class="btn btn-primary btn-block" type="submit">Save</button>
  </form>
  <p style="margin-top:12px"><a href="{% url 'storefront:addresses' %}">‹ Back to addresses</a></p>
</section>
{% endblock %}
```

- [ ] **Step 4: Add tests to `backend/storefront/tests/test_account.py`**
```python
class AddressBookTests(TestCase):
    def setUp(self):
        self.user = make_user(phone="+256772000001")
        self.other = make_user(phone="+256772000002")
        self.client.force_login(self.user)

    def test_list_shows_only_own_addresses_with_default_badge(self):
        mine = make_address(self.user)  # first address -> is_default
        make_address(self.other)
        r = self.client.get(reverse("storefront:addresses"))
        self.assertContains(r, mine.recipient_name)
        self.assertContains(r, "Default")

    def test_add_creates_address_and_normalises_phone(self):
        r = self.client.post(reverse("storefront:address_add"), {
            "recipient_name": "Ada L", "recipient_phone": "0770000000",
            "city_district": "Jinja", "street_area": "Main St", "landmark": "",
        })
        self.assertRedirects(r, reverse("storefront:addresses"))
        a = self.user.addresses.get()
        self.assertEqual(a.recipient_phone, "+256770000000")
        self.assertTrue(a.is_default)

    def test_edit_is_owner_scoped(self):
        mine = make_address(self.user)
        r = self.client.post(reverse("storefront:address_edit", args=[mine.pk]), {
            "recipient_name": "New Name", "recipient_phone": mine.recipient_phone,
            "city_district": mine.city_district, "street_area": mine.street_area, "landmark": "",
        })
        self.assertRedirects(r, reverse("storefront:addresses"))
        mine.refresh_from_db()
        self.assertEqual(mine.recipient_name, "New Name")
        theirs = make_address(self.other)
        self.assertEqual(self.client.get(reverse("storefront:address_edit", args=[theirs.pk])).status_code, 404)

    def test_set_default_switches_and_unsets_previous(self):
        a1 = make_address(self.user)   # default
        a2 = make_address(self.user)   # not default
        r = self.client.post(reverse("storefront:address_set_default", args=[a2.pk]))
        self.assertRedirects(r, reverse("storefront:addresses"))
        a1.refresh_from_db(); a2.refresh_from_db()
        self.assertFalse(a1.is_default)
        self.assertTrue(a2.is_default)

    def test_delete_promotes_a_replacement_default(self):
        a1 = make_address(self.user)   # default
        a2 = make_address(self.user)
        r = self.client.post(reverse("storefront:address_delete", args=[a1.pk]))
        self.assertRedirects(r, reverse("storefront:addresses"))
        self.assertFalse(self.user.addresses.filter(pk=a1.pk).exists())
        a2.refresh_from_db()
        self.assertTrue(a2.is_default)

    def test_delete_requires_post_and_is_owner_scoped(self):
        mine = make_address(self.user)
        self.assertEqual(self.client.get(reverse("storefront:address_delete", args=[mine.pk])).status_code, 405)
        theirs = make_address(self.other)
        self.assertEqual(self.client.post(reverse("storefront:address_delete", args=[theirs.pk])).status_code, 404)
```

- [ ] **Step 5: Run**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_account -v 2 2>&1 | grep -E "^Ran |^OK$|^FAILED"
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `test_account` all pass; full suite `Ran 236 tests` / `OK`.

- [ ] **Step 6: Commit**
```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront
git commit -m "feat(storefront): address book — list, add, edit, delete, set-default"
```

---

## Task 5: Phase 1c verification gate

**Files:** none (verification only).

- [ ] **Step 1: Full suite**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test 2>&1 | grep -E "^Ran |^OK$|^FAILED"
```
Expected: `OK`, 0 failures (≈236 tests).

- [ ] **Step 2: Deploy check**
```bash
DEBUG=False SECRET_KEY=verify-only-1234567890 python manage.py check --deploy 2>&1 | grep -E "W0|ERROR|identified"
```
Expected: only `security.W004`/`W008`/`W009`, no `ERROR`.

- [ ] **Step 3: Render check under `gunicorn` / `DEBUG=False`**
```bash
cd /Users/mac/projects/jango_mobileapp/backend
rm -f db.sqlite3 && rm -rf staticfiles media
export DEBUG=False SECRET_KEY=verify-only-1234567890 ALLOWED_HOSTS=127.0.0.1,localhost DJANGO_SETTINGS_MODULE=backend.settings
python manage.py collectstatic --no-input >/dev/null
python manage.py migrate >/dev/null
python manage.py seed_demo >/dev/null
../.venv/bin/gunicorn backend.wsgi:application --bind 127.0.0.1:8131 --workers 2 --pid /tmp/g8131.pid >/tmp/g8131.log 2>&1 &
sleep 6
for p in "/account/" "/account/orders/" "/account/addresses/" "/account/addresses/add/"; do
  printf '%-30s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' -L "http://127.0.0.1:8131$p")"
done
# each must land on the login page (302 -> 200 after -L) since anonymous
curl -s -L "http://127.0.0.1:8131/account/" | grep -o "Log in" | head -1
kill "$(cat /tmp/g8131.pid)"; rm -f /tmp/g8131.pid /tmp/g8131.log
rm -f db.sqlite3 && rm -rf staticfiles media
```
Expected: all four paths `200` (login page after the `@login_required` redirect); `Log in` echoed. (The authenticated flows are covered by the 18 new `test_account` tests.)

- [ ] **Step 4: Report**
Summarise: commits (dashboard+routes+nav → order history + receipt partial → cancel → address book), full suite green, account routes render under `DEBUG=False`. Phase 1c — and storefront Milestone 1 — is complete and deployable. Remaining follow-ups are the ones logged in the 1b review (rate-limiting, checkout address dedupe, `?simulate=fail` gating, `_variant_label` shared home) plus: real payment gateway, Cloudflare R2 media, prettier `payment_method` display.

---

## Self-Review

**Spec coverage (§6.2 account routes, §6.4 account pages, §12 "1c"):**
- `account` / `/account/` dashboard — Task 1.
- `account_orders` + `account_order` (list + detail, owner-scoped 404) — Task 2.
- `account_order_cancel` (POST, owner, restores stock via `services.cancel_order`) — Task 3.
- `addresses` / `address_add` / `address_edit` / `address_delete` (owner-scoped, promote-on-delete) — Task 4. `address_set_default` added (documented deviation).
- `account/index.html`, `account/orders.html`, `account/order_detail.html`, `account/addresses.html`, `account/address_form.html` — Tasks 1–4. `account/order_detail.html` "same content as confirmation + Cancel button" via the shared `partials/order_receipt.html`.
- Nav repointed (header authed link + bottom-nav Account) — Task 1.
- register / login / logout — **already shipped in Phase 1b**, not repeated here (noted in header).
- Tests per §6.8 "account" bullet (history scoped to user, detail 404 for other user, cancel restores stock + `CANCELLED`, address add/edit/delete) — Tasks 1–4; plus set-default, POST-only guards, and login-required checks.

**Placeholder scan:** none. Every step has full file content or an exact edit against known current text. Task 1's stub views carry an explicit `# Task N` marker and each is replaced verbatim in its later task.

**Type/name consistency:** URL names (`account`, `account_orders`, `account_order`, `account_order_cancel`, `addresses`, `address_add`, `address_edit`, `address_delete`, `address_set_default`) identical across `urls.py`, templates, views, and every test. View function names in `account.py` match the `urls.py` references. `Order.Status.{PENDING,PAID,CANCELLED,SHIPPED}` and `services.cancel_order` / `OrderNotCancellable` match the Phase 1b `orders` API. `AddressForm` fields match the Phase 1b definition (no `is_default` field — default changes go through `address_set_default`, mirroring `accounts.AddressViewSet`). `partials/order_receipt.html` and `partials/pagination.html` context keys (`order`, `page_obj`) match their consumers. `make_user` / `make_variant` / `make_address` / `make_request` / `SessionCart` imported from the Phase 1b `orders.tests.factories` and `orders.cart`.
