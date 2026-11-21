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

    def test_patch_rejects_blank_first_name(self):
        # format="json" matters here: multipart (the test client's default)
        # drops empty-string fields entirely, which would make this test
        # pass for the wrong reason (field just absent, nothing to reject).
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"first_name": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ada")

    def test_phone_is_read_only(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"phone": "0700000000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+256771234567")

    def test_put_not_allowed(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, {"first_name": "Grace"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
