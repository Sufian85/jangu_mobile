# Catalogue App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `catalogue` app — `Category`/`Product`/`ProductVariant`/`ProductImage` models, a public read-only browse API, and a staff-only management API — per `docs/superpowers/specs/2026-08-09-catalogue-design.md`.

**Architecture:** One new Django app, `catalogue`, layered like `accounts`: models → serializers → views → urls → admin, with public and staff concerns split into separate serializer/view/url modules (`serializers.py`/`views.py`/`urls.py` for the public browse API, `staff_serializers.py`/`staff_views.py`/`staff_urls.py` for the `IsAdminUser`-gated management API). No new permission class is needed — DRF's built-in `IsAdminUser` covers staff-only access via `accounts.User.is_staff`.

**Tech Stack:** Django 5.2, DRF, `django-filter` (category filter), DRF's built-in `SearchFilter`/`OrderingFilter`/`PageNumberPagination`, Pillow (already installed) for image handling. No git commands in any step (matches this project's existing convention — do not run `git add`/`git commit`).

**Paths used throughout:**
- Venv: `/Users/mac/projects/jango_mobileapp/.venv`
- Django project root (where `manage.py` lives): `/Users/mac/projects/jango_mobileapp/backend`
- App package: `/Users/mac/projects/jango_mobileapp/backend/catalogue`

---

### Task 1: Catalogue app skeleton + Category model + slug helper (TDD, first migration)

**Files:**
- Create: `backend/catalogue/__init__.py`
- Create: `backend/catalogue/apps.py`
- Create: `backend/catalogue/utils.py`
- Create: `backend/catalogue/models.py`
- Create: `backend/catalogue/tests/__init__.py`
- Create: `backend/catalogue/tests/test_models.py`
- Modify: `backend/backend/settings.py`

- [ ] **Step 1: Write the failing tests**

`catalogue/tests/test_models.py`:
```python
from django.test import TestCase

from catalogue.models import Category


class CategoryModelTests(TestCase):
    def test_slug_auto_generated_from_name(self):
        category = Category.objects.create(name="Mobile Phones")
        self.assertEqual(category.slug, "mobile-phones")

    def test_slug_collision_appends_suffix(self):
        Category.objects.create(name="Phones")
        second = Category.objects.create(name="Phones")
        self.assertEqual(second.slug, "phones-2")

    def test_explicit_slug_is_preserved(self):
        category = Category.objects.create(name="Tablets", slug="custom-slug")
        self.assertEqual(category.slug, "custom-slug")

    def test_nested_parent_child_relationship(self):
        electronics = Category.objects.create(name="Electronics")
        phones = Category.objects.create(name="Phones", parent=electronics)
        smartphones = Category.objects.create(name="Smartphones", parent=phones)
        self.assertEqual(smartphones.parent, phones)
        self.assertEqual(smartphones.parent.parent, electronics)

    def test_children_related_name(self):
        electronics = Category.objects.create(name="Electronics")
        phones = Category.objects.create(name="Phones", parent=electronics)
        self.assertIn(phones, electronics.children.all())
```

`catalogue/__init__.py`, `catalogue/tests/__init__.py`: empty files.

- [ ] **Step 2: Add catalogue to INSTALLED_APPS, run tests to verify they fail**

`catalogue/apps.py`:
```python
from django.apps import AppConfig


class CatalogueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalogue"
```

Modify `settings.py` `INSTALLED_APPS`, adding `"catalogue",` after `"accounts",`.

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue`
Expected: FAIL with `ModuleNotFoundError: No module named 'catalogue.models'`.

- [ ] **Step 3: Write the implementation**

`catalogue/utils.py`:
```python
from django.utils.text import slugify


def unique_slugify(model, value, instance_pk=None):
    """Return a slug for `value` that is unique among `model`'s existing rows."""
    base_slug = slugify(value)
    candidate = base_slug
    suffix = 2
    queryset = model.objects.all()
    if instance_pk is not None:
        queryset = queryset.exclude(pk=instance_pk)
    while queryset.filter(slug=candidate).exists():
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate
```

`catalogue/models.py`:
```python
from django.db import models

from .utils import unique_slugify


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    image = models.ImageField(upload_to="categories/", blank=True)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(Category, self.name, self.pk)
        super().save(*args, **kwargs)
