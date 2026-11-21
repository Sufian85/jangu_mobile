from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminBrandingTests(TestCase):
    def test_login_page_shows_jangu_branding(self):
        response = self.client.get(reverse("admin:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jangu Mobile")

    def test_uses_project_base_site_override(self):
        response = self.client.get(reverse("admin:login"))
        self.assertTemplateUsed(response, "admin/base_site.html")
        # our override injects a brand CSS variable
        self.assertContains(response, "--header-bg: #12356E")

    def test_index_title_configured(self):
        User = get_user_model()
        User.objects.create_superuser(
            phone="+256772000000", password="adminpass123",
            first_name="Ada", last_name="Admin",
        )
        self.client.force_login(User.objects.get(phone="+256772000000"))
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, "Jangu Mobile")
