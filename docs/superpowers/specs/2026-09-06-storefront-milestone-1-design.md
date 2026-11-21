# Jangu Mobile Storefront — Milestone 1 — design

- **Date:** 2026-09-06
- **Status:** Approved (design), pending implementation plan
- **Author:** Mugisha Ivan Jalagatha

## 1. Context

`jango_mobileapp` is a Django 5.2 + DRF backend. Existing apps:

- `accounts` — phone-keyed custom `User` (`USERNAME_FIELD = "phone"`), JWT auth,
  `Address` model.
- `catalogue` — `Category`, `Product`, `ProductVariant` (`sku`, `attributes` JSON,
  `price`, `stock_qty`), `ProductImage` (`image`, `is_primary`, `sort_order`);
  public browse APIs and staff CRUD APIs.
- `core` — exception handler; a temporary API-info page at `/`.

There is an **approved but unimplemented** spec for a REST cart/orders API
(`docs/superpowers/specs/2026-08-12-cart-orders-design.md`, "M3"). This milestone
supersedes M3's `Cart`/`CartItem` design (see §4) but keeps its `Order`/`OrderItem`
model and its transactional order-creation rules.

The goal: a **public-facing, server-rendered storefront** where a shopper browses
gadgets, adds them to a cart, and checks out with a **simulated** payment, styled
to the Jangu Mobile brand (navy + orange). Plus a **rebranded, recoloured Django
admin**.

## 2. Goals

- A customer can, on the deployed site: browse the home page, open a
  category, search, view a product, add variants to a cart, sign up / log in,
  choose a delivery address, "pay" (simulated), and see an order confirmation and
  their order history.
- Server-rendered Django (templates + light vanilla JS), one repo, one
  web service, one deploy. No SPA, no second service.
- Visual match to the supplied branding image: navy `#12356E` / orange `#EF7C1B`
  palette, Poppins headings, hero + "Shop by Category" + "Featured Products" +
  trust badges, sticky header with cart badge, mobile bottom nav.
- Durable `Order`/`OrderItem` records with price/address snapshotting and
  transactional stock handling (per M3).
- Django admin shows "Jangu Mobile" branding and the brand colours.
- Demo catalogue seeded automatically on every deploy (SQLite is ephemeral).
- TDD throughout, matching the `accounts`/`catalogue` test style
  (`django.test`, `manage.py test`).

## 3. Non-goals (later milestones)

- Real payment gateway (MTN/Airtel MoMo, card). Payment is **simulated** — a
  method choice and a "Pay" button that always succeeds (with a test-only failure
  path).
- A REST cart/order API for a future mobile app.
- Guest checkout — checkout requires login (M3: carts/orders require a `User`).
- Delivery-fee calculation — `delivery_fee` is always `0`.
- Coupons, promotions, wishlist, product reviews/ratings (the image's star
  ratings are omitted — there is no rating model), stock reservations beyond
  order creation, order fulfilment states past `PAID`, email/SMS notifications,
  multi-currency (UGX only), Cloudflare R2 media (demo images are re-seeded each
  deploy).
- Changes to the existing `accounts` / `catalogue` REST APIs.

## 4. Architecture

Two new Django apps under `backend/`, plus small changes to `core` and config.

```
backend/
  storefront/      NEW — all customer-facing pages, brand design system, seed
  orders/          NEW — Order/OrderItem models, order service layer, session cart, admin
  core/            + admin.py (site branding), - index view/template/test
  templates/admin/base_site.html   NEW — project-level admin recolour override
  backend/
    settings.py    + INSTALLED_APPS, TEMPLATES DIRS, LOGIN_URL/redirects, storefront context processor
    urls.py        - core.index route; + include("storefront.urls") LAST
```

- `catalogue` and `accounts` models are **reused unchanged**. The storefront
  reads catalogue models directly (via `storefront/selectors.py`), not through
  the DRF API.
- **Session cart, not a DB cart.** The cart is `request.session["cart"]`, a
  `{ "<variant_id>": quantity }` map. Anonymous shoppers can add to cart; login
  is required only at checkout. This replaces M3's `Cart`/`CartItem` tables
  (never built). A future mobile app can get a DB/REST cart in its own
  sub-project.
