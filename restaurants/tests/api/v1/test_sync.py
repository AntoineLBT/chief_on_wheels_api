from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.constants import OrderIngredientActionType
from restaurants.models import Order, OrderIngredient, Shift
from restaurants.tests.fixtures import (IngredientFixture, OrderFixture,
                                        RecipeFixture)


class TestSync(TestCase, OrderFixture, RecipeFixture, IngredientFixture):

    client_class = APIClient

    def any_data(self, restaurant, recipe, ingredient):
        return {
            "id": "11111111-1111-1111-1111-111111111111",
            "restaurant": f"{restaurant.pk}",
            "date": "2026-05-25T10:00:00Z",
            "ended_at": "2026-05-25T18:00:00Z",
            "orders": [
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "customer_name": "Alice",
                    "picking_time": "2026-05-25T12:30:00Z",
                    "status": "TODO",
                    "order_recipes": [
                        {
                            "id": "33333333-3333-3333-3333-333333333333",
                            "recipe": f"{recipe.pk}",
                            "order_ingredients": [
                                {
                                    "id": "44444444-4444-4444-4444-444444444444",
                                    "ingredient": f"{ingredient.pk}",
                                    "action_type": "REMOVE",
                                }
                            ],
                        }
                    ],
                }
            ],
        }

    def test_sync_general_case(self):

        user = self.any_user()
        restaurant = self.any_restaurant(user)
        recipe = self.any_recipe(restaurant)
        ingredient = self.any_ingredient("tomato", restaurant)

        token = self.any_token(user)

        data = self.any_data(restaurant, recipe, ingredient)

        assert Order.objects.count() == 0
        assert Shift.objects.count() == 0
        assert OrderIngredient.objects.count() == 0

        response = self.client.post(
            "/sync/", HTTP_AUTHORIZATION=f"Bearer {token}", data=data, format="json"
        )
        assert response.status_code == 201

        assert Shift.objects.count() == 1

        created_order = Order.objects.first()
        assert created_order
        assert created_order.customer_name == "Alice"

        assert (
            OrderIngredient.objects.filter(
                action_type=OrderIngredientActionType.REMOVE
            ).count()
            == 1
        )

    def test_sync_is_idempotent(self):

        user = self.any_user()
        restaurant = self.any_restaurant(user)
        recipe = self.any_recipe(restaurant)
        ingredient = self.any_ingredient("tomato", restaurant)

        token = self.any_token(user)

        data = self.any_data(restaurant, recipe, ingredient)

        assert Order.objects.count() == 0
        assert Shift.objects.count() == 0
        assert OrderIngredient.objects.count() == 0

        response = self.client.post(
            "/sync/", HTTP_AUTHORIZATION=f"Bearer {token}", data=data, format="json"
        )

        response = self.client.post(
            "/sync/", HTTP_AUTHORIZATION=f"Bearer {token}", data=data, format="json"
        )

        assert Shift.objects.count() == 1

        created_order = Order.objects.first()
        assert created_order
        assert created_order.customer_name == "Alice"

        assert (
            OrderIngredient.objects.filter(
                action_type=OrderIngredientActionType.REMOVE
            ).count()
            == 1
        )

        assert response.status_code == 201

    def test_sync_return_404_on_wrong_restaurant(self):

        user = self.any_user()
        restaurant = self.any_restaurant()
        recipe = self.any_recipe(restaurant)
        ingredient = self.any_ingredient("tomato", restaurant)

        data = self.any_data(restaurant, recipe, ingredient)

        token = self.any_token(user)

        response = self.client.post(
            "/sync/", HTTP_AUTHORIZATION=f"Bearer {token}", data=data, format="json"
        )

        assert response.status_code == 404
