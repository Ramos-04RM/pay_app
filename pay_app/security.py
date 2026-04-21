import hashlib
import logging
import os
import re
from typing import List

import cryptocode
from django.conf import settings
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

# cryptocode payload format may vary by version (3-part or 4-part segments),
# where each segment is Base64-like and separated by '*'.
# Using a structural format check is key-independent and reliably prevents
# double-encryption when the active key has changed.
_CRYPTOVALUE_RE = re.compile(
    r'^[A-Za-z0-9+/]{4,}={0,2}(\*[A-Za-z0-9+/]{4,}={0,2}){2,3}$'
)


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
    """Return the preferred encryption key used for writing new secret values."""
    candidates = _build_key_candidates()
    if not candidates:
        raise RuntimeError('No encryption key configured. Set APP_ENCRYPTION_KEY for production.')
    return candidates[0]


def encrypt_value(value: str) -> str:
    """Encrypt plaintext value unless it is empty or already encrypted."""
    if value in (None, ''):
        return value
    plaintext = str(value)
    # Prevent double-encryption during edits when old value is still encrypted.
    if is_encrypted_value(plaintext):
        return plaintext
    return cryptocode.encrypt(plaintext, get_write_encryption_key())


def decrypt_value(value: str) -> str | None:
    """Try all key candidates and return decrypted plaintext or ``None`` on failure."""
    if value in (None, ''):
        return value

    encrypted = str(value)
    for key in _build_key_candidates():
        decrypted = cryptocode.decrypt(encrypted, key)
        if decrypted not in (False, None, ''):
            return decrypted
    return None


def is_encrypted_value(value: str) -> bool:
    """Return True when *value* looks like a cryptocode-encrypted string.

    Detection is based on the output FORMAT (base64 segments joined by '*') rather than
    attempting decryption with the current key.  The previous implementation
    called decrypt_value() here, which meant that any value encrypted under a
    key that is no longer in _build_key_candidates() was mis-classified as
    "not encrypted" and subsequently re-encrypted – producing double-encrypted
    data in the database.
    """
    if not value:
        return False
    return bool(_CRYPTOVALUE_RE.match(str(value)))


def key_fingerprint() -> str:
    """Return a short SHA-256 fingerprint of the active write encryption key."""
    key = get_write_encryption_key()
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:10]
