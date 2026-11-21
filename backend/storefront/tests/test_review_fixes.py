import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from catalogue.models import ProductImage
from catalogue.tests.helpers import make_test_image
from storefront.templatetags.storefront_extras import variant_label
from storefront.tests.factories import make_category, make_product


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PriceFilterCoercionTests(TestCase):
    def test_non_numeric_price_params_do_not_500(self):
        phones = make_category("Smartphones")
        make_product(title="Galaxy S23", category=phones, brand="Samsung", price="2800000")
        for params in ({"price_min": "abc"}, {"price_max": "!!"}, {"price_min": "", "price_max": "  "}):
            r = self.client.get(reverse("storefront:category", args=[phones.slug]), params)
            self.assertEqual(r.status_code, 200, params)
        r = self.client.get(reverse("storefront:search"), {"q": "gal", "price_min": "xyz"})
        self.assertEqual(r.status_code, 200)

    def test_numeric_price_filter_still_applies(self):
        phones = make_category("Smartphones")
        make_product(title="Cheap", category=phones, brand="A", price="500000")
        make_product(title="Pricey", category=phones, brand="B", price="9000000")
        r = self.client.get(reverse("storefront:category", args=[phones.slug]), {"price_max": "1000000"})
        self.assertContains(r, "Cheap")
        self.assertNotContains(r, "Pricey")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PrimaryImageTests(TestCase):
    def test_selector_orders_primary_image_first(self):
        from storefront import selectors
        p = make_product(title="Pixel 9", brand="Google", price="3500000")  # first image auto-primary
        second = ProductImage.objects.create(product=p, image=make_test_image("second.png"))
        second.is_primary = True
        second.save()  # unsets the other, per model
        got = selectors.active_products().get(pk=p.pk)
        first_rendered = list(got.images.all())[0]
        self.assertEqual(first_rendered.pk, second.pk)
        self.assertTrue(first_rendered.is_primary)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class MediaServingTests(TestCase):
    def test_uploaded_media_url_is_served(self):
        # test client runs with DEBUG=False; media must still resolve
        p = make_product(title="Watch", brand="Apple", price="1600000")
        url = p.images.first().image.url
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)


class VariantLabelFixTests(TestCase):
    def test_skips_none_and_blank(self):
        self.assertEqual(variant_label({"size": "41mm", "gps": None, "note": ""}), "41mm")

    def test_all_blank_returns_standard(self):
        self.assertEqual(variant_label({"a": None, "b": ""}), "Standard")
