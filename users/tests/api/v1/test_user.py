from django.test import TestCase
from rest_framework.test import APIClient

from users.tests.fixtures import UserFixture


class TestUserRoute(TestCase, UserFixture):

    client_class = APIClient

    def test_user_list(self):
        user = self.any_user()
        user.first_name = "Alan"
        user.save()

        token = self.any_token(user)

        response = self.client.get("/users/", HTTP_AUTHORIZATION=f"Bearer {token}")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["first_name"] == "Alan"

    def test_user_create(self):

        data = self.any_user_data()
        data["first_name"] = "toto"

        response = self.client.post("/users/", data=data)
        assert response.status_code == 201
        assert response.json()["first_name"] == "toto"

    def test_user_login(self):
        user = self.any_user()

        response = self.client.post(
            "/users/login/", data={"username": user.username, "password": "password"}
        )
        assert response.status_code == 200
        assert "access" in response.json()
        assert "refresh" in response.json()
        assert response.json()["user"]["username"] == user.username

    def test_user_refresh(self):
        user = self.any_user()

        login_response = self.client.post(
            "/users/login/", data={"username": user.username, "password": "password"}
        )
        refresh_token = login_response.json()["refresh"]

        refresh_response = self.client.post(
            "/users/refresh/", data={"refresh": refresh_token}
        )
        assert refresh_response.status_code == 200
        assert "access" in refresh_response.json()
