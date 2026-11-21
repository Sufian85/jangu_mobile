# Jangu Storefront — Phase 1a (Foundation & Browsing) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a branded, server-rendered, publicly browsable Jangu Mobile storefront (home, category, search, product detail) on the existing deployment, plus a rebranded/recoloured Django admin — no cart or checkout yet.

**Architecture:** One new Django app `storefront` under `backend/` (templates + selectors + light vanilla JS), reusing `catalogue` models directly. `/` becomes the storefront home; the temporary `core` API-info page is removed. Django admin is re-skinned via a project-level `templates/admin/base_site.html`. A `seed_demo` management command populates a demo catalogue on every deploy (SQLite is ephemeral) using Pillow-generated placeholder images.

**Tech Stack:** Django 5.2 templates, `django.contrib.staticfiles` + WhiteNoise, Pillow (already a dep), vanilla JS. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-06-storefront-milestone-1-design.md` (this plan covers phase **1a** from spec §12 only; phases 1b and 1c get their own plans after 1a merges).

**Deviations from spec (intentional, decided while planning):**
- **Fonts:** load Poppins via a Google Fonts `<link>` with a full system-font fallback stack, instead of self-hosted woff2. Keeps the plan executable with no manual binary download; a later swap to self-hosted is trivial. This is a normal Django page (no artifact CSP).
- **Seed images:** `seed_demo` *generates* placeholder JPEGs with Pillow (navy/orange, product name) straight into `MEDIA_ROOT`, instead of copying committed files from a `seed_assets/` dir. No binary assets in the repo; fully reproducible; real photos can be uploaded via admin later.
- **Storefront palette:** committed light theme only (the brand design is light). No `prefers-color-scheme` dark handling for storefront pages. The admin override keeps Django's own dark-mode block intact.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/storefront/apps.py` | `StorefrontConfig` |
| `backend/storefront/urls.py` | storefront routes (`app_name = "storefront"`) — phase 1a: home, category, search, product |
| `backend/storefront/selectors.py` | read-only catalogue query helpers (annotations, filters, sort, search, related) |
| `backend/storefront/context_processors.py` | `cart_summary` — cart item count from `request.session` (raw in 1a; upgraded in 1b) |
| `backend/storefront/views/__init__.py` | package marker |
| `backend/storefront/views/catalog.py` | `home`, `category`, `search`, `product_detail` |
| `backend/storefront/templatetags/storefront_extras.py` | `ugx` filter, `variant_label` filter |
| `backend/storefront/management/commands/seed_demo.py` | idempotent demo catalogue + generated images |
| `backend/storefront/static/storefront/css/app.css` | full storefront stylesheet (design tokens + components) |
| `backend/storefront/static/storefront/js/app.js` | mobile-nav toggle, product image swap, variant `<select>` price update |
| `backend/storefront/static/storefront/img/logo.svg` | Jangu wordmark + cart/phone mark (SVG) |
| `backend/storefront/static/storefront/img/placeholder.svg` | product-image fallback |
| `backend/storefront/templates/storefront/base.html` | shell: `<head>`, header, messages, content block, trust badges, footer, bottom nav |
| `backend/storefront/templates/storefront/partials/*.html` | `header`, `footer`, `bottom_nav`, `trust_badges`, `product_card`, `pagination` |
| `backend/storefront/templates/storefront/{home,category,search,product_detail}.html` | pages |
| `backend/storefront/tests/factories.py` | `make_category`, `make_product` test helpers |
| `backend/storefront/tests/test_selectors.py` | selector unit tests |
| `backend/storefront/tests/test_extras.py` | template-tag tests |
| `backend/storefront/tests/test_home.py` | home page |
| `backend/storefront/tests/test_catalog.py` | category, search, product detail |
| `backend/storefront/tests/test_seed.py` | `seed_demo` idempotency + output |
| `backend/templates/admin/base_site.html` | project-level admin recolour + branding |
| `backend/core/admin.py` | `admin.site.site_header/site_title/index_title` = "Jangu Mobile" |
| `backend/core/tests/test_admin_branding.py` | admin branding assertions |
| `backend/backend/settings.py` | INSTALLED_APPS, TEMPLATES DIRS + context processor, LOGIN_* |
| `backend/backend/urls.py` | drop `core.index`; `include("storefront.urls")` last |
| Deletions | `backend/core/views.py`, `backend/core/templates/core/index.html`, `backend/core/tests/test_index.py` |

Every command below assumes the virtualenv is active:
`cd /Users/mac/projects/jango_mobileapp && source .venv/bin/activate`. Test commands run from `backend/`.

---

## Task 1: Branch, `storefront` skeleton, config, `core` cleanup

**Files:**
- Create: `backend/storefront/__init__.py`, `backend/storefront/apps.py`, `backend/storefront/urls.py`, `backend/storefront/views/__init__.py`, `backend/storefront/templatetags/__init__.py`, `backend/storefront/management/__init__.py`, `backend/storefront/management/commands/__init__.py`, `backend/storefront/tests/__init__.py`, `backend/storefront/context_processors.py`
- Modify: `backend/backend/settings.py`, `backend/backend/urls.py`
- Delete: `backend/core/views.py`, `backend/core/templates/core/index.html`, `backend/core/tests/test_index.py`

- [ ] **Step 1: Branch**

```bash
cd /Users/mac/projects/jango_mobileapp
git switch -c storefront/milestone-1
```
Expected: `Switched to a new branch 'storefront/milestone-1'`

- [ ] **Step 2: Create the app package files**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
mkdir -p storefront/views storefront/templatetags storefront/management/commands storefront/tests \
         storefront/static/storefront/css storefront/static/storefront/js storefront/static/storefront/img \
         storefront/templates/storefront/partials
touch storefront/__init__.py storefront/views/__init__.py storefront/templatetags/__init__.py \
      storefront/management/__init__.py storefront/management/commands/__init__.py storefront/tests/__init__.py
```

- [ ] **Step 3: `storefront/apps.py`**

```python
from django.apps import AppConfig


class StorefrontConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "storefront"
```

- [ ] **Step 4: `storefront/urls.py` (empty for now — home is added in Task 6)**

```python
from django.urls import path

app_name = "storefront"

urlpatterns: list[path] = []
```

- [ ] **Step 5: `storefront/context_processors.py`**

```python
def cart_summary(request):
    """Cart badge data for every template.

    Phase 1a reads the raw session map ({variant_id: qty}); phase 1b swaps
    this for orders.SessionCart once that exists.
    """
    cart = request.session.get("cart", {})
    try:
        count = sum(int(qty) for qty in cart.values())
    except (AttributeError, ValueError, TypeError):
        count = 0
    return {"cart_count": count}
```

- [ ] **Step 6: Wire settings** — edit `backend/backend/settings.py`

Add `"storefront"` to `INSTALLED_APPS` immediately after `"catalogue"`:
```python
    "core",
    "accounts",
    "catalogue",
    "storefront",
]
```

Replace the `TEMPLATES` `DIRS` line:
```python
        "DIRS": [],
```
with:
```python
        "DIRS": [BASE_DIR / "templates"],
```

Add the context processor to the same `TEMPLATES` block's list:
```python
                "django.contrib.messages.context_processors.messages",
                "storefront.context_processors.cart_summary",
            ],
```

Add auth redirect settings at the end of the file:
```python

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
```

- [ ] **Step 7: Remove `core.index`, mount storefront** — edit `backend/backend/urls.py`

Delete the import `from core.views import index` and the route `path("", index, name="index"),`.
Add, as the **last** entry of `urlpatterns` (after the `api/docs/` path, before the `if settings.DEBUG` block):
```python
    path("", include("storefront.urls")),
```
`include` is already imported.

- [ ] **Step 8: Delete the retired core landing page**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
rm core/views.py core/templates/core/index.html core/tests/test_index.py
rmdir core/templates/core core/templates 2>/dev/null || true
```

- [ ] **Step 9: Verify**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py check
python manage.py test 2>&1 | tail -6
```
Expected: `check` clean; test suite `OK` with **124 tests** (128 − 4 removed `test_index` tests). `/` now resolves to nothing (storefront urls empty) — that is expected mid-phase and fixed in Task 6.

- [ ] **Step 10: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add -A
git commit -m "feat(storefront): scaffold app, wire config, remove core landing page"
```

