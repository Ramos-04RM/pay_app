import json
import logging
from collections.abc import Mapping
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from ..models import Cabinet, Pay
from ..security import decrypt_value

logger = logging.getLogger(__name__)


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

    if not (user.is_staff or user.is_superuser):
        raise PermissionDenied('You do not have permission to decrypt secrets.')

    obj = get_object_or_404(allowed[model]['cls'], pk=obj_id)
    encrypted_value = getattr(obj, field, None)
    if not encrypted_value:
        return JsonResponse({'error': 'Empty value'}, status=400)

    decrypted_value = decrypt_value(encrypted_value)
    if decrypted_value in {False, None, ''}:
        return JsonResponse({'error': 'Decryption failed'}, status=400)

    logger.info(
        'secret_decrypt user=%s model=%s object_id=%s field=%s',
        user.id,
        model,
        obj_id,
        field,
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
