from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from typing import Any

from .models import Cabinet, Pay
from .services import recalculate_cabinet_paid_up_to


@receiver(pre_save, sender=Cabinet)
def cabinet_pre_save(sender: type[Cabinet], instance: Cabinet, **kwargs: Any) -> None:
    """Cache previous cabinet balance/daily flags before save for change detection."""
    instance._prev_balance = None
    instance._prev_is_daily_payment = None

    if not instance.pk:
        return

    previous = Cabinet.objects.filter(pk=instance.pk).values('balance', 'is_daily_payment').first()
    if previous:
        instance._prev_balance = previous['balance']
        instance._prev_is_daily_payment = previous['is_daily_payment']


@receiver(post_save, sender=Cabinet)
def cabinet_post_save(sender: type[Cabinet], instance: Cabinet, created: bool, **kwargs: Any) -> None:
    """Recalculate daily-payment coverage when cabinet state changes."""
    if created:
        if instance.is_daily_payment:
            recalculate_cabinet_paid_up_to(instance.id)
        return

    if (
        instance._prev_balance != instance.balance
        or instance._prev_is_daily_payment != instance.is_daily_payment
    ):
        recalculate_cabinet_paid_up_to(instance.id)


@receiver(pre_save, sender=Pay)
def pay_pre_save(sender: type[Pay], instance: Pay, **kwargs: Any) -> None:
    """Cache previous pay pricing/status/cabinet fields before save."""
    instance._prev_price_per_month = None
    instance._prev_status = None
    instance._prev_cabinet_id = None

    if not instance.pk:
        return

    previous = Pay.objects.filter(pk=instance.pk).values(
        'price_per_month',
        'status',
        'cabinet_id',
    ).first()
    if previous:
        instance._prev_price_per_month = previous['price_per_month']
        instance._prev_status = previous['status']
        instance._prev_cabinet_id = previous['cabinet_id']


@receiver(post_save, sender=Pay)
def pay_post_save(sender: type[Pay], instance: Pay, created: bool, **kwargs: Any) -> None:
    """Recalculate affected cabinet coverage when pay fields change."""
    affected_cabinet_ids = set()

    if created:
        affected_cabinet_ids.add(instance.cabinet_id)
    else:
        if (
            instance._prev_price_per_month != instance.price_per_month
            or instance._prev_status != instance.status
            or instance._prev_cabinet_id != instance.cabinet_id
        ):
            affected_cabinet_ids.add(instance.cabinet_id)
            if instance._prev_cabinet_id is not None:
                affected_cabinet_ids.add(instance._prev_cabinet_id)

    for cabinet_id in affected_cabinet_ids:
        recalculate_cabinet_paid_up_to(cabinet_id)


@receiver(post_delete, sender=Pay)
def pay_post_delete(sender: type[Pay], instance: Pay, **kwargs: Any) -> None:
    """Recalculate cabinet coverage after pay deletion."""
    recalculate_cabinet_paid_up_to(instance.cabinet_id)