---

## Task 2: Django admin rebrand + recolour

**Files:**
- Create: `backend/core/admin.py`, `backend/templates/admin/base_site.html`, `backend/core/tests/test_admin_branding.py`

- [ ] **Step 1: Write the failing test** — `backend/core/tests/test_admin_branding.py`

```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminBrandingTests(TestCase):
    def test_login_page_shows_jangu_branding(self):
        response = self.client.get(reverse("admin:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jangu Mobile")

    def test_uses_project_base_site_override(self):
        response = self.client.get(reverse("admin:login"))
        self.assertTemplateUsed(response, "admin/base_site.html")
        # our override injects a brand CSS variable
        self.assertContains(response, "--header-bg: #12356E")

    def test_index_title_configured(self):
        User = get_user_model()
        User.objects.create_superuser(
            phone="+256772000000", password="adminpass123",
            first_name="Ada", last_name="Admin",
        )
        self.client.force_login(User.objects.get(phone="+256772000000"))
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, "Jangu Mobile")
```

- [ ] **Step 2: Run — verify it fails**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test core.tests.test_admin_branding -v 2
```
Expected: FAIL — `--header-bg: #12356E` not found (default admin), branding still "Django administration".

- [ ] **Step 3: `backend/core/admin.py`**

```python
from django.contrib import admin

admin.site.site_header = "Jangu Mobile"
admin.site.site_title = "Jangu Mobile admin"
admin.site.index_title = "Administration"
```

- [ ] **Step 4: `backend/templates/admin/base_site.html`**

```html
{% extends "admin/base.html" %}

{% block title %}{{ subtitle }}{% if subtitle %} | {% endif %}{{ title }} | Jangu Mobile{% endblock %}

{% block branding %}
<div id="site-name">
  <a href="{% url 'admin:index' %}" style="color:#EF7C1B;font-weight:700;letter-spacing:.5px;">
    Jangu&nbsp;Mobile
  </a>
</div>
{% endblock %}

{% block extrastyle %}{{ block.super }}
<style>
  :root {
    --primary: #12356E; --secondary: #12356E; --accent: #EF7C1B;
    --header-bg: #12356E; --header-color: #ffffff; --header-branding-color: #EF7C1B;
    --header-link-color: #ffffff;
    --link-fg: #12356E; --link-hover-color: #EF7C1B; --link-selected-fg: #0d2a58;
    --button-bg: #EF7C1B; --button-hover-bg: #d96f14; --button-fg: #ffffff;
    --default-button-bg: #12356E; --default-button-hover-bg: #0d2a58;
    --object-tools-bg: #12356E; --object-tools-hover-bg: #EF7C1B;
    --breadcrumbs-bg: #0d2a58; --breadcrumbs-link-fg: #ffffff; --breadcrumbs-fg: #cdd7e6;
  }
</style>
{% endblock %}
```

- [ ] **Step 5: Run — verify it passes**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test core.tests.test_admin_branding -v 2
```
Expected: `Ran 3 tests` … `OK`.

- [ ] **Step 6: Regression + visual check**

```bash
python manage.py test core 2>&1 | tail -4
python manage.py collectstatic --no-input >/dev/null && echo collectstatic-ok
```
Expected: `OK`; `collectstatic-ok`.

- [ ] **Step 7: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/core/admin.py backend/templates/admin/base_site.html backend/core/tests/test_admin_branding.py
git commit -m "feat(admin): rebrand to Jangu Mobile with navy/orange theme"
```

---

## Task 3: Brand static assets (CSS, JS, SVG)

**Files:**
- Create: `backend/storefront/static/storefront/css/app.css`, `backend/storefront/static/storefront/js/app.js`, `backend/storefront/static/storefront/img/logo.svg`, `backend/storefront/static/storefront/img/placeholder.svg`

- [ ] **Step 1: `img/logo.svg`**

```html
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 44" role="img" aria-label="Jangu Mobile">
  <rect x="2" y="6" width="26" height="32" rx="5" fill="none" stroke="#12356E" stroke-width="3"/>
  <path d="M9 30h13l3-11H10" fill="none" stroke="#EF7C1B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="12" cy="34" r="2" fill="#EF7C1B"/><circle cx="21" cy="34" r="2" fill="#EF7C1B"/>
  <text x="36" y="30" font-family="Poppins, Arial, sans-serif" font-size="24" font-weight="700">
    <tspan fill="#12356E">Jan</tspan><tspan fill="#EF7C1B">gu</tspan>
  </text>
  <text x="37" y="40" font-family="Poppins, Arial, sans-serif" font-size="7" letter-spacing="2" fill="#12356E">MOBILE &amp; E-COMMERCE</text>
</svg>
```

- [ ] **Step 2: `img/placeholder.svg`**

```html
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
  <rect width="400" height="400" fill="#EEF3FA"/>
  <rect x="120" y="120" width="160" height="160" rx="14" fill="none" stroke="#12356E" stroke-width="6"/>
  <path d="M150 250l35-45 30 35 25-30 30 40" fill="none" stroke="#EF7C1B" stroke-width="6" stroke-linecap="round"/>
  <text x="200" y="330" text-anchor="middle" font-family="Poppins, Arial, sans-serif" font-size="20" fill="#12356E">Jangu Mobile</text>
</svg>
```

- [ ] **Step 3: `css/app.css`** (complete)

