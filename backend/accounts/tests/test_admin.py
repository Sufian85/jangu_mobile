from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User


class UserAdminAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_superuser(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.customer = User.objects.create_user(
            phone="0709876543",
            password="strongpass123",
            first_name="Grace",
            last_name="Hopper",
        )

    def test_staff_can_access_user_changelist(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_non_staff_redirected_from_admin(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_render_add_user_form(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("admin:accounts_user_add"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_create_user_via_admin(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "phone": "0700111222",
                "first_name": "New",
                "last_name": "Staffer",
                "password1": "SuperSecret123!",
                "password2": "SuperSecret123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(phone="+256700111222")
        self.assertTrue(created.check_password("SuperSecret123!"))

    def test_staff_can_render_change_user_form(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(
            reverse("admin:accounts_user_change", args=[self.customer.pk])
        )
        self.assertEqual(response.status_code, 200)


class AdminLoginTests(TestCase):
    """Phones are stored as "+256...", but the admin login form used to hand the
    raw text to ModelBackend, so a staff user typing "0771..." was rejected."""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse("admin:login")
        self.staff_user = User.objects.create_superuser(
            phone="0771234567",
            password="strongpass123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.customer = User.objects.create_user(
            phone="0709876543",
            password="strongpass123",
            first_name="Grace",
            last_name="Hopper",
        )

    def _post_login(self, phone, password="strongpass123"):
        return self.client.post(
            self.login_url,
            {"username": phone, "password": password, "next": "/admin/"},
        )

    def test_staff_can_log_in_with_local_format_phone(self):
        response = self._post_login("0771234567")
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.staff_user.pk))

    def test_staff_can_log_in_with_international_phone(self):
        response = self._post_login("+256771234567")
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.staff_user.pk))

    def test_non_staff_cannot_log_in_with_local_format_phone(self):
        response = self._post_login("0709876543")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
