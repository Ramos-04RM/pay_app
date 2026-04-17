import calendar
import datetime

from ..models import Pay


def add_one_month(value):
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def get_common_context():
    today = datetime.date.today()
    month = today + datetime.timedelta(days=31)
    week = today + datetime.timedelta(days=7)
    month_ago = today - datetime.timedelta(days=31)

    last_dt = Pay.objects.filter(
        status='active',
        paid_up_to__gte=today,
        paid_up_to__lte=week,
    ).order_by('paid_up_to')[:5]

    not_paid = Pay.objects.filter(
        status='active',
        paid_up_to__lt=today,
        paid_up_to__gte=month_ago,
    ).order_by('paid_up_to')[:5]

    return {
        'week': week,
        'today': today,
        'last_dt': last_dt,
        'not_paid': not_paid,
        'month': month,
        'month_ago': month_ago,
    }
