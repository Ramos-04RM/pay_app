import hashlib
import logging
import os
from typing import List

import cryptocode
from django.conf import settings
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


def _build_key_candidates() -> List[str]:
    """Return keys ordered from preferred write key to legacy fallback keys."""
    candidates: List[str] = []

    app_key = (getattr(settings, 'APP_ENCRYPTION_KEY', '') or os.getenv('APP_ENCRYPTION_KEY', '')).strip()
    if app_key:
        candidates.append(app_key)

    legacy_username = (getattr(settings, 'LEGACY_ENCRYPTION_USER', 'admin') or 'admin').strip()
    try:
        user = get_user_model().objects.filter(username=legacy_username).only('password').first()
    except Exception:  # pragma: no cover - defensive DB safety
        user = None

    if user and user.password:
        candidates.append(user.password)

    return candidates


def get_write_encryption_key() -> str:
    candidates = _build_key_candidates()
    if not candidates:
        raise RuntimeError('No encryption key configured. Set APP_ENCRYPTION_KEY for production.')
    return candidates[0]


def encrypt_value(value: str) -> str:
    if value in (None, ''):
        return value
    plaintext = str(value)
    # Prevent double-encryption during edits when old value is still encrypted.
    if is_encrypted_value(plaintext):
        return plaintext
    return cryptocode.encrypt(plaintext, get_write_encryption_key())


def decrypt_value(value: str) -> str:
    if value in (None, ''):
        return value

    encrypted = str(value)
    for key in _build_key_candidates():
        decrypted = cryptocode.decrypt(encrypted, key)
        if decrypted not in (False, None, ''):
            return decrypted
    return None


def is_encrypted_value(value: str) -> bool:
    return decrypt_value(value) not in (None, False)


def key_fingerprint() -> str:
    key = get_write_encryption_key()
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:10]