```css
:root{
  --navy:#12356E; --navy-dark:#0d2a58; --orange:#EF7C1B; --orange-dark:#d96f14;
  --bg:#EEF3FA; --card:#ffffff; --ink:#15223B; --muted:#5b6a82; --line:#e2e8f2;
  --radius:12px; --shadow:0 6px 20px rgba(18,53,110,.08);
  --font:"Poppins",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg);color:var(--ink);font-family:var(--font);line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:var(--navy);text-decoration:none}
img{max-width:100%;display:block}
.container{max-width:1160px;margin:0 auto;padding:0 16px}
h1,h2,h3{font-weight:700;line-height:1.2;margin:0 0 .5em}
.section{padding:32px 0}
.section-head{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:16px}
.section-head a{font-size:.9rem;color:var(--orange);font-weight:600}

/* buttons */
.btn{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:999px;
  padding:11px 22px;font:inherit;font-weight:600;cursor:pointer;text-align:center}
.btn-primary{background:var(--orange);color:#fff}
.btn-primary:hover{background:var(--orange-dark)}
.btn-navy{background:var(--navy);color:#fff}
.btn-navy:hover{background:var(--navy-dark)}
.btn-block{display:flex;width:100%;justify-content:center}
.btn:disabled{opacity:.5;cursor:not-allowed}

/* header */
.site-header{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line)}
.site-header .row{display:flex;align-items:center;gap:16px;padding:12px 0}
.site-header .logo img{height:38px;width:auto}
.site-header form.search{flex:1;display:flex;max-width:560px}
.site-header .search input{flex:1;border:1px solid var(--line);border-right:0;border-radius:999px 0 0 999px;padding:10px 16px;font:inherit}
.site-header .search button{border:0;background:var(--navy);color:#fff;border-radius:0 999px 999px 0;padding:0 18px;cursor:pointer}
.header-actions{display:flex;align-items:center;gap:18px;margin-left:auto}
.header-actions a{display:flex;align-items:center;gap:6px;font-weight:600;font-size:.9rem}
.cart-link{position:relative}
.cart-badge{position:absolute;top:-8px;right:-10px;background:var(--orange);color:#fff;
  font-size:.7rem;font-weight:700;min-width:18px;height:18px;border-radius:999px;
  display:flex;align-items:center;justify-content:center;padding:0 4px}

/* hero */
.hero{background:linear-gradient(120deg,var(--navy),#1f4e9e);color:#fff;border-radius:var(--radius);
  padding:44px 32px;margin:24px 0;display:grid;gap:10px}
.hero h1{font-size:2rem;margin:0}
.hero .tag{color:#ffd9b8;font-weight:600;letter-spacing:.5px}
.hero .btn{margin-top:12px;align-self:start}

/* trust badges */
.trust{background:var(--navy);color:#fff}
.trust .container{display:flex;flex-wrap:wrap;gap:24px;justify-content:space-around;padding:18px 16px;font-size:.85rem;font-weight:600}
.trust span{display:flex;align-items:center;gap:8px}

/* category grid */
.cat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
.cat-card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:18px;text-align:center;box-shadow:var(--shadow)}
.cat-card:hover{border-color:var(--orange)}
.cat-card svg{width:40px;height:40px;margin-bottom:8px}
.cat-card b{display:block;color:var(--ink);font-size:.95rem}

/* product card + grid */
.product-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px}
.product-card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  overflow:hidden;box-shadow:var(--shadow);display:flex;flex-direction:column}
.product-card:hover{border-color:var(--orange)}
.product-card .thumb{aspect-ratio:1/1;background:var(--bg)}
.product-card .body{padding:12px;display:flex;flex-direction:column;gap:4px;flex:1}
.product-card .brand{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.product-card .title{font-weight:600;color:var(--ink);font-size:.95rem}
.product-card .price{margin-top:auto;font-weight:700;color:var(--navy)}
.product-card .oos{font-size:.75rem;color:#b23b3b;font-weight:600}

/* filter bar */
.filter-bar{display:flex;flex-wrap:wrap;gap:10px;align-items:end;background:var(--card);
  border:1px solid var(--line);border-radius:var(--radius);padding:14px;margin-bottom:18px}
.filter-bar label{display:flex;flex-direction:column;font-size:.75rem;font-weight:600;color:var(--muted);gap:4px}
.filter-bar input,.filter-bar select{border:1px solid var(--line);border-radius:8px;padding:8px 10px;font:inherit}

/* pagination */
.pagination{display:flex;gap:6px;justify-content:center;margin-top:24px}
.pagination a,.pagination span{padding:8px 13px;border:1px solid var(--line);border-radius:8px;background:#fff;font-weight:600}
.pagination .current{background:var(--navy);color:#fff;border-color:var(--navy)}

/* product detail */
.pd{display:grid;grid-template-columns:1fr 1fr;gap:32px;margin:24px 0}
.pd .gallery .main{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);aspect-ratio:1/1}
.pd .gallery .thumbs{display:flex;gap:8px;margin-top:8px}
.pd .gallery .thumbs img{width:64px;height:64px;border:1px solid var(--line);border-radius:8px;cursor:pointer;object-fit:cover}
.pd .buy{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:20px}
.pd .price{font-size:1.6rem;font-weight:700;color:var(--navy);margin:8px 0}
.pd select,.pd .qty input{border:1px solid var(--line);border-radius:8px;padding:9px 12px;font:inherit}
.pd .qty{display:flex;align-items:center;gap:8px;margin:12px 0}
.pd .qty button{width:34px;height:34px;border:1px solid var(--line);background:#fff;border-radius:8px;font-size:1.1rem;cursor:pointer}

/* messages */
.messages{list-style:none;padding:0;margin:16px 0}
.messages li{padding:12px 16px;border-radius:8px;margin-bottom:8px;font-weight:600}
.messages li.success{background:#e6f4ec;color:#186a3b}
.messages li.error{background:#fbe9e9;color:#a12d2d}
.messages li.info,.messages li.warning{background:#fef4e6;color:#8a5a12}

/* footer + bottom nav */
.site-footer{background:var(--navy);color:#cdd7e6;margin-top:40px}
.site-footer .container{display:flex;flex-wrap:wrap;gap:32px;justify-content:space-between;padding:32px 16px}
.site-footer a{color:#cdd7e6}
.site-footer .pay{display:flex;gap:8px;margin-top:8px;font-weight:700;color:#fff}
.bottom-nav{display:none}

@media (max-width:820px){
  .pd{grid-template-columns:1fr}
  .site-header .search{order:3;flex-basis:100%;max-width:none}
  .hero h1{font-size:1.5rem}
  .bottom-nav{display:flex;position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid var(--line);
    justify-content:space-around;padding:8px 0;z-index:30}
  .bottom-nav a{display:flex;flex-direction:column;align-items:center;font-size:.7rem;color:var(--muted);gap:2px}
  .bottom-nav a.active{color:var(--orange)}
  body{padding-bottom:64px}
}
```

- [ ] **Step 4: `js/app.js`** (complete)

```javascript
(function () {
  // mobile nav is CSS-only; nothing needed here yet for it.

  // product detail: thumbnail swap
  document.querySelectorAll(".pd .gallery .thumbs img").forEach(function (t) {
    t.addEventListener("click", function () {
      var main = document.querySelector(".pd .gallery .main img");
      if (main) main.src = t.dataset.full || t.src;
    });
  });

  // product detail: variant <select> updates price + stock button state
  var sel = document.querySelector("[data-variant-select]");
  if (sel) {
    var priceEl = document.querySelector("[data-variant-price]");
    var addBtn = document.querySelector("[data-add-btn]");
    var sync = function () {
      var opt = sel.options[sel.selectedIndex];
      if (priceEl && opt.dataset.price) priceEl.textContent = opt.dataset.price;
      if (addBtn) addBtn.disabled = opt.dataset.inStock !== "1";
    };
    sel.addEventListener("change", sync);
    sync();
  }

  // qty steppers
  document.querySelectorAll("[data-qty]").forEach(function (wrap) {
    var input = wrap.querySelector("input");
    wrap.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        var step = b.dataset.step === "down" ? -1 : 1;
        var v = Math.max(1, (parseInt(input.value, 10) || 1) + step);
        input.value = v;
      });
    });
  });
})();
```

- [ ] **Step 5: Verify collectstatic picks them up**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py collectstatic --no-input 2>&1 | tail -2
```
Expected: reports files copied, no error.

- [ ] **Step 6: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront/static
git commit -m "feat(storefront): brand design system (app.css, logo, js)"
```

---

## Task 4: Template tags — `ugx`, `variant_label`

**Files:**
- Create: `backend/storefront/templatetags/storefront_extras.py`, `backend/storefront/tests/test_extras.py`

- [ ] **Step 1: Write the failing test** — `backend/storefront/tests/test_extras.py`

```python
from decimal import Decimal

from django.test import SimpleTestCase

from storefront.templatetags.storefront_extras import ugx, variant_label


class UgxFilterTests(SimpleTestCase):
    def test_formats_integer_with_thousands_and_prefix(self):
        self.assertEqual(ugx(2800000), "UGX 2,800,000")

    def test_formats_decimal_without_cents(self):
        self.assertEqual(ugx(Decimal("1950000.00")), "UGX 1,950,000")

    def test_handles_none(self):
        self.assertEqual(ugx(None), "—")


class VariantLabelTests(SimpleTestCase):
    def test_joins_attribute_values(self):
        self.assertEqual(variant_label({"storage": "128GB", "color": "Black"}), "128GB / Black")

    def test_empty_attributes_returns_standard(self):
        self.assertEqual(variant_label({}), "Standard")

    def test_non_dict_returns_standard(self):
        self.assertEqual(variant_label(None), "Standard")
```

- [ ] **Step 2: Run — verify it fails**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_extras -v 2
```
Expected: `ModuleNotFoundError` / import error for `storefront_extras`.

- [ ] **Step 3: Implement** — `backend/storefront/templatetags/storefront_extras.py`

```python
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def ugx(value):
    """Format a number as `UGX 2,800,000` (no decimals)."""
    if value is None or value == "":
        return "—"
    try:
        amount = int(round(Decimal(str(value))))
    except (InvalidOperation, ValueError, TypeError):
        return "—"
    return f"UGX {amount:,}"


@register.filter
def variant_label(attributes):
    """`{"storage": "128GB", "color": "Black"}` -> `128GB / Black`; `{}` -> `Standard`."""
    if not isinstance(attributes, dict) or not attributes:
        return "Standard"
    return " / ".join(str(v) for v in attributes.values())
```

- [ ] **Step 4: Run — verify it passes**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_extras -v 2
```
Expected: `Ran 6 tests` … `OK`.

