# Jango Mobile Backend — Sub-project 1: Project Setup + Accounts (Auth/JWT)

**Status:** Approved · **Date:** 2026-07-04

## Context

Jango Mobile is a Django + DRF e-commerce backend (Jumia UG-style) with a Flutter
customer app and a Django-template staff console, per `Jangu-Mobile-Spec (1).md`.
The full backend is being built as a sequence of sub-projects following the spec's
app boundaries: **accounts (this doc) → catalogue → cart/orders → payments →
staff console**, with the Flutter app as a separate project once the API exists.

Current state: a bare `django-admin startproject` scaffold exists
(`backend/manage.py`, `backend/backend/{settings,urls,asgi,wsgi}.py`), Django
6.0.6, SQLite default DB, no apps, no third-party packages installed beyond
Django/asgiref/sqlparse.

This sub-project covers: environment-based settings, MySQL, CORS, API-docs
scaffolding, and the `accounts` app (custom User, JWT auth, addresses).
Catalogue, cart, orders, payments, and the staff console are explicitly out of
scope here.

## Goals

- Reconfigure the project for env-driven settings, MySQL, and the full
  third-party dependency set the spec calls for, without yet building
  catalogue/cart/orders/payments features.
- Custom User model keyed on Uganda phone number, used for JWT-authenticated
  customer access.
- Staff continue to use Django's existing session/admin auth, unaffected by
  the JWT changes.
- Address book (multiple saved addresses per customer).
- Everything covered by automated tests (TDD).

## Non-goals

- Catalogue, cart, orders, payments, staff console templates — later
  sub-projects.
- Flutter app — later, separate project.
- SMS/OTP phone verification — no SMS gateway in the spec's tech stack; phone
  is format-validated only.
- Email-based login — email is optional profile data, not a login credential.

## 1. Architecture & config

- `requirements.txt` pinned to `Django==5.2.*` (current LTS), replacing the
  installed 6.0.6.
- New dependencies: `djangorestframework`, `djangorestframework-simplejwt`,
  `django-cors-headers`, `django-environ`, `mysqlclient`, `drf-spectacular`,
  `django-filter`, `Pillow`.
- `backend/settings.py` rewritten to read from a `.env` file via
  `django-environ`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_NAME`,
  `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, JWT lifetimes, CORS allowed
  origins. `.env` is gitignored; a `.env.example` is committed with blank/
  placeholder values.
- `DATABASES['default']` switches to `django.db.backends.mysql`. Local MySQL
  is already installed; a dedicated `jango_db` database + `jango_user` will be
  created via SQL provided at implementation time.
- `INSTALLED_APPS` gains: `rest_framework`, `rest_framework_simplejwt`,
  `rest_framework_simplejwt.token_blacklist`, `corsheaders`,
  `drf_spectacular`, `django_filters`, plus the new `core` and `accounts`
  apps.
- `MIDDLEWARE` gains `corsheaders.middleware.CorsMiddleware` (placed high, per
  django-cors-headers docs).
- `REST_FRAMEWORK` settings: default auth classes
  (`JWTAuthentication` + `SessionAuthentication` for browsable API/admin),
  default schema class `drf_spectacular.openapi.AutoSchema`,
  `DEFAULT_FILTER_BACKENDS` including `django_filters.rest_framework.DjangoFilterBackend`
  (unused until catalogue, but configured once here).
- `drf-spectacular` wired up: `/api/schema/`, `/api/docs/` (Swagger UI).
- `core` app: house for cross-cutting pieces — currently a custom DRF
  exception handler (uniform error response shape) and any shared permission
  classes. Deliberately thin; expected to grow in later sub-projects.
- `accounts` app: custom User model, Address model, auth
  serializers/views/urls.

## 2. Data model

### User (`accounts.User`, `AUTH_USER_MODEL`)

Extends `AbstractUser`, `USERNAME_FIELD = "phone"`, `REQUIRED_FIELDS` excludes
phone (already the username).

