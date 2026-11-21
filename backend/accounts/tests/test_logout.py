from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


class LogoutViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("logout")
        self.user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )

    def test_unauthenticated_request_returns_401(self):
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(self.url, {"refresh": str(refresh)})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self):
        self.client.force_authenticate(user=self.user)
        refresh = RefreshToken.for_user(self.user)
        response = self.client.post(self.url, {"refresh": str(refresh)})
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_url = reverse("refresh")
        replay = self.client.post(refresh_url, {"refresh": str(refresh)})
        self.assertEqual(replay.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_garbage_refresh_returns_400_not_500(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"refresh": "not-a-real-token"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
