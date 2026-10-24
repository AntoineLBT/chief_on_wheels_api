from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.test import APIClient

from restaurants.constants import OrderIngredientActionType, OrderStatus
from restaurants.models import Order, OrderIngredient, OrderRecipe, Shift
from restaurants.tests.fixtures import (FixedChargeFixture,
                                        RecipeIngredientFixture)

UTC = ZoneInfo("UTC")


class AccountingTestCase(TestCase, FixedChargeFixture, RecipeIngredientFixture):

    client_class = APIClient

    def setUp(self):
        self.restaurant = self.any_restaurant()
        self.recipe = self.any_recipe(self.restaurant)
        self.ingredient = self.any_ingredient("mozzarella", self.restaurant)

    def get(self, params, restaurant=None, user=None):
        restaurant = restaurant or self.restaurant
        token = self.any_token(user or restaurant.owner)
        return self.client.get(
            f"/restaurants/{restaurant.pk}/accounting/",
            params,
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def shift(self, when: datetime, vat_rate="0", restaurant=None):
        return Shift.objects.create(
            restaurant=restaurant or self.restaurant,
            date=when,
            vat_rate=Decimal(vat_rate),
        )

    def sale(
        self,
        shift,
        price,
        cost,
        extra_price="0",
        extra_cost="0",
        picking_time=None,
        status=OrderStatus.DONE,
    ):
        """One order of one recipe, with one ADD extra."""
        order = Order.objects.create(
            shift=shift,
            customer_name="Jean",
            picking_time=picking_time or shift.date,
            status=status,
        )
        order_recipe = OrderRecipe.objects.create(
            order=order,
            recipe=self.recipe,
            unit_price=Decimal(price),
            unit_cost=Decimal(cost),
        )
        OrderIngredient.objects.create(
            order_recipe=order_recipe,
            ingredient=self.ingredient,
            action_type=OrderIngredientActionType.ADD,
            extra_price=Decimal(extra_price),
            extra_cost=Decimal(extra_cost),
        )
        return order


class TestAccountingMonth(AccountingTestCase):

    def test_month_totals(self):
        self.any_fixed_charge(self.restaurant)  # 300 MONTHLY since 2026-01-01
        s1 = self.shift(datetime(2026, 10, 10, 10, tzinfo=UTC), vat_rate="10")
        self.sale(s1, "100", "30", extra_price="10", extra_cost="2")
        s2 = self.shift(datetime(2026, 10, 17, 10, tzinfo=UTC))
        self.sale(s2, "50", "10")
        # September: excluded.
        self.sale(self.shift(datetime(2026, 9, 30, 10, tzinfo=UTC)), "999", "1")

        response = self.get({"period": "month", "date": "2026-10-15"})

        assert response.status_code == 200
        assert response.json()["period"] == "month"
        assert response.json()["start"] == "2026-10-01"
        assert response.json()["end"] == "2026-10-31"
        assert response.json()["totals"] == {
            "revenue_incl_vat": 160,
            # 110 at 10 % + 50 at 0 %
            "revenue_excl_vat": 150,
            "material_cost": 42,
            "fixed_charges": 300,
            "profit": -192,
            "shift_count": 2,
            "order_count": 2,
        }

    def test_month_breakdown_lists_its_shifts(self):
        self.any_fixed_charge(self.restaurant)  # 300 MONTHLY
        s1 = self.shift(datetime(2026, 10, 17, 10, tzinfo=UTC))
        self.sale(s1, "50", "10")
        s2 = self.shift(datetime(2026, 10, 10, 10, tzinfo=UTC), vat_rate="10")
        self.sale(s2, "110", "30")

        response = self.get({"period": "month", "date": "2026-10-01"})

        assert response.json()["breakdown"] == [
            {
                "shift": str(s2.pk),
                "date": "2026-10-10",
                "revenue_incl_vat": 110,
                "revenue_excl_vat": 100,
                "material_cost": 30,
                "fixed_charges": 150,
                "profit": -80,
                "shift_count": 1,
                "order_count": 1,
            },
            {
                "shift": str(s1.pk),
                "date": "2026-10-17",
                "revenue_incl_vat": 50,
                "revenue_excl_vat": 50,
                "material_cost": 10,
                "fixed_charges": 150,
                "profit": -110,
                "shift_count": 1,
                "order_count": 1,
            },
        ]

    def test_month_without_shift_shows_its_charges(self):
        self.any_fixed_charge(self.restaurant)

        response = self.get({"period": "month", "date": "2026-10-01"})

        assert response.json()["breakdown"] == [
            {
                "shift": None,
                "date": None,
                "revenue_incl_vat": 0,
                "revenue_excl_vat": 0,
                "material_cost": 0,
                "fixed_charges": 300,
                "profit": -300,
                "shift_count": 0,
                "order_count": 0,
            }
        ]


class TestAccountingDoneOrders(AccountingTestCase):

    def test_only_done_orders_count(self):
        shift = self.shift(datetime(2026, 10, 10, 10, tzinfo=UTC))
        self.sale(shift, "100", "30", extra_price="10", extra_cost="2")
        self.sale(shift, "50", "10", status=OrderStatus.TODO)
        self.sale(shift, "40", "8", status=OrderStatus.IN_PROGRESS)

        totals = self.get({"period": "month", "date": "2026-10-01"}).json()["totals"]

        assert totals["revenue_incl_vat"] == 110
        assert totals["material_cost"] == 32
        assert totals["order_count"] == 1

    def test_shift_without_done_order_still_bears_its_charges(self):
        self.any_fixed_charge(self.restaurant)  # 300 MONTHLY
        shift = self.shift(datetime(2026, 10, 10, 10, tzinfo=UTC))
        self.sale(shift, "50", "10", status=OrderStatus.TODO)

        response = self.get({"period": "month", "date": "2026-10-01"}).json()

        assert response["totals"]["shift_count"] == 1
        assert response["totals"]["order_count"] == 0
        assert response["breakdown"][0]["shift"] == str(shift.pk)
        assert response["breakdown"][0]["fixed_charges"] == 300
        assert response["breakdown"][0]["revenue_incl_vat"] == 0


class TestAccountingWeek(AccountingTestCase):

    def test_week_across_two_months(self):
        self.any_fixed_charge(self.restaurant)  # 300 MONTHLY
        # Wednesday 30 September and Saturday 3 October 2026.
        s1 = self.shift(datetime(2026, 9, 30, 10, tzinfo=UTC))
        s2 = self.shift(datetime(2026, 10, 3, 10, tzinfo=UTC))
        self.shift(datetime(2026, 10, 5, 10, tzinfo=UTC))  # next week

        response = self.get({"period": "week", "date": "2026-10-01"})

        assert response.json()["start"] == "2026-09-28"
        assert response.json()["end"] == "2026-10-04"
        # 300 × 3/30 + 300 × 4/31
        assert response.json()["totals"]["fixed_charges"] == 68.71
        assert [
            (row["shift"], row["date"]) for row in response.json()["breakdown"]
        ] == [
            (str(s1.pk), "2026-09-30"),
            (str(s2.pk), "2026-10-03"),
        ]


@patch("django.utils.timezone.localdate", return_value=date(2026, 10, 25))
class TestAccountingYear(AccountingTestCase):

    def test_year_breakdown_by_month(self, _):
        self.any_fixed_charge(self.restaurant)  # 300 MONTHLY since 2026-01-01
        self.sale(self.shift(datetime(2026, 3, 14, 10, tzinfo=UTC)), "100", "20")

        response = self.get({"period": "year", "date": "2026-06-01"})

        assert (response.json()["start"], response.json()["end"]) == (
            "2026-01-01",
            "2026-12-31",
        )
        assert response.json()["totals"]["fixed_charges"] == 3600
        months = response.json()["breakdown"]
        assert [(m["start"], m["end"]) for m in months][:2] == [
            ("2026-01-01", "2026-01-31"),
            ("2026-02-01", "2026-02-28"),
        ]
        assert [m["status"] for m in months] == ["past"] * 9 + ["current"] + [
            "future"
        ] * 2
        assert [m["fixed_charges"] for m in months] == [300] * 12
        assert months[2]["revenue_incl_vat"] == 100

    def test_year_to_date(self, _):
        self.any_fixed_charge(self.restaurant)  # 300 MONTHLY
        self.sale(self.shift(datetime(2026, 3, 14, 10, tzinfo=UTC)), "100", "20")

        response = self.get({"period": "year", "date": "2026-06-01"})

        # 9 months + 25 days of October (31 days).
        assert response.json()["to_date"] == {
            "revenue_incl_vat": 100,
            "revenue_excl_vat": 100,
            "material_cost": 20,
            "fixed_charges": 2941.94,
            "profit": -2861.94,
            "shift_count": 1,
            "order_count": 1,
        }

    def test_past_and_future_years_to_date(self, _):
        self.any_fixed_charge(self.restaurant, start_date=date(2025, 1, 1))

        past = self.get({"period": "year", "date": "2025-06-01"}).json()
        future = self.get({"period": "year", "date": "2027-06-01"}).json()

        assert past["to_date"] == past["totals"]
        assert {m["status"] for m in past["breakdown"]} == {"past"}
        assert future["to_date"]["fixed_charges"] == 0
        assert {m["status"] for m in future["breakdown"]} == {"future"}


class TestAccountingShift(AccountingTestCase):

    def test_shift_figures_and_orders(self):
        self.any_fixed_charge(self.restaurant)  # 300 MONTHLY
        shift = self.shift(datetime(2026, 10, 10, 10, tzinfo=UTC), vat_rate="10")
        o2 = self.sale(
            shift, "55", "12", picking_time=datetime(2026, 10, 10, 11, tzinfo=UTC)
        )
        o1 = self.sale(shift, "100", "30", extra_price="10", extra_cost="2")
        # Another shift of the month: halves the monthly share.
        self.shift(datetime(2026, 10, 17, 10, tzinfo=UTC))

        response = self.get({"period": "shift", "shift": str(shift.pk)})

        assert response.status_code == 200
        assert response.json()["period"] == "shift"
        assert response.json()["shift"] == str(shift.pk)
        assert response.json()["start"] == "2026-10-10"
        assert response.json()["end"] == "2026-10-10"
        assert response.json()["totals"] == {
            "revenue_incl_vat": 165,
            "revenue_excl_vat": 150,
            "material_cost": 44,
            "fixed_charges": 150,
            "profit": -44,
            "shift_count": 1,
            "order_count": 2,
        }
        assert response.json()["breakdown"] == [
            {
                "order": str(o1.pk),
                "customer_name": "Jean",
                "picking_time": "2026-10-10T12:00:00+02:00",
                "status": "DONE",
                "amount": 110,
                "cost": 32,
            },
            {
                "order": str(o2.pk),
                "customer_name": "Jean",
                "picking_time": "2026-10-10T13:00:00+02:00",
                "status": "DONE",
                "amount": 55,
                "cost": 12,
            },
        ]

    def test_shift_of_another_restaurant(self):
        other = self.any_restaurant(self.restaurant.owner)
        shift = self.shift(datetime(2026, 10, 10, 10, tzinfo=UTC), restaurant=other)

        response = self.get({"period": "shift", "shift": str(shift.pk)})

        assert response.status_code == 404

    def test_shift_lists_orders_that_do_not_count(self):
        shift = self.shift(datetime(2026, 10, 10, 10, tzinfo=UTC))
        done = self.sale(shift, "100", "30")
        todo = self.sale(
            shift,
            "50",
            "10",
            picking_time=datetime(2026, 10, 10, 11, tzinfo=UTC),
            status=OrderStatus.TODO,
        )

        response = self.get({"period": "shift", "shift": str(shift.pk)}).json()

        assert response["totals"]["order_count"] == 1
        assert [(row["order"], row["status"]) for row in response["breakdown"]] == [
            (str(done.pk), "DONE"),
            (str(todo.pk), "TODO"),
        ]


class TestAccountingShiftDay(AccountingTestCase):

    def test_shift_day_is_the_local_day(self):
        # 23:30 UTC on 31 October = 00:30 on 1 November in Paris.
        shift = self.shift(datetime(2026, 10, 31, 23, 30, tzinfo=UTC))
        self.sale(shift, "100", "20")

        october = self.get({"period": "month", "date": "2026-10-01"}).json()
        november = self.get({"period": "month", "date": "2026-11-01"}).json()

        assert october["totals"]["shift_count"] == 0
        assert november["totals"]["shift_count"] == 1
        assert november["breakdown"][0]["date"] == "2026-11-01"


class TestAccountingErrors(AccountingTestCase):

    def test_requires_authentication(self):
        response = self.client.get(f"/restaurants/{self.restaurant.pk}/accounting/")
        assert response.status_code == 401

    def test_other_owner_restaurant_is_not_found(self):
        response = self.get(
            {"period": "month", "date": "2026-10-01"}, user=self.any_user()
        )
        assert response.status_code == 404

    def test_invalid_query(self):
        for params, field in [
            ({}, "period"),
            ({"period": "day", "date": "2026-10-01"}, "period"),
            ({"period": "month"}, "date"),
            ({"period": "month", "date": "2026-13-01"}, "date"),
            ({"period": "shift"}, "shift"),
            ({"period": "shift", "shift": "not-a-uuid"}, "shift"),
        ]:
            with self.subTest(params=params):
                response = self.get(params)

                assert response.status_code == 400
                assert field in response.json()
