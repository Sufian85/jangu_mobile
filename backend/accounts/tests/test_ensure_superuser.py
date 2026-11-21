import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from accounts.models import User

ENV = {
    "DJANGO_SUPERUSER_PHONE": "0771234567",
    "DJANGO_SUPERUSER_PASSWORD": "strongpass123",
    "DJANGO_SUPERUSER_FIRST_NAME": "Ada",
    "DJANGO_SUPERUSER_LAST_NAME": "Lovelace",
}


class EnsureSuperuserCommandTests(TestCase):
    def test_skips_when_env_missing(self):
        out = StringIO()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DJANGO_SUPERUSER_PHONE", None)
            os.environ.pop("DJANGO_SUPERUSER_PASSWORD", None)
            call_command("ensure_superuser", stdout=out)
        self.assertIn("skipping", out.getvalue().lower())
        self.assertEqual(User.objects.count(), 0)

    def test_creates_superuser_from_env(self):
        out = StringIO()
        with mock.patch.dict(os.environ, ENV):
            call_command("ensure_superuser", stdout=out)
        user = User.objects.get()
        self.assertEqual(user.phone, "+256771234567")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password("strongpass123"))
        self.assertEqual(user.first_name, "Ada")
        self.assertEqual(user.last_name, "Lovelace")

    def test_idempotent_when_user_exists(self):
        with mock.patch.dict(os.environ, ENV):
            call_command("ensure_superuser", stdout=StringIO())
            out = StringIO()
            call_command("ensure_superuser", stdout=out)
        self.assertEqual(User.objects.count(), 1)
        self.assertIn("already exists", out.getvalue().lower())

    def test_invalid_phone_skips_without_creating(self):
        out = StringIO()
        bad = {**ENV, "DJANGO_SUPERUSER_PHONE": "12345"}
        with mock.patch.dict(os.environ, bad):
            call_command("ensure_superuser", stdout=out, stderr=out)
        self.assertEqual(User.objects.count(), 0)
        self.assertIn("invalid", out.getvalue().lower())