- **`orders` owns durable data + domain logic only** — no views, no REST API
  this milestone. The storefront calls `orders.services`.
- Storefront auth is **Django session auth** (`django.contrib.auth`) over the
  existing `accounts.User`. The DRF API keeps JWT. `SessionAuthentication` is
  already enabled project-wide.
- The storefront `views/` is a **package** (not a flat `views.py`) because it has
  many view groups; `orders` uses flat modules like `accounts`/`catalogue`. This
  is a deliberate, size-justified deviation from the flat-file pattern.

## 5. `orders` app

### 5.1 Models (`orders/models.py`)

**`Order`**

| Field | Type | Notes |
|---|---|---|
| `user` | FK → `accounts.User`, `related_name="orders"`, `on_delete=PROTECT` | order history outlives account-deletion attempts |
| `order_number` | `CharField(max_length=20, unique=True, editable=False)` | `JNG-YYYYMMDD-NNNN` (§5.2) |
| `status` | `CharField(max_length=12, choices=Status, default=Status.PENDING)` | `PENDING, PAID, PROCESSING, SHIPPED, DELIVERED, CANCELLED` (only `PENDING`/`PAID`/`CANCELLED` reachable this milestone) |
| `payment_method` | `CharField(max_length=20, blank=True)` | `mtn_momo` \| `airtel_money` \| `card`, set at simulated payment |
| `payment_reference` | `CharField(max_length=40, blank=True)` | `SIM-XXXXXXXX` generated at simulated payment |
| `subtotal` | `DecimalField(max_digits=12, decimal_places=2)` | snapshot Σ(`OrderItem.unit_price` × `quantity`) |
| `delivery_fee` | `DecimalField(max_digits=12, decimal_places=2, default=0)` | always `0` |
| `total` | `DecimalField(max_digits=12, decimal_places=2)` | `subtotal + delivery_fee` |
| `recipient_name` | `CharField(max_length=100)` | snapshot from `Address` |
| `recipient_phone` | `CharField(max_length=13)` | snapshot |
| `city_district` | `CharField(max_length=100)` | snapshot |
| `street_area` | `CharField(max_length=255)` | snapshot |
| `landmark` | `CharField(max_length=255, blank=True)` | snapshot |
| `address` | FK → `accounts.Address`, `null=True, blank=True, on_delete=SET_NULL` | reference only; snapshots above are source of truth |
| `created_at` | `DateTimeField(auto_now_add=True)` | |
| `paid_at` | `DateTimeField(null=True, blank=True)` | set at simulated payment |

`Meta.ordering = ["-created_at"]`. `Status` is a `models.TextChoices`.
`__str__` → `order_number`.

**`OrderItem`**

| Field | Type | Notes |
|---|---|---|
| `order` | FK → `Order`, `related_name="items"`, `on_delete=CASCADE` | |
| `variant` | FK → `catalogue.ProductVariant`, `on_delete=PROTECT` | mirrors catalogue's PROTECT precedent |
| `product_title` | `CharField(max_length=200)` | snapshot, for display resilience |
| `variant_label` | `CharField(max_length=120, blank=True)` | snapshot, e.g. `128GB / Black` from `attributes` |
| `quantity` | `PositiveIntegerField` | ≥ 1 |
| `unit_price` | `DecimalField(max_digits=10, decimal_places=2)` | snapshot of `variant.price` at creation |

`line_total` is a `@property` (`unit_price * quantity`), not stored.

Both models registered in Django admin (§7).

### 5.2 `order_number` generation

Format `JNG-YYYYMMDD-NNNN`, `NNNN` a per-day 1-based counter, zero-padded to 4.
Race-safe implementation: inside the order-creation transaction, compute
`NNNN = Order.objects.filter(created_at__date=today).count() + 1`, build the
number, `save()`; on `IntegrityError` (unique collision under concurrency), retry
with `NNNN += 1`, up to 5 attempts, then raise. No counter table.
(Alternative — a `DailyCounter(date unique, value)` row locked with
`select_for_update` — is acceptable if the retry loop proves awkward; call it at
implementation time.)

### 5.3 Session cart (`orders/cart.py`)

