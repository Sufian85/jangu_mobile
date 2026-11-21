from django.test import TestCase
from django.urls import reverse

from orders.tests.factories import make_user


class OrderAdminTests(TestCase):
    def setUp(self):
        admin = make_user(phone="+256772000100", is_staff=True, is_superuser=True)
        self.client.force_login(admin)

    def test_order_changelist_loads(self):
        r = self.client.get(reverse("admin:orders_order_changelist"))
        self.assertEqual(r.status_code, 200)

    def test_orderitem_changelist_loads(self):
        r = self.client.get(reverse("admin:orders_orderitem_changelist"))
        self.assertEqual(r.status_code, 200)
