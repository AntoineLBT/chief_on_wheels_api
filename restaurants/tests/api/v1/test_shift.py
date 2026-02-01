from datetime import datetime, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.tests.fixtures import ShiftFixture


class TestShiftList(TestCase, ShiftFixture):

    client_class = APIClient

    def test_shift_list_requires_authentication(self):
        response = self.client.get("/restaurants/1/shifts/")
        assert response.status_code == 401

    def test_shift_list(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        shift = self.any_shift(restaurant)
        now = datetime.now()
        shift.date = now
        shift.save()

        token = self.any_token(user)

        response = self.client.get(
            f"/restaurants/{restaurant.pk}/shifts/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert now.isoformat() in response.json()[0]["date"]


class TestShiftCreate(TestCase, ShiftFixture):

    client_class = APIClient

    def test_shift_create(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        token = self.any_token(user)

        data = {"date": datetime.now().date().isoformat(), "restaurant": restaurant.pk}

        response = self.client.post(
            f"/restaurants/{restaurant.pk}/shifts/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 201
        assert "date" in response.json()
        assert response.json()["restaurant"] == restaurant.pk

    def test_shift_create__owner_only(self):
        owner = self.any_user()
        owner.username = "Proprio"
        owner.save()
        restaurant = self.any_restaurant(owner)

        data = {"date": datetime.now().date().isoformat(), "restaurant": restaurant.pk}

        user = self.any_user()
        token = self.any_token(user)
        response = self.client.post(
            f"/restaurants/{restaurant.pk}/shifts/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404


class TestShiftUpdate(TestCase, ShiftFixture):

    client_class = APIClient

    def test_shift_update(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        shift = self.any_shift(restaurant)
        token = self.any_token(user)

        new_date = shift.date + timedelta(days=2)
        data = {"date": new_date.isoformat(), "restaurant": restaurant.pk}

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/shifts/{shift.pk}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 200
        assert "date" in response.json()
        assert new_date.isoformat() in response.json()["date"]
        assert response.json()["restaurant"] == restaurant.pk

    def test_shift_update__owner_only(self):
        owner = self.any_user()
        restaurant = self.any_restaurant(owner)
        shift = self.any_shift(restaurant)

        user = self.any_user()
        token = self.any_token(user)

        new_date = shift.date + timedelta(days=2)
        data = {"date": new_date.isoformat(), "restaurant": restaurant.pk}

        response = self.client.patch(
            f"/restaurants/{restaurant.pk}/shifts/{shift.pk}/",
            data=data,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404


class TestDeleteUpdate(TestCase, ShiftFixture):

    client_class = APIClient

    def test_shift_delete(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        shift = self.any_shift(restaurant)
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/shifts/{shift.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 204

    def test_shift_delete__owner_only(self):
        owner = self.any_user()
        restaurant = self.any_restaurant(owner)
        shift = self.any_shift(restaurant)

        user = self.any_user()
        token = self.any_token(user)

        response = self.client.delete(
            f"/restaurants/{restaurant.pk}/shifts/{shift.pk}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        assert response.status_code == 404