`class SessionCart` wrapping `request.session`:

- `SESSION_KEY = "cart"`; stored value is `{ "<variant_id>": <int qty> }`.
- `add(variant, qty=1, *, replace=False)` — add or increment (or set, if
  `replace`); raises `InsufficientStockError` if resulting qty >
  `variant.stock_qty`.
- `set_quantity(variant_id, qty)` — absolute; `qty <= 0` removes; stock-checked.
- `remove(variant_id)`.
- `clear()`.
- `__iter__()` — yields `{"variant": ProductVariant, "quantity": int,
  "unit_price": Decimal, "line_total": Decimal}`, prices resolved **live**;
  unknown/deleted variant ids are skipped and pruned from the session.
- `__len__()` — total unit count (Σ quantities).
- `subtotal` property — Σ `line_total`.
- Mutations set `session.modified = True`.

### 5.4 Service layer (`orders/services.py`)

All functions `@transaction.atomic`. Custom exceptions in `orders/exceptions.py`:
`EmptyCartError`, `InsufficientStockError` (carries a list of
`{variant, requested, available}`), `AddressOwnershipError`,
`PaymentSimulatedFailure`, `OrderNotCancellable`.

- `create_order_from_cart(*, user, cart: SessionCart, address: Address) -> Order`
  1. If `address.user_id != user.id` → `AddressOwnershipError`.
  2. Materialise cart lines; empty → `EmptyCartError`.
  3. `select_for_update()` every referenced `ProductVariant`; for any line with
     `quantity > variant.stock_qty`, collect it; if any → `InsufficientStockError`
     (nothing persisted).
  4. Create `Order` (snapshot address fields, `subtotal`/`total`,
     `order_number`), one `OrderItem` per line (snapshot `product_title`,
     `variant_label` from `attributes`, `unit_price`).
  5. Decrement each `variant.stock_qty`.
  6. `cart.clear()`.
- `mark_paid(order, *, method: str, fail: bool = False) -> Order`
  - `fail` → `PaymentSimulatedFailure` (order untouched).
  - else: set `status=PAID`, `payment_method=method`,
    `payment_reference="SIM-" + 8 hex`, `paid_at=now()`; save.
  - Idempotent: a non-`PENDING` order is returned unchanged.
- `cancel_order(order) -> Order`
  - Only `status in {PENDING, PAID}` → else `OrderNotCancellable`.
  - `select_for_update()` variants, restore `stock_qty` for each `OrderItem`,
    set `status=CANCELLED`.

### 5.5 `orders` tests (`orders/tests/`)

- **models:** `order_number` format; uniqueness; same-day counter increments;
  `line_total` maths.
- **cart:** add creates/increments; `replace`; `set_quantity` absolute + `<=0`
  removes; stock over-add raises; `__len__`/`subtotal`; deleted-variant id pruned
  on iteration.
- **services:** `create_order_from_cart` — happy path clears cart, decrements
  stock, snapshots (mutate variant price + `Address` afterwards → order
  unchanged); empty cart raises; over-stock on any line raises and persists
  nothing (assert no `Order`/`OrderItem` rows); foreign `Address` raises.
  `mark_paid` sets fields; `fail=True` raises and leaves `PENDING`; second call
  is a no-op. `cancel_order` restores stock and sets `CANCELLED`; non-cancellable
  status raises.
- **admin:** staff can load the `Order` changelist (smoke test, per existing
  pattern).

## 6. `storefront` app

### 6.1 Structure

```
storefront/
  apps.py  urls.py  forms.py  context_processors.py  selectors.py
  views/__init__.py  views/catalog.py  views/cart.py  views/checkout.py
        views/account.py  views/auth.py
  templatetags/storefront_extras.py       # `ugx`, `variant_label`
  static/storefront/css/app.css
  static/storefront/js/app.js             # mobile nav, qty steppers, variant select, add-to-cart
  static/storefront/fonts/                # self-hosted Poppins 500/600/700 woff2 (OFL; from google-webfonts-helper)
  static/storefront/img/logo.svg  icon-*.svg  placeholder.svg
  seed_assets/                            # ~12 product JPEGs, 4 category images
  management/commands/seed_demo.py
  templates/storefront/
    base.html
    partials/{header,footer,bottom_nav,trust_badges,product_card,pagination,messages,price}.html
    home.html  category.html  search.html  product_detail.html
    cart.html  checkout.html  payment.html  order_confirmation.html
    account/{index,orders,order_detail,addresses,address_form}.html
    auth/{login,register}.html
  tests/{test_home,test_catalog,test_cart,test_checkout,test_account,test_auth,test_seed}.py
```

