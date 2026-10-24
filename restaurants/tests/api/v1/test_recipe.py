from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.constants import IngredientUnit
from restaurants.models import Ingredient
from restaurants.tests.fixtures import RecipeIngredientFixture


class RecipeApiTestCase(TestCase, RecipeIngredientFixture):

    client_class = APIClient

    def call(self, method, restaurant, data=None, recipe=None, user=None):
        token = self.any_token(user or restaurant.owner)
        url = f"/restaurants/{restaurant.pk}/recipes/"
        if recipe:
            url += f"{recipe.pk}/"
        return getattr(self.client, method)(
            url, data=data, format="json", HTTP_AUTHORIZATION=f"Bearer {token}"
        )


class TestRecipeList(RecipeApiTestCase):

    def test_recipe_list_requires_authentication(self) -> None:
        response = self.client.get("/restaurants/1/recipes/")
        assert response.status_code == 401

    def test_recipe_list(self) -> None:
        restaurant = self.any_restaurant()
        recipe = self.any_recipe(restaurant)
        recipe_ingredient = self.any_recipe_ingredient(recipe)

        response = self.call("get", restaurant)

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["pk"] == str(recipe.pk)
        assert response.json()[0]["recipe_ingredients"] == [
            {
                "pk": str(recipe_ingredient.pk),
                "ingredient": str(recipe_ingredient.ingredient.pk),
                "quantity": 100,
            }
        ]

    def test_recipe_list__only_url_restaurant(self) -> None:
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        recipe = self.any_recipe(restaurant)
        self.any_recipe(self.any_restaurant(user))

        response = self.call("get", restaurant)

        assert [r["pk"] for r in response.json()] == [str(recipe.pk)]


