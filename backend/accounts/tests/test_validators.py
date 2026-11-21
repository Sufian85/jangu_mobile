from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from accounts.validators import normalize_uganda_phone, validate_uganda_phone


class NormalizeUgandaPhoneTests(SimpleTestCase):
    def test_local_format_normalizes_to_e164(self):
        self.assertEqual(normalize_uganda_phone("0771234567"), "+256771234567")

    def test_already_e164_format_stays_normalized(self):
        self.assertEqual(normalize_uganda_phone("+256771234567"), "+256771234567")

    def test_country_code_without_plus_normalizes(self):
        self.assertEqual(normalize_uganda_phone("256771234567"), "+256771234567")

    def test_strips_spaces_and_dashes(self):
        self.assertEqual(normalize_uganda_phone("077 123-4567"), "+256771234567")

    def test_invalid_prefix_raises(self):
        with self.assertRaises(ValidationError):
            normalize_uganda_phone("0871234567")

    def test_too_short_raises(self):
        with self.assertRaises(ValidationError):
            normalize_uganda_phone("12345")

    def test_none_raises(self):
        with self.assertRaises(ValidationError):
            normalize_uganda_phone(None)


class ValidateUgandaPhoneTests(SimpleTestCase):
    def test_valid_number_passes(self):
        validate_uganda_phone("0771234567")

    def test_invalid_number_raises(self):
        with self.assertRaises(ValidationError):
            validate_uganda_phone("not-a-phone")