### 6.2 Routes (`storefront/urls.py`, `app_name = "storefront"`)

| Name | Path | View | Auth |
|---|---|---|---|
| `home` | `/` | `catalog.home` | public |
| `category` | `/c/<slug:slug>/` | `catalog.category` | public |
| `search` | `/search/` | `catalog.search` (`?q=`) | public |
| `product` | `/p/<slug:slug>/` | `catalog.product_detail` | public |
| `cart` | `/cart/` | `cart.detail` | public |
| `cart_add` | `/cart/add/` | `cart.add` (POST) | public |
| `cart_update` | `/cart/update/` | `cart.update` (POST) | public |
| `cart_remove` | `/cart/remove/` | `cart.remove` (POST) | public |
| `checkout` | `/checkout/` | `checkout.checkout` | login |
| `payment` | `/checkout/payment/` | `checkout.payment` | login |
| `order_confirmation` | `/orders/<str:order_number>/` | `checkout.order_confirmation` | login, owner |
| `account` | `/account/` | `account.index` | login |
| `account_orders` | `/account/orders/` | `account.orders` | login |
| `account_order` | `/account/orders/<str:order_number>/` | `account.order_detail` | login, owner |
| `account_order_cancel` | `/account/orders/<str:order_number>/cancel/` | `account.order_cancel` (POST) | login, owner |
| `addresses` | `/account/addresses/` | `account.addresses` | login |
| `address_add` | `/account/addresses/add/` | `account.address_add` | login |
| `address_edit` | `/account/addresses/<int:pk>/edit/` | `account.address_edit` | login, owner |
| `address_delete` | `/account/addresses/<int:pk>/delete/` | `account.address_delete` (POST) | login, owner |
| `register` | `/register/` | `auth.register` | anon |
| `login` | `/login/` | `auth.login` (`django.contrib.auth` `LoginView`, custom template + phone form) | anon |
| `logout` | `/logout/` | `auth.logout` (POST) | — |

Root `urls.py`: keep `admin/`, `api/...`, `api/schema|docs/`; **remove** the
`core.index` route; append `path("", include("storefront.urls"))` **last**.
Owner-scoped views return **404** (not 403) for another user's order/address,
matching the `accounts.Address` precedent.

### 6.3 Selectors (`storefront/selectors.py`)

Query helpers returning querysets annotated with
`min_price=Min("variants__price")` and
`in_stock=Exists(variants with stock_qty > 0)`:

- `active_products()` → `Product.objects.filter(is_active=True)` base.
- `featured_products(limit=8)` → newest active with ≥1 image and stock.
- `category_products(category, *, brand=None, price_min=None, price_max=None,
  in_stock=None, sort=None)` — `sort ∈ {price_asc, price_desc, newest}`
  (default `newest`); filters on annotated `min_price`; `brand__iexact`.
- `search_products(q, **same filters)` —
  `Q(title__icontains=q) | Q(brand__icontains=q) | Q(description__icontains=q)`.
- `related_products(product, limit=4)` — same category, exclude self, newest.
- Pagination: Django `Paginator`, 12/page.

### 6.4 Pages

- **base.html** — `<head>` (self-hosted Poppins `@font-face`, `app.css`, meta
  viewport/theme-color navy), sticky **header** (logo → home, search form,
  account link, cart link with live badge from context processor), **messages**
  partial, `{% block content %}`, **trust_badges**, **footer** (navy: links,
  payment-method glyphs, copyright "© 2026 Jangu Mobile"), **bottom_nav**
  (mobile only: Home / Categories / Cart / Account).
