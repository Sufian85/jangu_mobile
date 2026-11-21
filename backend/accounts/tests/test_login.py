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

    def test_malformed_phone_returns_401_not_validation_error(self):
        # Exercises PhoneTokenObtainPairSerializer's except-and-fall-back
        # path: a phone that fails normalize_uganda_phone() should still
        # degrade to a generic 401, not leak a validation error or crash.
        response = self.client.post(
            self.url, {"phone": "not-a-phone", "password": "strongpass123"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
