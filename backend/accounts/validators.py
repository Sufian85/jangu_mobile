import re

from django.core.exceptions import ValidationError

UGANDA_PHONE_REGEX = re.compile(r"^(?:\+?256|0)(7\d{8})$")


def normalize_uganda_phone(value):
    if value is None:
        raise ValidationError("Phone number is required.")
    cleaned = value.strip().replace(" ", "").replace("-", "")
    match = UGANDA_PHONE_REGEX.match(cleaned)
    if not match:
        raise ValidationError(
            "Enter a valid Uganda phone number, e.g. 0771234567 or +256771234567."
        )
    return f"+256{match.group(1)}"


def validate_uganda_phone(value):
    normalize_uganda_phone(value)
