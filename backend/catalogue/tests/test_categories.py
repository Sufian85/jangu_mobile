from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalogue.models import Category


class CategoryListViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("category-list")

    def test_list_returns_all_categories(self):
        electronics = Category.objects.create(name="Electronics")
        Category.objects.create(name="Phones", parent=electronics)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_includes_parent_id(self):
        electronics = Category.objects.create(name="Electronics")
        phones = Category.objects.create(name="Phones", parent=electronics)
        response = self.client.get(self.url)
        phones_row = next(row for row in response.data if row["id"] == phones.id)
        self.assertEqual(phones_row["parent"], electronics.id)

    def test_no_auth_required(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