- [ ] **Step 5: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront/templatetags/storefront_extras.py backend/storefront/tests/test_extras.py
git commit -m "feat(storefront): ugx and variant_label template filters"
```

---

## Task 5: Test factories + `selectors.py`

**Files:**
- Create: `backend/storefront/tests/factories.py`, `backend/storefront/selectors.py`, `backend/storefront/tests/test_selectors.py`

- [ ] **Step 1: `backend/storefront/tests/factories.py`**

```python
from decimal import Decimal

from catalogue.models import Category, Product, ProductImage, ProductVariant
from catalogue.tests.helpers import make_test_image


def make_category(name="Smartphones"):
    return Category.objects.create(name=name)


def make_product(
    *, title="Galaxy S23", category=None, brand="Samsung", price="2800000",
    stock_qty=10, is_active=True, with_image=True, variants=None,
):
    category = category or make_category()
    product = Product.objects.create(
        title=title, category=category, brand=brand, is_active=is_active,
        description=f"{brand} {title} demo unit.",
    )
    specs = variants or [{"sku": f"{title}-A", "price": price, "stock_qty": stock_qty,
                          "attributes": {"storage": "128GB", "color": "Black"}}]
    for spec in specs:
        ProductVariant.objects.create(
            product=product, sku=spec["sku"], price=Decimal(str(spec["price"])),
            stock_qty=spec["stock_qty"], attributes=spec.get("attributes", {}),
        )
    if with_image:
        ProductImage.objects.create(product=product, image=make_test_image(f"{title}.png"))
    return product
```

- [ ] **Step 2: Write the failing test** — `backend/storefront/tests/test_selectors.py`

```python
import tempfile
from decimal import Decimal

from django.test import TestCase, override_settings

from storefront import selectors
from storefront.tests.factories import make_category, make_product


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SelectorTests(TestCase):
    def setUp(self):
        self.phones = make_category("Smartphones")
        self.laptops = make_category("Laptops & Accessories")
        self.s23 = make_product(title="Galaxy S23", category=self.phones, brand="Samsung",
                                price="2800000", stock_qty=5)
        self.note = make_product(title="Note 50 Pro", category=self.phones, brand="Infinix",
                                 price="1950000", stock_qty=0)
        self.mbp = make_product(title="MacBook Air", category=self.laptops, brand="Apple",
                                price="6900000", stock_qty=3)
        make_product(title="Hidden", category=self.phones, brand="Nokia", price="100000",
                     is_active=False)

    def test_active_products_excludes_inactive(self):
        titles = set(selectors.active_products().values_list("title", flat=True))
        self.assertEqual(titles, {"Galaxy S23", "Note 50 Pro", "MacBook Air"})

    def test_annotations_min_price_and_in_stock(self):
        p = selectors.active_products().get(title="Galaxy S23")
        self.assertEqual(p.min_price, Decimal("2800000"))
        self.assertTrue(p.in_stock)
        n = selectors.active_products().get(title="Note 50 Pro")
        self.assertFalse(n.in_stock)

    def test_category_products_filter_and_sort(self):
        qs = selectors.category_products(self.phones, sort="price_asc")
        self.assertEqual([p.title for p in qs], ["Note 50 Pro", "Galaxy S23"])
        qs = selectors.category_products(self.phones, brand="samsung")
        self.assertEqual([p.title for p in qs], ["Galaxy S23"])
        qs = selectors.category_products(self.phones, in_stock=True)
        self.assertEqual([p.title for p in qs], ["Galaxy S23"])
        qs = selectors.category_products(self.phones, price_max=2000000)
        self.assertEqual([p.title for p in qs], ["Note 50 Pro"])

    def test_search_matches_title_brand_description(self):
        self.assertEqual([p.title for p in selectors.search_products("galaxy")], ["Galaxy S23"])
        self.assertEqual([p.title for p in selectors.search_products("apple")], ["MacBook Air"])
        self.assertEqual(list(selectors.search_products("nokia")), [])  # inactive excluded

    def test_related_products_same_category_excludes_self(self):
        rel = selectors.related_products(self.s23)
        self.assertIn(self.note, rel)
        self.assertNotIn(self.s23, rel)
        self.assertNotIn(self.mbp, rel)

    def test_featured_products_have_image_and_stock(self):
        featured = list(selectors.featured_products())
        self.assertIn(self.s23, featured)
        self.assertNotIn(self.note, featured)  # out of stock
```

- [ ] **Step 3: Run — verify it fails**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_selectors -v 2
```
Expected: import error (`storefront.selectors` missing).

- [ ] **Step 4: Implement** — `backend/storefront/selectors.py`

```python
from django.db.models import Exists, Min, OuterRef, Q

from catalogue.models import Product, ProductVariant

_SORTS = {
    "price_asc": "min_price",
    "price_desc": "-min_price",
    "newest": "-created_at",
}


def active_products():
    """Base queryset: active products annotated with `min_price` and `in_stock`.

    `in_stock` is an `Exists` annotation (not a `variants__` aggregate) so it is
    readable off a `.get(...)` and does not perturb the `min_price` aggregate.
    """
    has_stock = ProductVariant.objects.filter(product=OuterRef("pk"), stock_qty__gt=0)
    return (
        Product.objects.filter(is_active=True)
        .annotate(min_price=Min("variants__price"), in_stock=Exists(has_stock))
        .prefetch_related("variants", "images")
    )


def _apply_filters(qs, *, brand=None, price_min=None, price_max=None, in_stock=None, sort=None):
    if brand:
        qs = qs.filter(brand__iexact=brand)
    if price_min not in (None, ""):
        qs = qs.filter(min_price__gte=price_min)
    if price_max not in (None, ""):
        qs = qs.filter(min_price__lte=price_max)
    if in_stock:
        qs = qs.filter(in_stock=True)
    return qs.order_by(_SORTS.get(sort, _SORTS["newest"]))


def category_products(category, **filters):
    return _apply_filters(active_products().filter(category=category), **filters)


def search_products(query, **filters):
    query = (query or "").strip()
    qs = active_products()
    if query:
        qs = qs.filter(
            Q(title__icontains=query) | Q(brand__icontains=query) | Q(description__icontains=query)
        )
    return _apply_filters(qs, **filters)


def related_products(product, limit=4):
    return list(
        active_products().filter(category=product.category).exclude(pk=product.pk)[:limit]
    )


def featured_products(limit=8):
    return list(
        active_products().filter(in_stock=True, images__isnull=False)
        .distinct().order_by("-created_at")[:limit]
    )
```

`qs.filter(in_stock=True)` works because `in_stock` is an `Exists` annotation —
Django allows filtering on boolean `Exists` annotations directly.

- [ ] **Step 5: Run — verify it passes**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_selectors -v 2
```
Expected: `Ran 6 tests` … `OK`.

- [ ] **Step 6: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront/selectors.py backend/storefront/tests/factories.py backend/storefront/tests/test_selectors.py
git commit -m "feat(storefront): catalogue selectors (filter, sort, search, related, featured)"
```

---

## Task 6: Base template + partials + home page

**Files:**
- Create: `backend/storefront/templates/storefront/base.html`, `.../partials/{header,footer,bottom_nav,trust_badges,product_card,pagination}.html`, `.../home.html`, `backend/storefront/views/catalog.py`, `backend/storefront/tests/test_home.py`
- Modify: `backend/storefront/urls.py`

- [ ] **Step 1: `partials/header.html`**

```html
{% load static %}
<header class="site-header">
  <div class="container row">
    <a class="logo" href="{% url 'storefront:home' %}"><img src="{% static 'storefront/img/logo.svg' %}" alt="Jangu Mobile"></a>
    <form class="search" action="{% url 'storefront:search' %}" method="get" role="search">
      <input type="search" name="q" value="{{ request.GET.q|default:'' }}" placeholder="Search for products…" aria-label="Search for products">
      <button type="submit">Search</button>
    </form>
    <nav class="header-actions">
      <a href="{% url 'storefront:home' %}">Account</a>
      <a class="cart-link" href="{% url 'storefront:home' %}">Cart
        {% if cart_count %}<span class="cart-badge">{{ cart_count }}</span>{% endif %}
      </a>
    </nav>
  </div>
</header>
```
(The Account/Cart hrefs point at `home` in phase 1a; phase 1b/1c repoint them.)

- [ ] **Step 2: `partials/trust_badges.html`**