| Field | Notes |
|---|---|
| `phone` | unique, stored normalized E.164 (`+256...`) |
| `email` | optional, blank allowed |
| `first_name`, `last_name` | required at registration |
| `is_staff`, `is_superuser`, `is_active` | from `AbstractUser`; staff-ness is `is_staff`, no separate role field |
| `date_joined` | from `AbstractUser` |

`username` field from `AbstractUser` is unused/removed (phone is the login
identifier). A custom `UserManager` implements `create_user`/`create_superuser`
keyed on phone.

**Phone validation:** a reusable validator + normalizer accepting Uganda
formats (`07XXXXXXXX`, `256XXXXXXXXX`, `+256XXXXXXXXX`) and storing as
`+256XXXXXXXXX`. Invalid formats raise a `ValidationError` at the serializer
level (register/update).

### Address (`accounts.Address`)

| Field | Notes |
|---|---|
| `user` | FK → User, `related_name="addresses"` |
| `recipient_name` | required |
| `recipient_phone` | required, same validator as User.phone |
| `city_district` | required, free text (e.g. "Kampala") |
| `street_area` | required, free text |
| `landmark` | optional free text (common for Uganda addressing) |
| `is_default` | bool, default `False` |
| `created_at` | auto |

Save logic: setting `is_default=True` on one address unsets it on the user's
other addresses (enforced in the serializer/model `save()`, transactionally).
A user's first address is auto-set as default.

Both models registered in Django Admin (`list_display`, basic search) so
staff can view/manage users per spec §7.

## 3. Auth API & JWT

Base path: `/api/auth/`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register/` | `phone, password, first_name, last_name` → creates user, returns `{access, refresh}` |
| POST | `/api/auth/login/` | `phone, password` → `{access, refresh}` (custom `TokenObtainPairSerializer` keyed on phone) |
| POST | `/api/auth/refresh/` | `refresh` → new `access` (rotation + blacklist enabled) |
| GET/PATCH | `/api/auth/me/` | view/update own profile (not phone — phone changes go through a separate future flow, out of scope now) |
| GET/POST | `/api/auth/addresses/` | list own addresses / create new |
| GET/PATCH/DELETE | `/api/auth/addresses/{id}/` | retrieve/update/delete own address |
| POST | `/api/auth/addresses/{id}/set-default/` | mark as default |

JWT settings (`SIMPLE_JWT`): `ACCESS_TOKEN_LIFETIME=60min`,
`REFRESH_TOKEN_LIFETIME=7days`, `ROTATE_REFRESH_TOKENS=True`,
`BLACKLIST_AFTER_ROTATION=True` — all overridable via env vars.

Permissions: register/login are `AllowAny`; all other `accounts` endpoints
require an authenticated request and operate only on `request.user`'s own
data (no user can see another user's addresses/profile).

CORS: `django-cors-headers` installed; `CORS_ALLOWED_ORIGINS` read from env,
empty by default (locked down until the Flutter sub-project sets a dev
origin).

Staff auth is untouched — Django admin login via session, using the same
`User` model with `is_staff=True`.

## 4. Testing

TDD throughout — tests written before the corresponding implementation.

- **Model/validator tests:** phone validator accepts valid Uganda formats and
  normalizes to E.164; rejects malformed numbers; `User` uniqueness on phone;
  `Address.save()` default-switching logic (setting a new default unsets the
  old one; first address auto-defaults).
- **API tests:**
  - Register: success; duplicate phone → 400; weak password → 400; missing
    required field → 400.
  - Login: success; wrong password → 401; unknown phone → 401.
  - Refresh: success; reused/blacklisted refresh token → 401.
  - `me`: GET/PATCH when authenticated; 401 when not.
  - Addresses: CRUD scoped to own user; 404 (not 403) when accessing another
    user's address by id; set-default flips flags correctly.
- Django Admin smoke test: staff (`is_staff=True`) can log in to `/admin/` and
  see User/Address list views; non-staff cannot.

## Open items for implementation time

- Exact `CREATE DATABASE`/`CREATE USER` MySQL statements — provided as a
  setup step, not part of this spec.
- `.env.example` committed alongside the settings rewrite.
