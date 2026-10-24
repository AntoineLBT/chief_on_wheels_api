from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from restaurants.tests.fixtures import FixedChargeFixture


class FixedChargeTestCase(TestCase, FixedChargeFixture):

    client_class = APIClient

    def url(self, restaurant, suffix=""):
        return f"/restaurants/{restaurant.pk}/fixed-charges/{suffix}"

    def auth(self, restaurant, user=None):
        token = self.any_token(user or restaurant.owner)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


class TestFixedChargeCreate(FixedChargeTestCase):

    def post(self, restaurant, data, user=None):
        return self.client.post(
            self.url(restaurant),
            data=data,
            format="json",
            **self.auth(restaurant, user),
        )

    def test_fixed_charge_create(self):
        restaurant = self.any_restaurant()

        response = self.post(
            restaurant, {"name": "Loyer", "amount": 300, "frequency": "MONTHLY"}
        )

        assert response.status_code == 201
        assert response.json()["restaurant"] == str(restaurant.pk)
        assert response.json()["name"] == "Loyer"
        assert response.json()["amount"] == 300
        assert response.json()["frequency"] == "MONTHLY"
        assert response.json()["start_date"] == timezone.localdate().isoformat()
        assert response.json()["end_date"] is None

    def test_fixed_charge_create__past_start_date(self):
        restaurant = self.any_restaurant()

        response = self.post(
            restaurant,
            {
                "name": "Assurance",
                "amount": 600,
                "frequency": "YEARLY",
                "start_date": "2026-01-01",
            },
        )

        assert response.status_code == 201
        assert response.json()["start_date"] == "2026-01-01"

    def test_fixed_charge_create__end_date_is_read_only(self):
        restaurant = self.any_restaurant()

        response = self.post(
            restaurant,
            {
                "name": "Loyer",
                "amount": 300,
                "frequency": "MONTHLY",
                "end_date": "2026-12-31",
            },
        )

        assert response.status_code == 201
        assert response.json()["end_date"] is None

    def test_fixed_charge_create__invalid_frequency(self):
        restaurant = self.any_restaurant()

        response = self.post(
            restaurant, {"name": "Loyer", "amount": 300, "frequency": "WEEKLY"}
        )

        assert response.status_code == 400
        assert "frequency" in response.json()

    def test_fixed_charge_create__invalid_amount(self):
        restaurant = self.any_restaurant()

        for amount in [None, 0, -1, 10.001]:
            with self.subTest(amount=amount):
                data = {"name": "Loyer", "frequency": "MONTHLY", "amount": amount}
                if amount is None:
                    del data["amount"]

                response = self.post(restaurant, data)

                assert response.status_code == 400
                assert "amount" in response.json()


class TestFixedChargeList(FixedChargeTestCase):

    def test_fixed_charge_list_requires_authentication(self):
        response = self.client.get(self.url(self.any_restaurant()))
        assert response.status_code == 401

    def test_fixed_charge_list__only_active_charges_of_url_restaurant(self):
        user = self.any_user()
        restaurant = self.any_restaurant(user)
        active = self.any_fixed_charge(restaurant)
        self.any_fixed_charge(restaurant, end_date=date(2026, 6, 30))
        self.any_fixed_charge(self.any_restaurant(user))

        response = self.client.get(self.url(restaurant), **self.auth(restaurant))

        assert response.status_code == 200
        assert [c["pk"] for c in response.json()] == [str(active.pk)]


class TestFixedChargeRevise(FixedChargeTestCase):

    def revise(self, charge, data, user=None):
        restaurant = charge.restaurant
        return self.client.post(
            self.url(restaurant, f"{charge.pk}/revise/"),
            data=data,
            format="json",
            **self.auth(restaurant, user),
        )

    def test_fixed_charge_revise(self):
        charge = self.any_fixed_charge(start_date=date(2026, 1, 1))

        response = self.revise(charge, {"amount": 350, "effective_date": "2026-07-01"})

        assert response.status_code == 201
        assert response.json()["pk"] != str(charge.pk)
        assert response.json()["name"] == "Loyer"
        assert response.json()["amount"] == 350
        assert response.json()["frequency"] == "MONTHLY"
        assert response.json()["start_date"] == "2026-07-01"
        assert response.json()["end_date"] is None
        charge.refresh_from_db()
        assert charge.end_date == date(2026, 6, 30)
        assert charge.amount == 300

    def test_fixed_charge_revise__frequency(self):
        charge = self.any_fixed_charge()

        response = self.revise(charge, {"frequency": "YEARLY"})

        assert response.status_code == 201
        assert response.json()["amount"] == 300
        assert response.json()["frequency"] == "YEARLY"

    def test_fixed_charge_revise__effective_date_defaults_to_today(self):
        charge = self.any_fixed_charge(start_date=date(2026, 1, 1))
        today = timezone.localdate()

        response = self.revise(charge, {"amount": 350})

        assert response.status_code == 201
        assert response.json()["start_date"] == today.isoformat()
        charge.refresh_from_db()
        assert charge.end_date == today - timedelta(days=1)

    def test_fixed_charge_revise__replaces_the_charge_in_the_list(self):
        charge = self.any_fixed_charge()

        new_pk = self.revise(charge, {"amount": 350}).json()["pk"]

        response = self.client.get(
            self.url(charge.restaurant), **self.auth(charge.restaurant)
        )
        assert [c["pk"] for c in response.json()] == [new_pk]

    def test_fixed_charge_revise__effective_date_not_after_start_date(self):
        charge = self.any_fixed_charge(start_date=date(2026, 7, 1))

        for effective_date in ["2026-07-01", "2026-06-15"]:
            with self.subTest(effective_date=effective_date):
                response = self.revise(
                    charge, {"amount": 350, "effective_date": effective_date}
                )

                assert response.status_code == 400
                assert response.json() == {
                    "effective_date": [
                        "The effective date must be after the start of the charge "
                        "(2026-07-01)."
                    ]
                }
                charge.refresh_from_db()
                assert charge.end_date is None

    def test_fixed_charge_revise__closed_charge(self):
        charge = self.any_fixed_charge(end_date=date(2026, 6, 30))

        response = self.revise(charge, {"amount": 350})

        assert response.status_code == 400
        assert response.json() == {"detail": "This charge is already closed."}