```html
<section class="trust">
  <div class="container">
    <span>✓ 100% Genuine Products</span>
    <span>🏷️ Best Prices Guaranteed</span>
    <span>🎧 24/7 Customer Support</span>
    <span>🔒 Secure Payments</span>
    <span>🚚 Fast &amp; Reliable Delivery</span>
  </div>
</section>
```

- [ ] **Step 3: `partials/footer.html`**

```html
<footer class="site-footer">
  <div class="container">
    <div>
      <strong style="color:#fff">Jangu Mobile</strong><br>
      Your Gadget. Our Priority.
      <div class="pay">MTN MoMo · Airtel Money · Card</div>
    </div>
    <div>
      <a href="{% url 'storefront:home' %}">Home</a><br>
      <a href="/api/docs/">API Docs</a><br>
      <a href="/admin/">Admin</a>
    </div>
    <div>&copy; {% now "Y" %} Jangu Mobile &middot; Kampala, Uganda</div>
  </div>
</footer>
```

- [ ] **Step 4: `partials/bottom_nav.html`**

```html
<nav class="bottom-nav">
  <a href="{% url 'storefront:home' %}" class="{% if active == 'home' %}active{% endif %}">🏠<span>Home</span></a>
  <a href="{% url 'storefront:home' %}">🗂️<span>Categories</span></a>
  <a href="{% url 'storefront:home' %}">🛒<span>Cart</span></a>
  <a href="{% url 'storefront:home' %}">👤<span>Account</span></a>
</nav>
```

- [ ] **Step 5: `partials/product_card.html`**

```html
{% load static storefront_extras %}
<a class="product-card" href="{% url 'storefront:product' product.slug %}">
  <div class="thumb">
    {% with img=product.images.all|first %}
      <img src="{% if img %}{{ img.image.url }}{% else %}{% static 'storefront/img/placeholder.svg' %}{% endif %}" alt="{{ product.title }}" loading="lazy">
    {% endwith %}
  </div>
  <div class="body">
    <span class="brand">{{ product.brand }}</span>
    <span class="title">{{ product.title }}</span>
    {% if not product.in_stock %}<span class="oos">Out of stock</span>{% endif %}
    <span class="price">from {{ product.min_price|ugx }}</span>
  </div>
</a>
```

- [ ] **Step 6: `partials/pagination.html`**

```html
{% if page_obj.paginator.num_pages > 1 %}
<nav class="pagination">
  {% if page_obj.has_previous %}<a href="?{{ querystring }}page={{ page_obj.previous_page_number }}">‹ Prev</a>{% endif %}
  {% for n in page_obj.paginator.page_range %}
    {% if n == page_obj.number %}<span class="current">{{ n }}</span>
    {% else %}<a href="?{{ querystring }}page={{ n }}">{{ n }}</a>{% endif %}
  {% endfor %}
  {% if page_obj.has_next %}<a href="?{{ querystring }}page={{ page_obj.next_page_number }}">Next ›</a>{% endif %}
</nav>
{% endif %}
```

- [ ] **Step 7: `base.html`**

```html
{% load static %}<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#12356E">
  <title>{% block title %}Jangu Mobile — Your Gadget. Our Priority.{% endblock %}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{% static 'storefront/css/app.css' %}">
</head>
<body>
  {% include "storefront/partials/header.html" %}
  <main class="container">
    {% if messages %}
      <ul class="messages">
        {% for m in messages %}<li class="{{ m.tags }}">{{ m }}</li>{% endfor %}
      </ul>
    {% endif %}
    {% block content %}{% endblock %}
  </main>
  {% include "storefront/partials/trust_badges.html" %}
  {% include "storefront/partials/footer.html" %}
  {% include "storefront/partials/bottom_nav.html" %}
  <script src="{% static 'storefront/js/app.js' %}" defer></script>
</body>
</html>
```

- [ ] **Step 8: `home.html`**

```html
{% extends "storefront/base.html" %}
{% load static storefront_extras %}

{% block content %}
<section class="hero">
  <span class="tag">Shop Smart · Live Better</span>
  <h1>Your Gadget. Our Priority.</h1>
  <p>Latest smartphones, laptops, audio, wearables and gaming gear — genuine, best-priced, delivered fast.</p>
  <a class="btn btn-primary" href="#featured">Start Shopping →</a>
</section>

<section class="section">
  <div class="section-head"><h2>Shop by Category</h2></div>
  <div class="cat-grid">
    {% for c in categories %}
      <a class="cat-card" href="{% url 'storefront:category' c.slug %}">
        <svg viewBox="0 0 24 24" fill="none" stroke="#12356E" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="3"/><line x1="10" y1="19" x2="14" y2="19"/></svg>
        <b>{{ c.name }}</b>
      </a>
    {% endfor %}
  </div>
</section>

<section class="section" id="featured">
  <div class="section-head">
    <h2>Featured Products</h2>
    {% if first_category %}<a href="{% url 'storefront:category' first_category.slug %}">View All</a>{% endif %}
  </div>
  {% if featured %}
    <div class="product-grid">
      {% for product in featured %}{% include "storefront/partials/product_card.html" %}{% endfor %}
    </div>
  {% else %}
    <p>No products yet. Run <code>python manage.py seed_demo</code>.</p>
  {% endif %}
</section>
{% endblock %}
```

- [ ] **Step 9: `views/catalog.py`** — real `home`, harmless stubs for the rest

The stubs return a plain 200 so nothing 500s mid-phase; Tasks 7 and 8 replace
them with real views. They are never exercised by this task's tests (which only
hit `home`), but the routes must be registered now because `product_card.html`
reverses `storefront:product`.

```python
from django.http import HttpResponse
from django.shortcuts import render

from catalogue.models import Category
from storefront import selectors


def home(request):
    categories = Category.objects.filter(parent__isnull=True).order_by("name")
    return render(request, "storefront/home.html", {
        "categories": categories,
        "first_category": categories.first(),
        "featured": selectors.featured_products(8),
        "active": "home",
    })


def category(request, slug):  # replaced in Task 7
    return HttpResponse("category (stub)")


def search(request):  # replaced in Task 7
    return HttpResponse("search (stub)")


def product_detail(request, slug):  # replaced in Task 8
    return HttpResponse("product (stub)")
```

- [ ] **Step 10: `storefront/urls.py`**

```python
from django.urls import path

from storefront.views import catalog

app_name = "storefront"

urlpatterns = [
    path("", catalog.home, name="home"),
    path("c/<slug:slug>/", catalog.category, name="category"),
    path("search/", catalog.search, name="search"),
    path("p/<slug:slug>/", catalog.product_detail, name="product"),
]
```

- [ ] **Step 11: Write the home test** — `backend/storefront/tests/test_home.py`

```python
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from storefront.tests.factories import make_category, make_product


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class HomePageTests(TestCase):
    def test_renders_hero_and_categories(self):
        make_category("Smartphones")
        make_category("Gaming Gear")
        response = self.client.get(reverse("storefront:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Gadget. Our Priority.")
        self.assertContains(response, "Shop Smart · Live Better")
        self.assertContains(response, "Smartphones")
        self.assertContains(response, "Gaming Gear")

    def test_featured_grid_shows_in_stock_products(self):
        phones = make_category("Smartphones")
        make_product(title="Galaxy S23", category=phones, brand="Samsung", price="2800000", stock_qty=4)
        make_product(title="Sold Out", category=phones, brand="X", price="10000", stock_qty=0)
        response = self.client.get(reverse("storefront:home"))
        self.assertContains(response, "Galaxy S23")
        self.assertContains(response, "UGX 2,800,000")
        self.assertNotContains(response, "Sold Out")

    def test_uses_storefront_base(self):
        response = self.client.get(reverse("storefront:home"))
        self.assertTemplateUsed(response, "storefront/base.html")
        self.assertTemplateUsed(response, "storefront/home.html")
```

- [ ] **Step 12: Run home tests**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_home -v 2
```
Expected: `Ran 3 tests` … `OK`.

- [ ] **Step 13: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront/templates backend/storefront/views backend/storefront/urls.py backend/storefront/tests/test_home.py
git commit -m "feat(storefront): base layout, partials, home page"
```

---

## Task 7: Category + search pages

