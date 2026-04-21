"""Unit tests for pay_app.services.cabinets."""

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings

from pay_app.models import Cabinet, CabinetTag, Pay, Tag
from pay_app.services.cabinets import (
    build_cabinet_page_context,
    build_cabinet_page_url,
    extract_prefixed_cabinet_form_data,
    parse_tag_ids,
    replace_cabinet_tags,
)


TEST_KEY = 'test-encryption-key-32chars!!'


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class CabinetHelpersTests(TestCase):
    """Validate cabinet helper utilities for filters, tags, and context generation."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')

        self.tag_fast = Tag.objects.create(name='Fast')
        self.tag_slow = Tag.objects.create(name='Slow')

        self.cab_a = Cabinet.objects.create(
            link='https://a.example.com',
            login='cab-a',
            password='p1',
            email_login='a@example.com',
            email_password='ep1',
            balance=120,
            currency='USD $',
            is_daily_payment=True,
            note='alpha note',
        )
        self.cab_b = Cabinet.objects.create(
            link='https://b.example.com',
            login='cab-b',
            password='p2',
            email_login='b@example.com',
            email_password='ep2',
            balance=10,
            currency='EURO €',
            is_daily_payment=False,
            note='beta note',
        )

        CabinetTag.objects.create(cabinet=self.cab_a, tag=self.tag_fast)
        CabinetTag.objects.create(cabinet=self.cab_b, tag=self.tag_slow)

        Pay.objects.create(
            cabinet=self.cab_a,
            groups='g1',
            service='Service Alpha',
            type_source='VPS',
            price_per_month=30,
            currency='USD $',
            pay_sys='BTC',
            paid_up_to=date.today() + timedelta(days=7),
            status='active',
            email_login='svc-a@example.com',
            password='pass-a',
            ip='1.1.1.1',
        )
        Pay.objects.create(
            cabinet=self.cab_b,
            groups='g2',
            service='Service Beta',
            type_source='site',
            price_per_month=60,
            currency='EURO €',
            pay_sys='WM',
            paid_up_to=date.today() - timedelta(days=2),
            status='not active',
            email_login='svc-b@example.com',
            password='pass-b',
            ip='2.2.2.2',
        )

        self.factory = RequestFactory()

    def test_build_cabinet_page_url_with_filters(self):
        url = build_cabinet_page_url(
            q='cab',
            has_active=True,
            tag_ids=[self.tag_fast.id, self.tag_slow.id],
            sort='login_asc',
            currency='USD $',
            balance_min='10',
            balance_max='200',
        )
        self.assertIn('q=cab', url)
        self.assertIn('has_active=1', url)
        self.assertIn('tag_id=', url)
        self.assertIn('sort=login_asc', url)
        self.assertIn('currency=USD+', url)

    def test_parse_tag_ids_ignores_invalid_values(self):
        parsed = parse_tag_ids(['1', 'x', '', None, '2'])
        self.assertEqual(parsed, [1, 2])

    def test_extract_prefixed_cabinet_form_data(self):
        data = {
            'cabinet_login': 'my-login',
            'cabinet_email_login': 'x@example.com',
            'other_field': 'ignored',
        }
        extracted = extract_prefixed_cabinet_form_data(data)
        self.assertEqual(extracted, {'login': 'my-login', 'email_login': 'x@example.com'})

    def test_replace_cabinet_tags_replaces_all(self):
        replace_cabinet_tags(self.cab_a, [self.tag_slow])
        ids = list(CabinetTag.objects.filter(cabinet=self.cab_a).values_list('tag_id', flat=True))
        self.assertEqual(ids, [self.tag_slow.id])

    def test_build_cabinet_page_context_filters_by_tag_and_currency(self):
        request = self.factory.get('/cabinet/', {
            'tag_id': [str(self.tag_fast.id)],
            'currency': 'USD $',
        })
        context = build_cabinet_page_context(request)
        ids = list(context['object_k'].values_list('id', flat=True))
        self.assertEqual(ids, [self.cab_a.id])

    def test_build_cabinet_page_context_searches_by_service_name(self):
        request = self.factory.get('/cabinet/', {'q': 'Alpha'})
        context = build_cabinet_page_context(request)
        ids = list(context['object_k'].values_list('id', flat=True))
        self.assertIn(self.cab_a.id, ids)
        self.assertNotIn(self.cab_b.id, ids)

    def test_build_cabinet_page_context_balance_range(self):
        request = self.factory.get('/cabinet/', {'balance_min': '100', 'balance_max': '150'})
        context = build_cabinet_page_context(request)
        ids = list(context['object_k'].values_list('id', flat=True))
        self.assertEqual(ids, [self.cab_a.id])