class TestFixedChargeClose(FixedChargeTestCase):

    def close(self, charge, data=None, user=None):
        restaurant = charge.restaurant
        return self.client.post(
            self.url(restaurant, f"{charge.pk}/close/"),
            data=data or {},
            format="json",
            **self.auth(restaurant, user),
        )

    def test_fixed_charge_close(self):
        charge = self.any_fixed_charge(start_date=date(2026, 1, 1))

        response = self.close(charge, {"effective_date": "2026-06-30"})

        assert response.status_code == 200
        assert response.json()["pk"] == str(charge.pk)
        assert response.json()["end_date"] == "2026-06-30"

    def test_fixed_charge_close__on_its_start_date(self):
        charge = self.any_fixed_charge(start_date=date(2026, 7, 1))

        response = self.close(charge, {"effective_date": "2026-07-01"})

        assert response.status_code == 200
        assert response.json()["end_date"] == "2026-07-01"

    def test_fixed_charge_close__effective_date_defaults_to_today(self):
        charge = self.any_fixed_charge(start_date=date(2026, 1, 1))

        response = self.close(charge)

        assert response.json()["end_date"] == timezone.localdate().isoformat()

    def test_fixed_charge_close__removes_the_charge_from_the_list(self):
        charge = self.any_fixed_charge()

        self.close(charge)

        response = self.client.get(
            self.url(charge.restaurant), **self.auth(charge.restaurant)
        )
        assert response.json() == []

    def test_fixed_charge_close__effective_date_before_start_date(self):
        charge = self.any_fixed_charge(start_date=date(2026, 7, 1))

        response = self.close(charge, {"effective_date": "2026-06-30"})

        assert response.status_code == 400
        assert response.json() == {
            "effective_date": [
                "The effective date must not be before the start of the charge "
                "(2026-07-01)."
            ]
        }

    def test_fixed_charge_close__closed_charge(self):
        charge = self.any_fixed_charge(end_date=date(2026, 6, 30))

        response = self.close(charge)

        assert response.status_code == 400
        assert response.json() == {"detail": "This charge is already closed."}


class TestFixedChargeUpdate(FixedChargeTestCase):

    def patch(self, charge, data):
        restaurant = charge.restaurant
        return self.client.patch(
            self.url(restaurant, f"{charge.pk}/"),
            data=data,
            format="json",
            **self.auth(restaurant),
        )

    def test_fixed_charge_rename_in_place(self):
        charge = self.any_fixed_charge()

        response = self.patch(charge, {"name": "Loyer emplacement"})

        assert response.status_code == 200
        assert response.json()["pk"] == str(charge.pk)
        assert response.json()["name"] == "Loyer emplacement"

    def test_fixed_charge_patch__only_name(self):
        charge = self.any_fixed_charge()

        for data in [
            {"amount": 350},
            {"frequency": "YEARLY"},
            {"start_date": "2026-02-01"},
        ]:
            with self.subTest(data=data):
                response = self.patch(charge, {"name": "Loyer", **data})

                assert response.status_code == 400
                assert response.json() == {
                    "detail": "Only the name can be changed in place: "
                    "revise the charge instead."
                }

    def test_fixed_charge_put_and_delete_not_allowed(self):
        charge = self.any_fixed_charge()
        url = self.url(charge.restaurant, f"{charge.pk}/")
        auth = self.auth(charge.restaurant)

        assert self.client.put(url, {}, format="json", **auth).status_code == 405
        assert self.client.delete(url, **auth).status_code == 405


class TestFixedChargeOwnership(FixedChargeTestCase):

    def test_fixed_charge__other_owner_restaurant_is_not_found(self):
        charge = self.any_fixed_charge()
        restaurant = charge.restaurant
        auth = self.auth(restaurant, user=self.any_user())
        requests = {
            "list": lambda: self.client.get(self.url(restaurant), **auth),
            "create": lambda: self.client.post(
                self.url(restaurant),
                {"name": "Loyer", "amount": 300, "frequency": "MONTHLY"},
                format="json",
                **auth,
            ),
            "rename": lambda: self.client.patch(
                self.url(restaurant, f"{charge.pk}/"),
                {"name": "Volé"},
                format="json",
                **auth,
            ),
            "revise": lambda: self.client.post(
                self.url(restaurant, f"{charge.pk}/revise/"),
                {"amount": 1},
                format="json",
                **auth,
            ),
            "close": lambda: self.client.post(
                self.url(restaurant, f"{charge.pk}/close/"), {}, format="json", **auth
            ),
        }

        for name, request in requests.items():
            with self.subTest(name):
                assert request().status_code == 404

        charge.refresh_from_db()
        assert (charge.name, charge.end_date) == ("Loyer", None)