- **home.html** — hero (navy→blue gradient, "Your Gadget. Our Priority.",
  "Shop Smart · Live Better", orange **Start Shopping** CTA → `#featured`), trust
  strip, **Shop by Category** (4 cards: Smartphones, Laptops & Accessories,
  Audio & Wearables, Gaming Gear — icon + name → `category`), **Featured
  Products** grid (`product_card` × up to 8) with "View All" → first category.
- **category.html / search.html** — page title, result count, a filter bar
  (brand `<select>` of distinct brands in scope, price min/max, in-stock
  checkbox, sort `<select>`; GET form), product grid, pagination partial.
- **product_detail.html** — image gallery (primary + `sort_order`; JS thumbnail
  swap; `placeholder.svg` if none), brand, title, price block (`from` min price;
  updates on variant select), **variant `<select>`** (`"{variant_label} — {ugx
  price} — {In stock|Out of stock}"`), quantity stepper, **Add to Cart** (POST
  `cart_add` with `variant_id`, `quantity`; disabled if variant out of stock),
  description, **related** grid.
- **cart.html** — table/cards: thumbnail, title (link), `variant_label`, unit
  price, qty stepper (POST `cart_update`), line total, remove (POST
  `cart_remove`); empty state with CTA; summary box: subtotal, delivery
  `UGX 0`, total; **Proceed to Checkout** (→ `checkout`; anonymous users hit
  `LOGIN_URL` with `?next=/checkout/`).
- **checkout.html** — `@login_required`; if cart empty → redirect to `cart` with
  a message. Delivery address: radio list of the user's `Address`es (default
  preselected) + "Add a new address" (inline `AddressForm`); order summary
  (read-only line items + totals); **Continue to Payment** → `payment`.
  Chosen `address_id` carried via session (`checkout_address_id`).
- **payment.html** — `@login_required`; shows total and a method radio group
  (**MTN MoMo**, **Airtel Money**, **Card** — glyphs, no real fields); **Pay UGX
  {total}** button. POST → `services.create_order_from_cart(...)` then
  `services.mark_paid(order, method=…, fail=("simulate" in GET and
  GET["simulate"] == "fail"))`. On `InsufficientStockError` → back to `cart`
  with a per-item message. On `PaymentSimulatedFailure` → re-render with an
  error. On success → redirect to `order_confirmation`.
- **order_confirmation.html** — big success tick, `order_number`, status badge,
  itemised list, delivery snapshot, total, payment method + reference, links to
  `account_orders` and `home`.
- **account/index.html** — greeting (first name / phone), tiles → orders,
  addresses, logout.
- **account/orders.html** — paginated list (number, date, status badge, total,
  item count) → `account_order`.
- **account/order_detail.html** — same content as confirmation + a **Cancel
  order** button (POST `account_order_cancel`) shown only while
  `status in {PENDING, PAID}`.
- **account/addresses.html + address_form.html** — list with default badge,
  add / edit / delete; uses `AddressForm`. Reuses `accounts.Address` and its
  `save()` default-handling.
- **auth/login.html** — phone + password; Django `LoginView` with
  `authentication_form` = a form whose username field is labelled "Phone".
- **auth/register.html** — `RegisterForm`: `phone`, `first_name`, `last_name`,
  `password1`, `password2`; validates via `accounts.validators`
  `validate_uganda_phone` and `django.contrib.auth.password_validation`; on
  success creates the user (`User.objects.create_user`), logs them in, redirects
  to `next` or `home`.

### 6.5 Forms (`storefront/forms.py`)

`RegisterForm` (as above), `AddressForm` (`ModelForm` for `accounts.Address`
excluding `user`), `PhoneAuthenticationForm` (`AuthenticationForm` subclass
relabelling `username`), `AddToCartForm` / `UpdateCartForm` (validate
`variant_id` exists & active, `quantity >= 1`), `CheckoutAddressForm`
(choose existing address id or nested new-address fields).

### 6.6 Context processor & template tags

- `storefront.context_processors.cart_summary` → `{"cart_count": len(cart),
  "cart_subtotal": cart.subtotal}` on every request.
- `storefront_extras`: `ugx` filter (`2800000` → `"UGX 2,800,000"`, no
  decimals, thousands-separated), `variant_label(attributes)` (join dict values
  with `" / "`). No star-rating markup — there is no rating data and fabricated
  ratings are out of scope.

