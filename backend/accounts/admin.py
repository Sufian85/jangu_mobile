from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.core.exceptions import ValidationError

from .models import Address, User
from .validators import normalize_uganda_phone


class PhoneAdminAuthenticationForm(AdminAuthenticationForm):
    """Admin login form: normalise the phone so a number typed as ``0771…``
    or ``+256771…`` matches the stored ``+256771…`` value (ModelBackend looks
    the phone up raw). Keeps AdminAuthenticationForm's staff-only check."""

    def clean(self):
        raw = self.cleaned_data.get("username")
        if raw:
            try:
                self.cleaned_data["username"] = normalize_uganda_phone(raw)
            except ValidationError:
                # Malformed phone: fall through to the generic invalid-login error.
                pass
        return super().clean()


admin.site.login_form = PhoneAdminAuthenticationForm


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
