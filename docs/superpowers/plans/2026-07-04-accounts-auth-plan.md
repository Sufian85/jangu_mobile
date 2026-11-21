# Accounts App (Auth/JWT) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the bare Django scaffold into an env-configured, MySQL-backed project with a working phone/JWT-authenticated `accounts` app (custom User, addresses, register/login/refresh/me endpoints), per `docs/superpowers/specs/2026-07-04-accounts-auth-design.md`.

**Architecture:** Two new Django apps — `core` (thin, cross-cutting: custom DRF exception handler) and `accounts` (custom phone-keyed User model, Address model, JWT auth endpoints). Settings move to `django-environ`-driven config against local MySQL. No git commands in any step (user preference — do not run `git init`/`add`/`commit`).

**Tech Stack:** Django 5.2, DRF, `djangorestframework-simplejwt` (+ token blacklist), `django-cors-headers`, `django-environ`, `mysqlclient`, `drf-spectacular`, `django-filter`.

**Paths used throughout:**
- Venv: `/Users/mac/projects/jango_mobileapp/.venv`
- `requirements.txt`: `/Users/mac/projects/jango_mobileapp/requirements.txt`
- Django project root (where `manage.py` lives): `/Users/mac/projects/jango_mobileapp/backend`
- Project config package: `/Users/mac/projects/jango_mobileapp/backend/backend`

---

### Task 1: Pin and install dependencies

**Files:**
- Modify: `/Users/mac/projects/jango_mobileapp/requirements.txt`

- [ ] **Step 1: Write requirements.txt**

```
Django>=5.2,<5.3
djangorestframework>=3.15,<3.16
djangorestframework-simplejwt>=5.3,<5.4
django-cors-headers>=4.4,<5.0
django-environ>=0.11,<0.12
mysqlclient>=2.2,<2.3
drf-spectacular>=0.27,<0.28
django-filter>=24.2,<25.0
Pillow>=10.4,<11.0
```

- [ ] **Step 2: Install into the venv**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/pip install -r /Users/mac/projects/jango_mobileapp/requirements.txt`
Expected: all packages install successfully.

If `mysqlclient` fails to build (missing `mysql_config` on PATH), find it and retry:
```bash
find /opt/homebrew /usr/local -maxdepth 4 -name mysql_config 2>/dev/null
```
Then re-run the install with that directory prepended to `PATH`, e.g.:
```bash
PATH="/opt/homebrew/opt/mysql-client/bin:$PATH" /Users/mac/projects/jango_mobileapp/.venv/bin/pip install -r /Users/mac/projects/jango_mobileapp/requirements.txt
```

- [ ] **Step 3: Lock exact installed versions**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/pip freeze > /Users/mac/projects/jango_mobileapp/requirements.txt`

