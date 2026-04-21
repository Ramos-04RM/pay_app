"""Tests for custom template filters."""

from datetime import date

from django.test import TestCase

from pay_app.templatetags.date_filters import date_iso


class DateIsoFilterTests(TestCase):
    """Validate date_iso template filter output normalization."""

    def test_date_to_iso(self) -> None:
        self.assertEqual(date_iso(date(2026, 4, 20)), '2026-04-20')

    def test_none_returns_empty(self) -> None:
        self.assertEqual(date_iso(None), '')

    def test_non_date_returns_str(self) -> None:
        self.assertEqual(date_iso('2026/04/20'), '2026/04/20')

