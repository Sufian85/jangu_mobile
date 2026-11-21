from unittest.mock import patch

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

    def test_concurrent_duplicate_phone_returns_400_not_500(self):
        # validate_phone()'s existence check narrows the duplicate-phone
        # race but can't close it on its own (two requests can both pass
        # the check before either commits). Simulate that race by forcing
        # the check to report "not found" even though a row already
        # exists, and confirm RegisterView's IntegrityError handling still
        # turns the resulting DB-level clash into a clean 400.
        User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        with patch("accounts.serializers.User.objects.filter") as mock_filter:
            mock_filter.return_value.exists.return_value = False
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
