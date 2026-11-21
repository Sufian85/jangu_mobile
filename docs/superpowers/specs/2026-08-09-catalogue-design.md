# Jango Mobile Backend — Sub-project 2: Catalogue

**Status:** Approved · **Date:** 2026-08-09

## Context

Jango Mobile is a Django + DRF e-commerce backend (Jumia UG-style) with a Flutter
customer app and a staff console, per `Jangu-Mobile-Spec (1).md`. Sub-project 1
(`docs/superpowers/specs/2026-07-04-accounts-auth-design.md`) delivered env-driven
settings, MySQL, and the `accounts` app (custom phone-keyed `User`, JWT auth,
addresses) — that work is complete and merged into the current codebase.

This sub-project covers **catalogue**: categories, products, variants, images,
and both a public read-only browse API (for the future Flutter app) and a
staff-only management API (create/edit products, upload images, adjust stock),
built ahead of schedule relative to the master spec's M5 (staff console),
since a decision was made to expose catalogue management as an API now rather
than wait for the templated staff console.

## Goals

- `catalogue` app with `Category`, `Product`, `ProductVariant`, `ProductImage`
  models.
- Public, unauthenticated browse API: list/filter/search categories and
  products, product detail with variants and images.
- Staff-only (`IsAdminUser`) management API: full CRUD on categories,
  products, variants, and images, including image upload and "set primary
  image".
- Both surfaces registered in Django Admin as well, for quick spot-checks.
- Everything covered by automated tests (TDD), matching the `accounts` app's
  testing style.

## Non-goals

- Cart, orders, payments — later sub-projects.
- The templated staff console UI (`/staff/**` Django template views) — master
  spec's M5, still deferred; this sub-project only adds the *API* for staff
  catalogue management, not server-rendered pages.
- Flutter app — separate project.
- Full-text search — `search` uses simple `icontains` matching; a real search
  engine is out of scope for v0.1.
- Product reviews/ratings, promotions/discounts, multi-currency — not in the
  master spec.
- Stock-change audit history — `stock_qty` is edited directly; no ledger of
  past adjustments.

## 1. Architecture & config

- New `catalogue` app: models, validators (slug generation), serializers,
  views, urls, admin — same layering as `accounts`.
- No new permission class needed: DRF's built-in
  `rest_framework.permissions.IsAdminUser` (checks
  `request.user and request.user.is_staff`) is sufficient, since
  `accounts.User` already carries `is_staff`. Public endpoints use `AllowAny`.
- `INSTALLED_APPS` gains `"catalogue"`.
- `REST_FRAMEWORK` settings gain pagination (not previously needed by
  `accounts`): `DEFAULT_PAGINATION_CLASS = rest_framework.pagination.PageNumberPagination`,
  `PAGE_SIZE = 20`.
- Media: local Django media storage (`MEDIA_ROOT`/`MEDIA_URL`, not yet
  configured in `settings.py` — added here), served via Django in dev. Image
  files validated/processed with the already-installed Pillow.

## 2. Data model

### Category (`catalogue.Category`)

| Field | Notes |
|---|---|
| `name` | required |
| `slug` | auto-generated from `name` on save if blank, unique |
| `parent` | FK → self, nullable, `related_name="children"` — unlimited nesting depth |
| `image` | optional |

### Product (`catalogue.Product`)

| Field | Notes |
|---|---|
| `title` | required |
| `slug` | auto-generated from `title` on save if blank, unique |
| `category` | FK → Category |
| `description` | text, optional |
| `brand` | required |
| `is_active` | bool, default `True` — inactive products excluded from public API |
| `created_at` | auto |

No `base_price` field: every product requires at least one `ProductVariant`,
and variant price is the only price in the system (see below). Slug
uniqueness: on collision, append `-2`, `-3`, etc. (same pattern for both
`Category.slug` and `Product.slug`, factored into a shared helper).

### ProductVariant (`catalogue.ProductVariant`)

| Field | Notes |
|---|---|
| `product` | FK → Product, `related_name="variants"` |
| `sku` | required, unique, staff-entered (not auto-generated) |
| `attributes` | `JSONField`, default `{}` — free-form key/value pairs, e.g. `{"storage": "128GB", "color": "Black"}` |
| `price` | required, `DecimalField` |
| `stock_qty` | required, non-negative integer, default `0` |

