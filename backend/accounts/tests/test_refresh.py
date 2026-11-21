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