```

- [ ] **Step 4: Create and run the migration**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py makemigrations catalogue`
Expected: creates `catalogue/migrations/0001_initial.py` defining `Category`.

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py migrate`
Expected: applies the new migration with no errors.

- [ ] **Step 5: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue`
Expected: `OK` (5 tests pass).

---

### Task 2: Product model (TDD, migration)

**Files:**
- Modify: `backend/catalogue/models.py`
- Modify: `backend/catalogue/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

Change the import line at the top of `catalogue/tests/test_models.py` from:
```python
from catalogue.models import Category
```
to:
```python
from django.db.models.deletion import ProtectedError

from catalogue.models import Category, Product
```

Append to `catalogue/tests/test_models.py`:
```python
class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")

    def test_slug_auto_generated_from_title(self):
        product = Product.objects.create(
            title="Tecno Spark 10", category=self.category, brand="Tecno"
        )
        self.assertEqual(product.slug, "tecno-spark-10")

    def test_slug_collision_appends_suffix(self):
        Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        second = Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        self.assertEqual(second.slug, "spark-10-2")

    def test_is_active_defaults_to_true(self):
        product = Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        self.assertTrue(product.is_active)

    def test_category_protected_on_delete(self):
        Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        with self.assertRaises(ProtectedError):
            self.category.delete()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_models.ProductModelTests`
Expected: FAIL with `ImportError: cannot import name 'Product' from 'catalogue.models'`.

- [ ] **Step 3: Write the implementation**

Append to `catalogue/models.py`:
```python
class Product(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    description = models.TextField(blank=True)
    brand = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(Product, self.title, self.pk)
        super().save(*args, **kwargs)
```

`category` uses `on_delete=models.PROTECT`: a category with products can't be deleted until its products are reassigned or removed first, preventing orphaned products.

- [ ] **Step 4: Create and run the migration**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py makemigrations catalogue`
Expected: creates `catalogue/migrations/0002_product.py`.

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py migrate`
Expected: applies the new migration with no errors.

- [ ] **Step 5: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue`
Expected: `OK` (9 tests pass).

---

### Task 3: ProductVariant model (TDD, migration)

**Files:**
- Modify: `backend/catalogue/models.py`
- Modify: `backend/catalogue/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

Change the import line at the top of `catalogue/tests/test_models.py` to:
```python
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError

from catalogue.models import Category, Product, ProductVariant
```

Append to `catalogue/tests/test_models.py`:
```python
class ProductVariantModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )

    def test_attributes_default_to_empty_dict(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00"
        )
        self.assertEqual(variant.attributes, {})

    def test_attributes_json_roundtrip(self):
        variant = ProductVariant.objects.create(
            product=self.product,
            sku="SPARK10-128-BLK",
            price="450000.00",
            attributes={"storage": "128GB", "color": "Black"},
        )
        variant.refresh_from_db()
        self.assertEqual(variant.attributes, {"storage": "128GB", "color": "Black"})

    def test_stock_qty_defaults_to_zero(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00"
        )
        self.assertEqual(variant.stock_qty, 0)

    def test_in_stock_property(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00", stock_qty=5
        )
        self.assertTrue(variant.in_stock)
        variant.stock_qty = 0
        self.assertFalse(variant.in_stock)

    def test_sku_unique(self):
        ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128-BLK", price="450000.00"
        )
        with self.assertRaises(IntegrityError):
            ProductVariant.objects.create(
                product=self.product, sku="SPARK10-128-BLK", price="450000.00"
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_models.ProductVariantModelTests`
Expected: FAIL with `ImportError: cannot import name 'ProductVariant' from 'catalogue.models'`.

- [ ] **Step 3: Write the implementation**

Append to `catalogue/models.py`:
```python
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=64, unique=True)
    attributes = models.JSONField(default=dict, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_qty = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.sku

    @property
    def in_stock(self):
        return self.stock_qty > 0
```

- [ ] **Step 4: Create and run the migration**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py makemigrations catalogue`
Expected: creates `catalogue/migrations/0003_productvariant.py`.

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py migrate`
Expected: applies the new migration with no errors.

- [ ] **Step 5: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue`
Expected: `OK` (14 tests pass).

---

### Task 4: ProductImage model + media settings (TDD, migration)

**Files:**
- Modify: `backend/catalogue/models.py`
- Modify: `backend/catalogue/tests/test_models.py`
- Create: `backend/catalogue/tests/helpers.py`
- Modify: `backend/backend/settings.py`
- Modify: `backend/backend/urls.py`

- [ ] **Step 1: Write the failing tests**

`catalogue/tests/helpers.py`:
```python
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def make_test_image(name="test.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1)).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")
```

Change the import block at the top of `catalogue/tests/test_models.py` to:
```python
import tempfile

from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings

from catalogue.models import Category, Product, ProductImage, ProductVariant
from catalogue.tests.helpers import make_test_image
```

Append to `catalogue/tests/test_models.py`:
```python
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProductImageModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )

    def test_first_image_is_auto_primary(self):
        image = ProductImage.objects.create(product=self.product, image=make_test_image())
        self.assertTrue(image.is_primary)

    def test_new_primary_unsets_previous_primary(self):
        first = ProductImage.objects.create(
            product=self.product, image=make_test_image("a.png")
        )
        second = ProductImage.objects.create(
            product=self.product, image=make_test_image("b.png"), is_primary=True
        )
        first.refresh_from_db()
        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)

    def test_sort_order_defaults_to_zero(self):
        image = ProductImage.objects.create(product=self.product, image=make_test_image())
        self.assertEqual(image.sort_order, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_models.ProductImageModelTests`
Expected: FAIL with `ImportError: cannot import name 'ProductImage' from 'catalogue.models'`.

- [ ] **Step 3: Write the implementation**

Change the top import line of `catalogue/models.py` from `from django.db import models` to:
```python
from django.db import models, transaction
```

Append to `catalogue/models.py`:
```python
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.product.title} image #{self.pk}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            Product.objects.select_for_update().get(pk=self.product_id)

            is_first_image = self._state.adding and not ProductImage.objects.filter(
                product=self.product
            ).exists()
            if is_first_image:
                self.is_primary = True

            super().save(*args, **kwargs)

            if self.is_primary:
                ProductImage.objects.filter(product=self.product).exclude(pk=self.pk).update(
                    is_primary=False
                )
```

This mirrors `Address.save()`'s default-switching / row-locking pattern already in `accounts/models.py`.

Append to `settings.py`, directly below `STATIC_ROOT`:
```python
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
```

Replace `backend/urls.py` with:
```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
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

- [ ] **Step 4: Create and run the migration**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py makemigrations catalogue`
Expected: creates `catalogue/migrations/0004_productimage.py`.

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py migrate`
Expected: applies the new migration with no errors.

- [ ] **Step 5: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue`
Expected: `OK` (17 tests pass).

---

### Task 5: Django Admin registration (TDD)

**Files:**
- Create: `backend/catalogue/admin.py`
- Create: `backend/catalogue/tests/test_admin.py`

- [ ] **Step 1: Write the failing tests**

`catalogue/tests/test_admin.py`:
```python
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from catalogue.models import Category


class CatalogueAdminAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.customer = User.objects.create_user(
            phone="0709876543", password="strongpass123", first_name="Grace", last_name="Hopper"
        )
        Category.objects.create(name="Phones")

    def test_staff_can_access_category_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:catalogue_category_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_access_product_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:catalogue_product_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_redirected_from_category_changelist(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("admin:catalogue_category_changelist"))
        self.assertEqual(response.status_code, 302)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_admin`
Expected: FAIL with `NoReverseMatch` (models not registered in admin).

- [ ] **Step 3: Write the implementation**

`catalogue/admin.py`:
```python
from django.contrib import admin

from .models import Category, Product, ProductImage, ProductVariant


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "brand", "is_active", "created_at"]
    list_filter = ["is_active", "category"]
    search_fields = ["title", "brand"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProductVariantInline, ProductImageInline]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_admin`
Expected: `OK` (3 tests pass).

---

### Task 6: Public API — Category list (TDD)

**Files:**
- Create: `backend/catalogue/serializers.py`
- Create: `backend/catalogue/views.py`
- Create: `backend/catalogue/urls.py`
- Create: `backend/catalogue/tests/test_categories.py`
- Modify: `backend/backend/urls.py`

- [ ] **Step 1: Write the failing tests**

`catalogue/tests/test_categories.py`:
```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalogue.models import Category


class CategoryListViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("category-list")

    def test_list_returns_all_categories(self):
        electronics = Category.objects.create(name="Electronics")
        Category.objects.create(name="Phones", parent=electronics)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_includes_parent_id(self):
        electronics = Category.objects.create(name="Electronics")
        phones = Category.objects.create(name="Phones", parent=electronics)
        response = self.client.get(self.url)
        phones_row = next(row for row in response.data if row["id"] == phones.id)
        self.assertEqual(phones_row["parent"], electronics.id)

    def test_no_auth_required(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_categories`
Expected: FAIL with `NoReverseMatch: 'category-list' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

`catalogue/serializers.py`:
```python
from rest_framework import serializers

from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "image"]
```

`catalogue/views.py`:
```python
from rest_framework import generics, permissions

