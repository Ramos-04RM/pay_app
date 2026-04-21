"""Unit tests for pay_app.services.security helpers."""

import json
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings

from pay_app.models import Cabinet, Pay
from pay_app.services.security import (
    decrypt_cabinet_secrets,
    decrypt_item_payload,
    decrypt_pay_secrets,
    decrypt_secret,
)


TEST_KEY = 'test-encryption-key-32chars!!'


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class ServiceSecurityTests(TestCase):
    """Validate decrypt service payload parsing, permission checks, and mutation helpers."""

    def setUp(self) -> None:
        self.staff = User.objects.create_user(
            username='admin',
            password='secret123',
            is_staff=True,
            is_superuser=True,
        )
        self.user = User.objects.create_user(username='user', password='secret123')

        self.cabinet = Cabinet.objects.create(
            link='https://a.example.com',
            login='cab-a',
            password='cab-pass',
            email_login='a@example.com',
            email_password='mail-pass',
            balance=100,
            currency='USD $',
        )
        self.pay = Pay.objects.create(
            cabinet=self.cabinet,
            groups='g',
            service='svc',
            type_source='VPS',
            price_per_month=10,
            currency='USD $',
            pay_sys='BTC',
            paid_up_to=date.today() + timedelta(days=5),
            status='active',
            email_login='svc@example.com',
            password='svc-pass',
            ip='1.2.3.4',
        )
        self.factory = RequestFactory()

    def test_decrypt_item_payload_valid_json(self):
        request = self.factory.post(
            '/decrypt_item/',
            data=json.dumps({'model': 'pay', 'field': 'password', 'id': self.pay.id}),
            content_type='application/json',
        )
        payload, error = decrypt_item_payload(request)
        self.assertIsNone(error)
        self.assertEqual(payload['model'], 'pay')

    def test_decrypt_item_payload_invalid_json(self):
        request = self.factory.post('/decrypt_item/', data='not-json', content_type='application/json')
        payload, error = decrypt_item_payload(request)
        self.assertIsNone(payload)
        self.assertEqual(error.status_code, 400)

    def test_decrypt_secret_denies_non_staff(self):
        with self.assertRaises(PermissionDenied):
            decrypt_secret(self.user, {'model': 'pay', 'field': 'password', 'id': self.pay.id})

    def test_decrypt_secret_invalid_model(self):
        response = decrypt_secret(self.staff, {'model': 'user', 'field': 'password', 'id': 1})
        self.assertEqual(response.status_code, 400)

    def test_decrypt_secret_invalid_field(self):
        response = decrypt_secret(self.staff, {'model': 'pay', 'field': 'service', 'id': self.pay.id})
        self.assertEqual(response.status_code, 400)

    def test_decrypt_secret_invalid_id(self):
        response = decrypt_secret(self.staff, {'model': 'pay', 'field': 'password', 'id': 'x'})
        self.assertEqual(response.status_code, 400)

    def test_decrypt_secret_empty_value(self):
        empty_pay = Pay.objects.create(
            cabinet=self.cabinet,
            groups='g',
            service='svc-empty',
            type_source='VPS',
            price_per_month=10,
            currency='USD $',
            pay_sys='BTC',
            paid_up_to=date.today() + timedelta(days=5),
            status='active',
            email_login='svc-empty@example.com',
            password='',
            ip='1.2.3.9',
        )
        response = decrypt_secret(self.staff, {'model': 'pay', 'field': 'password', 'id': empty_pay.id})
        self.assertEqual(response.status_code, 400)

    def test_decrypt_pay_secrets_mutates_object_to_plaintext(self):
        encrypted = Pay.objects.get(pk=self.pay.pk)
        decrypted = decrypt_pay_secrets(encrypted)
        self.assertEqual(decrypted.password, 'svc-pass')
        self.assertEqual(decrypted.email_login, 'svc@example.com')

    def test_decrypt_cabinet_secrets_mutates_object_to_plaintext(self):
        encrypted = Cabinet.objects.get(pk=self.cabinet.pk)
        decrypted = decrypt_cabinet_secrets(encrypted)
        self.assertEqual(decrypted.password, 'cab-pass')
        self.assertEqual(decrypted.email_password, 'mail-pass')

