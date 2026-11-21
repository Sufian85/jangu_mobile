# Jango Mobile Backend — Sub-project 3: Cart & Orders

**Status:** Approved · **Date:** 2026-08-12

## Context

Jango Mobile is a Django + DRF e-commerce backend (Jumia UG-style) with a Flutter
customer app and a staff console, per `Jangu-Mobile-Spec (1).md`. Sub-projects 1
(`docs/superpowers/specs/2026-07-04-accounts-auth-design.md`) and 2
(`docs/superpowers/specs/2026-08-09-catalogue-design.md`) delivered the `accounts`
app (custom phone-keyed `User`, JWT auth, addresses) and the `catalogue` app
(categories, products, variants, images, public browse API, staff management
API) — both complete and merged into `master`.

This sub-project covers **cart and orders** (master spec's M3): a per-user
shopping cart backed by `catalogue.ProductVariant`, and order creation/history
built from that cart. It does not include payment processing (M4, mock
payment simulation) or a staff order-management API (M5, staff console) —
both later sub-projects.

## Goals

- `orders` app with `Cart`, `CartItem`, `Order`, `OrderItem` models.
- Customer-facing (`IsAuthenticated`) cart API: view cart, add/update/remove
  items, with live pricing and stock validation.
- Order creation from the cart: atomic stock decrement, address snapshotting,
  cart clearing.
- Order history: list/detail of the authenticated user's own orders, and
  self-service cancellation while an order is still `PENDING`.
- Django Admin registration for staff visibility, as a stopgap until the M5
  staff console.
- Everything covered by automated tests (TDD), matching the `accounts` and
  `catalogue` apps' testing style.

## Non-goals

- Payment processing / the `PAID` status transition and everything after it
  (`PROCESSING`, `SHIPPED`, `DELIVERED`) — master spec's M4/M5, later
  sub-projects. This sub-project only ever produces orders at `PENDING` or
  customer-cancelled `CANCELLED`.
- A staff-facing order-management API — deferred to M5, unlike the catalogue
  sub-project's staff API. Staff can already see/manage `Order`/`Cart` rows
  via Django Admin in the meantime.
- Delivery-zone-based pricing — `delivery_fee` is always `0` for now.
- Guest/anonymous carts — carts require an authenticated `User`.
- Coupons, promotions, multi-currency.

## 1. Architecture & config

- New `orders` app: models, serializers, views, urls, admin — same layering
  as `accounts`/`catalogue`.
- No new permission class needed: every endpoint uses
  `rest_framework.permissions.IsAuthenticated` (the project-wide default —
  no `AllowAny` overrides needed here, unlike catalogue's public browse
  endpoints), scoped to `request.user`'s own `Cart`/`Order`s.
- `INSTALLED_APPS` gains `"orders"`.
- No new third-party dependencies or settings changes required — reuses the
  pagination, filtering, and media config already established by `catalogue`.

## 2. Data model

### Cart (`orders.Cart`)

| Field | Notes |
|---|---|
| `user` | `OneToOneField` → `accounts.User` — one cart per user |
| `created_at` | auto |

Auto-created (get-or-create) the first time a user touches the cart API —
there is no explicit "create a cart" endpoint.

### CartItem (`orders.CartItem`)

| Field | Notes |
|---|---|
| `cart` | FK → `Cart`, `related_name="items"`, CASCADE |
| `variant` | FK → `catalogue.ProductVariant`, CASCADE — a cart is not historical, so removing a variant from the catalogue simply removes it from carts |
| `quantity` | `PositiveIntegerField`, must be ≥ 1 |
| `created_at` | auto |

`Meta.unique_together = [("cart", "variant")]` — adding a variant already in
the cart increments its `quantity` instead of creating a duplicate row.
**No stored price**: a cart item's line price is always computed live from
`variant.price × quantity` at read time. A product's price change is
reflected immediately in every cart that contains it — carts don't lock in
price, only completed orders do (see `OrderItem.unit_price` below).

Stock is validated (not reserved) on add/update: a write that would make
`quantity` exceed the variant's current `stock_qty` is rejected with 400.
This is a soft check — another customer could still buy the last unit before
this cart converts to an order — real reservation happens at order creation.

### Order (`orders.Order`)

| Field | Notes |
|---|---|
| `user` | FK → `accounts.User`, `related_name="orders"` |
| `order_number` | unique, format `JNG-YYYYMMDD-NNNN` (today's date + a per-day zero-padded 4-digit counter), generated at creation |
| `status` | `CharField` with choices `PENDING`, `PAID`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`; default `PENDING` |
| `subtotal` | `DecimalField`, snapshot sum of all `OrderItem.unit_price × quantity` at creation — never recomputed |
| `delivery_fee` | `DecimalField`, always `0` in this sub-project |
| `total` | `DecimalField`, `subtotal + delivery_fee` at creation |
| `recipient_name`, `recipient_phone`, `city_district`, `street_area`, `landmark` | snapshotted from the chosen `Address` at creation — order history stays accurate even if that address is later edited or deleted |
| `address` | FK → `accounts.Address`, nullable, `SET_NULL` — kept for reference/reorder convenience only; the snapshot fields above are the source of truth for display |
| `created_at` | auto |

### OrderItem (`orders.OrderItem`)

| Field | Notes |
|---|---|
| `order` | FK → `Order`, `related_name="items"`, CASCADE |
| `variant` | FK → `catalogue.ProductVariant`, **PROTECT** — mirrors the existing `Product.category` PROTECT precedent from the catalogue sub-project; staff cannot delete a variant that has order history |
| `quantity` | `PositiveIntegerField` |
| `unit_price` | `DecimalField`, snapshot of `variant.price` at order-creation time — order history must never change if the product's price changes later |

Both model pairs registered in Django Admin (`list_display`, basic
search/filter by status) so staff can view orders while M5's dedicated
console doesn't exist yet.

## 3. Cart & Order API

Base path: `/api/`. All endpoints `IsAuthenticated`, scoped to
`request.user`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/cart/` | current user's cart: items (variant, quantity, live unit price, line total) + computed subtotal |
| POST | `/api/cart/items/` | add an item (`variant_id`, `quantity`); increments quantity if the variant's already present |
| PATCH | `/api/cart/items/{id}/` | update quantity (absolute, not incremental) |
| DELETE | `/api/cart/items/{id}/` | remove an item |
| POST | `/api/orders/` | create an order from the cart (`address_id`); 400 if cart is empty, `address_id` doesn't belong to the user, or any line fails stock validation |
| GET | `/api/orders/` | list own orders, paginated, newest first |
| GET | `/api/orders/{order_number}/` | own order detail, with items |
| POST | `/api/orders/{order_number}/cancel/` | cancel own order — only while `status == PENDING`; restores stock |

All cart-item and order lookups scope to the requesting user and return 404
(not 403) for another user's resources — matching the existing `Address`
pattern from the `accounts` app.

**Order creation**, inside one DB transaction:
1. Re-validate stock for every cart line (hard check — the actual
   reservation moment, since there's no payment gateway to hook a later
   reservation to). Any insufficient line aborts the whole request with a
   400 listing which items failed — no order is created.
2. Create the `Order` (snapshotting address fields, `subtotal`/`total`,
   `order_number`) and one `OrderItem` per cart line (snapshotting
   `unit_price`).
3. Decrement `variant.stock_qty` for each line.
4. Clear the cart (delete its `CartItem`s).

**Order cancellation**, inside one DB transaction: only permitted while
`status == PENDING`; restores `variant.stock_qty` for every `OrderItem`,
then sets `status = CANCELLED`.

## 4. Testing

TDD throughout, matching the `accounts`/`catalogue` apps' testing style.

- **Model tests:** `order_number` generation format and uniqueness (including
  same-day counter increments); `CartItem` unique-together / quantity-
  increment-on-duplicate-add behavior; `Order`/`OrderItem` snapshot fields
  are genuinely copied values, not live references (mutate the source
  `Address`/`ProductVariant` after order creation and confirm the order is
  unaffected).
- **Cart API tests:** add/update/remove scoped to own cart (404 on another
  user's item); stock validation rejects over-quantity adds/updates; adding
  an already-present variant increments rather than duplicates; cart totals
  reflect live variant pricing.
- **Order API tests:** creation from a populated cart succeeds and clears
  the cart; creation from an empty cart returns 400; creation with
  insufficient stock on any line returns 400 and creates nothing (verify no
  partial `Order`/`OrderItem` rows persist — transactional); creation with
  an `address_id` belonging to another user returns 400/404; stock is
  actually decremented after creation; list/detail scoped to own orders
  (404 on another user's order by number); cancel restores stock and sets
  `CANCELLED`; cancel on a non-`PENDING` order is rejected.
- Django Admin smoke test: staff can reach the `Cart`/`Order` admin
  changelists (mirrors the existing pattern from `accounts`/`catalogue`).

## Open items for implementation time

- Exact per-day order-number counter implementation (e.g. a dedicated
  counter table vs. `Order.objects.filter(created_at__date=today).count()`
  under a row lock) — implementation-time call, not architecturally
  significant either way, as long as it's race-safe under concurrent order
  creation.
