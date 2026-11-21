from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class SchemaEndpointTests(APITestCase):
    def test_schema_endpoint_returns_200(self):
        response = self.client.get(reverse("schema"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SwaggerUIEndpointTests(APITestCase):
    def test_swagger_ui_endpoint_returns_200_html(self):
        response = self.client.get(reverse("swagger-ui"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response["Content-Type"])
