from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.tests.fixtures import IngredientFixture


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


class TestIngredientCreate(TestCase, IngredientFixture):

    client_class = APIClient

    def test_ingredient_create(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        token = self.any_token(user)

        data = {"name": "sauce_tomate", "price_by_kg": 10, "restaurant": restaurant.pk}

        response = self.client.post(
            f"/restaurants/{restaurant.pk}/ingredients/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 201
        assert "name" in response.json()

    def test_ingredient_create__owner_only(self):
        owner = self.any_user()
        owner.username = "Proprio"
        owner.save()
        restaurant = self.any_restaurant(owner)

        data = {"name": "sauce_tomate", "price_by_kg": 10, "restaurant": restaurant.pk}

        user = self.any_user()
        token = self.any_token(user)
        response = self.client.post(
            f"/restaurants/{restaurant.pk}/ingredients/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404


class TestIngredientUpdate(TestCase, IngredientFixture):

    client_class = APIClient

    def test_ingredient_update(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        ingredient = self.any_ingredient(with_restaurant=restaurant)
        token = self.any_token(user)

        data = {"name": ingredient.name, "price_by_kg": 42, "restaurant": restaurant.pk}

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/ingredients/{ingredient.pk}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        assert response.json()["price_by_kg"] == 42

    def test_ingredient_update__owner_only(self):
        owner = self.any_user()
        owner.username = "Proprio"
        owner.save()
        restaurant = self.any_restaurant(owner)
        ingredient = self.any_ingredient(with_restaurant=restaurant)

        data = {"name": ingredient.name, "price_by_kg": 42, "restaurant": restaurant.pk}

        user = self.any_user()
        token = self.any_token(user)
        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/ingredients/{ingredient.pk}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404


class TestDeleteingredient(TestCase, IngredientFixture):

    client_class = APIClient

    def test_shift_delete(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        shift = self.any_ingredient(with_restaurant=restaurant)
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/ingredients/{shift.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 204

    def test_shift_delete__owner_only(self):
        owner = self.any_user()
        restaurant = self.any_restaurant(owner)
        shift = self.any_ingredient(with_restaurant=restaurant)

        user = self.any_user()
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/ingredients/{shift.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404
