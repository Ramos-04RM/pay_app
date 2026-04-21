"""Shared test helpers and base classes for pay_app tests."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import User
from django.test import TestCase

from pay_app.models import Cabinet, CabinetTag, Pay, Tag


class BaseAppTestCase(TestCase):
    """Common setUp with admin/user, two cabinets, two pays, and two tags."""

    def setUp(self) -> None:
        self.admin = User.objects.create_user(
            username='admin',
            password='secret123',
            is_staff=True,
            is_superuser=True,
        )
        self.user = User.objects.create_user(username='user', password='secret123')
        self.client.force_login(self.admin)

        self.tag_fast = Tag.objects.create(name='Fast')
        self.tag_slow = Tag.objects.create(name='Slow')

        self.cabinet_a = Cabinet.objects.create(
            link='https://a.example.com',
            login='cab-a',
            password='cab-pass-a',
            email_login='a@example.com',
            email_password='mail-pass-a',
            balance=100,
            currency='USD $',
            note='alpha',
        )
        self.cabinet_b = Cabinet.objects.create(
            link='https://b.example.com',
            login='cab-b',
            password='cab-pass-b',
            email_login='b@example.com',
            email_password='mail-pass-b',
            balance=5,
            currency='USD $',
            note='beta',
            is_daily_payment=True,
        )
        CabinetTag.objects.create(cabinet=self.cabinet_a, tag=self.tag_fast)
        CabinetTag.objects.create(cabinet=self.cabinet_b, tag=self.tag_slow)

        self.pay_active = Pay.objects.create(
            cabinet=self.cabinet_a,
            groups='grp-a',
            service='Service Alpha',
            type_source='VPS',
            price_per_month=30,
            currency='USD $',
            pay_sys='BTC',
            paid_up_to=date.today() + timedelta(days=5),
            status='active',
            email_login='svc-a@example.com',
            password='svc-pass-a',
            ip='10.0.0.1',
            note_pay='note-a',
        )
        self.pay_inactive = Pay.objects.create(
            cabinet=self.cabinet_b,
            groups='grp-b',
            service='Service Beta',
            type_source='site',
            price_per_month=60,
            currency='USD $',
            pay_sys='WM',
            paid_up_to=date.today() - timedelta(days=2),
            status='not active',
            email_login='svc-b@example.com',
            password='svc-pass-b',
            ip='10.0.0.2',
            note_pay='note-b',
        )

    # ── helpers ──────────────────────────────────────────────────────────
    def make_pay_payload(self, **overrides: Any) -> dict[str, Any]:
        """Return a valid POST payload for creating / editing a Pay."""
        data = {
            'cabinet': self.cabinet_a.id,
            'groups': 'grp-test',
            'create_date': date.today().isoformat(),
            'service': 'Test Service',
            'type_source': 'VPS',
            'price_per_month': '10.00',
            'currency': 'USD $',
            'pay_sys': 'BTC',
            'paid_up_to': (date.today() + timedelta(days=30)).isoformat(),
            'status': 'active',
            'email_login': 'test@example.com',
            'password': 'test-password',
            'ip': '127.0.0.1',
            'note_pay': '',
        }
        data.update(overrides)
        return data

    def make_cabinet_payload(self, **overrides: Any) -> dict[str, Any]:
        """Return a valid POST payload for creating / editing a Cabinet."""
        data = {
            'link': 'https://test.example.com',
            'login': 'test-cab',
            'password': 'test-cab-pass',
            'email_login': 'test-cab@example.com',
            'email_password': 'test-mail-pass',
            'balance': '50.00',
            'currency': 'USD $',
            'note': '',
            'is_daily_payment': False,
        }
        data.update(overrides)
        return data

