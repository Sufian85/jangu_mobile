from django.utils.text import slugify

# Display order for variant attributes. Postgres jsonb does not keep the order
# keys were entered in, so labels cannot rely on dict order.
ATTRIBUTE_ORDER = {
    key: rank
    for rank, key in enumerate(["processor", "ram", "storage", "size", "connectivity", "color"])
}


def attribute_values(attributes):
    """The non-empty values of `attributes`, in display order."""
    if not isinstance(attributes, dict):
        return []
    keys = sorted(attributes, key=lambda key: (ATTRIBUTE_ORDER.get(key, len(ATTRIBUTE_ORDER)), key))
    return [str(attributes[key]) for key in keys if attributes[key] not in (None, "")]


def variant_label(attributes):
    """`{"storage": "128GB", "color": "Black"}` -> `128GB / Black`; empty -> `Standard`."""
    return " / ".join(attribute_values(attributes)) or "Standard"


def unique_slugify(model, value, instance_pk=None, field="slug", max_length=None):
    """Return a slug for `value` that is unique among `model`'s existing rows."""
    base_slug = slugify(value)
    if max_length:
        # Leave room for a "-2" style suffix.
        base_slug = base_slug[:max_length - 4].rstrip("-")
    candidate = base_slug
    suffix = 2
    queryset = model.objects.all()
    if instance_pk is not None:
        queryset = queryset.exclude(pk=instance_pk)
    while queryset.filter(**{field: candidate}).exists():
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate
