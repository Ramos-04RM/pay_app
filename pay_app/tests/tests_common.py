"""Unit tests for pay_app.services.common helpers."""

from datetime import date

from django.test import TestCase

from pay_app.services.common import add_one_month


class AddOneMonthTests(TestCase):
    """Verify month-shift helper for regular and edge calendar cases."""

    def test_regular_month_increment(self) -> None:
        self.assertEqual(add_one_month(date(2026, 4, 10)), date(2026, 5, 10))

    def test_end_of_month_clamps_day(self) -> None:
        self.assertEqual(add_one_month(date(2026, 1, 31)), date(2026, 2, 28))

    def test_leap_year_february(self) -> None:
        self.assertEqual(add_one_month(date(2024, 1, 31)), date(2024, 2, 29))

    def test_december_rollover(self) -> None:
        self.assertEqual(add_one_month(date(2026, 12, 15)), date(2027, 1, 15))

