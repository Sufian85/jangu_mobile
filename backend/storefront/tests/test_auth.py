from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegisterTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        r = self.client.post(reverse("storefront:register"), {
            "phone": "0771234567", "first_name": "Ada", "last_name": "Lovelace",
            "password1": "s3cure-pass-99", "password2": "s3cure-pass-99",
        })
        self.assertRedirects(r, reverse("storefront:home"))
        user = User.objects.get()
        self.assertEqual(user.phone, "+256771234567")
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_duplicate_phone_shows_error(self):
        User.objects.create_user(phone="+256771234567", password="x", first_name="A", last_name="B")
        r = self.client.post(reverse("storefront:register"), {
            "phone": "+256771234567", "first_name": "Ada", "last_name": "L",
            "password1": "s3cure-pass-99", "password2": "s3cure-pass-99",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "already exists")

    def test_weak_password_rejected(self):
        r = self.client.post(reverse("storefront:register"), {
            "phone": "0771234567", "first_name": "Ada", "last_name": "L",
            "password1": "12345678", "password2": "12345678",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "too common")

    def test_password_mismatch_rejected(self):
        r = self.client.post(reverse("storefront:register"), {
            "phone": "0771234567", "first_name": "Ada", "last_name": "L",
            "password1": "s3cure-pass-99", "password2": "different-99",
        })
        self.assertContains(r, "do not match", status_code=200)

    def test_register_page_labels_sit_above_styled_fields(self):
        r = self.client.get(reverse("storefront:register"))
        self.assertContains(r, 'class="auth-card"')
        self.assertContains(r, '<label for="id_phone">Phone</label>')
        self.assertContains(r, '<label for="id_password2">Confirm password</label>')

    def test_field_error_marks_its_field(self):
        r = self.client.post(reverse("storefront:register"), {
            "phone": "not-a-phone", "first_name": "Ada", "last_name": "L",
            "password1": "s3cure-pass-99", "password2": "s3cure-pass-99",
        })
        self.assertContains(r, '<div class="field has-error">')
        self.assertContains(r, "valid Uganda phone")


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone="+256771234567", password="s3cure-pass-99", first_name="Ada", last_name="L"
        )

    def test_login_with_local_format_phone(self):
        r = self.client.post(reverse("storefront:login"),
                             {"username": "0771234567", "password": "s3cure-pass-99"})
        self.assertRedirects(r, reverse("storefront:home"))

    def test_login_page_labels_sit_above_styled_fields(self):
        r = self.client.get(reverse("storefront:login"))
        self.assertContains(r, 'class="auth-card"')
        self.assertContains(r, '<div class="field">')
        self.assertContains(r, '<label for="id_username">Phone</label>')
        self.assertContains(r, '<label for="id_password">Password</label>')

    def test_failed_login_shows_the_error_in_the_card(self):
        r = self.client.post(reverse("storefront:login"), {"username": "0771234567", "password": "wrong"})
        self.assertContains(r, 'class="errorlist nonfield"')
        self.assertContains(r, "correct phone")

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("storefront:logout")).status_code, 405)
        r = self.client.post(reverse("storefront:logout"))
        self.assertRedirects(r, reverse("storefront:home"))
        self.assertNotIn("_auth_user_id", self.client.session)
