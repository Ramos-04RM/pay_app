"""Tests for payment service layer — filtering, sorting, URL building."""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from pay_app.models import Cabinet, Pay
from pay_app.services.constants import PAY_MODE_ALL, PAY_MODE_OVERDUE, PAY_MODE_UPCOMING, PAY_SORT_DEFAULT
from pay_app.services.payments import (
    build_pay_list_url,
    build_pay_queryset,
    get_default_statuses_for_mode,
    get_pay_base_url_name,
    get_pay_list_state,
    toggle_binary_filter,
)


TEST_KEY = 'test-encryption-key-32chars!!'


class GetDefaultStatusesTests(TestCase):
    """Verify default status set per pay list mode."""

    def test_all_mode_returns_active(self) -> None:
        self.assertEqual(get_default_statuses_for_mode(PAY_MODE_ALL), ['active'])

    def test_upcoming_mode_returns_active(self):
        self.assertEqual(get_default_statuses_for_mode(PAY_MODE_UPCOMING), ['active'])

    def test_overdue_mode_returns_both(self):
        self.assertEqual(get_default_statuses_for_mode(PAY_MODE_OVERDUE), ['active', 'not active'])


class ToggleBinaryFilterTests(TestCase):
    """Verify yes/no toggle helper behavior."""

    def test_toggle_on(self) -> None:
        result = toggle_binary_filter(['no'], 'yes')
        self.assertIn('yes', result)
        self.assertIn('no', result)

    def test_toggle_off(self):
        result = toggle_binary_filter(['yes', 'no'], 'yes')
        self.assertEqual(result, ['no'])

    def test_empty(self):
        result = toggle_binary_filter([], 'yes')
        self.assertEqual(result, ['yes'])


class BuildPayListUrlTests(TestCase):
    """Verify pay-list URL construction from state fragments."""

    def test_default_url(self) -> None:
        url = build_pay_list_url()
        self.assertEqual(url, reverse('app:index'))

    def test_url_with_mode(self):
        url = build_pay_list_url(mode=PAY_MODE_UPCOMING)
        self.assertIn('filter', url)

    def test_url_with_search(self):
        url = build_pay_list_url(q='test')
        self.assertIn('q=test', url)

    def test_url_with_statuses(self):
        url = build_pay_list_url(statuses=['active', 'not active'])
        self.assertIn('status=active', url)

    def test_url_with_sort(self):
        url = build_pay_list_url(sort='service_asc')
        self.assertIn('sort=service_asc', url)


class GetPayBaseUrlTests(TestCase):
    """Verify mode to base-route mapping."""

    def test_all_mode(self) -> None:
        self.assertEqual(get_pay_base_url_name(PAY_MODE_ALL), 'app:index')

    def test_upcoming_mode(self):
        self.assertEqual(get_pay_base_url_name(PAY_MODE_UPCOMING), 'app:filter_by_date')

    def test_overdue_mode(self):
        self.assertEqual(get_pay_base_url_name(PAY_MODE_OVERDUE), 'app:overdue_payments')


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class GetPayListStateTests(TestCase):
    """Validate query-string parsing and fallback behavior for pay list state."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')
        self.factory = RequestFactory()

    def test_defaults(self):
        request = self.factory.get('/')
        state = get_pay_list_state(request)
        self.assertEqual(state['mode'], PAY_MODE_ALL)
        self.assertEqual(state['selected_statuses'], ['active'])
        self.assertEqual(state['current_sort'], PAY_SORT_DEFAULT)

    def test_overrides_apply(self):
        request = self.factory.get('/')
        state = get_pay_list_state(request, overrides={'q': 'test', 'status': ['active', 'not active']})
        self.assertEqual(state['search_query'], 'test')
        self.assertEqual(state['selected_statuses'], ['active', 'not active'])

    def test_invalid_mode_falls_back(self):
        request = self.factory.get('/', {'mode': 'invalid'})
        state = get_pay_list_state(request)
        self.assertEqual(state['mode'], PAY_MODE_ALL)

    def test_invalid_sort_falls_back(self):
        request = self.factory.get('/', {'sort': 'nonexistent'})
        state = get_pay_list_state(request)
        self.assertEqual(state['current_sort'], PAY_SORT_DEFAULT)


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class BuildPayQuerysetTests(TestCase):
    """Validate queryset filtering/sorting behavior for pay list service layer."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')
        self.factory = RequestFactory()
        self.cabinet = Cabinet.objects.create(
            link='https://a.example.com', login='cab', password='p',
            email_login='a@e.com', email_password='ep',
            balance=100, currency='USD $',
        )
        self.pay_active = Pay.objects.create(
            cabinet=self.cabinet, groups='g', service='Active',
            type_source='VPS', price_per_month=10, currency='USD $',
            pay_sys='BTC', paid_up_to=date.today() + timedelta(days=5),
            status='active', email_login='e@e.com', password='p', ip='1.1.1.1',
        )
        self.pay_inactive = Pay.objects.create(
            cabinet=self.cabinet, groups='g', service='Inactive',
            type_source='site', price_per_month=20, currency='USD $',
            pay_sys='WM', paid_up_to=date.today() - timedelta(days=3),
            status='not active', email_login='e@e.com', password='p', ip='2.2.2.2',
        )

    def test_default_shows_active_only(self):
        request = self.factory.get('/')
        qs, state, _ = build_pay_queryset(request)
        ids = list(qs.values_list('id', flat=True))
        self.assertIn(self.pay_active.id, ids)
        self.assertNotIn(self.pay_inactive.id, ids)

    def test_overdue_mode(self):
        request = self.factory.get('/')
        qs, state, _ = build_pay_queryset(request, default_mode=PAY_MODE_OVERDUE)
        ids = list(qs.values_list('id', flat=True))
        self.assertIn(self.pay_inactive.id, ids)

    def test_search_by_service(self):
        request = self.factory.get('/', {'q': 'Active'})
        qs, _, _ = build_pay_queryset(request)
        services = list(qs.values_list('service', flat=True))
        self.assertIn('Active', services)

    def test_filter_by_pay_sys(self):
        request = self.factory.get('/')
        qs, _, _ = build_pay_queryset(request, overrides={'pay_sys': 'BTC'})
        for pay in qs:
            self.assertEqual(pay.pay_sys, 'BTC')

    def test_filter_by_type_source(self):
        request = self.factory.get('/')
        qs, _, _ = build_pay_queryset(request, overrides={
            'type_source': 'VPS',
            'status': ['active', 'not active'],
        })
        for pay in qs:
            self.assertEqual(pay.type_source, 'VPS')