from .models import Category
from .serializers import CategorySerializer


class CategoryListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    pagination_class = None
```

`pagination_class = None` keeps this a flat list — categories are a small, fixed set, not something to page through (unlike the product catalogue in Task 7, which does paginate).

`catalogue/urls.py`:
```python
from django.urls import path

from .views import CategoryListView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
]
```

Replace `backend/urls.py` with:
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

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_categories`
Expected: `OK` (3 tests pass).

---

### Task 7: Public API — Product list: filter, search, ordering, pagination (TDD)

**Files:**
- Create: `backend/catalogue/filters.py`
- Modify: `backend/catalogue/serializers.py`
- Modify: `backend/catalogue/views.py`
- Modify: `backend/catalogue/urls.py`
- Create: `backend/catalogue/tests/test_products.py`
- Modify: `backend/backend/settings.py`

- [ ] **Step 1: Write the failing tests**

`catalogue/tests/test_products.py`:
```python
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalogue.models import Category, Product, ProductVariant


class ProductListViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("product-list")
        self.phones = Category.objects.create(name="Phones")
        self.laptops = Category.objects.create(name="Laptops")

    def _make_product(self, title, category, brand, price, stock_qty=5, is_active=True):
        product = Product.objects.create(
            title=title, category=category, brand=brand, is_active=is_active
        )
        ProductVariant.objects.create(
            product=product, sku=f"{title}-SKU", price=Decimal(price), stock_qty=stock_qty
        )
        return product

    def test_excludes_inactive_products(self):
        self._make_product("Spark 10", self.phones, "Tecno", "450000.00", is_active=False)
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 0)

    def test_category_filter(self):
        self._make_product("Spark 10", self.phones, "Tecno", "450000.00")
        self._make_product("ThinkPad", self.laptops, "Lenovo", "2000000.00")
        response = self.client.get(self.url, {"category": self.phones.slug})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Spark 10")

    def test_search_matches_title(self):
        self._make_product("Spark 10", self.phones, "Tecno", "450000.00")
        response = self.client.get(self.url, {"search": "spark"})
        self.assertEqual(response.data["count"], 1)

    def test_search_matches_brand(self):
        self._make_product("Spark 10", self.phones, "Tecno", "450000.00")
        response = self.client.get(self.url, {"search": "tecno"})
        self.assertEqual(response.data["count"], 1)

    def test_ordering_by_price_ascending(self):
        self._make_product("Cheap Phone", self.phones, "Tecno", "100000.00")
        self._make_product("Pricey Phone", self.phones, "Apple", "3000000.00")
        response = self.client.get(self.url, {"ordering": "price_from"})
        titles = [row["title"] for row in response.data["results"]]
        self.assertEqual(titles, ["Cheap Phone", "Pricey Phone"])

    def test_ordering_by_price_descending(self):
        self._make_product("Cheap Phone", self.phones, "Tecno", "100000.00")
        self._make_product("Pricey Phone", self.phones, "Apple", "3000000.00")
        response = self.client.get(self.url, {"ordering": "-price_from"})
        titles = [row["title"] for row in response.data["results"]]
        self.assertEqual(titles, ["Pricey Phone", "Cheap Phone"])

    def test_out_of_stock_variant_still_visible_but_flagged(self):
        self._make_product("Spark 10", self.phones, "Tecno", "450000.00", stock_qty=0)
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 1)
        self.assertFalse(response.data["results"][0]["in_stock"])

    def test_price_from_is_minimum_variant_price(self):
        product = self._make_product("Spark 10", self.phones, "Tecno", "450000.00")
        ProductVariant.objects.create(
            product=product, sku="SPARK10-256", price=Decimal("500000.00"), stock_qty=3
        )
        response = self.client.get(self.url)
        self.assertEqual(response.data["results"][0]["price_from"], "450000.00")

    def test_pagination_page_size(self):
        for i in range(25):
            self._make_product(f"Phone {i}", self.phones, "Tecno", "100000.00")
        response = self.client.get(self.url)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_products`
