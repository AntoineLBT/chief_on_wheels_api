"""Fixed charge breakdown, independent of the ORM.

Every day bears `monthly / days in its month` of the MONTHLY and YEARLY
(= /12) charges active that day, so a full month bears 100 % of them and a
week or a partial month bears them pro rata. PER_SHIFT charges are borne by
each shift falling within their validity.

Amounts stay exact (Fraction) until `cents`, which rounds once per figure.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Iterable

from restaurants.constants import FixedChargeFrequency


@dataclass(frozen=True)
class Charge:
    amount: Decimal
    frequency: str
    start_date: date
    # Inclusive; None while the charge is active.
    end_date: date | None = None

    def applies_on(self, day: date) -> bool:
        return self.start_date <= day and (
            self.end_date is None or day <= self.end_date
        )

    @property
    def monthly_amount(self) -> Fraction:
        if self.frequency == FixedChargeFrequency.YEARLY:
            return Fraction(self.amount) / 12
        return Fraction(self.amount)


def cents(amount: Fraction) -> Decimal:
    """Round an exact amount to the cent, half up."""
    exact = Decimal(amount.numerator) / Decimal(amount.denominator)
    return exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def days(start: date, end: date) -> Iterable[date]:
    """Every day from start to end, both included."""
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


def daily_charges(charges: list[Charge], day: date) -> Fraction:
    """Share of the MONTHLY and YEARLY charges borne by one day."""
    monthly = sum(
        (
            c.monthly_amount
            for c in charges
            if c.frequency != FixedChargeFrequency.PER_SHIFT and c.applies_on(day)
        ),
        Fraction(0),
    )
    return monthly / monthrange(day.year, day.month)[1]


def per_shift_charges(charges: list[Charge], day: date) -> Fraction:
    """PER_SHIFT charges borne by a shift on that day."""
    return sum(
        (
            Fraction(c.amount)
            for c in charges
            if c.frequency == FixedChargeFrequency.PER_SHIFT and c.applies_on(day)
        ),
        Fraction(0),
    )


def period_fixed_charges(
    charges: list[Charge], shift_days: list[date], start: date, end: date
) -> Fraction:
    """Fixed charges borne by the days from start to end, both included, and
    by the shifts among shift_days falling within them."""
    periodic = sum(
        (daily_charges(charges, day) for day in days(start, end)), Fraction(0)
    )
    per_shift = sum(
        (per_shift_charges(charges, day) for day in shift_days if start <= day <= end),
        Fraction(0),
    )
    return periodic + per_shift


def month_bounds(day: date) -> tuple[date, date]:
    last = monthrange(day.year, day.month)[1]
    return day.replace(day=1), day.replace(day=last)


def shift_fixed_charges(
    charges: list[Charge], shift_days: list[date], shift_day: date
) -> Fraction:
    """PER_SHIFT charges of the shift, plus an equal share, among the shifts
    of its month, of the MONTHLY and YEARLY charges of that month."""
    start, end = month_bounds(shift_day)
    shifts_in_month = sum(1 for day in shift_days if start <= day <= end)
    monthly = sum(
        (daily_charges(charges, day) for day in days(start, end)), Fraction(0)
    )
    return per_shift_charges(charges, shift_day) + monthly / shifts_in_month
