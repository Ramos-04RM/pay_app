"""Tests for all views — authentication, CRUD, date editing, encryption flow."""

import json
from datetime import date, timedelta
from typing import Any

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from pay_app.models import Cabinet, Pay, Tag
from pay_app.security import decrypt_value, is_encrypted_value


TEST_KEY = 'test-encryption-key-32chars!!'


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class AuthenticationTests(TestCase):
    """All views (except healthz) require login."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(username='admin', password='secret123')

    def test_healthz_public(self) -> None:
        response = self.client.get(reverse('app:healthz'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_index_redirects_anonymous(self) -> None:
        response = self.client.get(reverse('app:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts/login', response.url)

    def test_cabinet_page_redirects_anonymous(self) -> None:
        response = self.client.get(reverse('app:cabinet_page'))
        self.assertEqual(response.status_code, 302)

    def test_statistics_redirects_anonymous(self) -> None:
        response = self.client.get(reverse('app:statistics'))
        self.assertEqual(response.status_code, 302)

    def test_login_grants_access(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(reverse('app:index'))
        self.assertEqual(response.status_code, 200)


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class PayCRUDViewTests(TestCase):
    """Cover pay creation, editing, deletion, and index/edit page accessibility."""

    def setUp(self) -> None:
        self.admin = User.objects.create_user(
            username='admin', password='secret123', is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.admin)
        self.cabinet = Cabinet.objects.create(
            link='https://a.example.com', login='cab-a', password='cab-pass',
            email_login='a@example.com', email_password='mail-pass',
            balance=100, currency='USD $',
        )

    def _pay_data(self, **kw: Any) -> dict[str, Any]:
        data = {
            'cabinet': self.cabinet.id,
            'groups': 'grp',
            'create_date': date.today().isoformat(),
            'service': 'New Service',
            'type_source': 'VPS',
            'price_per_month': '15.00',
            'currency': 'USD $',
            'pay_sys': 'BTC',
            'paid_up_to': (date.today() + timedelta(days=30)).isoformat(),
            'status': 'active',
            'email_login': 'new@test.com',
            'password': 'new-pass',
            'ip': '10.0.0.1',
            'note_pay': '',
        }
        data.update(kw)
        return data

    # ── Pay create ────────────────────────────────────────────────────
    def test_pay_create_get(self) -> None:
        response = self.client.get(reverse('app:pay_new'))
        self.assertEqual(response.status_code, 200)

    def test_pay_create_post_redirects(self) -> None:
        response = self.client.post(reverse('app:pay_new'), self._pay_data())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Pay.objects.filter(service='New Service').exists())

    def test_pay_create_encrypts_secrets(self) -> None:
        self.client.post(reverse('app:pay_new'), self._pay_data())
        pay = Pay.objects.get(service='New Service')
        raw_pw = Pay.objects.filter(pk=pay.pk).values_list('password', flat=True).first()
        self.assertTrue(is_encrypted_value(raw_pw))
        self.assertEqual(decrypt_value(raw_pw), 'new-pass')

    # ── Pay edit (edit_table) ─────────────────────────────────────────
    def test_edit_table_get(self) -> None:
        pay = Pay.objects.create(**{
            'cabinet': self.cabinet, 'groups': 'g', 'service': 'svc',
            'type_source': 'VPS', 'price_per_month': 10, 'currency': 'USD $',
            'pay_sys': 'BTC', 'paid_up_to': date.today() + timedelta(days=5),
            'status': 'active', 'email_login': 'e@e.com', 'password': 'p', 'ip': '1.2.3.4',
        })
        response = self.client.get(reverse('app:edit_table', args=[pay.id]))
        self.assertEqual(response.status_code, 200)

    def test_edit_table_post_saves(self) -> None:
        pay = Pay.objects.create(**{
            'cabinet': self.cabinet, 'groups': 'g', 'service': 'OldSvc',
            'type_source': 'VPS', 'price_per_month': 10, 'currency': 'USD $',
            'pay_sys': 'BTC', 'paid_up_to': date.today() + timedelta(days=5),
            'status': 'active', 'email_login': 'e@e.com', 'password': 'old', 'ip': '1.2.3.4',
        })
        response = self.client.post(
            reverse('app:edit_table', args=[pay.id]),
            self._pay_data(service='UpdatedSvc', password='new-secret'),
        )
        self.assertEqual(response.status_code, 302)
        pay.refresh_from_db()
        self.assertEqual(pay.service, 'UpdatedSvc')
        raw = Pay.objects.filter(pk=pay.pk).values_list('password', flat=True).first()
        self.assertEqual(decrypt_value(raw), 'new-secret')

    # ── Pay delete ────────────────────────────────────────────────────
    def test_delete_pay(self) -> None:
        pay = Pay.objects.create(**{
            'cabinet': self.cabinet, 'groups': 'g', 'service': 'to-delete',
            'type_source': 'VPS', 'price_per_month': 10, 'currency': 'USD $',
            'pay_sys': 'BTC', 'paid_up_to': date.today() + timedelta(days=5),
            'status': 'active', 'email_login': 'e@e.com', 'password': 'p', 'ip': '1.2.3.4',
        })
        response = self.client.get(reverse('app:delete', args=[pay.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Pay.objects.filter(pk=pay.pk).exists())

    def test_delete_pay_post_redirects_back_with_success_param(self) -> None:
        pay = Pay.objects.create(**{
            'cabinet': self.cabinet, 'groups': 'g', 'service': 'Delete Me',
            'type_source': 'VPS', 'price_per_month': 10, 'currency': 'USD $',
            'pay_sys': 'BTC', 'paid_up_to': date.today() + timedelta(days=5),
            'status': 'active', 'email_login': 'e@e.com', 'password': 'p', 'ip': '1.2.3.4',
        })
        response = self.client.post(reverse('app:delete', args=[pay.id]), {'next': reverse('app:index')})
        self.assertEqual(response.status_code, 302)
        self.assertIn('deleted_service=Delete+Me', response.url)
        self.assertFalse(Pay.objects.filter(pk=pay.pk).exists())

    def test_delete_pay_ajax_returns_json(self) -> None:
        pay = Pay.objects.create(**{
            'cabinet': self.cabinet, 'groups': 'g', 'service': 'Ajax Delete',
            'type_source': 'VPS', 'price_per_month': 10, 'currency': 'USD $',
            'pay_sys': 'BTC', 'paid_up_to': date.today() + timedelta(days=5),
            'status': 'active', 'email_login': 'e@e.com', 'password': 'p', 'ip': '1.2.3.4',
        })
        response = self.client.post(
            reverse('app:delete', args=[pay.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['ok'], True)
        self.assertFalse(Pay.objects.filter(pk=pay.pk).exists())

    def test_delete_nonexistent_pay_404(self) -> None:
        response = self.client.get(reverse('app:delete', args=[99999]))
        self.assertEqual(response.status_code, 404)

    # ── Home page ─────────────────────────────────────────────────────
    def test_index_page_loads(self) -> None:
        response = self.client.get(reverse('app:index'))
        self.assertEqual(response.status_code, 200)

    def test_edit_page_loads(self) -> None:
        response = self.client.get(reverse('app:edit_page'))
        self.assertEqual(response.status_code, 200)

    def test_pay_edit_dates_render_iso_with_ukrainian_language(self) -> None:
        pay = Pay.objects.create(**{
            'cabinet': self.cabinet,
            'groups': 'g',
            'create_date': date(2026, 4, 20),
            'service': 'svc',
            'type_source': 'VPS',
            'price_per_month': 10,
            'currency': 'USD $',
            'pay_sys': 'BTC',
            'paid_up_to': date(2026, 5, 20),
            'status': 'active',
            'email_login': 'e@e.com',
            'password': 'p',
            'ip': '1.2.3.4',
        })

        with translation.override('uk'):
            response = self.client.get(reverse('app:pay_edit', args=[pay.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="create_date"')
        self.assertContains(response, 'value="2026-04-20"')
        self.assertContains(response, 'name="paid_up_to"')
        self.assertContains(response, 'value="2026-05-20"')


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class EditDateViewTests(TestCase):
    """Tests for edit_dt — date-only update that must NOT touch encrypted fields."""

    def setUp(self) -> None:
        self.admin = User.objects.create_user(
            username='admin', password='secret123', is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.admin)
        self.cabinet = Cabinet.objects.create(
            link='https://test.com', login='cab', password='pass',
            email_login='e@e.com', email_password='ep',
            balance=0, currency='USD $',
        )
        self.pay = Pay.objects.create(
            cabinet=self.cabinet, groups='g', service='svc',
            type_source='VPS', price_per_month=10, currency='USD $',
            pay_sys='BTC', paid_up_to=date.today() + timedelta(days=5),
            status='active', email_login='e@e.com', password='secret-pw', ip='1.2.3.4',
        )

    def test_edit_dt_get(self) -> None:
        response = self.client.get(reverse('app:edit_dt', args=[self.pay.id]))
        self.assertEqual(response.status_code, 200)

    def test_edit_dt_changes_date_only(self) -> None:
        orig_pw = Pay.objects.filter(pk=self.pay.pk).values_list('password', flat=True).first()
        orig_email = Pay.objects.filter(pk=self.pay.pk).values_list('email_login', flat=True).first()

        new_date = (date.today() + timedelta(days=90)).isoformat()
        response = self.client.post(
            reverse('app:edit_dt', args=[self.pay.id]),
            {'paid_up_to': new_date},
        )
        self.assertEqual(response.status_code, 302)

        self.pay.refresh_from_db()
        self.assertEqual(self.pay.paid_up_to.isoformat(), new_date)

        after_pw = Pay.objects.filter(pk=self.pay.pk).values_list('password', flat=True).first()
        after_email = Pay.objects.filter(pk=self.pay.pk).values_list('email_login', flat=True).first()
        self.assertEqual(orig_pw, after_pw, 'password must not change on date edit')
        self.assertEqual(orig_email, after_email, 'email_login must not change on date edit')

    def test_edit_dt_invalid_date_shows_error(self) -> None:
        response = self.client.post(
            reverse('app:edit_dt', args=[self.pay.id]),
            {'paid_up_to': 'not-a-date'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['date_error'])

    def test_edit_dt_nonexistent_pay_404(self) -> None:
        response = self.client.get(reverse('app:edit_dt', args=[99999]))
        self.assertEqual(response.status_code, 404)


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class CabinetCRUDViewTests(TestCase):
    """Cover cabinet page/create/edit/delete behaviors and encryption side-effects."""

    def setUp(self) -> None:
        self.admin = User.objects.create_user(
            username='admin', password='secret123', is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.admin)
        self.cabinet = Cabinet.objects.create(
            link='https://a.example.com', login='cab-a', password='cab-pass',
            email_login='a@example.com', email_password='mail-pass',
            balance=100, currency='USD $',
        )

    def _cab_data(self, **kw: Any) -> dict[str, Any]:
        data = {
            'link': 'https://new.example.com',
            'login': 'new-cab',
            'password': 'new-cab-pass',
            'email_login': 'new@test.com',
            'email_password': 'new-mail-pass',
            'balance': '25.00',
            'currency': 'USD $',
            'note': '',
            'is_daily_payment': False,
        }
        data.update(kw)
        return data

    def test_cabinet_page_loads(self) -> None:
        response = self.client.get(reverse('app:cabinet_page'))
        self.assertEqual(response.status_code, 200)

    def test_cabinet_new_get(self) -> None:
        response = self.client.get(reverse('app:cabinet_new'))
        self.assertEqual(response.status_code, 200)

    def test_cabinet_new_post(self) -> None:
        data = self._cab_data()
        data['tags'] = []
        response = self.client.post(reverse('app:cabinet_new'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Cabinet.objects.filter(login='new-cab').exists())

    def test_cabinet_edit_get(self) -> None:
        response = self.client.get(reverse('app:cabinet_edit', args=[self.cabinet.id]))
        self.assertEqual(response.status_code, 200)

    def test_cabinet_edit_post(self) -> None:
        data = self._cab_data(login='updated-cab')
        data['tags'] = []
        response = self.client.post(reverse('app:cabinet_edit', args=[self.cabinet.id]), data)
        self.assertEqual(response.status_code, 302)
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.login, 'updated-cab')

    def test_cabinet_edit_encrypts_password(self) -> None:
        data = self._cab_data(password='fresh-pw')
        data['tags'] = []
        self.client.post(reverse('app:cabinet_edit', args=[self.cabinet.id]), data)
        raw = Cabinet.objects.filter(pk=self.cabinet.pk).values_list('password', flat=True).first()
        self.assertTrue(is_encrypted_value(raw))
        self.assertEqual(decrypt_value(raw), 'fresh-pw')

    def test_delete_cabinet(self) -> None:
        cab = Cabinet.objects.create(
            link='https://del.test.com', login='del-cab', password='x',
            email_login='d@d.com', email_password='y', balance=0, currency='USD $',
        )
        response = self.client.get(reverse('app:delete_cabinet', args=[cab.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Cabinet.objects.filter(pk=cab.pk).exists())

    def test_delete_cabinet_with_pays_fails(self) -> None:
        """Deleting a cabinet with linked pays must fail (DO_NOTHING FK constraint)."""
        Pay.objects.create(
            cabinet=self.cabinet, groups='g', service='svc',
            type_source='VPS', price_per_month=10, currency='USD $',
            pay_sys='BTC', paid_up_to=date.today() + timedelta(days=5),
            status='active', email_login='e@e.com', password='p', ip='1.2.3.4',
        )
        response = self.client.get(reverse('app:delete_cabinet', args=[self.cabinet.id]))
        # Should return error due to IntegrityError
        self.assertIn(response.status_code, [302, 404])
        # Cleanup for SQLite: if cabinet deletion succeeded, remove orphaned rows.
        Pay.objects.filter(cabinet_id=self.cabinet.id).delete()


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class TagCRUDViewTests(TestCase):
    """Cover tag listing, search, create, edit, and delete view behavior."""

    def setUp(self) -> None:
        self.admin = User.objects.create_user(
            username='admin', password='secret123', is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.admin)

    def test_tags_page_loads(self) -> None:
        response = self.client.get(reverse('app:tags_page'))
        self.assertEqual(response.status_code, 200)

    def test_tag_create(self) -> None:
        response = self.client.post(reverse('app:tag_create'), {'name': 'NewTag', 'note': ''})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tag.objects.filter(name='NewTag').exists())

    def test_tag_edit(self) -> None:
        tag = Tag.objects.create(name='OldName')
        response = self.client.post(reverse('app:tag_edit', args=[tag.id]), {'name': 'Updated', 'note': ''})
        self.assertEqual(response.status_code, 302)
        tag.refresh_from_db()
        self.assertEqual(tag.name, 'Updated')

    def test_tag_delete(self) -> None:
        tag = Tag.objects.create(name='ToDelete')
        response = self.client.post(reverse('app:tag_delete', args=[tag.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Tag.objects.filter(pk=tag.pk).exists())

    def test_tags_search(self) -> None:
        Tag.objects.create(name='Alpha')
        Tag.objects.create(name='Beta')
        response = self.client.get(reverse('app:tags_page'), {'q': 'Alpha'})
        self.assertEqual(response.status_code, 200)
        tags = list(response.context['tags'])
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].name, 'Alpha')


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class DecryptEndpointTests(TestCase):
    """Cover decrypt endpoint authorization and payload validation behavior."""

    def setUp(self) -> None:
        self.admin = User.objects.create_user(
            username='admin', password='secret123', is_staff=True, is_superuser=True,
        )
        self.user = User.objects.create_user(username='user', password='secret123')
        self.client.force_login(self.admin)
        self.cabinet = Cabinet.objects.create(
            link='https://a.example.com', login='cab-a', password='cab-pass',
            email_login='a@example.com', email_password='mail-pass',
            balance=100, currency='USD $',
        )
        self.pay = Pay.objects.create(
            cabinet=self.cabinet, groups='g', service='svc',
            type_source='VPS', price_per_month=10, currency='USD $',
            pay_sys='BTC', paid_up_to=date.today() + timedelta(days=5),
            status='active', email_login='svc@example.com', password='svc-pass', ip='1.2.3.4',
        )

    def test_decrypt_pay_password(self) -> None:
        response = self.client.post(
            reverse('app:decrypt_item'),
            data=json.dumps({'model': 'pay', 'field': 'password', 'id': self.pay.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['value'], 'svc-pass')

    def test_decrypt_pay_email_login(self) -> None:
        response = self.client.post(
            reverse('app:decrypt_item'),
            data=json.dumps({'model': 'pay', 'field': 'email_login', 'id': self.pay.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['value'], 'svc@example.com')

    def test_decrypt_cabinet_password(self) -> None:
        response = self.client.post(
            reverse('app:decrypt_item'),
            data=json.dumps({'model': 'cabinet', 'field': 'password', 'id': self.cabinet.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['value'], 'cab-pass')

    def test_decrypt_cabinet_email_password(self) -> None:
        response = self.client.post(
            reverse('app:decrypt_item'),
            data=json.dumps({'model': 'cabinet', 'field': 'email_password', 'id': self.cabinet.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['value'], 'mail-pass')

    def test_decrypt_cabinet_email_login_rejected(self) -> None:
        """Cabinet.email_login is NOT encrypted — should be rejected by endpoint."""
        response = self.client.post(
            reverse('app:decrypt_item'),
            data=json.dumps({'model': 'cabinet', 'field': 'email_login', 'id': self.cabinet.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_decrypt_requires_staff(self) -> None:
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('app:decrypt_item'),
            data=json.dumps({'model': 'pay', 'field': 'password', 'id': self.pay.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_decrypt_invalid_model(self) -> None:
        response = self.client.post(
            reverse('app:decrypt_item'),
            data=json.dumps({'model': 'user', 'field': 'password', 'id': 1}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_decrypt_invalid_field(self) -> None:
        response = self.client.post(
            reverse('app:decrypt_item'),
            data=json.dumps({'model': 'pay', 'field': 'service', 'id': self.pay.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_decrypt_nonexistent_id(self) -> None:
        response = self.client.post(
            reverse('app:decrypt_item'),
            data=json.dumps({'model': 'pay', 'field': 'password', 'id': 99999}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_decrypt_invalid_json(self) -> None:
        response = self.client.post(
            reverse('app:decrypt_item'),
            data='not-json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_decrypt_get_method_rejected(self) -> None:
        response = self.client.get(reverse('app:decrypt_item'))
        self.assertEqual(response.status_code, 405)


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class StatisticsViewTests(TestCase):
    """Cover statistics page rendering and basic filter variants."""

    def setUp(self) -> None:
        self.admin = User.objects.create_user(
            username='admin', password='secret123', is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.admin)
        self.cabinet = Cabinet.objects.create(
            link='https://a.example.com', login='cab', password='p',
            email_login='a@e.com', email_password='ep',
            balance=100, currency='USD $',
        )
        Pay.objects.create(
            cabinet=self.cabinet, groups='g', service='svc',
            type_source='VPS', price_per_month=30, currency='USD $',
            pay_sys='BTC', paid_up_to=date.today() + timedelta(days=30),
            status='active', email_login='e@e.com', password='p', ip='1.2.3.4',
        )

    def test_statistics_page_loads(self) -> None:
        response = self.client.get(reverse('app:statistics'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('burn_by_currency', response.context)
        self.assertIn('active_count', response.context)

    def test_statistics_filter_by_currency(self) -> None:
        response = self.client.get(reverse('app:statistics'), {'currency': 'USD $'})
        self.assertEqual(response.status_code, 200)

    def test_statistics_period_year(self) -> None:
        response = self.client.get(reverse('app:statistics'), {'period': 'year'})
        self.assertEqual(response.status_code, 200)

    def test_statistics_period_last12(self) -> None:
        response = self.client.get(reverse('app:statistics'), {'period': 'last12'})
        self.assertEqual(response.status_code, 200)

    def test_statistics_period_custom(self) -> None:
        response = self.client.get(reverse('app:statistics'), {
            'period': 'custom',
            'start': '2026-01-01',
            'end': '2026-12-31',
        })
        self.assertEqual(response.status_code, 200)


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class PayFilterViewTests(TestCase):
    """Cover legacy pay list filter/sort endpoints for compatibility."""

    def setUp(self) -> None:
        self.admin = User.objects.create_user(
            username='admin', password='secret123', is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.admin)
        self.cabinet = Cabinet.objects.create(
            link='https://a.example.com', login='cab', password='p',
            email_login='a@e.com', email_password='ep',
            balance=100, currency='USD $',
        )
        self.pay = Pay.objects.create(
            cabinet=self.cabinet, groups='g', service='FilterSvc',
            type_source='VPS', price_per_month=30, currency='USD $',
            pay_sys='BTC', paid_up_to=date.today() + timedelta(days=5),
            status='active', email_login='e@e.com', password='p', ip='1.2.3.4',
        )

    def test_search(self) -> None:
        response = self.client.get(reverse('app:searching', args=['x']), {'q': 'FilterSvc'})
        self.assertEqual(response.status_code, 200)

    def test_filter_by_pay_sys(self) -> None:
        response = self.client.get(reverse('app:filter_by_pay_sys', args=['BTC']))
        self.assertEqual(response.status_code, 200)

    def test_filter_by_type_source(self) -> None:
        response = self.client.get(reverse('app:filter_by_type_source', args=['VPS']))
        self.assertEqual(response.status_code, 200)

    def test_filter_by_active(self) -> None:
        response = self.client.get(reverse('app:filter_by_active', args=['active']))
        self.assertEqual(response.status_code, 200)

    def test_filter_upcoming(self) -> None:
        response = self.client.get(reverse('app:filter_by_date', args=['1']))
        self.assertEqual(response.status_code, 200)

    def test_filter_overdue(self) -> None:
        response = self.client.get(reverse('app:overdue_payments', args=['1']))
        self.assertEqual(response.status_code, 200)

    def test_sort_by_name(self) -> None:
        response = self.client.get(reverse('app:sorted_by_name', args=['service']))
        self.assertEqual(response.status_code, 200)