Expected: FAIL with `NoReverseMatch: 'product-list' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

`catalogue/filters.py`:
```python
import django_filters

from .models import Product


class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__slug")

    class Meta:
        model = Product
        fields = ["category"]
```

Append to `catalogue/serializers.py`:
```python
class ProductListSerializer(serializers.ModelSerializer):
    price_from = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    in_stock = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title", "brand", "category", "primary_image",
            "price_from", "in_stock",
        ]

    def get_in_stock(self, obj):
        return any(variant.stock_qty > 0 for variant in obj.variants.all())

    def get_primary_image(self, obj):
        primary = next((image for image in obj.images.all() if image.is_primary), None)
        if primary is None:
            return None
        request = self.context.get("request")
        url = primary.image.url
        return request.build_absolute_uri(url) if request else url
```

`price_from` comes from a queryset annotation (below), not a stored field — every product's real price lives only on its variants (see spec).

Append to `catalogue/views.py`:
```python
from django.db.models import Min
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from .filters import ProductFilter
from .models import Product
from .serializers import ProductListSerializer


class ProductListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer
    queryset = (
        Product.objects.filter(is_active=True)
        .annotate(price_from=Min("variants__price"))
        .prefetch_related("variants", "images")
    )
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["title", "brand"]
    ordering_fields = ["price_from", "created_at"]
