from decimal import Decimal, InvalidOperation

from django import template

from catalogue.utils import variant_label

register = template.Library()
register.filter("variant_label", variant_label)


@register.filter
def ugx(value):
    """Format a number as `UGX 2,800,000` (no decimals)."""
    if value is None or value == "":
        return "—"
    try:
        amount = int(round(Decimal(str(value))))
    except (InvalidOperation, ValueError, TypeError):
        return "—"
    return f"UGX {amount:,}"
