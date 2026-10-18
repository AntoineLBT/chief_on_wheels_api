from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.constants import OrderIngredientActionType
from restaurants.models import OrderIngredient
from restaurants.tests.fixtures import (IngredientFixture, OrderRecipeFixture,
                                        RecipeIngredientFixture)


class TestIngredientList(TestCase, IngredientFixture):

    client_class = APIClient

    def test_ingredient_list_requires_authentication(self) -> None:
        response = self.client.get("/restaurants/1/ingredients/")
        assert response.status_code == 401

    def test_ingredient_list(self) -> None:
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        ingredient = self.any_ingredient(with_restaurant=restaurant)

        token = self.any_token(user)

        response = self.client.get(
            f"/restaurants/{restaurant.pk}/ingredients/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["pk"] == str(ingredient.pk)

    def test_ingredient_list__only_url_restaurant(self) -> None:
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        ingredient = self.any_ingredient(with_restaurant=restaurant)
        self.any_ingredient(with_restaurant=self.any_restaurant(user))
        token = self.any_token(user)

        response = self.client.get(
            f"/restaurants/{restaurant.pk}/ingredients/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert [i["pk"] for i in response.json()] == [str(ingredient.pk)]


class TestIngredientCreate(TestCase, IngredientFixture):

    client_class = APIClient

    def post(self, restaurant, data, user=None):
        token = self.any_token(user or restaurant.owner)
        return self.client.post(
            f"/restaurants/{restaurant.pk}/ingredients/",
            data=data,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_ingredient_create(self):
        restaurant = self.any_restaurant()

        response = self.post(
            restaurant,
            {"name": "mozzarella", "unit": "KG", "price_per_unit": 12.5},
        )

        assert response.status_code == 201
        assert response.json()["restaurant"] == str(restaurant.pk)
        assert response.json()["unit"] == "KG"
        assert response.json()["price_per_unit"] == 12.5

    def test_ingredient_create__invalid_unit(self):
        restaurant = self.any_restaurant()

        response = self.post(
            restaurant,
            {"name": "mozzarella", "unit": "G", "price_per_unit": 12.5},
        )

        assert response.status_code == 400
        assert "unit" in response.json()

    def test_ingredient_create__with_extra(self):
        restaurant = self.any_restaurant()

        response = self.post(
            restaurant,
            {
                "name": "mozzarella",
                "unit": "KG",
                "price_per_unit": 12.5,
                "has_extra": True,
                "extra_price": 1.5,
                "extra_quantity": 40,
            },
        )

        assert response.status_code == 201
        assert response.json()["has_extra"] is True
        assert response.json()["extra_price"] == 1.5
        assert response.json()["extra_quantity"] == 40

    def test_ingredient_create__extra_requires_price_and_quantity(self):
        restaurant = self.any_restaurant()
        base = {
            "name": "mozzarella",
            "unit": "KG",
            "price_per_unit": 12.5,
            "has_extra": True,
        }

        for missing, present in [
            ("extra_price", {"extra_quantity": 40}),
            ("extra_quantity", {"extra_price": 1.5}),
        ]:
            response = self.post(restaurant, {**base, **present})

            assert response.status_code == 400, missing
            assert list(response.json()) == [missing]

    def test_ingredient_create__without_extra_clears_extra_values(self):
        restaurant = self.any_restaurant()

        response = self.post(
            restaurant,
            {
                "name": "mozzarella",
                "unit": "KG",
                "price_per_unit": 12.5,
                "has_extra": False,
                "extra_price": 1.5,
                "extra_quantity": 40,
            },
        )

        assert response.status_code == 201
        assert response.json()["extra_price"] is None
        assert response.json()["extra_quantity"] is None

    def test_ingredient_create__owner_only(self):
        restaurant = self.any_restaurant()

        response = self.post(
            restaurant,
            {"name": "mozzarella", "unit": "KG", "price_per_unit": 12.5},
            user=self.any_user(),
        )

        assert response.status_code == 404


class TestIngredientUpdate(TestCase, IngredientFixture):

    client_class = APIClient

    def test_ingredient_update__partial(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        ingredient = self.any_ingredient(with_restaurant=restaurant)
        token = self.any_token(user)

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/ingredients/{ingredient.pk}/",
            data={"name": "basilic"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        assert response.json()["name"] == "basilic"

    def test_ingredient_update__disabling_extra_clears_extra_values(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        ingredient = self.any_ingredient(with_restaurant=restaurant)
        ingredient.has_extra = True
        ingredient.extra_price = Decimal("1.50")
        ingredient.extra_quantity = 40
        ingredient.save()
        token = self.any_token(user)

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/ingredients/{ingredient.pk}/",
            data={"has_extra": False},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        assert response.json()["extra_price"] is None
        assert response.json()["extra_quantity"] is None

    def test_ingredient_update__enabling_extra_requires_price_and_quantity(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        ingredient = self.any_ingredient(with_restaurant=restaurant)
        token = self.any_token(user)

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/ingredients/{ingredient.pk}/",
            data={"has_extra": True, "extra_price": 1.5},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 400
        assert list(response.json()) == ["extra_quantity"]

    def test_ingredient_update__owner_only(self):
        restaurant = self.any_restaurant()
        ingredient = self.any_ingredient(with_restaurant=restaurant)
        token = self.any_token(self.any_user())

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/ingredients/{ingredient.pk}/",
            data={"name": "basilic"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404


class TestIngredientDelete(
    TestCase, RecipeIngredientFixture, OrderRecipeFixture, IngredientFixture
):

    client_class = APIClient

    def delete(self, ingredient):
        restaurant = ingredient.restaurant
        token = self.any_token(restaurant.owner)
        return self.client.delete(
            f"/restaurants/{restaurant.pk}/ingredients/{ingredient.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_ingredient_delete__used_in_recipes(self):
        ingredient = self.any_ingredient()
        for _ in range(2):
            self.any_recipe_ingredient(
                self.any_recipe(ingredient.restaurant), ingredient
            )

        response = self.delete(ingredient)

        assert response.status_code == 409
        assert response.json()["recipe_count"] == 2

    def test_ingredient_delete__used_in_an_order_only(self):
        ingredient = self.any_ingredient()
        OrderIngredient.objects.create(
            order_recipe=self.any_order_recipe(),
            ingredient=ingredient,
            action_type=OrderIngredientActionType.ADD,
        )

        response = self.delete(ingredient)

        assert response.status_code == 409
        assert response.json()["recipe_count"] == 0

    def test_ingredient_delete(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        ingredient = self.any_ingredient(with_restaurant=restaurant)
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/ingredients/{ingredient.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 204

    def test_ingredient_delete__owner_only(self):
        restaurant = self.any_restaurant()
        ingredient = self.any_ingredient(with_restaurant=restaurant)
        token = self.any_token(self.any_user())

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/ingredients/{ingredient.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404
