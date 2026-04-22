from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from typing import Any

from .logging_helpers import log_event
from .models import Cabinet, Pay, Tag
from .services import recalculate_cabinet_paid_up_to


def _request_log_context(request: Any) -> dict[str, Any]:
    """Return request metadata for signal-based audit events."""
    if request is None:
        return {}

    request_context = getattr(request, 'log_context', {}) or {}
    request_id = request_context.get('request_id')
    if not request_id:
        request_id = request.headers.get('X-Request-ID')

    return {
        'request_id': request_id,
        'http_method': request_context.get('http_method') or getattr(request, 'method', None),
        'path': request_context.get('path') or getattr(request, 'path', None),
        'remote_addr': request_context.get('remote_addr') or request.META.get('REMOTE_ADDR'),
        'user_agent': request_context.get('user_agent') or request.META.get('HTTP_USER_AGENT', ''),
    }


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
    log_event(
        event='cabinet.created' if created else 'cabinet.updated',
        message='Cabinet saved',
        cabinet_id=instance.id,
        created=created,
        is_daily_payment=instance.is_daily_payment,
    )

    if created:
        if instance.is_daily_payment:
            recalculate_cabinet_paid_up_to(instance.id)
            log_event(
                event='daily_payment.recalculated',
                message='Cabinet daily coverage recalculated after create',
                cabinet_id=instance.id,
                trigger='cabinet_created',
            )
        return

    if (
        instance._prev_balance != instance.balance
        or instance._prev_is_daily_payment != instance.is_daily_payment
    ):
        recalculate_cabinet_paid_up_to(instance.id)
        log_event(
            event='daily_payment.recalculated',
            message='Cabinet daily coverage recalculated after update',
            cabinet_id=instance.id,
            trigger='cabinet_updated',
        )


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
    log_event(
        event='pay.created' if created else 'pay.updated',
        message='Pay saved',
        pay_id=instance.id,
        cabinet_id=instance.cabinet_id,
        created=created,
        status=instance.status,
        price_per_month=str(instance.price_per_month),
    )

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
        log_event(
            event='daily_payment.recalculated',
            message='Cabinet daily coverage recalculated after pay save',
            cabinet_id=cabinet_id,
            trigger='pay_saved',
            pay_id=instance.id,
        )


@receiver(post_delete, sender=Pay)
def pay_post_delete(sender: type[Pay], instance: Pay, **kwargs: Any) -> None:
    """Recalculate cabinet coverage after pay deletion."""
    log_event(
        event='pay.deleted',
        message='Pay deleted',
        pay_id=instance.id,
        cabinet_id=instance.cabinet_id,
        status=instance.status,
    )
    recalculate_cabinet_paid_up_to(instance.cabinet_id)
    log_event(
        event='daily_payment.recalculated',
        message='Cabinet daily coverage recalculated after pay delete',
        cabinet_id=instance.cabinet_id,
        trigger='pay_deleted',
        pay_id=instance.id,
    )


@receiver(post_delete, sender=Cabinet)
def cabinet_post_delete(sender: type[Cabinet], instance: Cabinet, **kwargs: Any) -> None:
    """Emit audit event for cabinet deletion."""
    log_event(
        event='cabinet.deleted',
        message='Cabinet deleted',
        cabinet_id=instance.id,
        is_daily_payment=instance.is_daily_payment,
    )


@receiver(post_save, sender=Tag)
def tag_post_save(sender: type[Tag], instance: Tag, created: bool, **kwargs: Any) -> None:
    """Emit audit event for tag create/update operations."""
    log_event(
        event='tag.created' if created else 'tag.updated',
        message='Tag saved',
        tag_id=instance.id,
        created=created,
        name=instance.name,
    )


@receiver(post_delete, sender=Tag)
def tag_post_delete(sender: type[Tag], instance: Tag, **kwargs: Any) -> None:
    """Emit audit event for tag deletion."""
    log_event(
        event='tag.deleted',
        message='Tag deleted',
        tag_id=instance.id,
        name=instance.name,
    )


@receiver(user_logged_in)
def auth_logged_in(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    """Audit successful login events."""
    log_event(
        event='auth.login.success',
        message='User login successful',
        logger_name='pay_app.security_audit',
        username=user.username,
        user_id=user.id,
        **_request_log_context(request),
    )


@receiver(user_logged_out)
def auth_logged_out(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    """Audit logout events."""
    user_id = getattr(user, 'id', None)
    username = getattr(user, 'username', 'anonymous')
    log_event(
        event='auth.logout',
        message='User logout',
        logger_name='pay_app.security_audit',
        username=username,
        user_id=user_id,
        **_request_log_context(request),
    )


@receiver(user_login_failed)
def auth_login_failed(sender: Any, credentials: dict[str, Any], request: Any, **kwargs: Any) -> None:
    """Audit failed login attempts without exposing sensitive values."""
    log_event(
        event='auth.login.failed',
        message='User login failed',
        logger_name='pay_app.security_audit',
        username=credentials.get('username', 'unknown'),
        **_request_log_context(request),
    )