- [ ] **Step 4: Verify Django version**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python -c "import django; print(django.get_version())"`
Expected: prints a version starting with `5.2`.

---

### Task 2: MySQL database and user

**Files:** none (external DB state)

- [ ] **Step 1: Create database and user**

Run:
```bash
mysql -u root <<'SQL'
CREATE DATABASE IF NOT EXISTS jango_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'jango_user'@'localhost' IDENTIFIED BY 'JangoDevLocal2026!';
GRANT ALL PRIVILEGES ON jango_db.* TO 'jango_user'@'localhost';
FLUSH PRIVILEGES;
SQL
```
If `root` requires a password, add `-p` and supply it interactively. This is a local development credential only — rotate it for any shared/staging environment.

- [ ] **Step 2: Verify connection**

Run: `mysql -u jango_user -p'JangoDevLocal2026!' jango_db -e "SELECT 1;"`
Expected: output shows a row with `1`.

---

### Task 3: Environment config + MySQL settings

**Files:**
- Create: `/Users/mac/projects/jango_mobileapp/backend/.env`
- Create: `/Users/mac/projects/jango_mobileapp/backend/.env.example`
- Modify: `/Users/mac/projects/jango_mobileapp/backend/backend/settings.py`

- [ ] **Step 1: Generate a secret key**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
Copy the printed value for use in Step 2 (referred to below as `<GENERATED_SECRET_KEY>`).

- [ ] **Step 2: Create `.env`**

```
SECRET_KEY=<GENERATED_SECRET_KEY>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=jango_db
DB_USER=jango_user
DB_PASSWORD=JangoDevLocal2026!
DB_HOST=127.0.0.1
DB_PORT=3306
JWT_ACCESS_MINUTES=60
JWT_REFRESH_DAYS=7
CORS_ALLOWED_ORIGINS=
```

- [ ] **Step 3: Create `.env.example`** (same keys, no real secrets)

```
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=jango_db
DB_USER=jango_user
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
JWT_ACCESS_MINUTES=60
JWT_REFRESH_DAYS=7
CORS_ALLOWED_ORIGINS=
```

- [ ] **Step 4: Rewrite settings.py**

Replace the full contents of `/Users/mac/projects/jango_mobileapp/backend/backend/settings.py` with:

```python
"""Django settings for the Jango Mobile backend project."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

- [ ] **Step 5: Verify DB connectivity (no schema changes)**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py showmigrations`
Expected: connects to MySQL without error and lists Django's built-in apps' migrations as unapplied (`[ ]`).

---

### Task 4: Core app + third-party app wiring

**Files:**
- Create: `/Users/mac/projects/jango_mobileapp/backend/core/__init__.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/core/apps.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/core/exceptions.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/core/tests/__init__.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/core/tests/test_exceptions.py`
- Modify: `/Users/mac/projects/jango_mobileapp/backend/backend/settings.py`

- [ ] **Step 1: Write the failing test**

`core/tests/test_exceptions.py`:
```python
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from core.exceptions import custom_exception_handler


class CustomExceptionHandlerTests(SimpleTestCase):
    def test_wraps_validation_error_response(self):
        exc = ValidationError({"phone": ["This field is required."]})
        response = custom_exception_handler(exc, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {"errors": {"phone": ["This field is required."]}, "status_code": 400},
        )
```

`core/__init__.py`: empty file.
`core/tests/__init__.py`: empty file.

- [ ] **Step 2: Add `core` to INSTALLED_APPS so it's discoverable, run test to verify it fails**

Modify `settings.py` `INSTALLED_APPS` list, adding `"core",` after `"django.contrib.staticfiles",`.

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test core`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.exceptions'` (or `apps.py` missing error first — add `core/apps.py` below if Django complains about the app config first).

`core/apps.py`:
```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
```

- [ ] **Step 3: Write the implementation**

`core/exceptions.py`:
```python
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "errors": response.data,
            "status_code": response.status_code,
        }
    return response
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test core`
Expected: `OK` (1 test passes).

- [ ] **Step 5: Wire up DRF, JWT, CORS, drf-spectacular, django-filter in settings.py**

Add `from datetime import timedelta` near the top (after the `import environ` line).

Replace the `INSTALLED_APPS` list with:
```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "django_filters",
    "core",
]
```

Replace the `MIDDLEWARE` list with:
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

Append at the end of the file (after `DEFAULT_AUTO_FIELD`):
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
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=60)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Jango Mobile API",
    "DESCRIPTION": "Jumia UG-style e-commerce API for the Jango Mobile app.",
    "VERSION": "0.1.0",
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
```

- [ ] **Step 6: Verify configuration is valid**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py check`
Expected: `System check identified no issues (0 silenced).`

---

### Task 5: Accounts app skeleton + phone validator (TDD)

**Files:**
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/__init__.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/apps.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/validators.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/tests/__init__.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/tests/test_validators.py`
- Modify: `/Users/mac/projects/jango_mobileapp/backend/backend/settings.py`

- [ ] **Step 1: Write the failing tests**

`accounts/tests/test_validators.py`:
```python
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from accounts.validators import normalize_uganda_phone, validate_uganda_phone


class NormalizeUgandaPhoneTests(SimpleTestCase):
    def test_local_format_normalizes_to_e164(self):
        self.assertEqual(normalize_uganda_phone("0771234567"), "+256771234567")

    def test_already_e164_format_stays_normalized(self):
        self.assertEqual(normalize_uganda_phone("+256771234567"), "+256771234567")

    def test_country_code_without_plus_normalizes(self):
        self.assertEqual(normalize_uganda_phone("256771234567"), "+256771234567")

    def test_strips_spaces_and_dashes(self):
        self.assertEqual(normalize_uganda_phone("077 123-4567"), "+256771234567")

    def test_invalid_prefix_raises(self):
        with self.assertRaises(ValidationError):
            normalize_uganda_phone("0871234567")

    def test_too_short_raises(self):
        with self.assertRaises(ValidationError):
            normalize_uganda_phone("12345")

    def test_none_raises(self):
        with self.assertRaises(ValidationError):
            normalize_uganda_phone(None)


class ValidateUgandaPhoneTests(SimpleTestCase):
    def test_valid_number_passes(self):
        validate_uganda_phone("0771234567")

    def test_invalid_number_raises(self):
        with self.assertRaises(ValidationError):
            validate_uganda_phone("not-a-phone")
```

`accounts/__init__.py`, `accounts/tests/__init__.py`: empty files.

`accounts/apps.py`:
```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
```

Add `"accounts",` to `INSTALLED_APPS` in `settings.py`, after `"core",`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts`
Expected: FAIL with `ModuleNotFoundError: No module named 'accounts.validators'`.

- [ ] **Step 3: Write the implementation**

`accounts/validators.py`:
```python
import re

from django.core.exceptions import ValidationError

UGANDA_PHONE_REGEX = re.compile(r"^(?:\+?256|0)(7\d{8})$")


def normalize_uganda_phone(value):
    if value is None:
        raise ValidationError("Phone number is required.")
    cleaned = value.strip().replace(" ", "").replace("-", "")
    match = UGANDA_PHONE_REGEX.match(cleaned)
    if not match:
        raise ValidationError(
            "Enter a valid Uganda phone number, e.g. 0771234567 or +256771234567."
        )
    return f"+256{match.group(1)}"


def validate_uganda_phone(value):
    normalize_uganda_phone(value)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts`
Expected: `OK` (9 tests pass).

---

### Task 6: User model + manager (TDD, first migration)

**Files:**
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/managers.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/models.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/tests/test_models.py`
- Modify: `/Users/mac/projects/jango_mobileapp/backend/backend/settings.py`

- [ ] **Step 1: Write the failing tests**

`accounts/tests/test_models.py`:
```python
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import User


class UserModelTests(TestCase):
    def test_create_user_normalizes_phone(self):
        user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.assertEqual(user.phone, "+256771234567")
        self.assertTrue(user.check_password("strongpass123"))
        self.assertFalse(user.is_staff)

    def test_create_superuser_sets_staff_flags(self):
        user = User.objects.create_superuser(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_duplicate_phone_raises_integrity_error(self):
        User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                phone="+256771234567",
                password="anotherpass123",
                first_name="Grace",
                last_name="Hopper",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_models`
Expected: FAIL with `ModuleNotFoundError: No module named 'accounts.models'`.

- [ ] **Step 3: Write the implementation**

`accounts/managers.py`:
```python
from django.contrib.auth.base_user import BaseUserManager

from .validators import normalize_uganda_phone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("Users must have a phone number.")
        phone = normalize_uganda_phone(phone)
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(phone, password, **extra_fields)
```

`accounts/models.py`:
```python
from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager
from .validators import normalize_uganda_phone, validate_uganda_phone


class User(AbstractUser):
    username = None
    phone = models.CharField(
        max_length=13, unique=True, validators=[validate_uganda_phone]
    )
    email = models.EmailField(blank=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = normalize_uganda_phone(self.phone)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.phone
```

Add `AUTH_USER_MODEL = "accounts.User"` to `settings.py`, directly below `DATABASES`.

- [ ] **Step 4: Create and run the first migration**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py makemigrations accounts`
Expected: creates `accounts/migrations/0001_initial.py` defining the `User` model.

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py migrate`
Expected: applies all app migrations (admin, auth, contenttypes, sessions, accounts, token_blacklist) with no errors.

- [ ] **Step 5: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_models`
Expected: `OK` (3 tests pass).

---

### Task 7: Address model (TDD)

**Files:**
- Modify: `/Users/mac/projects/jango_mobileapp/backend/accounts/models.py`
- Modify: `/Users/mac/projects/jango_mobileapp/backend/accounts/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

Append to `accounts/tests/test_models.py`:
```python
from accounts.models import Address


class AddressModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )

    def test_first_address_is_auto_default(self):
        address = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        self.assertTrue(address.is_default)

    def test_recipient_phone_is_normalized(self):
        address = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        self.assertEqual(address.recipient_phone, "+256771234567")

    def test_new_default_unsets_previous_default(self):
        first = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        second = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0779876543",
            city_district="Kampala",
            street_area="Nakasero",
            is_default=True,
        )
        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)
```

Add the import `from accounts.models import Address` at the top of the file alongside the existing `from accounts.models import User` (or combine into one `from accounts.models import Address, User`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_models`
Expected: FAIL with `ImportError: cannot import name 'Address' from 'accounts.models'`.

- [ ] **Step 3: Write the implementation**

Append to `accounts/models.py`:
```python
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=13, validators=[validate_uganda_phone])
    city_district = models.CharField(max_length=100)
    street_area = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.recipient_name} - {self.city_district}"

    def save(self, *args, **kwargs):
        if self.recipient_phone:
            self.recipient_phone = normalize_uganda_phone(self.recipient_phone)

        is_first_address = self._state.adding and not Address.objects.filter(
            user=self.user
        ).exists()
        if is_first_address:
            self.is_default = True

        super().save(*args, **kwargs)

        if self.is_default:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(
                is_default=False
            )
```

- [ ] **Step 4: Create and run the migration**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py makemigrations accounts`
Expected: creates `accounts/migrations/0002_address.py`.

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py migrate`
Expected: applies the new migration with no errors.

- [ ] **Step 5: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_models`
Expected: `OK` (6 tests pass).

---

### Task 8: Django Admin registration

**Files:**
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/admin.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/tests/test_admin.py`

- [ ] **Step 1: Write the failing tests**

`accounts/tests/test_admin.py`:
```python
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User


class UserAdminAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_superuser(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.customer = User.objects.create_user(
            phone="0709876543",
            password="strongpass123",
            first_name="Grace",
            last_name="Hopper",
        )

    def test_staff_can_access_user_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_redirected_from_admin(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 302)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_admin`
Expected: FAIL with `NoReverseMatch` (User not registered in admin).

- [ ] **Step 3: Write the implementation**

`accounts/admin.py`:
```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Address, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["phone"]
    list_display = ["phone", "first_name", "last_name", "is_staff", "is_active"]
    search_fields = ["phone", "first_name", "last_name", "email"]
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["user", "recipient_name", "city_district", "is_default"]
    search_fields = ["recipient_name", "city_district", "user__phone"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_admin`
Expected: `OK` (2 tests pass).

---

### Task 9: Register endpoint (TDD)

**Files:**
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/serializers.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/views.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/urls.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/tests/test_register.py`
- Modify: `/Users/mac/projects/jango_mobileapp/backend/backend/urls.py`

- [ ] **Step 1: Write the failing tests**

`accounts/tests/test_register.py`:
```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User


class RegisterViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("register")

    def test_register_creates_user_and_returns_tokens(self):
        response = self.client.post(
            self.url,
            {
                "phone": "0771234567",
                "password": "strongpass123",
                "first_name": "Ada",
                "last_name": "Lovelace",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(User.objects.filter(phone="+256771234567").exists())

    def test_duplicate_phone_returns_400(self):
        User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        response = self.client.post(
            self.url,
            {
                "phone": "0771234567",
                "password": "anotherpass123",
                "first_name": "Grace",
                "last_name": "Hopper",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_returns_400(self):
        response = self.client.post(
            self.url,
            {
                "phone": "0771234567",
                "password": "123",
                "first_name": "Ada",
                "last_name": "Lovelace",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_first_name_returns_400(self):
        response = self.client.post(
            self.url,
            {"phone": "0771234567", "password": "strongpass123", "last_name": "Lovelace"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_register`
Expected: FAIL with `NoReverseMatch: 'register' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

`accounts/serializers.py`:
```python
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["phone", "password", "first_name", "last_name"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
```

`accounts/views.py`:
```python
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED,
        )
```

`accounts/urls.py`:
```python
from django.urls import path

from .views import RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
]
```

Modify `backend/urls.py` to:
```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_register`
Expected: `OK` (4 tests pass).

---

### Task 10: Login + Refresh endpoints (TDD)

**Files:**
- Modify: `/Users/mac/projects/jango_mobileapp/backend/accounts/urls.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/tests/test_login.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/tests/test_refresh.py`

Since `User.USERNAME_FIELD = "phone"`, SimpleJWT's stock `TokenObtainPairSerializer` does accept `phone` as the field name. **However, that alone is not sufficient**: `ModelBackend.authenticate()` looks phone up as a raw, unnormalized value, while `User.save()` always stores it normalized to E.164 (`+256...`). A user who registers with a local-format number (`"0771234567"`) cannot log back in with that same string unless something normalizes it first. This was caught by running the tests below against the stock view (not by inspection) — implement a `PhoneTokenObtainPairSerializer(TokenObtainPairSerializer)` that normalizes `attrs[self.username_field]` before calling `super().validate(attrs)` (falling back to the raw value on a normalization error, so malformed input still degrades to a generic 401 rather than leaking a validation message), and a thin `LoginView(TokenObtainPairView)` using it. Do not wire the stock `TokenObtainPairView` directly.

- [ ] **Step 1: Write the failing tests**

`accounts/tests/test_login.py`:
```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User


class LoginViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("login")
        self.user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )

    def test_valid_credentials_return_tokens(self):
        response = self.client.post(
            self.url, {"phone": "0771234567", "password": "strongpass123"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_wrong_password_returns_401(self):
        response = self.client.post(
            self.url, {"phone": "0771234567", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_phone_returns_401(self):
        response = self.client.post(
            self.url, {"phone": "0700000000", "password": "strongpass123"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

`accounts/tests/test_refresh.py`:
```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


class RefreshViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("refresh")
        self.user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )

    def test_valid_refresh_returns_new_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(self.url, {"refresh": str(refresh)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_reused_refresh_token_returns_401(self):
        refresh = RefreshToken.for_user(self.user)
        refresh_str = str(refresh)
        first_response = self.client.post(self.url, {"refresh": refresh_str})
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        second_response = self.client.post(self.url, {"refresh": refresh_str})
        self.assertEqual(second_response.status_code, status.HTTP_401_UNAUTHORIZED)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_login accounts.tests.test_refresh`
Expected: FAIL with `NoReverseMatch` for `login`/`refresh`.

- [ ] **Step 3: Write the implementation**

Replace `accounts/urls.py` with:
```python
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh"),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_login accounts.tests.test_refresh`
Expected: `OK` (5 tests pass).

---

### Task 11: Me endpoint (TDD)

**Files:**
- Modify: `/Users/mac/projects/jango_mobileapp/backend/accounts/serializers.py`
- Modify: `/Users/mac/projects/jango_mobileapp/backend/accounts/views.py`
- Modify: `/Users/mac/projects/jango_mobileapp/backend/accounts/urls.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/tests/test_me.py`

- [ ] **Step 1: Write the failing tests**

`accounts/tests/test_me.py`:
```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User


class MeViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("me")
        self.user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )

    def test_unauthenticated_request_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_get_returns_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["phone"], "+256771234567")

    def test_authenticated_patch_updates_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"first_name": "Grace"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Grace")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_me`
Expected: FAIL with `NoReverseMatch: 'me' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Append to `accounts/serializers.py`:
```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "email", "first_name", "last_name"]
        read_only_fields = ["id", "phone"]
```

Append to `accounts/views.py`:
```python
from .serializers import UserSerializer


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
```
(Add `UserSerializer` to the existing `from .serializers import RegisterSerializer` line instead of a new import if preferred — keep a single import line: `from .serializers import RegisterSerializer, UserSerializer`.)

Replace `accounts/urls.py` with:
```python
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import MeView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="me"),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_me`
Expected: `OK` (3 tests pass).

---

### Task 12: Addresses CRUD endpoint (TDD)

**Files:**
- Modify: `/Users/mac/projects/jango_mobileapp/backend/accounts/serializers.py`
- Modify: `/Users/mac/projects/jango_mobileapp/backend/accounts/views.py`
- Modify: `/Users/mac/projects/jango_mobileapp/backend/accounts/urls.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/accounts/tests/test_addresses.py`

- [ ] **Step 1: Write the failing tests**

`accounts/tests/test_addresses.py`:
```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Address, User


class AddressViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.other_user = User.objects.create_user(
            phone="0709876543",
            password="strongpass123",
            first_name="Grace",
            last_name="Hopper",
        )
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("address-list")

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_address_scoped_to_user(self):
        response = self.client.post(
            self.list_url,
            {
                "recipient_name": "Ada Lovelace",
                "recipient_phone": "0771234567",
                "city_district": "Kampala",
                "street_area": "Kololo",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Address.objects.get(pk=response.data["id"]).user, self.user)

    def test_list_only_returns_own_addresses(self):
        Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        Address.objects.create(
            user=self.other_user,
            recipient_name="Grace Hopper",
            recipient_phone="0709876543",
            city_district="Entebbe",
            street_area="Main St",
        )
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 1)

    def test_cannot_retrieve_another_users_address(self):
        other_address = Address.objects.create(
            user=self.other_user,
            recipient_name="Grace Hopper",
            recipient_phone="0709876543",
            city_district="Entebbe",
            street_area="Main St",
        )
        detail_url = reverse("address-detail", args=[other_address.pk])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_set_default_switches_default_address(self):
        first = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        second = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Nakasero",
        )
        set_default_url = reverse("address-set-default", args=[second.pk])
        response = self.client.post(set_default_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_addresses`
Expected: FAIL with `NoReverseMatch: 'address-list' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Append to `accounts/serializers.py`:
```python
from .models import Address


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "recipient_name",
            "recipient_phone",
            "city_district",
            "street_area",
            "landmark",
            "is_default",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
```

Append to `accounts/views.py`:
```python
from rest_framework import viewsets
from rest_framework.decorators import action

from .models import Address
from .serializers import AddressSerializer


class AddressViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        address = self.get_object()
        address.is_default = True
        address.save()
        return Response(AddressSerializer(address).data)
```
(`Response` is already imported at the top of `views.py` from Task 9 — no new import needed for it.)

Replace `accounts/urls.py` with:
```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import AddressViewSet, MeView, RegisterView

router = DefaultRouter()
router.register("addresses", AddressViewSet, basename="address")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test accounts.tests.test_addresses`
Expected: `OK` (5 tests pass).

---

### Task 13: API docs (drf-spectacular) wiring

**Files:**
- Modify: `/Users/mac/projects/jango_mobileapp/backend/backend/urls.py`
- Create: `/Users/mac/projects/jango_mobileapp/backend/core/tests/test_schema.py`

- [ ] **Step 1: Write the failing test**

`core/tests/test_schema.py`:
```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class SchemaEndpointTests(APITestCase):
    def test_schema_endpoint_returns_200(self):
        response = self.client.get(reverse("schema"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test core.tests.test_schema`
Expected: FAIL with `NoReverseMatch: 'schema' is not a registered namespace`.

- [ ] **Step 3: Write the implementation**

Replace `backend/urls.py` with:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test core.tests.test_schema`
Expected: `OK` (1 test passes).

---

### Task 14: Full test suite run

**Files:** none

- [ ] **Step 1: Run the entire suite**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py test`
Expected: `OK` — all tests across `core` and `accounts` pass (33 tests total: 1 core exception + 1 schema + 9 validator + 6 model + 2 admin + 4 register + 3 login + 2 refresh + 3 me + 5 addresses).

- [ ] **Step 2: Final config sanity check**

Run: `/Users/mac/projects/jango_mobileapp/.venv/bin/python /Users/mac/projects/jango_mobileapp/backend/manage.py check`
Expected: `System check identified no issues (0 silenced).`