**Files:**
- Create: `backend/storefront/templates/storefront/{category,search}.html`, `backend/storefront/templates/storefront/partials/filter_bar.html`, `backend/storefront/tests/test_catalog.py`
- Modify: `backend/storefront/views/catalog.py`

- [ ] **Step 1: `partials/filter_bar.html`**

```html
<form class="filter-bar" method="get">
  {% if request.GET.q %}<input type="hidden" name="q" value="{{ request.GET.q }}">{% endif %}
  <label>Brand
    <select name="brand">
      <option value="">All</option>
      {% for b in brands %}<option value="{{ b }}" {% if b|lower == request.GET.brand|lower %}selected{% endif %}>{{ b }}</option>{% endfor %}
    </select>
  </label>
  <label>Min price<input type="number" name="price_min" value="{{ request.GET.price_min }}" min="0"></label>
  <label>Max price<input type="number" name="price_max" value="{{ request.GET.price_max }}" min="0"></label>
  <label>In stock<input type="checkbox" name="in_stock" value="1" {% if request.GET.in_stock %}checked{% endif %}></label>
  <label>Sort
    <select name="sort">
      <option value="newest" {% if request.GET.sort == "newest" %}selected{% endif %}>Newest</option>
      <option value="price_asc" {% if request.GET.sort == "price_asc" %}selected{% endif %}>Price ↑</option>
      <option value="price_desc" {% if request.GET.sort == "price_desc" %}selected{% endif %}>Price ↓</option>
    </select>
  </label>
  <button class="btn btn-navy" type="submit">Apply</button>
</form>
```

- [ ] **Step 2: `category.html`**

```html
{% extends "storefront/base.html" %}
{% block title %}{{ category.name }} — Jangu Mobile{% endblock %}
{% block content %}
<section class="section">
  <div class="section-head"><h2>{{ category.name }}</h2><span>{{ page_obj.paginator.count }} product{{ page_obj.paginator.count|pluralize }}</span></div>
  {% include "storefront/partials/filter_bar.html" %}
  {% if page_obj.object_list %}
    <div class="product-grid">
      {% for product in page_obj.object_list %}{% include "storefront/partials/product_card.html" %}{% endfor %}
    </div>
    {% include "storefront/partials/pagination.html" %}
  {% else %}<p>No products match those filters.</p>{% endif %}
</section>
{% endblock %}
```

- [ ] **Step 3: `search.html`** (same as `category.html` but heading uses the query)

```html
{% extends "storefront/base.html" %}
{% block title %}Search: {{ query }} — Jangu Mobile{% endblock %}
{% block content %}
<section class="section">
  <div class="section-head"><h2>Results for “{{ query }}”</h2><span>{{ page_obj.paginator.count }} found</span></div>
  {% include "storefront/partials/filter_bar.html" %}
  {% if page_obj.object_list %}
    <div class="product-grid">
      {% for product in page_obj.object_list %}{% include "storefront/partials/product_card.html" %}{% endfor %}
    </div>
    {% include "storefront/partials/pagination.html" %}
  {% else %}<p>Nothing matched “{{ query }}”.</p>{% endif %}
</section>
{% endblock %}
```

- [ ] **Step 4: Rewrite `backend/storefront/views/catalog.py`** — complete file (real `home`, `category`, `search`; `product_detail` still a stub until Task 8)

```python
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from catalogue.models import Category
from storefront import selectors

PAGE_SIZE = 12


def _filters(request):
    return {
        "brand": request.GET.get("brand") or None,
        "price_min": request.GET.get("price_min") or None,
        "price_max": request.GET.get("price_max") or None,
        "in_stock": request.GET.get("in_stock") == "1",
        "sort": request.GET.get("sort") or "newest",
    }


def _paginate(request, queryset):
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    keep = {k: v for k, v in request.GET.items() if k != "page"}
    return page, (urlencode(keep) + "&" if keep else "")


def _brands(queryset):
    return sorted({b for b in queryset.values_list("brand", flat=True) if b})


def home(request):
    categories = Category.objects.filter(parent__isnull=True).order_by("name")
    return render(request, "storefront/home.html", {
        "categories": categories,
        "first_category": categories.first(),
        "featured": selectors.featured_products(8),
        "active": "home",
    })


def category(request, slug):
    cat = get_object_or_404(Category, slug=slug)
    base = selectors.category_products(cat, **_filters(request))
    page, querystring = _paginate(request, base)
    return render(request, "storefront/category.html", {
        "category": cat, "page_obj": page, "querystring": querystring,
        "brands": _brands(selectors.category_products(cat)),
    })


def search(request):
    query = (request.GET.get("q") or "").strip()
    base = selectors.search_products(query, **_filters(request))
    page, querystring = _paginate(request, base)
    return render(request, "storefront/search.html", {
        "query": query, "page_obj": page, "querystring": querystring,
        "brands": _brands(selectors.search_products(query)),
    })


def product_detail(request, slug):  # replaced in Task 8
    return HttpResponse("product (stub)")
```

- [ ] **Step 5: Write tests** — `backend/storefront/tests/test_catalog.py`

```python
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from storefront.tests.factories import make_category, make_product


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CategoryPageTests(TestCase):
    def setUp(self):
        self.phones = make_category("Smartphones")
        make_product(title="Galaxy S23", category=self.phones, brand="Samsung", price="2800000", stock_qty=5)
        make_product(title="Note 50 Pro", category=self.phones, brand="Infinix", price="1950000", stock_qty=0)
        make_product(title="MacBook", category=make_category("Laptops"), brand="Apple", price="6900000")

    def test_lists_only_category_products(self):
        r = self.client.get(reverse("storefront:category", args=[self.phones.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Galaxy S23")
        self.assertContains(r, "Note 50 Pro")
        self.assertNotContains(r, "MacBook")

    def test_brand_filter(self):
        r = self.client.get(reverse("storefront:category", args=[self.phones.slug]), {"brand": "Samsung"})
        self.assertContains(r, "Galaxy S23")
        self.assertNotContains(r, "Note 50 Pro")

    def test_price_sort_asc(self):
        r = self.client.get(reverse("storefront:category", args=[self.phones.slug]), {"sort": "price_asc"})
        self.assertLess(r.content.index(b"Note 50 Pro"), r.content.index(b"Galaxy S23"))

    def test_in_stock_filter(self):
        r = self.client.get(reverse("storefront:category", args=[self.phones.slug]), {"in_stock": "1"})
        self.assertContains(r, "Galaxy S23")
        self.assertNotContains(r, "Note 50 Pro")

    def test_unknown_category_404(self):
        self.assertEqual(self.client.get(reverse("storefront:category", args=["nope"])).status_code, 404)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SearchPageTests(TestCase):
    def setUp(self):
        self.phones = make_category("Smartphones")
        make_product(title="Galaxy S23", category=self.phones, brand="Samsung", price="2800000")
        make_product(title="AirPods Pro", category=self.phones, brand="Apple", price="950000",
                     stock_qty=3)

    def test_search_matches_brand(self):
        r = self.client.get(reverse("storefront:search"), {"q": "apple"})
        self.assertContains(r, "AirPods Pro")
        self.assertNotContains(r, "Galaxy S23")

    def test_empty_query_lists_all_active(self):
        r = self.client.get(reverse("storefront:search"), {"q": ""})
        self.assertContains(r, "Galaxy S23")
        self.assertContains(r, "AirPods Pro")
```

- [ ] **Step 6: Run**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_catalog -v 2
```
Expected: `Ran 7 tests` … `OK`.

- [ ] **Step 7: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront/templates backend/storefront/views/catalog.py backend/storefront/tests/test_catalog.py
git commit -m "feat(storefront): category and search pages with filters, sort, pagination"
```

---

## Task 8: Product detail page

**Files:**
- Create: `backend/storefront/templates/storefront/product_detail.html`
- Modify: `backend/storefront/views/catalog.py`, `backend/storefront/tests/test_catalog.py`

- [ ] **Step 1: `product_detail.html`**

