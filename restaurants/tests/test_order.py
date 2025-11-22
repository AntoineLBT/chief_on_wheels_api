from django.test import TestCase

from restaurants.tests.fixtures import OrderFixture


class TestOrderModel(TestCase, OrderFixture):

    def test_order_model(self):
        order = self.any_order()
        order.customer_name = "Bertrand"
        order.save()

        assert "Bertrand" in str(order)
