"""Idempotently create a superuser from environment variables.

For non-interactive deploys. Safe to run on every deploy: it no-ops when the
env vars are unset, when the phone is invalid, or when the user already exists.

Env vars:
    DJANGO_SUPERUSER_PHONE       (required to do anything)
    DJANGO_SUPERUSER_PASSWORD    (required to do anything)
    DJANGO_SUPERUSER_FIRST_NAME  (optional, default "Admin")
    DJANGO_SUPERUSER_LAST_NAME   (optional, default "User")
"""

import os

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from accounts.validators import normalize_uganda_phone


class Command(BaseCommand):
    help = "Create a superuser from DJANGO_SUPERUSER_* env vars if it does not exist."

    def handle(self, *args, **options):
        phone = os.environ.get("DJANGO_SUPERUSER_PHONE")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not phone or not password:
            self.stdout.write(
                "ensure_superuser: DJANGO_SUPERUSER_PHONE/PASSWORD not set; skipping."
            )
            return

        try:
            phone = normalize_uganda_phone(phone)
        except ValidationError:
            self.stderr.write(
                "ensure_superuser: invalid DJANGO_SUPERUSER_PHONE; skipping."
            )
            return

        user_model = get_user_model()
        if user_model.objects.filter(phone=phone).exists():
            self.stdout.write(
                f"ensure_superuser: {phone} already exists; nothing to do."
            )
            return

        user_model.objects.create_superuser(
            phone=phone,
            password=password,
            first_name=os.environ.get("DJANGO_SUPERUSER_FIRST_NAME", "Admin"),
            last_name=os.environ.get("DJANGO_SUPERUSER_LAST_NAME", "User"),
        )
        self.stdout.write(
            self.style.SUCCESS(f"ensure_superuser: created superuser {phone}.")
        )
