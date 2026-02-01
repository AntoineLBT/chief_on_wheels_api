from django.test import TestCase

from restaurants.tests.fixtures import OrderFixture


class TestOrderList(TestCase, OrderFixture):

    def test_order_list_require_authentication(self):
        response = self.client.get("/restaurants/1/shifts/1/orders/")
        assert response.status_code == 401

    def test_order_list(self):
        owner = self.any_user()
        restaurant = self.any_restaurant(owner)
        order = self.any_order(restaurant)
        token = self.any_token(owner)

        self.any_order()

        response = self.client.get(
            f"/restaurants/{order.shift.restaurant.pk}/shifts/{order.shift.pk}/orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert "picking_time" in response.json()[0]
        assert "customer_name" in response.json()[0]
