from django.db import IntegrityError
from django.test import TestCase

from accounts.models import Address, User


class UserModelTests(TestCase):
    def test_create_user_normalizes_phone(self):
        user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.assertEqual(user.phone, "+256771234567")
        self.assertTrue(user.check_password("strongpass123"))
        self.assertFalse(user.is_staff)

    def test_create_superuser_sets_staff_flags(self):
        user = User.objects.create_superuser(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_duplicate_phone_raises_integrity_error(self):
        User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                phone="+256771234567",
                password="anotherpass123",
                first_name="Grace",
                last_name="Hopper",
            )


class AddressModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )

    def test_first_address_is_auto_default(self):
        address = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        self.assertTrue(address.is_default)

    def test_recipient_phone_is_normalized(self):
        address = Address.objects.create(
            user=self.user,
            recipient_name="Ada Lovelace",
            recipient_phone="0771234567",
            city_district="Kampala",
            street_area="Kololo",
        )
        self.assertEqual(address.recipient_phone, "+256771234567")

    def test_new_default_unsets_previous_default(self):
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
            recipient_phone="0779876543",
            city_district="Kampala",
            street_area="Nakasero",
            is_default=True,
        )
        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)
