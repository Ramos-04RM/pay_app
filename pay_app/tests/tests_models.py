"""Tests for model save / encryption behaviour."""

from datetime import date, timedelta
from typing import Any

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from pay_app.models import Cabinet, Pay
from pay_app.security import decrypt_value, is_encrypted_value


TEST_KEY = 'test-encryption-key-32chars!!'


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class PayModelSaveTests(TestCase):
    """Ensure Pay model save encrypts secrets and preserves non-secret updates."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')
        self.cabinet = Cabinet.objects.create(
            link='https://example.com',
            login='cab',
            password='cab-pass',
            email_login='cab@example.com',
            email_password='mail-pass',
            balance=100,
            currency='USD $',
        )

    def _create_pay(self, **kw: Any) -> Pay:
        defaults = dict(
            cabinet=self.cabinet,
            groups='g',
            service='svc',
            type_source='VPS',
            price_per_month=10,
            currency='USD $',
            pay_sys='BTC',
            paid_up_to=date.today() + timedelta(days=30),
            status='active',
            email_login='user@example.com',
            password='secret-pass',
            ip='127.0.0.1',
        )
        defaults.update(kw)
        return Pay.objects.create(**defaults)

    def test_password_encrypted_on_create(self):
        pay = self._create_pay(password='plain-pass')
        raw = Pay.objects.filter(pk=pay.pk).values_list('password', flat=True).first()
        self.assertTrue(is_encrypted_value(raw), 'password must be encrypted in DB')
        self.assertEqual(decrypt_value(raw), 'plain-pass')

    def test_email_login_encrypted_on_create(self):
        pay = self._create_pay(email_login='login@test.com')
        raw = Pay.objects.filter(pk=pay.pk).values_list('email_login', flat=True).first()
        self.assertTrue(is_encrypted_value(raw), 'email_login must be encrypted in DB')
        self.assertEqual(decrypt_value(raw), 'login@test.com')

    def test_save_does_not_double_encrypt(self):
        pay = self._create_pay(password='abc')
        raw1 = Pay.objects.filter(pk=pay.pk).values_list('password', flat=True).first()
        # trigger save again without changing the password
        pay.refresh_from_db()
        pay.save()
        raw2 = Pay.objects.filter(pk=pay.pk).values_list('password', flat=True).first()
        self.assertEqual(decrypt_value(raw2), 'abc')

    def test_date_only_update_does_not_touch_secrets(self):
        """QuerySet.update(paid_up_to=...) bypasses save() — secrets untouched."""
        pay = self._create_pay(password='dont-touch')
        orig_pw = Pay.objects.filter(pk=pay.pk).values_list('password', flat=True).first()
        orig_email = Pay.objects.filter(pk=pay.pk).values_list('email_login', flat=True).first()

        new_date = date.today() + timedelta(days=99)
        Pay.objects.filter(pk=pay.pk).update(paid_up_to=new_date)

        pay.refresh_from_db()
        self.assertEqual(pay.paid_up_to, new_date)
        after_pw = Pay.objects.filter(pk=pay.pk).values_list('password', flat=True).first()
        after_email = Pay.objects.filter(pk=pay.pk).values_list('email_login', flat=True).first()
        self.assertEqual(orig_pw, after_pw)
        self.assertEqual(orig_email, after_email)

    def test_non_encrypted_fields_stored_plaintext(self):
        pay = self._create_pay(ip='10.0.0.1', note_pay='hello', service='My VPS')
        pay.refresh_from_db()
        self.assertEqual(pay.ip, '10.0.0.1')
        self.assertEqual(pay.note_pay, 'hello')
        self.assertEqual(pay.service, 'My VPS')


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class CabinetModelSaveTests(TestCase):
    """Ensure Cabinet model save encrypts secret fields correctly."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')

    def test_password_encrypted_on_create(self):
        cab = Cabinet.objects.create(
            link='https://test.com', login='cab', password='cab-pass',
            email_login='e@test.com', email_password='mail-pass',
            balance=0, currency='USD $',
        )
        raw_pw = Cabinet.objects.filter(pk=cab.pk).values_list('password', flat=True).first()
        raw_email_pw = Cabinet.objects.filter(pk=cab.pk).values_list('email_password', flat=True).first()
        self.assertTrue(is_encrypted_value(raw_pw))
        self.assertTrue(is_encrypted_value(raw_email_pw))
        self.assertEqual(decrypt_value(raw_pw), 'cab-pass')
        self.assertEqual(decrypt_value(raw_email_pw), 'mail-pass')

    def test_email_login_not_encrypted(self):
        """Cabinet.email_login is NOT an encrypted field — stored plaintext."""
        cab = Cabinet.objects.create(
            link='https://test.com', login='cab', password='x',
            email_login='plain@test.com', email_password='y',
            balance=0, currency='USD $',
        )
        raw = Cabinet.objects.filter(pk=cab.pk).values_list('email_login', flat=True).first()
        self.assertEqual(raw, 'plain@test.com')

    def test_save_does_not_double_encrypt(self):
        cab = Cabinet.objects.create(
            link='https://test.com', login='cab', password='double-check',
            email_login='e@test.com', email_password='mail-check',
            balance=0, currency='USD $',
        )
        cab.refresh_from_db()
        cab.save()
        raw = Cabinet.objects.filter(pk=cab.pk).values_list('password', flat=True).first()
        self.assertEqual(decrypt_value(raw), 'double-check')

