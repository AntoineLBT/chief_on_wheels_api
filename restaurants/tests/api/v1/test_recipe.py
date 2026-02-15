from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.tests.fixtures import RecipeFixture


class TestRecipeList(TestCase, RecipeFixture):

    client_class = APIClient

    def test_recipe_list_requires_authentication(self) -> None:
        response = self.client.get("/restaurants/1/recipes/")
        assert response.status_code == 401

    def test_recipe_list(self) -> None:
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        recipe = self.any_recipe(with_restaurant=restaurant)

        token = self.any_token(user)

        response = self.client.get(
            f"/restaurants/{restaurant.pk}/recipes/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["pk"] == recipe.pk


class TestRecipeCreate(TestCase, RecipeFixture):

    client_class = APIClient

    def test_recipe_create(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        token = self.any_token(user)

        data = {"name": "margharita", "price": 10, "restaurant": restaurant.pk}

        response = self.client.post(
            f"/restaurants/{restaurant.pk}/recipes/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 201
        assert "name" in response.json()

    def test_recipe_create__owner_only(self):
        owner = self.any_user()
        owner.username = "Proprio"
        owner.save()
        restaurant = self.any_restaurant(owner)

        data = {"name": "margharita", "price": 10, "restaurant": restaurant.pk}

        user = self.any_user()
        token = self.any_token(user)
        response = self.client.post(
            f"/restaurants/{restaurant.pk}/recipes/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404


class TestRecipeUpdate(TestCase, RecipeFixture):

    client_class = APIClient

    def test_recipe_update(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        recipe = self.any_recipe(restaurant)
        token = self.any_token(user)

        data = {"name": recipe.name, "price": 42, "restaurant": restaurant.pk}

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/recipes/{recipe.pk}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        assert response.json()["price"] == 42

    def test_recipe_update__owner_only(self):
        owner = self.any_user()
        owner.username = "Proprio"
        owner.save()
        restaurant = self.any_restaurant(owner)
        recipe = self.any_recipe(restaurant)

        data = {"name": recipe.name, "price": 42, "restaurant": restaurant.pk}

        user = self.any_user()
        token = self.any_token(user)
        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/recipes/{recipe.pk}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404


class TestDeleteRecipe(TestCase, RecipeFixture):

    client_class = APIClient

    def test_shift_delete(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        shift = self.any_recipe(restaurant)
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/recipes/{shift.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 204

    def test_shift_delete__owner_only(self):
        owner = self.any_user()
        restaurant = self.any_restaurant(owner)
        shift = self.any_recipe(restaurant)

        user = self.any_user()
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/recipes/{shift.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404
