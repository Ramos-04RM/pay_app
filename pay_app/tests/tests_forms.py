"""Tests for Django forms validation (PayForm, CabinetForm, TagForm)."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import translation

from pay_app.forms import CabinetForm, CabinetTagAssignForm, PayForm, TagForm
from pay_app.models import Cabinet, Tag


TEST_KEY = 'test-encryption-key-32chars!!'


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class PayFormTests(TestCase):
    """Validate pay form required fields, decimal rules, and locale-safe dates."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')
        self.cabinet = Cabinet.objects.create(
            link='https://example.com', login='cab', password='p',
            email_login='e@e.com', email_password='ep',
            balance=0, currency='USD $',
        )

    def _base_data(self, **overrides: Any) -> dict[str, Any]:
        data = {
            'cabinet': self.cabinet.id,
            'groups': 'grp',
            'create_date': date.today().isoformat(),
            'service': 'Svc',
            'type_source': 'VPS',
            'price_per_month': '10.00',
            'currency': 'USD $',
            'pay_sys': 'BTC',
            'paid_up_to': (date.today() + timedelta(days=30)).isoformat(),
            'status': 'active',
            'email_login': 'u@e.com',
            'password': 'pass',
            'ip': '1.2.3.4',
            'note_pay': '',
        }
        data.update(overrides)
        return data

    def test_valid_form(self) -> None:
        form = PayForm(data=self._base_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_service_invalid(self):
        form = PayForm(data=self._base_data(service=''))
        self.assertFalse(form.is_valid())
        self.assertIn('service', form.errors)

    def test_negative_price_invalid(self):
        form = PayForm(data=self._base_data(price_per_month='-5'))
        self.assertFalse(form.is_valid())

    def test_zero_price_invalid(self):
        form = PayForm(data=self._base_data(price_per_month='0'))
        self.assertFalse(form.is_valid())

    def test_comma_decimal_rejected_by_number_input(self):
        form = PayForm(data=self._base_data(price_per_month='10,50'))
        self.assertFalse(form.is_valid())
        self.assertIn('price_per_month', form.errors)

    def test_too_many_decimal_places(self):
        form = PayForm(data=self._base_data(price_per_month='10.123'))
        self.assertFalse(form.is_valid())

    def test_missing_password_invalid(self):
        form = PayForm(data=self._base_data(password=''))
        self.assertFalse(form.is_valid())

    def test_invalid_type_source(self):
        form = PayForm(data=self._base_data(type_source='invalid'))
        self.assertFalse(form.is_valid())

    def test_invalid_status(self):
        form = PayForm(data=self._base_data(status='unknown'))
        self.assertFalse(form.is_valid())

    def test_dates_render_iso_under_ukrainian_locale(self):
        pay = self.cabinet.pay_set.create(
            groups='grp',
            create_date=date(2026, 4, 20),
            service='Svc',
            type_source='VPS',
            price_per_month='10.00',
            currency='USD $',
            pay_sys='BTC',
            paid_up_to=date(2026, 5, 20),
            status='active',
            email_login='u@e.com',
            password='pass',
            ip='1.2.3.4',
            note_pay='',
        )

        with translation.override('uk'):
            form = PayForm(instance=pay)

        self.assertIn('value="2026-04-20"', str(form['create_date']))
        self.assertIn('value="2026-05-20"', str(form['paid_up_to']))
        self.assertFalse(form.fields['create_date'].localize)
        self.assertFalse(form.fields['paid_up_to'].localize)


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class CabinetFormTests(TestCase):
    """Validate cabinet form required fields and URL/email constraints."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')

    def _base_data(self, **overrides: Any) -> dict[str, Any]:
        data = {
            'link': 'https://test.com',
            'login': 'cab-login',
            'password': 'cab-pass',
            'email_login': 'cab@test.com',
            'email_password': 'mail-pass',
            'balance': '50.00',
            'currency': 'USD $',
            'note': '',
            'is_daily_payment': False,
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = CabinetForm(data=self._base_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_login_invalid(self):
        form = CabinetForm(data=self._base_data(login=''))
        self.assertFalse(form.is_valid())

    def test_missing_password_invalid(self):
        form = CabinetForm(data=self._base_data(password=''))
        self.assertFalse(form.is_valid())

    def test_invalid_email(self):
        form = CabinetForm(data=self._base_data(email_login='not-an-email'))
        self.assertFalse(form.is_valid())

    def test_invalid_link(self):
        form = CabinetForm(data=self._base_data(link='not-a-url'))
        self.assertFalse(form.is_valid())


class TagFormTests(TestCase):
    """Validate tag naming rules and uniqueness behavior."""

    def test_valid_tag(self):
        form = TagForm(data={'name': 'New Tag', 'note': ''})
        self.assertTrue(form.is_valid(), form.errors)

    def test_empty_name_invalid(self):
        form = TagForm(data={'name': '', 'note': ''})
        self.assertFalse(form.is_valid())

    def test_whitespace_name_invalid(self):
        form = TagForm(data={'name': '   ', 'note': ''})
        self.assertFalse(form.is_valid())

    def test_duplicate_name_invalid(self):
        Tag.objects.create(name='Existing')
        form = TagForm(data={'name': 'Existing', 'note': ''})
        self.assertFalse(form.is_valid())


class CabinetTagAssignFormTests(TestCase):
    """Validate multiple tag selection assignment form."""

    def test_empty_tags_valid(self):
        form = CabinetTagAssignForm(data={'tags': []})
        self.assertTrue(form.is_valid())

    def test_valid_tag_selection(self):
        t1 = Tag.objects.create(name='T1')
        t2 = Tag.objects.create(name='T2')
        form = CabinetTagAssignForm(data={'tags': [t1.id, t2.id]})
        self.assertTrue(form.is_valid())
        self.assertEqual(set(form.cleaned_data['tags']), {t1, t2})

