from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

# ScopedRateThrottle.THROTTLE_RATES is bound once, at class-definition time,
# to the same dict object as REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] - so
# override_settings doesn't actually reach it (DRF's reload_api_settings
# only resets api_settings' own cache, not this already-bound class attr).
# patch.dict mutates that shared dict in place instead, which does work.


class ThrottlingTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_register_is_throttled_after_limit(self):
        url = reverse("register")
        payload = {
            "phone": "0771234567",
            "password": "strongpass123",
            "first_name": "Ada",
            "last_name": "Lovelace",
        }
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"register": "1/min"}):
            first = self.client.post(url, payload)
            self.assertNotEqual(first.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

            second = self.client.post(url, {**payload, "phone": "0709876543"})
            self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_login_is_throttled_after_limit(self):
        url = reverse("login")
        payload = {"phone": "0771234567", "password": "wrongpass"}
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"login": "1/min"}):
            first = self.client.post(url, payload)
            self.assertNotEqual(first.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

            second = self.client.post(url, payload)
            self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
