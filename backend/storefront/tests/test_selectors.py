import tempfile
from decimal import Decimal

from django.test import TestCase, override_settings

from storefront import selectors
from storefront.tests.factories import make_category, make_product


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SelectorTests(TestCase):
    def setUp(self):
        self.phones = make_category("Smartphones")
        self.laptops = make_category("Laptops & Accessories")
        self.s23 = make_product(title="Galaxy S23", category=self.phones, brand="Samsung",
                                price="2800000", stock_qty=5)
        self.note = make_product(title="Note 50 Pro", category=self.phones, brand="Infinix",
                                 price="1950000", stock_qty=0)
        self.mbp = make_product(title="MacBook Air", category=self.laptops, brand="Apple",
                                price="6900000", stock_qty=3)
        make_product(title="Hidden", category=self.phones, brand="Nokia", price="100000",
                     is_active=False)

    def test_active_products_excludes_inactive(self):
        titles = set(selectors.active_products().values_list("title", flat=True))
        self.assertEqual(titles, {"Galaxy S23", "Note 50 Pro", "MacBook Air"})

    def test_annotations_min_price_and_in_stock(self):
        p = selectors.active_products().get(title="Galaxy S23")
        self.assertEqual(p.min_price, Decimal("2800000"))
        self.assertTrue(p.in_stock)
        n = selectors.active_products().get(title="Note 50 Pro")
        self.assertFalse(n.in_stock)

    def test_category_products_filter_and_sort(self):
        qs = selectors.category_products(self.phones, sort="price_asc")
        self.assertEqual([p.title for p in qs], ["Note 50 Pro", "Galaxy S23"])
        qs = selectors.category_products(self.phones, brand="samsung")
        self.assertEqual([p.title for p in qs], ["Galaxy S23"])
        qs = selectors.category_products(self.phones, in_stock=True)
        self.assertEqual([p.title for p in qs], ["Galaxy S23"])
        qs = selectors.category_products(self.phones, price_max=2000000)
        self.assertEqual([p.title for p in qs], ["Note 50 Pro"])

    def test_search_matches_title_brand_description(self):
        self.assertEqual([p.title for p in selectors.search_products("galaxy")], ["Galaxy S23"])
        self.assertEqual([p.title for p in selectors.search_products("apple")], ["MacBook Air"])
        self.assertEqual(list(selectors.search_products("nokia")), [])  # inactive excluded

    def test_related_products_same_category_excludes_self(self):
        rel = selectors.related_products(self.s23)
        self.assertIn(self.note, rel)
        self.assertNotIn(self.s23, rel)
        self.assertNotIn(self.mbp, rel)

    def test_featured_products_have_image_and_stock(self):
        featured = list(selectors.featured_products())
        self.assertIn(self.s23, featured)
        self.assertNotIn(self.note, featured)  # out of stock
