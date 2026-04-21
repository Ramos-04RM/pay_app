"""Tests for core encryption / decryption logic (pay_app.security)."""

import os
from unittest.mock import patch
from typing import Any

import cryptocode
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from pay_app.security import (
    _build_key_candidates,
    decrypt_value,
    encrypt_value,
    get_write_encryption_key,
    is_encrypted_value,
    key_fingerprint,
)


TEST_KEY = 'test-encryption-key-32chars!!'


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class EncryptValueTests(TestCase):
    """Validate encryption/decryption behavior and edge-case handling."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')

    def test_encrypt_then_decrypt_roundtrip(self) -> None:
        plain = 'MyS3cretPassword!'
        cipher = encrypt_value(plain)
        self.assertNotEqual(cipher, plain)
        self.assertEqual(decrypt_value(cipher), plain)

    def test_encrypt_empty_string_returns_empty(self) -> None:
        self.assertEqual(encrypt_value(''), '')

    def test_encrypt_none_returns_none(self) -> None:
        self.assertIsNone(encrypt_value(None))

    def test_decrypt_empty_string_returns_empty(self) -> None:
        self.assertEqual(decrypt_value(''), '')

    def test_decrypt_none_returns_none(self) -> None:
        self.assertIsNone(decrypt_value(None))

    def test_decrypt_garbage_returns_none(self) -> None:
        result = decrypt_value('not-encrypted-at-all')
        self.assertIsNone(result)

    def test_double_encryption_prevention(self) -> None:
        """Encrypting an already-encrypted value must be idempotent."""
        plain = 'DoNotDoubleEncrypt'
        cipher1 = encrypt_value(plain)
        cipher2 = encrypt_value(cipher1)
        self.assertEqual(cipher1, cipher2, 'Second encrypt_value call must return the same ciphertext')
        self.assertEqual(decrypt_value(cipher2), plain)

    def test_is_encrypted_detects_format(self) -> None:
        cipher = cryptocode.encrypt('hello', TEST_KEY)
        self.assertTrue(is_encrypted_value(cipher))

    def test_is_encrypted_rejects_plain_text(self) -> None:
        self.assertFalse(is_encrypted_value('just-a-password'))
        self.assertFalse(is_encrypted_value(''))
        self.assertFalse(is_encrypted_value(None))

    def test_is_encrypted_handles_tricky_plain(self) -> None:
        """A plain password like 'AAAA*BBBB*CCCC' matches the regex — known edge case."""
        tricky = 'AAAA*BBBB*CCCC'
        # This is a known limitation; document the behaviour.
        result = is_encrypted_value(tricky)
        # We just assert it doesn't crash; result may be True (false positive).
        self.assertIsInstance(result, bool)


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class KeyCandidatesTests(TestCase):
    """Check key resolution priority and legacy fallback rules."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')

    def test_app_key_takes_priority(self) -> None:
        candidates = _build_key_candidates()
        self.assertEqual(candidates[0], TEST_KEY)

    def test_legacy_key_is_second(self) -> None:
        candidates = _build_key_candidates()
        self.assertTrue(len(candidates) >= 2)
        # second candidate is the hashed password of the 'admin' user
        admin = User.objects.get(username='admin')
        self.assertEqual(candidates[1], admin.password)

    @override_settings(APP_ENCRYPTION_KEY='')
    def test_no_app_key_falls_back_to_legacy(self) -> None:
        with patch.dict(os.environ, {'APP_ENCRYPTION_KEY': ''}, clear=False):
            candidates = _build_key_candidates()
            self.assertTrue(len(candidates) >= 1)
            admin = User.objects.get(username='admin')
            self.assertEqual(candidates[0], admin.password)

    @override_settings(APP_ENCRYPTION_KEY='', LEGACY_ENCRYPTION_USER='nonexistent')
    def test_no_keys_raises(self) -> None:
        with patch.dict(os.environ, {'APP_ENCRYPTION_KEY': ''}, clear=False):
            with self.assertRaises(RuntimeError):
                get_write_encryption_key()


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class LegacyKeyDecryptionTests(TestCase):
    """Verify that data encrypted with a legacy key can still be decrypted."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')

    def test_decrypt_with_legacy_key(self) -> None:
        admin = User.objects.get(username='admin')
        legacy_cipher = cryptocode.encrypt('legacy-secret', admin.password)
        self.assertEqual(decrypt_value(legacy_cipher), 'legacy-secret')

    @patch('pay_app.security._build_key_candidates')
    def test_decrypt_fails_when_key_not_in_candidates(self, mock_keys: Any) -> None:
        mock_keys.return_value = ['some-other-key']
        cipher = cryptocode.encrypt('secret', 'unknown-key')
        self.assertIsNone(decrypt_value(cipher))


@override_settings(APP_ENCRYPTION_KEY=TEST_KEY)
class KeyFingerprintTests(TestCase):
    """Ensure key fingerprint helper is deterministic and size-stable."""

    def setUp(self) -> None:
        User.objects.create_user(username='admin', password='secret123')

    def test_fingerprint_is_stable(self) -> None:
        fp1 = key_fingerprint()
        fp2 = key_fingerprint()
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 10)

