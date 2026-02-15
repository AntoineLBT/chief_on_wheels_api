from datetime import datetime

from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.tests.fixtures import OrderFixture


class TestOrderList(TestCase, OrderFixture):

    client_class = APIClient

    def test_order_list_require_authentication(self):
        response = self.client.get("/restaurants/1/shifts/1/orders/")
        assert response.status_code == 401

    def test_order_list(self):
        owner = self.any_user()
        restaurant = self.any_restaurant(owner)
        order = self.any_order(restaurant)
        self.any_order()
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


class TestOrderCreate(TestCase, OrderFixture):

    client_class = APIClient

    def test_order_create(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        shift = self.any_shift(restaurant)
        token = self.any_token(user)

        data = {
            "shift": shift.pk,
            "customer_name": "Patrick",
            "picking_time": datetime.now(),
        }

        response = self.client.post(
            f"/restaurants/{restaurant.pk}/shifts/{shift.pk}/orders/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 201
        assert "customer_name" in response.json()
        assert response.json()["shift"] == shift.pk

    def test_order_create__onwer_only(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        shift = self.any_shift(restaurant)

        data = {
            "shift": shift.pk,
            "customer_name": "Patrick",
            "picking_time": datetime.now(),
        }

        user = self.any_user()
        token = self.any_token(user)
        response = self.client.post(
            f"/restaurants/{restaurant.pk}/shifts/{shift.pk}/orders/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404


class TestOrderUpdate(TestCase, OrderFixture):

    client_class = APIClient

    def test_order_update(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        order = self.any_order(restaurant)
        token = self.any_token(user)

        data = {
            "shift": order.shift.pk,
            "customer_name": "Bernardo",
            "picking_time": datetime.now(),
        }

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/shifts/{order.shift.pk}/orders/{order.pk}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        assert response.json()["customer_name"] == "Bernardo"

    def test_order_update__onwer_only(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        order = self.any_order(restaurant)

        data = {
            "shift": order.shift.pk,
            "customer_name": "Patrick",
            "picking_time": datetime.now(),
        }

        user = self.any_user()
        token = self.any_token(user)
        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/shifts/{order.shift.pk}/orders/{order.pk}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404


class TestOrderDelete(TestCase, OrderFixture):

    client_class = APIClient

    def test_order_delete(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        order = self.any_order(restaurant)
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/shifts/{order.shift.pk}/orders/{order.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 204

    def test_order_delete__onwer_only(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        order = self.any_order(restaurant)

        user = self.any_user()
        token = self.any_token(user)
        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/shifts/{order.shift.pk}/orders/{order.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404
