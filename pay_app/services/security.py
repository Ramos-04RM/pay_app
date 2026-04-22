import json
from collections.abc import Mapping
from typing import Any

from django.http import HttpRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ..logging_helpers import log_event
from ..models import Cabinet, Pay
from ..security import decrypt_value


def decrypt_item_payload(request: HttpRequest) -> tuple[dict[str, Any] | None, JsonResponse | None]:
    """Parse JSON payload for decrypt endpoint and return a validation error response on failure."""
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return None, JsonResponse({'error': 'Invalid JSON'}, status=400)
    return payload, None


def decrypt_secret(user: Any, payload: Mapping[str, Any]) -> JsonResponse:
    """Validate decrypt request permissions/shape and return decrypted secret value as JSON."""
    model = (payload.get('model') or '').strip().lower()
    field = (payload.get('field') or '').strip()
    obj_id = payload.get('id')

    allowed = {
        'pay': {'cls': Pay, 'fields': {'password', 'email_login'}},
        'cabinet': {'cls': Cabinet, 'fields': {'password', 'email_password'}},
    }

    if model not in allowed:
        return JsonResponse({'error': 'Invalid model'}, status=400)
    if field not in allowed[model]['fields']:
        return JsonResponse({'error': 'Invalid field'}, status=400)

    try:
        obj_id = int(obj_id)
    except Exception:
        return JsonResponse({'error': 'Invalid id'}, status=400)


    obj = get_object_or_404(allowed[model]['cls'], pk=obj_id)
    encrypted_value = getattr(obj, field, None)
    if not encrypted_value:
        return JsonResponse({'error': 'Empty value'}, status=400)

    decrypted_value = decrypt_value(encrypted_value)
    if decrypted_value in {False, None, ''}:
        log_event(
            event='secret.decrypt.failed',
            message='Secret decryption failed',
            logger_name='pay_app.security_audit',
            model=model,
            object_id=obj_id,
            field=field,
        )
        return JsonResponse({'error': 'Decryption failed'}, status=400)

    log_event(
        event='secret.decrypt.success',
        message='Secret decrypted',
        logger_name='pay_app.security_audit',
        model=model,
        object_id=obj_id,
        field=field,
        target_user_id=user.id,
    )
    return JsonResponse({'value': decrypted_value})


def decrypt_cabinet_secrets(cabinet: Cabinet) -> Cabinet:
    """Decrypt cabinet secret fields in-memory for rendering/editing flows."""
    cabinet.password = decrypt_value(cabinet.password)
    cabinet.email_password = decrypt_value(cabinet.email_password)
    return cabinet


def decrypt_pay_secrets(pay: Pay) -> Pay:
    """Decrypt pay secret fields in-memory for rendering/editing flows."""
    pay.password = decrypt_value(pay.password)
    pay.email_login = decrypt_value(pay.email_login)
    return pay
