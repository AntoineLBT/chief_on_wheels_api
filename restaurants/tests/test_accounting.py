from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from restaurants.accounting import (Charge, cents, period_fixed_charges,
                                    shift_fixed_charges)
from restaurants.constants import FixedChargeFrequency

OCTOBER = (date(2026, 10, 1), date(2026, 10, 31))


def charge(amount, frequency, start=date(2026, 1, 1), end=None):
    return Charge(Decimal(amount), frequency, start, end)


RENT = charge("300", FixedChargeFrequency.MONTHLY)
INSURANCE = charge("1200", FixedChargeFrequency.YEARLY)
CLEANING = charge("50", FixedChargeFrequency.PER_SHIFT)


class TestPeriodFixedCharges(SimpleTestCase):

    def test_month_without_shift(self):
        total = period_fixed_charges([RENT, INSURANCE, CLEANING], [], *OCTOBER)

        assert cents(total) == Decimal("400.00")

    def test_month_with_shifts(self):
        shift_days = [date(2026, 10, 3), date(2026, 10, 10), date(2026, 10, 17)]

        total = period_fixed_charges([RENT, INSURANCE, CLEANING], shift_days, *OCTOBER)

        assert cents(total) == Decimal("550.00")

    def test_shifts_outside_the_period_bear_nothing(self):
        shift_days = [date(2026, 9, 30), date(2026, 11, 1)]

        total = period_fixed_charges([CLEANING], shift_days, *OCTOBER)

        assert total == 0

    def test_charge_revised_during_the_month(self):
        charges = [
            charge("300", FixedChargeFrequency.MONTHLY, end=date(2026, 10, 15)),
            charge("350", FixedChargeFrequency.MONTHLY, start=date(2026, 10, 16)),
        ]

        total = period_fixed_charges(charges, [], *OCTOBER)

        # 300 × 15/31 + 350 × 16/31
        assert cents(total) == Decimal("325.81")

    def test_charge_opened_or_closed_during_the_month(self):
        cases = [
            # Opened on the 22nd: 10 days of 31.
            (
                charge("310", FixedChargeFrequency.MONTHLY, start=date(2026, 10, 22)),
                "100.00",
            ),
            # Closed on the 10th, included: 10 days of 31.
            (
                charge("310", FixedChargeFrequency.MONTHLY, end=date(2026, 10, 10)),
                "100.00",
            ),
            # Open and closed the same day.
            (
                charge(
                    "310",
                    FixedChargeFrequency.MONTHLY,
                    start=date(2026, 10, 5),
                    end=date(2026, 10, 5),
                ),
                "10.00",
            ),
        ]
        for rent, expected in cases:
            with self.subTest(rent=rent):
                assert cents(period_fixed_charges([rent], [], *OCTOBER)) == Decimal(
                    expected
                )

    def test_charge_outside_the_period(self):
        charges = [
            charge("300", FixedChargeFrequency.MONTHLY, end=date(2026, 9, 30)),
            charge("300", FixedChargeFrequency.MONTHLY, start=date(2026, 11, 1)),
            charge(
                "50",
                FixedChargeFrequency.PER_SHIFT,
                start=date(2026, 10, 20),
            ),
        ]

        total = period_fixed_charges(charges, [date(2026, 10, 3)], *OCTOBER)

        assert total == 0

    def test_week_across_two_months(self):
        total = period_fixed_charges([RENT], [], date(2026, 9, 28), date(2026, 10, 4))

        # 300 × 3/30 + 300 × 4/31
        assert cents(total) == Decimal("68.71")

    def test_year_is_the_sum_of_its_months(self):
        charges = [
            charge("300", FixedChargeFrequency.MONTHLY, end=date(2026, 6, 30)),
            charge("350", FixedChargeFrequency.MONTHLY, start=date(2026, 7, 1)),
            INSURANCE,
        ]

        total = period_fixed_charges(charges, [], date(2026, 1, 1), date(2026, 12, 31))

        # 6 × 300 + 6 × 350 + 1200
        assert cents(total) == Decimal("5100.00")


class TestShiftFixedCharges(SimpleTestCase):

    OCTOBER_SHIFTS = [date(2026, 10, d) for d in (3, 10, 17, 24)]

    def test_shift_bears_its_share_of_the_month(self):
        # Shifts of other months do not dilute October's share.
        shift_days = [date(2026, 9, 26), *self.OCTOBER_SHIFTS, date(2026, 11, 7)]

        total = shift_fixed_charges([RENT, CLEANING], shift_days, date(2026, 10, 10))

        # 300 / 4 + 50
        assert cents(total) == Decimal("125.00")

    def test_shift_shares_the_prorated_month(self):
        charges = [
            charge("300", FixedChargeFrequency.MONTHLY, end=date(2026, 10, 15)),
            charge("350", FixedChargeFrequency.MONTHLY, start=date(2026, 10, 16)),
        ]

        total = shift_fixed_charges(charges, self.OCTOBER_SHIFTS, date(2026, 10, 3))

        # (300 × 15/31 + 350 × 16/31) / 4
        assert cents(total) == Decimal("81.45")

    def test_per_shift_charge_only_within_its_validity(self):
        cleaning = charge(
            "50",
            FixedChargeFrequency.PER_SHIFT,
            start=date(2026, 10, 5),
            end=date(2026, 10, 20),
        )

        assert [
            shift_fixed_charges([cleaning], self.OCTOBER_SHIFTS, day)
            for day in self.OCTOBER_SHIFTS
        ] == [0, 50, 50, 0]
