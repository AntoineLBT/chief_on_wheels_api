from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.utils import aware_utcnow

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

    def test_user_update(self):
        user = self.any_user()
        token = self.any_token(user)
        response = self.client.patch(
            f"/users/{user.pk}/",
            data={"first_name": "NewName", "password": "newpassword"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == "NewName"


class TestAuthRoute(TestCase, UserFixture):

    client_class = APIClient

    def test_user_login(self):
        user = self.any_user()

        response = self.client.post(
            "/auth/login/", data={"username": user.username, "password": "password"}
        )
        assert response.status_code == 200
        assert "access" in response.json()
        assert "refresh" in response.json()

    def test_user_login_invalid_credentials(self):
        response = self.client.post(
            "/auth/login/", data={"username": "nonexistent", "password": "wrongpass"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_user_login_unexpected_field(self):
        response = self.client.post(
            "/auth/login/",
            data={
                "username": "nonexistent",
                "password": "wrongpass",
                "firstname": "perlinpinpin",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Unexpected field: firstname"

    def test_user_refresh(self):
        user = self.any_user()

        login_response = self.client.post(
            "/auth/login/", data={"username": user.username, "password": "password"}
        )
        refresh_token = login_response.json()["refresh"]

        refresh_response = self.client.post(
            "/auth/refresh/", data={"refresh": refresh_token}
        )
        assert refresh_response.status_code == 200
        assert "access" in refresh_response.json()

    def _refresh_days_after_login(self, days):
        user = self.any_user()
        refresh_token = self.client.post(
            "/auth/login/", data={"username": user.username, "password": "password"}
        ).json()["refresh"]
        later = aware_utcnow() + timedelta(days=days)
        with patch("rest_framework_simplejwt.tokens.aware_utcnow", return_value=later):
            return self.client.post("/auth/refresh/", data={"refresh": refresh_token})

    def test_user_refresh_still_valid_89_days_after_login(self):
        """A weekly (or rarer) sync must not force a new login."""
        assert self._refresh_days_after_login(89).status_code == 200

    def test_user_refresh_expired_91_days_after_login(self):
        assert self._refresh_days_after_login(91).status_code == 401

    def test_user_refresh_invalid_token(self):
        refresh_response = self.client.post(
            "/auth/refresh/", data={"refresh": "invalidtoken"}
        )
        assert refresh_response.status_code == 401

    def test_user_refresh_unexpected_field(self):
        refresh_response = self.client.post(
            "/auth/refresh/", data={"refresh": "invalidtoken", "extra": "field"}
        )
        assert refresh_response.status_code == 400