```

Append to `catalogue/urls.py`'s `urlpatterns` (import `ProductListView` alongside `CategoryListView`):
```python
from .views import CategoryListView, ProductListView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("products/", ProductListView.as_view(), name="product-list"),
]
```

Modify `settings.py`'s `REST_FRAMEWORK` dict — add two keys (full block shown for clarity):
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "register": "5/hour",
        "login": "10/min",
    },
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_products`
Expected: `OK` (9 tests pass).

---

### Task 8: Public API — Product detail (TDD)

**Files:**
- Modify: `backend/catalogue/serializers.py`
- Modify: `backend/catalogue/views.py`
- Modify: `backend/catalogue/urls.py`
- Modify: `backend/catalogue/tests/test_products.py`

- [ ] **Step 1: Write the failing tests**

Change the import line at the top of `catalogue/tests/test_products.py` to:
```python
from catalogue.models import Category, Product, ProductVariant
```
(already present — no change needed if it already imports all three).

Append to `catalogue/tests/test_products.py`:
```python
class ProductDetailViewTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="SPARK10-128", price=Decimal("450000.00"), stock_qty=0
        )
        self.url = reverse("product-detail", args=[self.product.slug])

    def test_returns_full_detail_with_variants(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["variants"]), 1)
        self.assertEqual(response.data["variants"][0]["sku"], "SPARK10-128")

    def test_out_of_stock_variant_flagged_in_detail(self):
        response = self.client.get(self.url)
        self.assertFalse(response.data["variants"][0]["in_stock"])

    def test_inactive_product_returns_404(self):
        self.product.is_active = False
        self.product.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_products.ProductDetailViewTests`
Expected: FAIL with `NoReverseMatch: 'product-detail' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Change the top import line of `catalogue/serializers.py` from `from .models import Category` to:
```python
from .models import Category, Product, ProductImage, ProductVariant
```

Append to `catalogue/serializers.py`:
```python
class ProductVariantSerializer(serializers.ModelSerializer):
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "attributes", "price", "stock_qty", "in_stock"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "is_primary", "sort_order"]


class ProductDetailSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title", "brand", "category", "description",
            "variants", "images",
        ]
```

Append to `catalogue/views.py` (add `ProductDetailSerializer` to the existing `from .serializers import ProductListSerializer` line instead of a new import):
```python
from .serializers import ProductDetailSerializer, ProductListSerializer


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductDetailSerializer
    queryset = Product.objects.filter(is_active=True).prefetch_related("variants", "images")
    lookup_field = "slug"
```

Replace `catalogue/urls.py` with:
```python
from django.urls import path

from .views import CategoryListView, ProductDetailView, ProductListView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_products`
Expected: `OK` (12 tests pass).

---

### Task 9: Staff API — Category CRUD (TDD)

**Files:**
- Create: `backend/catalogue/staff_serializers.py`
- Create: `backend/catalogue/staff_views.py`
- Create: `backend/catalogue/staff_urls.py`
- Create: `backend/catalogue/tests/test_staff_api.py`
- Modify: `backend/backend/urls.py`

- [ ] **Step 1: Write the failing tests**

`catalogue/tests/test_staff_api.py`:
```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from catalogue.models import Category


