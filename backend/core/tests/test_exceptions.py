from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from core.exceptions import custom_exception_handler


class CustomExceptionHandlerTests(SimpleTestCase):
    def test_wraps_validation_error_response(self):
        exc = ValidationError({"phone": ["This field is required."]})
        response = custom_exception_handler(exc, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data,
            {"errors": {"phone": ["This field is required."]}, "status_code": 400},
        )