### 6.7 JS (`storefront/static/storefront/js/app.js`)

Vanilla, no framework: mobile nav toggle, quantity steppers (+/- buttons write
to a number input then submit or AJAX-post the cart form), product-image
thumbnail swap, variant `<select>` → update visible price + Add-to-Cart enabled
state, and optional `fetch`-based cart add/update returning a JSON fragment to
update the header badge without a full reload (progressive enhancement — forms
still work with JS disabled).

### 6.8 `storefront` tests

- **home:** 200; contains "Your Gadget. Our Priority." and the 4 category names;
  featured grid shows seeded products.
- **catalog:** category page filters by brand / price / in-stock and sorts;
  pagination; search matches title/brand/description; product detail 200 with
  variant options; 404 for unknown slug.
- **cart:** add sets session; add same variant increments; update to 0 removes;
  over-stock add is rejected with a message; cart totals; badge count via
  context processor.
- **checkout:** anonymous `Proceed to Checkout` → redirect to `/login/?next=`;
  empty-cart checkout → redirect to cart; logged-in checkout renders addresses;
  payment POST creates a `PAID` order, clears the cart, decrements stock,
  redirects to confirmation; `?simulate=fail` re-renders with an error and
  creates **no** order; confirmation page 404s for a different user.
- **account:** order history lists only the user's orders; order detail 404 for
  another user's number; cancel restores stock and sets `CANCELLED`; address
  add/edit/delete.
- **auth:** register creates a user, logs in, redirects; duplicate phone shows a
  form error; weak password rejected; login/logout work; `logout` requires POST.
- **seed:** `seed_demo` creates the 4 categories and N products idempotently
  (run twice → same counts), each product has ≥1 `ProductImage`, prices are
  positive.

## 7. Django admin rebrand + recolour

### 7.1 Text (`core/admin.py`, new — Django auto-imports app `admin` modules)

```python
from django.contrib import admin

admin.site.site_header = "Jangu Mobile"
admin.site.site_title = "Jangu Mobile admin"
admin.site.index_title = "Administration"
```

### 7.2 Colours (`backend/templates/admin/base_site.html`, new)

