from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from restaurants.constants import OrderIngredientActionType
from restaurants.tests.fixtures import (IngredientFixture, OrderFixture,
                                        RecipeFixture)

from ....models import OrderIngredient, OrderRecipe


class TestOrderList(TestCase, OrderFixture, RecipeFixture, IngredientFixture):

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
        assert "amount" in response.json()[0]

    def test_order_list_amount(self):
        owner = self.any_user()
        restaurant = self.any_restaurant(owner)
        order = self.any_order(restaurant)
        token = self.any_token(owner)
        recipe = self.any_recipe(restaurant)
        ingredient = self.any_ingredient(with_restaurant=restaurant)
        with_extra, plain = [
            OrderRecipe.objects.create(
                order=order,
                recipe=recipe,
                unit_price=Decimal(unit_price),
                unit_cost=Decimal("3.00"),
            )
            for unit_price in ["11.00", "9.00"]
        ]
        for action_type, extra_price in [
            (OrderIngredientActionType.ADD, "1.50"),
            (OrderIngredientActionType.REMOVE, "0"),
        ]:
            OrderIngredient.objects.create(
                order_recipe=with_extra,
                ingredient=ingredient,
                action_type=action_type,
                extra_price=Decimal(extra_price),
                extra_cost=Decimal("0"),
            )

        response = self.client.get(
            f"/restaurants/{order.shift.restaurant.pk}/shifts/{order.shift.pk}/orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        # Snapshots, not the current recipe price (12.50); each line counted once.
        assert response.json()[0]["amount"] == 21.5

    def test_order_list_amount__empty_order(self):
        owner = self.any_user()
        order = self.any_order(self.any_restaurant(owner))
        token = self.any_token(owner)

        response = self.client.get(
            f"/restaurants/{order.shift.restaurant.pk}/shifts/{order.shift.pk}/orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.json()[0]["amount"] == 0


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
            "picking_time": timezone.now(),
        }

        response = self.client.post(
            f"/restaurants/{restaurant.pk}/shifts/{shift.pk}/orders/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 201
        assert "customer_name" in response.json()
        assert response.json()["shift"] == str(shift.pk)

    def test_order_create__onwer_only(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        shift = self.any_shift(restaurant)

        data = {
            "shift": shift.pk,
            "customer_name": "Patrick",
            "picking_time": timezone.now(),
        }

        user = self.any_user()
        token = self.any_token(user)
        response = self.client.post(
            f"/restaurants/{restaurant.pk}/shifts/{shift.pk}/orders/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404

    def test_order_create__foreign_shift_in_body(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        shift = self.any_shift(restaurant)
        foreign_shift = self.any_shift(self.any_restaurant())
        token = self.any_token(user)

        data = {
            "shift": foreign_shift.pk,
            "customer_name": "Patrick",
            "picking_time": timezone.now(),
        }

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
            "picking_time": timezone.now(),
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
            "picking_time": timezone.now(),
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
