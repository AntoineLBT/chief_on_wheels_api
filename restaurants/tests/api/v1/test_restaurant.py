from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.tests.fixtures import RestaurantFixture


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

        data = {"name": "NewRestaurant", "type": "PIZZERIA"}

        response = self.client.post(
            "/restaurants/", data=data, HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        assert response.status_code == 201
        assert response.json()["name"] == "NewRestaurant"


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


class TestRestaurantDelete(TestCase, RestaurantFixture):

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
