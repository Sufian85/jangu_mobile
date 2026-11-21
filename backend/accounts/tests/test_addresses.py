from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Address, User


class AddressViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.other_user = User.objects.create_user(
            phone="0709876543",
            password="strongpass123",
            first_name="Grace",
            last_name="Hopper",
        )
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("address-list")

    def test_unauthenticated_request_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_address_scoped_to_user(self):
        response = self.client.post(
            self.list_url,
            {
                "recipient_name": "Ada Lovelace",
                "recipient_phone": "0771234567",
                "city_district": "Kampala",
                "street_area": "Kololo",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Address.objects.get(pk=response.data["id"]).user, self.user)

    def test_list_only_returns_own_addresses(self):
        Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        Address.objects.create(
            user=self.other_user,
            recipient_name="Grace Hopper",
            recipient_phone="0709876543",
            city_district="Entebbe",
            street_area="Main St",
        )
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 1)

    def test_cannot_retrieve_another_users_address(self):
        other_address = Address.objects.create(
            user=self.other_user,
            recipient_name="Grace Hopper",
            recipient_phone="0709876543",
            city_district="Entebbe",
            street_area="Main St",
        )
        detail_url = reverse("address-detail", args=[other_address.pk])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_set_default_switches_default_address(self):
        first = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        second = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Nakasero",
        )
        set_default_url = reverse("address-set-default", args=[second.pk])
        response = self.client.post(set_default_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

    def test_is_default_cannot_be_set_via_patch(self):
        # Task 12 deviation: is_default is read-only on AddressSerializer so
        # that default-switching can only happen through the dedicated
        # set-default action (see AddressSerializer.Meta.read_only_fields).
        # Directly PATCHing is_default=False on a user's only default address
        # would otherwise leave them with zero defaults, since Address.save()
        # only ever adds a default, never reassigns one when the current
        # default is turned off.
        #
        # Note: the first address created for a user is auto-promoted to
        # default by Address.save()'s "first address" invariant, independent
        # of anything the serializer does. To actually isolate the
        # read-only-field behavior under test, a second (non-default)
        # address is required here - otherwise this test would pass for the
        # wrong reason (the model's own invariant, not the serializer).
        first = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        second = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Nakasero",
        )
        self.assertTrue(first.is_default)
        self.assertFalse(second.is_default)

        detail_url = reverse("address-detail", args=[second.pk])
        response = self.client.patch(detail_url, {"is_default": True})
        # DRF silently drops read-only fields from a PATCH rather than
        # rejecting them, so this is deterministically 200, not an error.
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(second.is_default)
        self.assertTrue(first.is_default)

    def test_cannot_set_default_on_another_users_address(self):
        other_address = Address.objects.create(
            user=self.other_user,
            recipient_name="Grace Hopper",
            recipient_phone="0709876543",
            city_district="Entebbe",
            street_area="Main St",
        )
        set_default_url = reverse("address-set-default", args=[other_address.pk])
        response = self.client.post(set_default_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        other_address.refresh_from_db()
        self.assertTrue(other_address.is_default)  # unchanged (still its own first/only default)

    def test_deleting_default_address_promotes_a_replacement(self):
        first = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        second = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Nakasero",
        )
        self.assertTrue(first.is_default)
        self.assertFalse(second.is_default)

        detail_url = reverse("address-detail", args=[first.pk])
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        second.refresh_from_db()
        self.assertTrue(second.is_default)
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)

    def test_deleting_non_default_address_leaves_default_unchanged(self):
        first = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        second = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Nakasero",
        )
        detail_url = reverse("address-detail", args=[second.pk])
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        first.refresh_from_db()
        self.assertTrue(first.is_default)


class AccountsAPIRootViewTests(APITestCase):
    # Regression test: catalogue's staff-only API root fix (catalogue/staff_urls.py)
    # previously mutated the shared rest_framework.routers.APIRootView class
    # attribute directly, which locked down every DefaultRouter's root view
    # process-wide - including this app's own router (registered "addresses",
    # mounted at /api/auth/). A non-staff authenticated user must still be able
    # to view the accounts API root.
    def test_non_staff_can_view_accounts_api_root(self):
        user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/auth/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
