from django.test import TestCase
from rest_framework.test import APIClient

from users.tests.fixtures import UserFixture


class TestUserRoute(TestCase, UserFixture):

    client_class = APIClient

    def test_user_list(self):
        user = self.any_user()
        user.first_name = "Alan"
        user.save()

        response = self.client.get("/users/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["first_name"] == "Alan"

    def test_user_create(self):

        data = self.any_user_data()
        data["first_name"] = "toto"

        response = self.client.post("/users/", data=data)

        assert response.status_code == 201
        assert response.json()["first_name"] == "toto"