Every `Product` must have ≥1 `ProductVariant` — enforced at the serializer
level for staff-created products (creation requires at least one variant
payload; a product can never be saved into a zero-variant state through the
API). A single-option product (e.g. a phone case) still gets exactly one
variant, holding its price/stock/SKU — this keeps every downstream feature
(cart, orders, stock checks, in the next sub-projects) dealing with a variant
uniformly, with no separate "simple product" code path.

Out-of-stock variants (`stock_qty == 0`) remain visible in the public API,
never hidden — the product/detail serializers expose a computed `in_stock`
flag per variant instead of filtering them out.

### ProductImage (`catalogue.ProductImage`)

| Field | Notes |
|---|---|
| `product` | FK → Product, `related_name="images"` |
| `image` | required, `ImageField` |
| `is_primary` | bool, default `False` |
| `sort_order` | integer, default `0` — display ordering among a product's images |

Save logic mirrors `Address.is_default`: setting `is_primary=True` on one
image unsets it on the product's other images (same
`select_for_update`-guarded pattern already used in `accounts/models.py`,
to avoid the same race condition class). A product's first image is
auto-set as primary.

Both models plus `ProductVariant`/`ProductImage` (as inlines) registered in
Django Admin for quick staff spot-checks, in addition to the staff API.

## 3. Public browse API

Base path: `/api/`. All endpoints `AllowAny`, read-only (`ListAPIView`/
`RetrieveAPIView`), excluding `is_active=False` products.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/categories/` | flat list of all categories (each row includes `parent` id) |
| GET | `/api/products/` | paginated list; filters: `?category=<slug>`, `?search=<title/brand icontains>`, `?ordering=price,-price,created_at,-created_at`; `page=` |
| GET | `/api/products/{slug}/` | full detail: nested variants (`attributes`, `price`, `stock_qty`, `in_stock`) and images |

List serializer is lightweight (`id`, `slug`, `title`, `brand`, `category`,
primary image, computed `price_from` = min variant price, computed
`in_stock` = any variant with `stock_qty > 0`). Detail serializer includes
the full variant and image lists.

Filtering/search implemented via `django-filter` (`DjangoFilterBackend`,
already the default filter backend project-wide) plus DRF's
`OrderingFilter` for `?ordering=`.

## 4. Staff management API

Base path: `/api/staff/catalogue/`. All endpoints `IsAdminUser`. Flat
`ModelViewSet`s (no nested routers), children scoped by query param —
matching the `Address` ownership-filter pattern from the accounts app.

| Endpoint | Purpose |
|---|---|
| `/api/staff/catalogue/categories/` | CRUD |
| `/api/staff/catalogue/products/` | CRUD (create requires ≥1 nested variant in the payload) |
| `/api/staff/catalogue/variants/?product=<id>` | CRUD, list scoped to `?product=` |
| `/api/staff/catalogue/images/?product=<id>` | CRUD (multipart upload), list scoped to `?product=` |
| POST | `/api/staff/catalogue/images/{id}/set-primary/` | mark as primary (mirrors `Address`'s `set-default` action) |

Stock is adjusted via a normal `PATCH` to a variant — no separate
increment/decrement endpoint.

## 5. Testing

TDD throughout, matching the `accounts` app's testing style.

- **Model tests:** slug auto-generation and uniqueness-on-collision for
  `Category` and `Product`; unlimited-depth category nesting (a
  grandchild category resolves its ancestry correctly); `ProductImage`
  primary-switching logic (first image auto-primary; setting a new primary
  unsets the old one) — same shape as the existing `Address` default tests;
  `ProductVariant.attributes` JSON round-trips correctly.
- **Public API tests:** list/detail return only `is_active=True` products;
  `category` filter; `search` matches title/brand substrings
  case-insensitively; `ordering` by price and `created_at` (both
  directions); pagination page size and `page=` param; out-of-stock
  variants still appear with `in_stock: false`; computed `price_from` picks
  the minimum variant price.
- **Staff API tests:** anonymous and non-staff-authenticated requests get
  401/403 on every staff endpoint; staff (`is_staff=True`) can create a
  category, create a product with a nested variant, add an image, and
  set-primary; creating a product with zero variants returns 400.
- Django Admin smoke test: staff can reach the `Product`/`Category` admin
  changelist (mirrors the existing `UserAdminAccessTests` pattern).

## Open items for implementation time

- Exact `MEDIA_ROOT`/`MEDIA_URL` values and whether `backend/urls.py` needs
  `static()` serving wired up for local dev (standard Django dev-media
  pattern, not decided here).
- Shared slug-generation helper's exact location (e.g. `core/utils.py` vs.
  a `catalogue`-local helper) — implementation-time call, not
  architecturally significant either way.
