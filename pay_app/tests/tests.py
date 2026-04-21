"""Legacy integration-style tests for core pay/cabinet/decrypt flows."""

from datetime import date, timedelta
from unittest.mock import patch
from typing import Any

import cryptocode
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from pay_app.models import Cabinet, CabinetTag, Pay, Tag


class BaseAppTestCase(TestCase):
    """Shared fixtures for flow tests in this legacy module."""

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


class PayAndCabinetFlowTests(BaseAppTestCase):
    """End-to-end checks for list/filter/create page flows."""

    def test_pay_list_search_and_filter(self) -> None:
        response = self.client.get(reverse('app:index'), {'q': 'Alpha', 'status': ['active']})
        self.assertEqual(response.status_code, 200)
        object_l = list(response.context['object_l'])
        self.assertEqual(len(object_l), 1)
        self.assertEqual(object_l[0].id, self.pay_active.id)

    def test_cabinet_list_filter_by_tag(self) -> None:
        response = self.client.get(reverse('app:cabinet_page'), {'tag_id': [self.tag_fast.id]})
        self.assertEqual(response.status_code, 200)
        object_k = list(response.context['object_k'])
        self.assertEqual(len(object_k), 1)
        self.assertEqual(object_k[0].id, self.cabinet_a.id)

    def test_statistics_page_loads_with_filters(self) -> None:
        response = self.client.get(reverse('app:statistics'), {'currency': 'USD $', 'status': 'active'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('burn_by_currency', response.context)
        self.assertGreaterEqual(response.context['active_count'], 1)

    def test_pay_create_flow(self) -> None:
        payload = {
            'cabinet': self.cabinet_a.id,
            'groups': 'grp-c',
            'create_date': date.today().isoformat(),
            'service': 'Service New',
            'type_source': 'proxy',
            'price_per_month': '22.50',
            'currency': 'USD $',
            'pay_sys': 'BTC',
            'paid_up_to': (date.today() + timedelta(days=30)).isoformat(),
            'status': 'active',
            'email_login': 'new@example.com',
            'password': 'new-password',
            'ip': '10.0.0.3',
            'note_pay': 'new',
        }
        response = self.client.post(reverse('app:pay_new'), payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Pay.objects.filter(service='Service New').exists())


class DecryptEndpointTests(BaseAppTestCase):
    """Permission and success-path checks for decrypt endpoint."""

    def test_decrypt_requires_staff_permission(self) -> None:
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('app:decrypt_item'),
            data='{"model":"pay","field":"password","id": %d}' % self.pay_active.id,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_decrypt_success_for_staff(self) -> None:
        response = self.client.post(
            reverse('app:decrypt_item'),
            data='{"model":"pay","field":"password","id": %d}' % self.pay_active.id,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['value'], 'svc-pass-a')


class CompatibilityEncryptionTests(BaseAppTestCase):
    """Compatibility checks for legacy ciphertext decrypt behavior."""

    @patch('pay_app.security._build_key_candidates')
    def test_legacy_encrypted_values_can_be_decrypted(self, mock_keys: Any) -> None:
        legacy_key = 'legacy-key'
        app_key = 'new-app-key'
        mock_keys.return_value = [app_key, legacy_key]
        legacy_cipher = cryptocode.encrypt('legacy-secret', legacy_key)
        Pay.objects.filter(id=self.pay_active.id).update(password=legacy_cipher)

        response = self.client.post(
            reverse('app:decrypt_item'),
            data='{"model":"pay","field":"password","id": %d}' % self.pay_active.id,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['value'], 'legacy-secret')