class TestRecipeCreate(RecipeApiTestCase):

    def test_recipe_create(self):
        restaurant = self.any_restaurant()
        tomato = self.any_ingredient("tomate", restaurant)
        mozzarella = self.any_ingredient("mozzarella", restaurant)

        response = self.call(
            "post",
            restaurant,
            {
                "name": "margherita",
                "price": 10.5,
                "recipe_ingredients": [
                    {"ingredient": str(tomato.pk), "quantity": 80},
                    {"ingredient": str(mozzarella.pk), "quantity": 120},
                ],
            },
        )

        assert response.status_code == 201
        assert response.json()["restaurant"] == str(restaurant.pk)
        assert response.json()["price"] == 10.5
        assert response.json()["is_active"] is True
        assert sorted(
            (line["ingredient"], line["quantity"])
            for line in response.json()["recipe_ingredients"]
        ) == sorted([(str(tomato.pk), 80), (str(mozzarella.pk), 120)])

    def test_recipe_create__without_ingredients(self):
        restaurant = self.any_restaurant()

        response = self.call("post", restaurant, {"name": "pain", "price": 3})

        assert response.status_code == 201
        assert response.json()["recipe_ingredients"] == []

    def test_recipe_create__invalid_quantity(self):
        restaurant = self.any_restaurant()
        tomato = self.any_ingredient("tomate", restaurant)

        for quantity in [None, 0, -5, 12.5]:
            line = {"ingredient": str(tomato.pk)}
            if quantity is not None:
                line["quantity"] = quantity

            response = self.call(
                "post",
                restaurant,
                {"name": "pain", "price": 3, "recipe_ingredients": [line]},
            )

            assert response.status_code == 400, quantity
            assert "quantity" in response.json()["recipe_ingredients"][0], quantity

    def test_recipe_create__ingredient_of_another_restaurant(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        foreign = self.any_ingredient("tomate", self.any_restaurant(user))

        response = self.call(
            "post",
            restaurant,
            {
                "name": "pain",
                "price": 3,
                "recipe_ingredients": [{"ingredient": str(foreign.pk), "quantity": 1}],
            },
        )

        assert response.status_code == 400
        assert "ingredient" in response.json()["recipe_ingredients"][0]

    def test_recipe_create__same_ingredient_twice(self):
        restaurant = self.any_restaurant()
        tomato = self.any_ingredient("tomate", restaurant)
        line = {"ingredient": str(tomato.pk), "quantity": 80}

        response = self.call(
            "post",
            restaurant,
            {"name": "pain", "price": 3, "recipe_ingredients": [line, line]},
        )

        assert response.status_code == 400
        assert "recipe_ingredients" in response.json()

    def test_recipe_create__owner_only(self):
        restaurant = self.any_restaurant()

        response = self.call(
            "post", restaurant, {"name": "pain", "price": 3}, user=self.any_user()
        )

        assert response.status_code == 404


class TestRecipeUpdate(RecipeApiTestCase):

    def test_recipe_update__partial(self):
        restaurant = self.any_restaurant()
        recipe = self.any_recipe(restaurant)

        response = self.call("patch", restaurant, {"name": "regina"}, recipe)

        assert response.status_code == 200
        assert response.json()["name"] == "regina"

    def test_recipe_update__replaces_ingredients(self):
        restaurant = self.any_restaurant()
        recipe = self.any_recipe(restaurant)
        kept = self.any_recipe_ingredient(
            recipe, self.any_ingredient("tomate", restaurant)
        )
        self.any_recipe_ingredient(recipe, self.any_ingredient("olive", restaurant))
        added = self.any_ingredient("basilic", restaurant)

        response = self.call(
            "patch",
            restaurant,
            {
                "recipe_ingredients": [
                    {"ingredient": str(kept.ingredient.pk), "quantity": 90},
                    {"ingredient": str(added.pk), "quantity": 5},
                ]
            },
            recipe,
        )

        assert response.status_code == 200
        assert sorted(
            (line["ingredient"], line["quantity"])
            for line in response.json()["recipe_ingredients"]
        ) == sorted([(str(kept.ingredient.pk), 90), (str(added.pk), 5)])
        assert recipe.recipeingredient_set.count() == 2

    def test_recipe_update__without_ingredients_keeps_them(self):
        restaurant = self.any_restaurant()
        recipe = self.any_recipe(restaurant)
        recipe_ingredient = self.any_recipe_ingredient(recipe)

        response = self.call("patch", restaurant, {"is_active": False}, recipe)

        assert [line["pk"] for line in response.json()["recipe_ingredients"]] == [
            str(recipe_ingredient.pk)
        ]

    def test_recipe_update__deactivate(self):
        restaurant = self.any_restaurant()
        recipe = self.any_recipe(restaurant)

        response = self.call("patch", restaurant, {"is_active": False}, recipe)

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_recipe_update__owner_only(self):
        restaurant = self.any_restaurant()
        recipe = self.any_recipe(restaurant)

        response = self.call(
            "patch", restaurant, {"name": "regina"}, recipe, user=self.any_user()
        )

        assert response.status_code == 404


class TestRecipeDelete(RecipeApiTestCase):

    def test_recipe_delete__not_allowed(self):
        restaurant = self.any_restaurant()
        recipe = self.any_recipe(restaurant)

        response = self.call("delete", restaurant, recipe=recipe)

        assert response.status_code == 405


class TestRecipeCost(RecipeApiTestCase):
    """Cases shared with recipeCost in chief_on_wheels_ui/src/utils/cost.test.ts."""

    def ingredient(self, restaurant, name, unit, price):
        return Ingredient.objects.create(
            restaurant=restaurant, name=name, unit=unit, price_per_unit=Decimal(price)
        )

    def test_recipe_cost(self):
        restaurant = self.any_restaurant()
        recipe = self.any_recipe(restaurant)
        for name, unit, price, quantity in [
            ("mozzarella", IngredientUnit.KG, "12.50", 80),
            ("huile", IngredientUnit.L, "9.00", 15),
            ("oeuf", IngredientUnit.UNIT, "0.30", 2),
        ]:
            self.any_recipe_ingredient(
                recipe, self.ingredient(restaurant, name, unit, price), quantity
            )

        response = self.call("get", restaurant, recipe=recipe)

        # 1.00 + 0.135 + 0.60 = 1.735, rounded half up.
        assert response.json()["cost"] == 1.74

    def test_recipe_cost__without_ingredients(self):
        restaurant = self.any_restaurant()
        recipe = self.any_recipe(restaurant)

        response = self.call("get", restaurant, recipe=recipe)

        assert response.json()["cost"] == 0

    def test_recipe_cost__read_only(self):
        restaurant = self.any_restaurant()

        response = self.call(
            "post", restaurant, {"name": "pain", "price": 3, "cost": 99}
        )

        assert response.json()["cost"] == 0