class StaffCategoryAPITests(APITestCase):
    def setUp(self):
        self.list_url = reverse("staff-category-list")
        self.staff = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.customer = User.objects.create_user(
            phone="0709876543", password="strongpass123", first_name="Grace", last_name="Hopper"
        )

    def test_anonymous_request_returns_401(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_staff_request_returns_403(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_create_category(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(self.list_url, {"name": "Phones"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["slug"], "phones")

    def test_staff_can_update_category(self):
        self.client.force_authenticate(user=self.staff)
        category = Category.objects.create(name="Phones")
        detail_url = reverse("staff-category-detail", args=[category.pk])
        response = self.client.patch(detail_url, {"name": "Smartphones"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category.refresh_from_db()
        self.assertEqual(category.name, "Smartphones")

    def test_staff_can_delete_category(self):
        self.client.force_authenticate(user=self.staff)
        category = Category.objects.create(name="Phones")
        detail_url = reverse("staff-category-detail", args=[category.pk])
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_staff_api`
Expected: FAIL with `NoReverseMatch: 'staff-category-list' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

`catalogue/staff_serializers.py`:
```python
from rest_framework import serializers

from .models import Category


class StaffCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "image"]
        read_only_fields = ["slug"]
```

`catalogue/staff_views.py`:
```python
from rest_framework import permissions, viewsets

from .models import Category
from .staff_serializers import StaffCategorySerializer


class StaffCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffCategorySerializer
    queryset = Category.objects.all()
    pagination_class = None
```

`pagination_class = None` on every staff viewset in this app: staff CRUD lists (categories, and later per-product variants/images) are small, scoped collections, not the large public catalogue — pagination would only add friction here.

`catalogue/staff_urls.py`:
```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .staff_views import StaffCategoryViewSet

router = DefaultRouter()
router.register("categories", StaffCategoryViewSet, basename="staff-category")

urlpatterns = [
    path("", include(router.urls)),
]
```

Replace `backend/urls.py` with:
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

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_staff_api`
Expected: `OK` (5 tests pass).

---

### Task 10: Staff API — Product CRUD with nested variant creation (TDD)

**Files:**
- Modify: `backend/catalogue/staff_serializers.py`
- Modify: `backend/catalogue/staff_views.py`
- Modify: `backend/catalogue/staff_urls.py`
- Modify: `backend/catalogue/tests/test_staff_api.py`

- [ ] **Step 1: Write the failing tests**

Change the import line at the top of `catalogue/tests/test_staff_api.py` to:
```python
from catalogue.models import Category, Product, ProductVariant
```

Append to `catalogue/tests/test_staff_api.py`:
```python
class StaffProductAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.client.force_authenticate(user=self.staff)
        self.category = Category.objects.create(name="Phones")
        self.list_url = reverse("staff-product-list")

    def test_create_product_with_variant_returns_201(self):
        payload = {
            "title": "Spark 10",
            "category": self.category.id,
            "brand": "Tecno",
            "variants": [
                {
                    "sku": "SPARK10-128",
                    "price": "450000.00",
                    "stock_qty": 10,
                    "attributes": {"storage": "128GB"},
                }
            ],
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(pk=response.data["id"])
        self.assertEqual(product.variants.count(), 1)
        self.assertEqual(product.variants.first().sku, "SPARK10-128")

    def test_create_product_without_variants_returns_400(self):
        payload = {
            "title": "Spark 10", "category": self.category.id, "brand": "Tecno", "variants": [],
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_product_ignores_variants_payload(self):
        product = Product.objects.create(title="Spark 10", category=self.category, brand="Tecno")
        ProductVariant.objects.create(product=product, sku="SPARK10-128", price="450000.00")
        detail_url = reverse("staff-product-detail", args=[product.pk])
        response = self.client.patch(
            detail_url, {"title": "Spark 10 Pro", "variants": []}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertEqual(product.title, "Spark 10 Pro")
        self.assertEqual(product.variants.count(), 1)

    def test_non_staff_cannot_create_product(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.list_url, {"title": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_staff_api.StaffProductAPITests`
Expected: FAIL with `NoReverseMatch: 'staff-product-list' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Change the top import line of `catalogue/staff_serializers.py` from `from .models import Category` to:
```python
from .models import Category, Product, ProductVariant
```

Append to `catalogue/staff_serializers.py`:
```python
class StaffProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "attributes", "price", "stock_qty"]
        read_only_fields = ["id"]


class StaffProductSerializer(serializers.ModelSerializer):
    variants = StaffProductVariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title", "category", "description", "brand",
            "is_active", "variants",
        ]
        read_only_fields = ["slug"]

    def create(self, validated_data):
        variants_data = validated_data.pop("variants", [])
        if not variants_data:
            raise serializers.ValidationError(
                {"variants": "A product needs at least one variant."}
            )
        product = Product.objects.create(**validated_data)
        for variant_data in variants_data:
            ProductVariant.objects.create(product=product, **variant_data)
        return product

    def update(self, instance, validated_data):
        validated_data.pop("variants", None)
        return super().update(instance, validated_data)
```

`variants` is only meaningful on create — a product's variants are managed afterwards through the dedicated `/variants/` endpoint (Task 11), so `update()` drops the key entirely instead of trying to reconcile a nested list against existing rows.

Append to `catalogue/staff_views.py` (add `Product` to the existing `from .models import Category` line, and `StaffProductSerializer` to the existing serializers import line):
```python
from .models import Category, Product
from .staff_serializers import StaffCategorySerializer, StaffProductSerializer


class StaffProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffProductSerializer
    queryset = Product.objects.all()
    pagination_class = None
```

Modify `catalogue/staff_urls.py`:
```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .staff_views import StaffCategoryViewSet, StaffProductViewSet

router = DefaultRouter()
router.register("categories", StaffCategoryViewSet, basename="staff-category")
router.register("products", StaffProductViewSet, basename="staff-product")

urlpatterns = [
    path("", include(router.urls)),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_staff_api.StaffProductAPITests`
Expected: `OK` (4 tests pass).

---

### Task 11: Staff API — Variant CRUD scoped by product (TDD)

**Files:**
- Modify: `backend/catalogue/staff_views.py`
- Modify: `backend/catalogue/staff_urls.py`
- Modify: `backend/catalogue/tests/test_staff_api.py`

- [ ] **Step 1: Write the failing tests**

Append to `catalogue/tests/test_staff_api.py`:
```python
class StaffProductVariantAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.client.force_authenticate(user=self.staff)
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.other_product = Product.objects.create(
            title="ThinkPad", category=self.category, brand="Lenovo"
        )
        self.list_url = reverse("staff-variant-list")

    def test_create_variant_for_product(self):
        response = self.client.post(
            f"{self.list_url}?product={self.product.id}",
            {
                "sku": "SPARK10-128", "price": "450000.00", "stock_qty": 10,
                "attributes": {"storage": "128GB"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.product.variants.count(), 1)

    def test_list_scoped_to_product(self):
        ProductVariant.objects.create(product=self.product, sku="A", price="100.00")
        ProductVariant.objects.create(product=self.other_product, sku="B", price="200.00")
        response = self.client.get(f"{self.list_url}?product={self.product.id}")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["sku"], "A")

    def test_patch_updates_stock_qty(self):
        variant = ProductVariant.objects.create(
            product=self.product, sku="A", price="100.00", stock_qty=5
        )
        detail_url = reverse("staff-variant-detail", args=[variant.pk])
        response = self.client.patch(detail_url, {"stock_qty": 50}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        variant.refresh_from_db()
        self.assertEqual(variant.stock_qty, 50)

    def test_non_staff_blocked(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_staff_api.StaffProductVariantAPITests`
Expected: FAIL with `NoReverseMatch: 'staff-variant-list' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Change the top of `catalogue/staff_views.py` to:
```python
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets

from .models import Category, Product, ProductVariant
from .staff_serializers import (
    StaffCategorySerializer,
    StaffProductSerializer,
    StaffProductVariantSerializer,
)
```

Append to `catalogue/staff_views.py`:
```python
class StaffProductVariantViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffProductVariantSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = ProductVariant.objects.all()
        product_id = self.request.query_params.get("product")
        if product_id is not None:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.request.query_params.get("product"))
        serializer.save(product=product)
```

Modify `catalogue/staff_urls.py`:
```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .staff_views import StaffCategoryViewSet, StaffProductVariantViewSet, StaffProductViewSet

router = DefaultRouter()
router.register("categories", StaffCategoryViewSet, basename="staff-category")
router.register("products", StaffProductViewSet, basename="staff-product")
router.register("variants", StaffProductVariantViewSet, basename="staff-variant")

urlpatterns = [
    path("", include(router.urls)),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_staff_api.StaffProductVariantAPITests`
Expected: `OK` (4 tests pass).

---

### Task 12: Staff API — Image CRUD + set-primary scoped by product (TDD)

**Files:**
- Modify: `backend/catalogue/staff_serializers.py`
- Modify: `backend/catalogue/staff_views.py`
- Modify: `backend/catalogue/staff_urls.py`
- Modify: `backend/catalogue/tests/test_staff_api.py`

- [ ] **Step 1: Write the failing tests**

Change the import block at the top of `catalogue/tests/test_staff_api.py` to:
```python
import tempfile

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from catalogue.models import Category, Product, ProductImage, ProductVariant
from catalogue.tests.helpers import make_test_image
```

Append to `catalogue/tests/test_staff_api.py`:
```python
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class StaffProductImageAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            phone="0771234567", password="strongpass123", first_name="Ada", last_name="Lovelace"
        )
        self.client.force_authenticate(user=self.staff)
        self.category = Category.objects.create(name="Phones")
        self.product = Product.objects.create(
            title="Spark 10", category=self.category, brand="Tecno"
        )
        self.list_url = reverse("staff-image-list")

    def test_upload_image_for_product(self):
        response = self.client.post(
            f"{self.list_url}?product={self.product.id}",
            {"image": make_test_image()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.product.images.count(), 1)

    def test_first_upload_is_auto_primary(self):
        response = self.client.post(
            f"{self.list_url}?product={self.product.id}",
            {"image": make_test_image()},
            format="multipart",
        )
        self.assertTrue(response.data["is_primary"])

    def test_set_primary_action(self):
        first = ProductImage.objects.create(product=self.product, image=make_test_image("a.png"))
        second = ProductImage.objects.create(
            product=self.product, image=make_test_image("b.png")
        )
        set_primary_url = reverse("staff-image-set-primary", args=[second.pk])
        response = self.client.post(set_primary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)

    def test_non_staff_blocked(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_staff_api.StaffProductImageAPITests`
Expected: FAIL with `NoReverseMatch: 'staff-image-list' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Change the top import line of `catalogue/staff_serializers.py` from `from .models import Category, Product, ProductVariant` to:
```python
from .models import Category, Product, ProductImage, ProductVariant
```

Append to `catalogue/staff_serializers.py`:
```python
class StaffProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "is_primary", "sort_order"]
        read_only_fields = ["id"]
```

Change the top of `catalogue/staff_views.py` to:
```python
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Product, ProductImage, ProductVariant
from .staff_serializers import (
    StaffCategorySerializer,
    StaffProductImageSerializer,
    StaffProductSerializer,
    StaffProductVariantSerializer,
)
```

Append to `catalogue/staff_views.py`:
```python
class StaffProductImageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = StaffProductImageSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = ProductImage.objects.all()
        product_id = self.request.query_params.get("product")
        if product_id is not None:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.request.query_params.get("product"))
        serializer.save(product=product)

    @action(detail=True, methods=["post"], url_path="set-primary")
    def set_primary(self, request, pk=None):
        image = self.get_object()
        image.is_primary = True
        image.save()
        return Response(StaffProductImageSerializer(image).data)
```

Modify `catalogue/staff_urls.py`:
```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .staff_views import (
    StaffCategoryViewSet,
    StaffProductImageViewSet,
    StaffProductVariantViewSet,
    StaffProductViewSet,
)

router = DefaultRouter()
router.register("categories", StaffCategoryViewSet, basename="staff-category")
router.register("products", StaffProductViewSet, basename="staff-product")
router.register("variants", StaffProductVariantViewSet, basename="staff-variant")
router.register("images", StaffProductImageViewSet, basename="staff-image")

urlpatterns = [
    path("", include(router.urls)),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test catalogue.tests.test_staff_api.StaffProductImageAPITests`
Expected: `OK` (4 tests pass).

---

### Task 13: Full test suite run

**Files:** none

- [ ] **Step 1: Run the entire suite**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py test`
Expected: `OK` — 85 tests total (33 existing from `core`/`accounts` + 52 new from `catalogue`: 5 Category model + 4 Product model + 5 ProductVariant model + 3 ProductImage model + 3 admin + 3 category API + 9 product list + 3 product detail + 5 staff category + 4 staff product + 4 staff variant + 4 staff image).

- [ ] **Step 2: Final config sanity check**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python manage.py check`
Expected: `System check identified no issues (0 silenced).`