```html
{% extends "storefront/base.html" %}
{% load static storefront_extras %}
{% block title %}{{ product.title }} — Jangu Mobile{% endblock %}
{% block content %}
<div class="pd">
  <div class="gallery">
    <div class="main">
      {% with first=images|first %}
      <img src="{% if first %}{{ first.image.url }}{% else %}{% static 'storefront/img/placeholder.svg' %}{% endif %}" alt="{{ product.title }}">
      {% endwith %}
    </div>
    {% if images|length > 1 %}
      <div class="thumbs">
        {% for im in images %}<img src="{{ im.image.url }}" data-full="{{ im.image.url }}" alt="">{% endfor %}
      </div>
    {% endif %}
  </div>

  <div class="buy">
    <span class="product-card"><span class="brand">{{ product.brand }}</span></span>
    <h1>{{ product.title }}</h1>
    <div class="price">UGX <span data-variant-price>{{ product.min_price|ugx|cut:"UGX " }}</span></div>

    {% if variants %}
    <label for="variant">Option</label>
    <select id="variant" data-variant-select>
      {% for v in variants %}
        <option value="{{ v.id }}" data-price="{{ v.price|ugx|cut:'UGX ' }}" data-in-stock="{% if v.stock_qty > 0 %}1{% else %}0{% endif %}">
          {{ v.attributes|variant_label }} — {{ v.price|ugx }}{% if v.stock_qty == 0 %} (Out of stock){% endif %}
        </option>
      {% endfor %}
    </select>
    {% endif %}

    <div class="qty" data-qty>
      <button type="button" data-step="down">−</button>
      <input type="number" value="1" min="1" aria-label="Quantity">
      <button type="button" data-step="up">+</button>
    </div>

    <button class="btn btn-primary btn-block" data-add-btn {% if not product.in_stock %}disabled{% endif %}>
      Add to Cart
    </button>
    <p style="color:var(--muted);font-size:.85rem;margin-top:10px">Cart & checkout arrive in the next update.</p>

    {% if product.description %}<h3 style="margin-top:20px">Details</h3><p>{{ product.description|linebreaks }}</p>{% endif %}
  </div>
</div>

{% if related %}
<section class="section">
  <div class="section-head"><h2>You may also like</h2></div>
  <div class="product-grid">
    {% for product in related %}{% include "storefront/partials/product_card.html" %}{% endfor %}
  </div>
</section>
{% endif %}
{% endblock %}
```
(The Add-to-Cart button is inert in phase 1a — it gets its form/endpoint in 1b.)

- [ ] **Step 2: Replace the `product_detail` stub in `backend/storefront/views/catalog.py`**

Remove the `from django.http import HttpResponse` import (no longer used) and
replace the stub `product_detail` with:

```python
def product_detail(request, slug):
    product = get_object_or_404(selectors.active_products(), slug=slug)
    return render(request, "storefront/product_detail.html", {
        "product": product,
        "images": list(product.images.all()),
        "variants": list(product.variants.all()),
        "related": selectors.related_products(product),
    })
```
(`active_products()` already `prefetch_related("variants", "images")`.)

- [ ] **Step 3: Add tests to `backend/storefront/tests/test_catalog.py`**

```python
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProductDetailTests(TestCase):
    def setUp(self):
        self.phones = make_category("Smartphones")
        self.p = make_product(
            title="Galaxy S23", category=self.phones, brand="Samsung",
            variants=[
                {"sku": "S23-128", "price": "2800000", "stock_qty": 5, "attributes": {"storage": "128GB", "color": "Black"}},
                {"sku": "S23-256", "price": "3050000", "stock_qty": 0, "attributes": {"storage": "256GB", "color": "Cream"}},
            ],
        )
        make_product(title="Note 50 Pro", category=self.phones, brand="Infinix", price="1950000")

    def test_renders_title_price_and_variants(self):
        r = self.client.get(reverse("storefront:product", args=[self.p.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Galaxy S23")
        self.assertContains(r, "128GB / Black — UGX 2,800,000")
        self.assertContains(r, "256GB / Cream — UGX 3,050,000 (Out of stock)")

    def test_shows_related_from_same_category(self):
        r = self.client.get(reverse("storefront:product", args=[self.p.slug]))
        self.assertContains(r, "Note 50 Pro")

    def test_inactive_or_unknown_is_404(self):
        self.assertEqual(self.client.get(reverse("storefront:product", args=["ghost"])).status_code, 404)
```

- [ ] **Step 4: Run catalog tests**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_catalog -v 2
```
Expected: `Ran 10 tests` … `OK`.

- [ ] **Step 5: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront/templates/storefront/product_detail.html backend/storefront/views/catalog.py backend/storefront/tests/test_catalog.py
git commit -m "feat(storefront): product detail page with variants and related"
```

---

## Task 9: `seed_demo` management command

**Files:**
- Create: `backend/storefront/management/commands/seed_demo.py`, `backend/storefront/tests/test_seed.py`

- [ ] **Step 1: Write the failing test** — `backend/storefront/tests/test_seed.py`

```python
import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings

from catalogue.models import Category, Product, ProductImage, ProductVariant


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SeedDemoTests(TestCase):
    def test_creates_catalogue(self):
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Category.objects.count(), 4)
        self.assertGreaterEqual(Product.objects.count(), 12)
        self.assertTrue(all(p.variants.exists() for p in Product.objects.all()))
        self.assertTrue(all(p.images.exists() for p in Product.objects.all()))
        self.assertTrue(all(v.price > 0 for v in ProductVariant.objects.all()))

    def test_is_idempotent(self):
        call_command("seed_demo", verbosity=0)
        c1, p1, v1, i1 = (Category.objects.count(), Product.objects.count(),
                          ProductVariant.objects.count(), ProductImage.objects.count())
        call_command("seed_demo", verbosity=0)
        self.assertEqual(
            (c1, p1, v1, i1),
            (Category.objects.count(), Product.objects.count(),
             ProductVariant.objects.count(), ProductImage.objects.count()),
        )
```

- [ ] **Step 2: Run — verify it fails**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_seed -v 2
```
Expected: `CommandError: Unknown command: 'seed_demo'`.

- [ ] **Step 3: Implement** — `backend/storefront/management/commands/seed_demo.py`

```python
"""Populate a demo Jangu catalogue. Idempotent; safe to run on every deploy."""

import io
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from catalogue.models import Category, Product, ProductImage, ProductVariant

CATEGORIES = [
    "Smartphones", "Laptops & Accessories", "Audio & Wearables", "Gaming Gear",
]

# title, category, brand, [ (sku_suffix, attributes, price, stock) ]
PRODUCTS = [
    ("Samsung Galaxy S23", "Smartphones", "Samsung", [
        ("128", {"storage": "128GB", "color": "Black"}, "2800000", 20),
        ("256", {"storage": "256GB", "color": "Cream"}, "3050000", 12)]),
    ("Infinix Note 50 Pro", "Smartphones", "Infinix", [
        ("256", {"storage": "256GB", "color": "Titan Grey"}, "1950000", 30)]),
    ("iPhone 15 Pro", "Smartphones", "Apple", [
        ("128", {"storage": "128GB", "color": "Natural Titanium"}, "5200000", 15),
        ("256", {"storage": "256GB", "color": "Blue Titanium"}, "5750000", 9)]),
    ("Tecno Camon 30", "Smartphones", "Tecno", [
        ("256", {"storage": "256GB", "color": "Black"}, "1350000", 25)]),
    ("MacBook Air M3", "Laptops & Accessories", "Apple", [
        ("8-256", {"ram": "8GB", "storage": "256GB"}, "6900000", 8)]),
    ("Dell XPS 13", "Laptops & Accessories", "Dell", [
        ("16-512", {"ram": "16GB", "storage": "512GB"}, "7400000", 6)]),
    ("HP Pavilion 15", "Laptops & Accessories", "HP", [
        ("16-512", {"ram": "16GB", "storage": "512GB"}, "3600000", 14)]),
    ("Anker 65W GaN Charger", "Laptops & Accessories", "Anker", [
        ("std", {}, "180000", 60)]),
    ("Sony WH-1000XM5", "Audio & Wearables", "Sony", [
        ("blk", {"color": "Black"}, "1250000", 18)]),
    ("JBL Tune 770NC", "Audio & Wearables", "JBL", [
        ("blk", {"color": "Black"}, "420000", 40)]),
    ("Apple AirPods Pro 2", "Audio & Wearables", "Apple", [
        ("usbc", {"connectivity": "USB-C"}, "950000", 22)]),
    ("Apple Watch Series 9", "Audio & Wearables", "Apple", [
        ("41", {"size": "41mm", "connectivity": "GPS"}, "1600000", 10)]),
    ("Samsung Galaxy Watch 6", "Audio & Wearables", "Samsung", [
        ("40", {"size": "40mm"}, "1150000", 13)]),
    ("Sony PlayStation 5 DualSense", "Gaming Gear", "Sony", [
        ("wht", {"color": "White"}, "380000", 35)]),
    ("Xbox Wireless Controller", "Gaming Gear", "Microsoft", [
        ("blk", {"color": "Carbon Black"}, "320000", 28)]),
    ("Logitech G502 HERO Mouse", "Gaming Gear", "Logitech", [
        ("blk", {"color": "Black"}, "190000", 45)]),
]


def _slug_of(title):
    from django.utils.text import slugify
    return slugify(title)


def _placeholder_png(label):
    img = Image.new("RGB", (600, 600), "#12356E")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 500, 600, 600], fill="#EF7C1B")
    d.rectangle([60, 60, 540, 460], outline="#ffffff", width=6)
    d.text((60, 250), label[:22], fill="#ffffff")
    d.text((70, 525), "JANGU MOBILE", fill="#12356E")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class Command(BaseCommand):
    help = "Populate a demo catalogue (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true",
                            help="Delete demo rows first (dev only).")

    def handle(self, *args, **opts):
        if opts["flush"]:
            ProductImage.objects.all().delete()
            ProductVariant.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.filter(name__in=CATEGORIES).delete()

        created_c = created_p = 0
        cats = {}
        for name in CATEGORIES:
            cat, made = Category.objects.get_or_create(slug=_slug_of(name), defaults={"name": name})
            cats[name] = cat
            created_c += made

        for title, cat_name, brand, variants in PRODUCTS:
            product, made = Product.objects.get_or_create(
                slug=_slug_of(title),
                defaults={"title": title, "brand": brand, "category": cats[cat_name],
                          "description": f"{brand} {title} — genuine, warrantied, delivered fast."},
            )
            created_p += made
            for suffix, attrs, price, stock in variants:
                ProductVariant.objects.get_or_create(
                    sku=f"{_slug_of(title)}-{suffix}",
                    defaults={"product": product, "attributes": attrs,
                              "price": Decimal(price), "stock_qty": stock},
                )
            if not product.images.exists():
                pi = ProductImage(product=product)
                pi.image.save(f"{_slug_of(title)}.png",
                              ContentFile(_placeholder_png(title)), save=True)

        self.stdout.write(self.style.SUCCESS(
            f"seed_demo: categories +{created_c}/{len(CATEGORIES)}, "
            f"products +{created_p}/{len(PRODUCTS)}."))
```

- [ ] **Step 4: Run — verify it passes**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test storefront.tests.test_seed -v 2
```
Expected: `Ran 2 tests` … `OK`.

- [ ] **Step 5: Smoke-run it against a scratch DB**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
rm -f db.sqlite3 && python manage.py migrate >/dev/null && python manage.py seed_demo
python manage.py seed_demo
rm -f db.sqlite3
```
Expected: first run `categories +4/4, products +16/16`; second run `+0/4 … +0/16`.

- [ ] **Step 6: Commit**

```bash
cd /Users/mac/projects/jango_mobileapp
git add backend/storefront/management/commands/seed_demo.py backend/storefront/tests/test_seed.py
git commit -m "feat(storefront): seed_demo command with generated placeholder images"
```

---

## Task 11: Phase 1a verification gate

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
python manage.py test 2>&1 | tail -8
```
Expected: `OK`. Count ≈ **124 − 4 (removed test_index) + 3 (admin branding) + 6 (extras) + 6 (selectors) + 3 (home) + 10 (catalog) + 2 (seed) = 150** (exact number may vary slightly; the requirement is **0 failures / 0 errors**).

- [ ] **Step 2: Deploy check**

```bash
DEBUG=False SECRET_KEY=verify-only-1234567890 python manage.py check --deploy 2>&1 | grep -E "W0|ERROR|identified"
```
Expected: only `security.W004`/`W008`/`W009` warnings, no `ERROR`.

- [ ] **Step 3: Build + browse simulation (DEBUG=False, gunicorn)**

```bash
cd /Users/mac/projects/jango_mobileapp/backend
rm -f db.sqlite3 && rm -rf staticfiles
export DEBUG=False SECRET_KEY=verify-only-1234567890 ALLOWED_HOSTS=127.0.0.1,localhost
python manage.py collectstatic --no-input >/dev/null
python manage.py migrate >/dev/null
python manage.py seed_demo
../.venv/bin/gunicorn backend.wsgi:application --bind 127.0.0.1:8126 --workers 1 --pid /tmp/g8126.pid >/tmp/g8126.log 2>&1 &
sleep 5
for path in / "/c/smartphones/" "/search/?q=apple" "/p/samsung-galaxy-s23/" /admin/login/; do
  printf '%s -> %s\n' "$path" "$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:8126$path")"
done
curl -sS http://127.0.0.1:8126/ | grep -o "Your Gadget. Our Priority." | head -1
curl -sS http://127.0.0.1:8126/admin/login/ | grep -o "Jangu Mobile" | head -1
kill "$(cat /tmp/g8126.pid)"; rm -f /tmp/g8126.pid /tmp/g8126.log
rm -f db.sqlite3 && rm -rf staticfiles
```
Expected: every path `200`; the two `grep`s echo their strings.

- [ ] **Step 4: Manual visual check (optional but recommended)**

Run `python manage.py runserver` after `seed_demo`, open `http://127.0.0.1:8000/`
and `http://127.0.0.1:8000/admin/`. Confirm: navy/orange palette, Poppins
headings, hero, category grid, featured product cards with generated images,
working filters on a category page, product detail with a variant `<select>`,
and the admin shell in navy with "Jangu Mobile" branding.

- [ ] **Step 5: Report**

Summarise: branch `storefront/milestone-1`, commits for scaffold → admin rebrand →
design system → filters/tags/selectors → base+home → category/search → product
detail → seed; full suite green; storefront + admin verified under
`DEBUG=False`. Phase 1a is deployable. Next: either push/merge to deploy 1a, or
proceed to writing the **Phase 1b** plan (cart, checkout, simulated payment,
`orders` app).

---

## Self-Review

**Spec coverage (phase 1a scope only — spec §12 "1a"):**
- Design system (base template, `app.css`, Poppins, logo) — Tasks 3, 6.
- `selectors` — Task 5.
- Home / category / search / product detail — Tasks 6, 7, 8.
- `seed_demo` — Task 9.
- Admin rebrand + recolour (spec §7) — Task 2.
- `core` cleanup (spec §10) — Task 1.
- Config (spec §9: INSTALLED_APPS, TEMPLATES DIRS + context processor, LOGIN_*) — Task 1.
- `ugx` / `variant_label` (spec §6.6) — Task 4.
- Tests per spec §6.8 (home, catalog, seed) + §5-not-applicable (orders is phase 1b) — Tasks 4-9.
- Phases 1b (cart/checkout/orders, spec §5, §6.2 cart/checkout routes, §6.4 those pages) and 1c (accounts UI) — **explicitly out of this plan**, own plans later.

**Placeholder scan:** none. Every code step has full content; Task 5 Step 4
deliberately shows a rejected approach then the exact code to write (labelled).
Task 6 Step 10 flags the stub functions that Tasks 7-8 replace, with the stub
code given.

**Type/name consistency:** `selectors.active_products/category_products/`
`search_products/related_products/featured_products` names match across Task 5
definition and Tasks 6-8 callers. Annotated attrs `min_price` + `in_stock` used
consistently in selectors, `product_card.html`, and tests. `cart_count` context
key matches `context_processors.py` and `header.html`. `seed_demo` command name
matches Tasks 9 and 11. Template filter names `ugx` /
`variant_label` consistent across `storefront_extras.py`, templates, tests.
`storefront:home|category|search|product` URL names consistent across
`urls.py`, templates, tests.
