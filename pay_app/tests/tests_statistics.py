"""Unit tests for pay_app.services.statistics."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings

from pay_app.models import Cabinet, Pay
from pay_app.services.statistics import (
    _build_statistics_query_params,
    _calculate_proportional_cost,
    _get_period_bounds,
    _normalize_stat_period,
    _parse_iso_date,
    build_statistics_context,
)


TEST_KEY = 'test-encryption-key-32chars!!'


class StatisticsHelpersTests(TestCase):
    """Cover pure helper logic for period/date/query param utilities."""

    def test_parse_iso_date_valid_and_invalid(self) -> None:
        self.assertEqual(_parse_iso_date('2026-04-20'), date(2026, 4, 20))
        self.assertIsNone(_parse_iso_date('20-04-2026'))
        self.assertIsNone(_parse_iso_date(''))

    def test_normalize_period_fallback(self):
        self.assertEqual(_normalize_stat_period('YEAR'), 'year')
        self.assertEqual(_normalize_stat_period('unknown'), 'month')

    def test_get_period_bounds_custom_swaps_if_reversed(self):
        today = date(2026, 4, 20)
        start, end = _get_period_bounds('custom', '2026-12-01', '2026-01-01', today)
        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 12, 1))

    def test_calculate_proportional_cost_partial_month(self):
        # Active from Jan 10 to Jan 20 (11 days) in a 31-day month.
        service = SimpleNamespace(
            price_per_month=Decimal('31'),
            create_date=date(2026, 1, 10),
            paid_up_to=date(2026, 1, 20),
        )
        cost = _calculate_proportional_cost(service, date(2026, 1, 1), date(2026, 1, 31))
        self.assertEqual(cost, Decimal('11'))

    def test_build_statistics_query_params_includes_only_non_empty(self):
        query = _build_statistics_query_params({
            'currency': 'USD $',
            'status': 'active',
            'groups': 'g1',
            'cabinet': 5,
            'period': 'year',
            'start': '',
            'end': '',
        })
        self.assertIn('currency=USD+', query)
        self.assertIn('status=active', query)
        self.assertIn('group=g1', query)
        self.assertIn('cabinet=5', query)
        self.assertIn('period=year', query)
        self.assertNotIn('start=', query)


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class BuildStatisticsContextTests(TestCase):
    """Validate statistics context composition with filters and drill-down paths."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')
        self.factory = RequestFactory()

        self.cab_a = Cabinet.objects.create(
            link='https://a.example.com',
            login='cab-a',
            password='p1',
            email_login='a@example.com',
            email_password='ep1',
            balance=100,
            currency='USD $',
        )
        self.cab_b = Cabinet.objects.create(
            link='https://b.example.com',
            login='cab-b',
            password='p2',
            email_login='b@example.com',
            email_password='ep2',
            balance=100,
            currency='USD $',
        )

        today = date.today()
        self.pay_active = Pay.objects.create(
            cabinet=self.cab_a,
            groups='g1',
            service='Service Active',
            type_source='VPS',
            price_per_month=30,
            currency='USD $',
            pay_sys='BTC',
            paid_up_to=today + timedelta(days=7),
            status='active',
            email_login='active@example.com',
            password='active-pass',
            ip='1.1.1.1',
        )
        self.pay_inactive = Pay.objects.create(
            cabinet=self.cab_b,
            groups='g2',
            service='Service Inactive',
            type_source='site',
            price_per_month=40,
            currency='USD $',
            pay_sys='WM',
            paid_up_to=today + timedelta(days=35),
            status='not active',
            email_login='inactive@example.com',
            password='inactive-pass',
            ip='2.2.2.2',
        )

    def test_context_contains_core_metrics(self):
        request = self.factory.get('/statistics/')
        context = build_statistics_context(request)
        self.assertIn('burn_by_currency', context)
        self.assertIn('expiry_pipeline', context)
        self.assertIn('status_mix', context)
        self.assertIn('month_points', context)

    def test_filter_by_status_active(self):
        request = self.factory.get('/statistics/', {'status': 'active'})
        context = build_statistics_context(request)
        self.assertEqual(context['active_count'], 1)
        self.assertEqual(context['inactive_count'], 0)

    def test_filter_by_cabinet(self):
        request = self.factory.get('/statistics/', {'cabinet': str(self.cab_a.id)})
        context = build_statistics_context(request)
        self.assertEqual(context['cabinets_count'], 1)

    def test_drill_by_status(self):
        request = self.factory.get('/statistics/', {'drill': 'status', 'drill_value': 'active'})
        context = build_statistics_context(request)
        self.assertTrue(all(row['status'] == 'active' for row in context['detail_rows']))

    def test_invalid_custom_period_falls_back_to_month(self):
        request = self.factory.get('/statistics/', {
            'period': 'custom',
            'start': 'bad-date',
            'end': 'also-bad',
        })
        context = build_statistics_context(request)
        self.assertEqual(context['period'], 'custom')
        # Dates are still populated with a fallback month range.
        self.assertRegex(context['period_start'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertRegex(context['period_end'], r'^\d{4}-\d{2}-\d{2}$')

