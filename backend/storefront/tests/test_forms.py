from django.test import TestCase

from orders.tests.factories import make_variant
from storefront.forms import AddToCartForm, UpdateCartForm


class AddToCartFormTests(TestCase):
    def test_valid_for_active_variant(self):
        v = make_variant(sku="A", stock_qty=5)
        form = AddToCartForm(data={"variant_id": v.id, "quantity": 2})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["variant"], v)
        self.assertEqual(form.cleaned_data["quantity"], 2)

    def test_rejects_unknown_variant(self):
        form = AddToCartForm(data={"variant_id": 999999, "quantity": 1})
        self.assertFalse(form.is_valid())
        self.assertIn("variant_id", form.errors)

    def test_rejects_inactive_product_variant(self):
        v = make_variant(sku="B", stock_qty=5)
        v.product.is_active = False
        v.product.save()
        form = AddToCartForm(data={"variant_id": v.id, "quantity": 1})
        self.assertFalse(form.is_valid())

    def test_quantity_must_be_positive(self):
        v = make_variant(sku="C", stock_qty=5)
        self.assertFalse(AddToCartForm(data={"variant_id": v.id, "quantity": 0}).is_valid())


class UpdateCartFormTests(TestCase):
    def test_allows_zero_for_removal(self):
        v = make_variant(sku="D", stock_qty=5)
        form = UpdateCartForm(data={"variant_id": v.id, "quantity": 0})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["quantity"], 0)

    def test_rejects_negative(self):
        v = make_variant(sku="E", stock_qty=5)
        self.assertFalse(UpdateCartForm(data={"variant_id": v.id, "quantity": -1}).is_valid())
