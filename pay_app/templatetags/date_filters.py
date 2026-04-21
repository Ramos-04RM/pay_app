from django import template
from datetime import date
from typing import Any

register = template.Library()


@register.filter
def date_iso(value: Any) -> str:
    """Return value formatted for HTML5 date inputs using stable ISO representation."""
    if not value:
        return ''

    if isinstance(value, date):
        return value.isoformat()

    return str(value)
