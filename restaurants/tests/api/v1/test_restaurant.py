from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.constants import OrderIngredientActionType
from restaurants.models import (FixedCharge, Ingredient, OrderIngredient,
                                OrderRecipe)
from restaurants.tests.fixtures import (FixedChargeFixture, OrderFixture,
                                        RecipeIngredientFixture,
                                        RestaurantFixture)


class TestRestaurantList(TestCase, RestaurantFixture):

    client_class = APIClient

    def test_restaurant_list_requires_authentication(self):
        response = self.client.get("/restaurants/")
        assert response.status_code == 401

    def test_restaurant_list(self):
        user = self.any_user()
        user.username = "TestUser"
        user.save()
        restaurant = self.any_restaurant(user)
        restaurant.name = "MyTestaurant"
        restaurant.save()

        self.any_restaurant()

        token = self.any_token(user)

        response = self.client.get(
            "/restaurants/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "MyTestaurant"


class TestRestaurantCreate(TestCase, RestaurantFixture):

    client_class = APIClient

    def test_restaurant_create(self):

        user = self.any_user()
        token = self.any_token(user)

        data = {"name": "NewRestaurant"}

        response = self.client.post(
            "/restaurants/", data=data, HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        assert response.status_code == 201
        assert response.json()["name"] == "NewRestaurant"

    def test_restaurant_create__vat_rate_defaults_to_zero(self):
        user = self.any_user()
        token = self.any_token(user)

        response = self.client.post(
            "/restaurants/",
            data={"name": "NewRestaurant"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 201
        assert response.json()["vat_rate"] == 0


class TestRestaurantUpdate(TestCase, RestaurantFixture):

    client_class = APIClient

    def test_restaurant_update(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        token = self.any_token(user)

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/",
            data={"name": "UpdatedName"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "UpdatedName"

    def test_restaurant_update__only_own_restaurant(self):
        owner = self.any_user()
        restaurant = self.any_restaurant(owner)

        user = self.any_user()
        token = self.any_token(user)

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/",
            data={"name": "UpdatedName"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404

    def test_restaurant_update__vat_rate(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        token = self.any_token(user)

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/",
            data={"vat_rate": "10.00"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert response.json()["vat_rate"] == 10

    def test_restaurant_update__vat_rate_out_of_bounds(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        token = self.any_token(user)

        for vat_rate in ["-0.01", "100.01"]:
            response = self.client.patch(
                f"/restaurants/{restaurant.pk}/",
                data={"vat_rate": vat_rate},
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            assert response.status_code == 400, vat_rate
            assert "vat_rate" in response.json()


class TestRestaurantDelete(
    TestCase, RecipeIngredientFixture, OrderFixture, FixedChargeFixture
):

    client_class = APIClient

    def test_restaurant_delete(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 204

    def test_restaurant_delete__cascades_to_used_ingredients(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        recipe_ingredient = self.any_recipe_ingredient(self.any_recipe(restaurant))
        order_recipe = OrderRecipe.objects.create(
            order=self.any_order(restaurant),
            recipe=recipe_ingredient.recipe,
            unit_price=Decimal("12.50"),
            unit_cost=Decimal("3.00"),
        )
        OrderIngredient.objects.create(
            order_recipe=order_recipe,
            ingredient=recipe_ingredient.ingredient,
            action_type=OrderIngredientActionType.REMOVE,
            extra_price=Decimal("0"),
            extra_cost=Decimal("0"),
        )
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 204
        assert not Ingredient.objects.exists()

    def test_restaurant_delete__cascades_to_fixed_charges(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        self.any_fixed_charge(restaurant)
        self.any_fixed_charge(restaurant, end_date=date(2026, 6, 30))
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 204
        assert not FixedCharge.objects.exists()

    def test_restaurant_delete__only_own_restaurant(self):
        owner = self.any_user()
        restaurant = self.any_restaurant(owner)

        user = self.any_user()
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 404
