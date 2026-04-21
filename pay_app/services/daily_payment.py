from datetime import timedelta
from decimal import Decimal, InvalidOperation
from math import floor

from django.utils import timezone

from ..models import Cabinet, Pay
from .constants import DAILY_DIVISOR


def recalculate_cabinet_paid_up_to(cabinet_id: int) -> None:
    """Recompute `paid_up_to` for active cabinet services using balance-based daily coverage."""
    cabinet = Cabinet.objects.filter(id=cabinet_id).values('id', 'balance', 'is_daily_payment').first()
    if not cabinet or not cabinet['is_daily_payment']:
        return

    active_pays = list(
        Pay.objects.filter(cabinet_id=cabinet_id, status='active').values('id', 'price_per_month')
    )
    if not active_pays:
        return

    daily_prices = []
    for pay in active_pays:
        try:
            monthly_price = Decimal(str(pay['price_per_month']))
        except (InvalidOperation, TypeError, ValueError):
            return

        if monthly_price <= 0:
            return

        daily_prices.append(monthly_price / DAILY_DIVISOR)

    total_daily = sum(daily_prices, Decimal('0'))
    if total_daily <= 0:
        return

    balance = cabinet['balance'] if cabinet['balance'] is not None else Decimal('0')
    days_covered = floor(balance / total_daily)
    paid_up_to = timezone.localdate() + timedelta(days=days_covered)

    Pay.objects.filter(cabinet_id=cabinet_id, status='active').update(paid_up_to=paid_up_to)
