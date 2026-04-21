"""Tests for daily-payment recalculation rules and signal triggers."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from typing import Any

from django.contrib.auth.models import User
from django.test import TestCase

from pay_app.models import Cabinet, Pay
from pay_app.services import recalculate_cabinet_paid_up_to


class DailyPaymentLogicTests(TestCase):
    """Cover daily cabinet billing edge-cases and recalculation triggers."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')
        self.fixed_today = date(2026, 1, 10)

    def create_cabinet(self, **kwargs: Any) -> Cabinet:
        data = {
            'link': 'https://example.com',
            'login': f"cab-{Cabinet.objects.count() + 1}",
            'password': 'cab-pass',
            'email_login': 'cab@example.com',
            'email_password': f"mail-pass-{Cabinet.objects.count() + 1}",
            'balance': Decimal('0.00'),
            'currency': 'USD $',
            'is_daily_payment': False,
        }
        data.update(kwargs)
        return Cabinet.objects.create(**data)

    def create_pay(self, cabinet: Cabinet, **kwargs: Any) -> Pay:
        idx = Pay.objects.count() + 1
        data = {
            'cabinet': cabinet,
            'groups': 'g',
            'service': f'service-{idx}',
            'type_source': 'VPS',
            'price_per_month': 27,
            'currency': 'USD $',
            'pay_sys': 'BTC',
            'status': 'active',
            'email_login': f'user{idx}@example.com',
            'password': f'pass-{idx}',
            'ip': '127.0.0.1',
            'note_pay': '',
        }
        data.update(kwargs)
        return Pay.objects.create(**data)

    def test_is_daily_payment_false_no_recalculation(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('100.00'), is_daily_payment=False)
        pay = self.create_pay(cabinet=cabinet, paid_up_to=self.fixed_today + timedelta(days=3))

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            cabinet.balance = Decimal('200.00')
            cabinet.save()

        pay.refresh_from_db()
        self.assertEqual(pay.paid_up_to, self.fixed_today + timedelta(days=3))

    def test_balance_null_treated_as_zero(self) -> None:
        cabinet = self.create_cabinet(balance=None, is_daily_payment=True)
        pay = self.create_pay(cabinet=cabinet, paid_up_to=self.fixed_today + timedelta(days=5))

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            recalculate_cabinet_paid_up_to(cabinet.id)

        pay.refresh_from_db()
        self.assertEqual(pay.paid_up_to, self.fixed_today)

    def test_balance_zero_sets_paid_up_to_today(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('0.00'), is_daily_payment=True)
        pay = self.create_pay(cabinet=cabinet)

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            recalculate_cabinet_paid_up_to(cabinet.id)

        pay.refresh_from_db()
        self.assertEqual(pay.paid_up_to, self.fixed_today)

    def test_single_active_service(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('54.00'), is_daily_payment=True)
        pay = self.create_pay(cabinet=cabinet, price_per_month=27)

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            recalculate_cabinet_paid_up_to(cabinet.id)

        pay.refresh_from_db()
        self.assertEqual(pay.paid_up_to, self.fixed_today + timedelta(days=56))

    def test_multiple_active_services_same_date(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('81.00'), is_daily_payment=True)
        pay1 = self.create_pay(cabinet=cabinet, price_per_month=27)
        pay2 = self.create_pay(cabinet=cabinet, price_per_month=54)

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            recalculate_cabinet_paid_up_to(cabinet.id)

        expected_date = self.fixed_today + timedelta(days=28)
        pay1.refresh_from_db()
        pay2.refresh_from_db()
        self.assertEqual(pay1.paid_up_to, expected_date)
        self.assertEqual(pay2.paid_up_to, expected_date)

    def test_inactive_services_ignored(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('27.00'), is_daily_payment=True)
        active_pay = self.create_pay(cabinet=cabinet, status='active', price_per_month=27)
        inactive_date = self.fixed_today + timedelta(days=99)
        inactive_pay = self.create_pay(
            cabinet=cabinet,
            status='not active',
            price_per_month=270,
            paid_up_to=inactive_date,
        )

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            recalculate_cabinet_paid_up_to(cabinet.id)

        active_pay.refresh_from_db()
        inactive_pay.refresh_from_db()
        self.assertEqual(active_pay.paid_up_to, self.fixed_today + timedelta(days=28))
        self.assertEqual(inactive_pay.paid_up_to, inactive_date)

    def test_active_service_with_non_positive_price_blocks_recalculation(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('100.00'), is_daily_payment=True)
        pay1 = self.create_pay(cabinet=cabinet, price_per_month=27)
        pay2 = self.create_pay(cabinet=cabinet, price_per_month=0)
        Pay.objects.filter(pk=pay1.pk).update(paid_up_to=self.fixed_today + timedelta(days=5))
        Pay.objects.filter(pk=pay2.pk).update(paid_up_to=self.fixed_today + timedelta(days=7))

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            recalculate_cabinet_paid_up_to(cabinet.id)

        pay1.refresh_from_db()
        pay2.refresh_from_db()
        self.assertEqual(pay1.paid_up_to, self.fixed_today + timedelta(days=5))
        self.assertEqual(pay2.paid_up_to, self.fixed_today + timedelta(days=7))

    def test_balance_change_triggers_recalculation(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('27.00'), is_daily_payment=True)
        pay = self.create_pay(cabinet=cabinet, price_per_month=27)

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            cabinet.balance = Decimal('54.00')
            cabinet.save()

        pay.refresh_from_db()
        self.assertEqual(pay.paid_up_to, self.fixed_today + timedelta(days=56))

    def test_is_daily_payment_switch_to_true_triggers_recalculation(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('27.00'), is_daily_payment=False)
        pay = self.create_pay(cabinet=cabinet, price_per_month=27, paid_up_to=self.fixed_today + timedelta(days=2))

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            cabinet.is_daily_payment = True
            cabinet.save()

        pay.refresh_from_db()
        self.assertEqual(pay.paid_up_to, self.fixed_today + timedelta(days=28))

    def test_create_active_pay_triggers_recalculation(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('27.00'), is_daily_payment=True)

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            pay = self.create_pay(cabinet=cabinet, price_per_month=27)

        pay.refresh_from_db()
        self.assertEqual(pay.paid_up_to, self.fixed_today + timedelta(days=28))

    def test_price_change_triggers_recalculation(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('54.00'), is_daily_payment=True)
        pay = self.create_pay(cabinet=cabinet, price_per_month=27)

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            pay.price_per_month = 54
            pay.save()

        pay.refresh_from_db()
        self.assertEqual(pay.paid_up_to, self.fixed_today + timedelta(days=27))

    def test_status_change_triggers_recalculation(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('54.00'), is_daily_payment=True)
        pay1 = self.create_pay(cabinet=cabinet, price_per_month=27)
        pay2 = self.create_pay(cabinet=cabinet, price_per_month=27)

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            pay2.status = 'not active'
            pay2.save()

        pay1.refresh_from_db()
        pay2.refresh_from_db()
        self.assertEqual(pay1.paid_up_to, self.fixed_today + timedelta(days=56))
        self.assertNotEqual(pay2.status, 'active')

    def test_move_pay_to_another_cabinet_recalculates_both(self) -> None:
        old_cab = self.create_cabinet(balance=Decimal('54.00'), is_daily_payment=True, login='old-cab')
        new_cab = self.create_cabinet(balance=Decimal('27.00'), is_daily_payment=True, login='new-cab')

        old_pay_1 = self.create_pay(cabinet=old_cab, price_per_month=27)
        moving_pay = self.create_pay(cabinet=old_cab, price_per_month=27)
        new_pay = self.create_pay(cabinet=new_cab, price_per_month=27)

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            moving_pay.cabinet = new_cab
            moving_pay.save()

        old_pay_1.refresh_from_db()
        moving_pay.refresh_from_db()
        new_pay.refresh_from_db()

        self.assertEqual(old_pay_1.paid_up_to, self.fixed_today + timedelta(days=56))
        self.assertEqual(moving_pay.paid_up_to, self.fixed_today + timedelta(days=14))
        self.assertEqual(new_pay.paid_up_to, self.fixed_today + timedelta(days=14))

    def test_delete_pay_triggers_recalculation(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('54.00'), is_daily_payment=True)
        pay1 = self.create_pay(cabinet=cabinet, price_per_month=27)
        pay2 = self.create_pay(cabinet=cabinet, price_per_month=27)

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            pay2.delete()

        pay1.refresh_from_db()
        self.assertEqual(pay1.paid_up_to, self.fixed_today + timedelta(days=56))

    def test_days_are_rounded_down(self) -> None:
        cabinet = self.create_cabinet(balance=Decimal('40.00'), is_daily_payment=True)
        pay = self.create_pay(cabinet=cabinet, price_per_month=27)
        self.create_pay(cabinet=cabinet, price_per_month=54)

        with patch('pay_app.services.daily_payment.timezone.localdate', return_value=self.fixed_today):
            recalculate_cabinet_paid_up_to(cabinet.id)

        pay.refresh_from_db()
        self.assertEqual(pay.paid_up_to, self.fixed_today + timedelta(days=13))