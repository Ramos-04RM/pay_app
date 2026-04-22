import logging
from collections.abc import Mapping, Sequence
from typing import Any

AUDIT_LOGGER = logging.getLogger('pay_app.audit')
SENSITIVE_KEYS = {
    'password',
    'email_password',
    'email_login',
    'auth_password',
    'secret',
    'token',
    'access_token',
    'refresh_token',
}


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, nested_value in value.items():
            key_str = str(key)
            if key_str.lower() in SENSITIVE_KEYS:
                clean[key_str] = '***'
            else:
                clean[key_str] = _sanitize(nested_value)
        return clean

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize(item) for item in value]

    return value


def log_event(
    event: str,
    message: str,
    level: int = logging.INFO,
    logger_name: str = 'pay_app.audit',
    **context: Any,
) -> None:
    """Emit a structured audit event without leaking sensitive fields."""
    safe_context = _sanitize(context)
    top_level_fields = {
        'username': safe_context.pop('username', None),
        'user_id': safe_context.pop('user_id', None),
        'request_id': safe_context.pop('request_id', None),
        'path': safe_context.pop('path', None),
        'http_method': safe_context.pop('http_method', None),
        'remote_addr': safe_context.pop('remote_addr', None),
        'user_agent': safe_context.pop('user_agent', None),
    }
    extra = {'event': event, 'context': safe_context}
    extra.update({key: value for key, value in top_level_fields.items() if value is not None})
    logger = AUDIT_LOGGER if logger_name == 'pay_app.audit' else logging.getLogger(logger_name)
    logger.log(level, message, extra=extra)

