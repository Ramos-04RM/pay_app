import json
import logging
from datetime import date, timedelta
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings

from pay_app.log_context import clear_request_context, set_request_context
from pay_app.logging_filters import RequestContextFilter
from pay_app.logging_formatters import JsonLogFormatter
from pay_app.logging_helpers import _sanitize, log_event
from pay_app.models import Cabinet, Pay
from pay_app.signals import _request_log_context


TEST_KEY = 'test-encryption-key-32chars!!'


class LoggingUtilityTests(SimpleTestCase):
    def test_sanitize_masks_sensitive_values(self) -> None:
        payload = {
            'password': 'plain',
            'nested': {
                'token': 'abc',
                'safe': 'ok',
            },
        }
        masked = _sanitize(payload)
        self.assertEqual(masked['password'], '***')
        self.assertEqual(masked['nested']['token'], '***')
        self.assertEqual(masked['nested']['safe'], 'ok')

    def test_request_context_filter_injects_defaults(self) -> None:
        set_request_context({'username': 'alice', 'request_id': 'req-1', 'path': '/cabinet/'})
        try:
            record = logging.LogRecord('pay_app.audit', logging.INFO, __file__, 1, 'msg', (), None)
            filtered = RequestContextFilter().filter(record)
            self.assertTrue(filtered)
            self.assertEqual(record.username, 'alice')
            self.assertEqual(record.request_id, 'req-1')
            self.assertEqual(record.path, '/cabinet/')
        finally:
            clear_request_context()

    def test_json_formatter_outputs_expected_fields(self) -> None:
        record = logging.LogRecord('pay_app.audit', logging.INFO, __file__, 1, 'created', (), None)
        record.username = 'bob'
        record.event = 'pay.created'
        record.context = {'pay_id': 10}
        payload = json.loads(JsonLogFormatter().format(record))
        self.assertEqual(payload['event'], 'pay.created')
        self.assertEqual(payload['username'], 'bob')
        self.assertEqual(payload['context']['pay_id'], 10)
        self.assertIn('time', payload)

    def test_log_event_routes_to_security_logger(self) -> None:
        with self.assertLogs('pay_app.security_audit', level='INFO') as captured:
            log_event(
                event='auth.login.success',
                message='User login successful',
                logger_name='pay_app.security_audit',
                username='admin',
            )
        self.assertTrue(any('User login successful' in line for line in captured.output))

    def test_logging_config_has_security_file_and_90_day_retention(self) -> None:
        handlers = settings.LOGGING['handlers']
        self.assertEqual(handlers['app_file']['backupCount'], 90)
        self.assertEqual(handlers['security_file']['backupCount'], 90)
        self.assertTrue(str(handlers['security_file']['filename']).endswith('security.jsonl'))

    def test_request_log_context_uses_request_values(self) -> None:
        request = SimpleNamespace(
            method='POST',
            path='/accounts/login/',
            headers={'X-Request-ID': 'req-123'},
            META={'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'UA'},
            log_context={},
        )
        context = _request_log_context(request)
        self.assertEqual(context['request_id'], 'req-123')
        self.assertEqual(context['http_method'], 'POST')
        self.assertEqual(context['path'], '/accounts/login/')
        self.assertEqual(context['remote_addr'], '127.0.0.1')


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class AuditSignalTests(TestCase):
    def setUp(self) -> None:
        clear_request_context()
        set_request_context({'username': 'tester', 'request_id': 'req-signal'})
        self.user = User.objects.create_user(username='admin', password='secret123')
        self.cabinet = Cabinet.objects.create(
            link='https://a.example.com',
            login='cab-a',
            password='cab-pass',
            email_login='a@example.com',
            email_password='mail-pass',
            balance=100,
            currency='USD $',
        )

    def tearDown(self) -> None:
        clear_request_context()

    def test_pay_create_emits_audit_log(self) -> None:
        with self.assertLogs('pay_app.audit', level='INFO') as captured:
            Pay.objects.create(
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

        self.assertTrue(any('Pay saved' in line for line in captured.output))

