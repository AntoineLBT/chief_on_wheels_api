from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.constants import OrderIngredientActionType
from restaurants.models import Order, OrderIngredient, OrderRecipe, Shift
from restaurants.tests.fixtures import (IngredientFixture, OrderFixture,
                                        RecipeFixture)


class TestSync(TestCase, OrderFixture, RecipeFixture, IngredientFixture):

    client_class = APIClient

    def any_data(self, restaurant, recipe, ingredient, extra=None):
        extra = extra or self.any_ingredient("mozzarella", restaurant)
        return {
            "id": "11111111-1111-1111-1111-111111111111",
            "restaurant": f"{restaurant.pk}",
            "date": "2026-05-25T10:00:00Z",
            "ended_at": "2026-05-25T18:00:00Z",
            "vat_rate": 5.5,
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
                            "unit_price": 11,
                            "unit_cost": 3.21,
                            "order_ingredients": [
                                {
                                    "id": "44444444-4444-4444-4444-444444444444",
                                    "ingredient": f"{ingredient.pk}",
                                    "action_type": "REMOVE",
                                    "extra_price": 0,
                                    "extra_cost": 0,
                                },
                                {
                                    "id": "55555555-5555-5555-5555-555555555555",
                                    "ingredient": f"{extra.pk}",
                                    "action_type": "ADD",
                                    "extra_price": 1.5,
                                    "extra_cost": 0.4,
                                },
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
        self.assert_snapshots_persisted_as_sent()

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

    def assert_snapshots_persisted_as_sent(self):
        order_recipe = OrderRecipe.objects.get()
        assert (order_recipe.unit_price, order_recipe.unit_cost) == (
            Decimal("11.00"),
            Decimal("3.21"),
        )
        added = OrderIngredient.objects.get(action_type=OrderIngredientActionType.ADD)
        assert (added.extra_price, added.extra_cost) == (
            Decimal("1.50"),
            Decimal("0.40"),
        )

    def post(self, user, data):
        token = self.any_token(user)
        return self.client.post(
            "/sync/", HTTP_AUTHORIZATION=f"Bearer {token}", data=data, format="json"
        )

    def test_sync_persists_snapshots_as_sent(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        # The catalogue says otherwise: the server must not recompute.
        recipe = self.any_recipe(restaurant)

        response = self.post(
            user,
            self.any_data(restaurant, recipe, self.any_ingredient(None, restaurant)),
        )

        assert response.status_code == 201
        assert recipe.price == Decimal("12.50")
        self.assert_snapshots_persisted_as_sent()

    def test_sync_rejects_invalid_snapshots(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        recipe = self.any_recipe(restaurant)
        ingredient = self.any_ingredient("tomato", restaurant)
        extra = self.any_ingredient("mozzarella", restaurant)

        def order_recipe(data):
            return data["orders"][0]["order_recipes"][0]

        def order_ingredient(data):
            return order_recipe(data)["order_ingredients"][1]

        for target, field in [
            (order_recipe, "unit_price"),
            (order_recipe, "unit_cost"),
            (order_ingredient, "extra_price"),
            (order_ingredient, "extra_cost"),
        ]:
            for value in [None, -1, 1.735]:
                data = self.any_data(restaurant, recipe, ingredient, extra)
                if value is None:
                    del target(data)[field]
                else:
                    target(data)[field] = value

                response = self.post(user, data)

                assert response.status_code == 400, (field, value)
        assert not Shift.objects.exists()

    def test_sync_persists_shift_vat_rate_as_sent(self):
        user = self.any_user()
        # The restaurant rate is 0: the shift keeps the rate it started with.
        restaurant = self.any_restaurant(user)
        data = self.any_data(
            restaurant,
            self.any_recipe(restaurant),
            self.any_ingredient(None, restaurant),
        )

        response = self.post(user, data)

        assert response.status_code == 201
        assert Shift.objects.get().vat_rate == Decimal("5.5")

    def test_sync_rejects_invalid_shift_vat_rate(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        recipe = self.any_recipe(restaurant)
        ingredient = self.any_ingredient("tomato", restaurant)

        for value in [None, -1, 100.01, 5.555]:
            with self.subTest(value=value):
                data = self.any_data(restaurant, recipe, ingredient)
                if value is None:
                    del data["vat_rate"]
                else:
                    data["vat_rate"] = value

                response = self.post(user, data)

                assert response.status_code == 400
                assert "vat_rate" in response.json()
        assert not Shift.objects.exists()

    def test_sync_rejects_open_shift(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        recipe = self.any_recipe(restaurant)
        ingredient = self.any_ingredient("tomato", restaurant)

        for value in [None, "missing"]:
            with self.subTest(ended_at=value):
                data = self.any_data(restaurant, recipe, ingredient)
                if value == "missing":
                    del data["ended_at"]
                else:
                    data["ended_at"] = value

                response = self.post(user, data)

                assert response.status_code == 400
                assert "ended_at" in response.json()
        assert not Shift.objects.exists()

    def test_sync_rejects_shift_ending_before_it_starts(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        data = self.any_data(
            restaurant,
            self.any_recipe(restaurant),
            self.any_ingredient(None, restaurant),
        )
        data["ended_at"] = "2026-05-25T09:59:59Z"

        response = self.post(user, data)

        assert response.status_code == 400
        assert response.json() == {"ended_at": ["A shift cannot end before it starts."]}
        assert not Shift.objects.exists()