Lives in a **project-level** template dir (see §9) so the filesystem loader finds
it ahead of `django.contrib.admin`'s copy — an app-level override in `core`
would lose, because `django.contrib.admin` precedes `core` in `INSTALLED_APPS`.
The file `{% extends "admin/base.html" %}` (not `base_site.html`, to avoid
recursion), overrides the `branding` block with the Jangu wordmark, and adds an
`{% block extrastyle %}` `<style>` that sets the admin CSS custom properties to
the brand palette on `:root` (Django's dark-mode block stays usable):

```
--primary: #12356E;  --secondary: #12356E;  --accent: #EF7C1B;
--header-bg: #12356E;  --header-color: #ffffff;  --header-branding-color: #EF7C1B;
--header-link-color: #ffffff;
--link-fg: #12356E;  --link-hover-color: #EF7C1B;  --link-selected-fg: #0d2a58;
--button-bg: #EF7C1B;  --button-hover-bg: #d96f14;  --button-fg: #ffffff;
--default-button-bg: #12356E;  --default-button-hover-bg: #0d2a58;
--object-tools-bg: #12356E;  --object-tools-hover-bg: #EF7C1B;
--breadcrumbs-bg: #0d2a58;  --breadcrumbs-link-fg: #ffffff;  --breadcrumbs-fg: #cdd7e6;
```

### 7.3 Model registration

`orders/admin.py` registers `Order` (`list_display`: number, user, status, total,
created; `list_filter`: status, created; `search_fields`: order_number,
recipient_phone; `OrderItem` inline, read-only) and `OrderItem`. `accounts` and
`catalogue` admins are untouched.

### 7.4 Admin tests

`core/tests/test_admin_branding.py`: the admin login page HTML contains "Jangu
Mobile"; the response uses the project `admin/base_site.html` override
(`assertTemplateUsed`).

## 8. Seed command (`storefront/management/commands/seed_demo.py`)

Idempotent. `get_or_create` semantics keyed by `Category.slug`,
`Product.slug`, `ProductVariant.sku`.

- **Categories:** Smartphones, Laptops & Accessories, Audio & Wearables, Gaming
  Gear (each with an image from `seed_assets/`).
- **Products (~12)** in the image's spirit, e.g. Samsung Galaxy S23
  (`UGX 2,800,000`), Infinix Note 50 Pro (`UGX 1,950,000`), iPhone 15 Pro,
  MacBook Air M3, Dell XPS 13, JBL Tune 770NC, Sony WH-1000XM5, Apple AirPods
  Pro 2, Apple Watch Series 9, PlayStation 5 DualSense, Xbox Series Controller,
  Anker charging kit — each: `brand`, `description`, 1–3 `ProductVariant`s
  (`attributes` like `{"storage": "256GB", "color": "Black"}`, `price`,
  `stock_qty` 5–50), and 1 primary `ProductImage`.
- **Images:** copy the matching JPEG from `storefront/seed_assets/` into
  `MEDIA_ROOT/products/` (and category images into `MEDIA_ROOT/categories/`),
  then create the `ProductImage`/`Category.image` rows. Runs each deploy because
  media is ephemeral; skips copy if the file already exists.
- `--flush` flag (dev only, not used in the build) deletes seeded rows first.
- Output: a one-line summary of created vs. existing counts.

`seed_assets/` holds royalty-free / self-made placeholder gadget images
committed to the repo (not extracted from the branding image). Real product
photography can replace them later once R2 media is enabled.

## 9. Config changes (`backend/backend/settings.py`)

- `INSTALLED_APPS += ["storefront", "orders"]` (after `catalogue`).
- `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]` (currently `[]`) — enables the
  project-level `backend/templates/admin/base_site.html` override (§7.2).
- `TEMPLATES[0]["OPTIONS"]["context_processors"] +=
  ["storefront.context_processors.cart_summary"]`.
- `LOGIN_URL = "/login/"`, `LOGIN_REDIRECT_URL = "/"`,
  `LOGOUT_REDIRECT_URL = "/"`.
- No new dependencies. WhiteNoise already serves `storefront/static/`;
  `collectstatic` already runs in the build.
- `MEDIA_ROOT` unchanged; the deploy runs `python manage.py seed_demo` after
  `migrate` (before `ensure_superuser`).

## 10. `core` cleanup

Remove `core/views.py` (`index`), `core/templates/core/index.html`,
`core/tests/test_index.py`, and the `core.views.index` import + `path("", …)`
route in `backend/urls.py`. `/` is now the storefront home. API discovery is via
`/api/docs/`.

## 11. Rollout / verification

- **Local:** `manage.py test` green; `manage.py seed_demo` then
  `DEBUG=False gunicorn` — click through home → category → product → add to cart
  → register → checkout → simulated pay → confirmation → account orders; load
  `/admin/` and confirm "Jangu Mobile" + navy/orange.
- **Deploy:** push to `main`; the build runs
  `collectstatic` + `migrate` + `seed_demo` + `ensure_superuser`; health check
  `/api/schema/` still 200; visit `/` for the storefront.
- **Rollback:** the changes are additive (two new apps), so reverting the merge
  commit fully restores the prior state.

## 12. Implementation phasing (for the plan)

One spec, but the plan sequences it with a review checkpoint between phases:

- **1a — foundation & browsing:** `orders` app skeleton is *not* needed yet;
  build `storefront` design system (base template, `app.css`, Poppins, logo),
  `selectors`, home / category / search / product detail, `seed_demo`, admin
  rebrand + recolour, `core` cleanup. Deployable: a browsable catalogue.
- **1b — cart, checkout, orders:** `orders` models + `order_number` +
  `SessionCart` + `services` + admin; storefront cart / checkout / payment
  (simulated) / order confirmation; context processor + badge.
- **1c — accounts UI:** register / login / logout, account home, order history +
  cancel, address book.

Each phase ends green (`manage.py test`) and is independently deployable.

## 13. Open questions

None blocking. Brand text is taken as **"Jangu Mobile"** (per the logo in the
supplied image); change if "Djangu" is intended. Seed catalogue contents are
illustrative and easy to edit post-implementation.
