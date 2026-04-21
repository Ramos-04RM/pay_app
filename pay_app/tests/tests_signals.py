"""Targeted tests for signal-triggered recalculation behavior."""

from datetime import date, timedelta
from typing import Any

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from unittest.mock import patch

from pay_app.models import Cabinet, Pay


TEST_KEY = 'test-encryption-key-32chars!!'


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class SignalRecalculationTests(TestCase):
    """Verify signal handlers trigger daily-payment recalculation only when required."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')
        self.cabinet = Cabinet.objects.create(
            link='https://a.example.com',
            login='cab-a',
            password='p1',
            email_login='a@example.com',
            email_password='ep1',
            balance=100,
            currency='USD $',
            is_daily_payment=True,
        )

    def _create_pay(self, **overrides: Any) -> Pay:
        data = {
            'cabinet': self.cabinet,
            'groups': 'g',
            'service': 'svc',
            'type_source': 'VPS',
            'price_per_month': 10,
            'currency': 'USD $',
            'pay_sys': 'BTC',
            'paid_up_to': date.today() + timedelta(days=5),
            'status': 'active',
            'email_login': 'svc@example.com',
            'password': 'svc-pass',
            'ip': '1.2.3.4',
        }
        data.update(overrides)
        return Pay.objects.create(**data)

    def test_cabinet_create_with_daily_payment_triggers_recalc(self):
        with patch('pay_app.signals.recalculate_cabinet_paid_up_to') as mocked:
            cab = Cabinet.objects.create(
                link='https://b.example.com',
                login='cab-b',
                password='p2',
                email_login='b@example.com',
                email_password='ep2',
                balance=50,
                currency='USD $',
                is_daily_payment=True,
            )
        mocked.assert_called_once_with(cab.id)

    def test_cabinet_update_without_relevant_changes_does_not_trigger(self):
        with patch('pay_app.signals.recalculate_cabinet_paid_up_to') as mocked:
            self.cabinet.note = 'just note'
            self.cabinet.save()
        mocked.assert_not_called()

    def test_pay_create_triggers_recalc_for_cabinet(self):
        with patch('pay_app.signals.recalculate_cabinet_paid_up_to') as mocked:
            pay = self._create_pay()
        mocked.assert_called_once_with(pay.cabinet_id)

    def test_pay_update_unrelated_field_does_not_trigger(self):
        pay = self._create_pay()
        with patch('pay_app.signals.recalculate_cabinet_paid_up_to') as mocked:
            pay.note_pay = 'update note only'
            pay.save()
        mocked.assert_not_called()

    def test_pay_status_change_triggers_recalc(self):
        pay = self._create_pay(status='active')
        with patch('pay_app.signals.recalculate_cabinet_paid_up_to') as mocked:
            pay.status = 'not active'
            pay.save()
        mocked.assert_called_once_with(pay.cabinet_id)

    def test_pay_delete_triggers_recalc(self):
        pay = self._create_pay()
        with patch('pay_app.signals.recalculate_cabinet_paid_up_to') as mocked:
            pay.delete()
        mocked.assert_called_once_with(self.cabinet.id)

