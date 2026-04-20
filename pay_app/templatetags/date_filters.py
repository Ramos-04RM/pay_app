from django import template
from datetime import date

register = template.Library()


@register.filter
def date_iso(value):
    """
    Повертає дату в ISO форматі (Y-m-d), незалежно від локалізації.
    Це необхідно для HTML5 input[type="date"] елементів.
    """
    if not value:
        return ''

    if isinstance(value, date):
        return value.isoformat()

    return str(value)

