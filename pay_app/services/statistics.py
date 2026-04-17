import calendar
import datetime
from decimal import Decimal
from urllib.parse import urlencode

from django.db.models import Sum
from django.db.models.functions import Coalesce

from ..models import Cabinet, Pay
from .common import add_one_month, get_common_context
from .constants import (
    STAT_PERIOD_CHOICES,
    STAT_PERIOD_CUSTOM,
    STAT_PERIOD_LAST_12,
    STAT_PERIOD_MONTH,
    STAT_PERIOD_YEAR,
)


def _start_of_month(value):
    return value.replace(day=1)


def _end_of_month(value):
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])


def _iter_month_starts(start_date, end_date):
    current = _start_of_month(start_date)
    end_month = _start_of_month(end_date)
    while current <= end_month:
        yield current
        current = add_one_month(current)


def _normalize_stat_period(value):
    period = (value or STAT_PERIOD_MONTH).strip().lower()
    if period not in STAT_PERIOD_CHOICES:
        return STAT_PERIOD_MONTH
    return period


def _parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def _get_period_bounds(period, start_raw, end_raw, today):
    if period == STAT_PERIOD_YEAR:
        start = datetime.date(today.year, 1, 1)
        end = datetime.date(today.year, 12, 31)
    elif period == STAT_PERIOD_LAST_12:
        start = _start_of_month(add_one_month(today) - datetime.timedelta(days=365))
        end = _end_of_month(today)
    elif period == STAT_PERIOD_CUSTOM:
        start = _parse_iso_date(start_raw)
        end = _parse_iso_date(end_raw)
        if not start or not end:
            start = _start_of_month(today)
            end = _end_of_month(today)
        if start > end:
            start, end = end, start
    else:
        start = _start_of_month(today)
        end = _end_of_month(today)
    return start, end


def _build_statistics_query_params(data):
    params = {}
    if data.get('currency'):
        params['currency'] = data['currency']
    if data.get('status'):
        params['status'] = data['status']
    if data.get('groups'):
        params['group'] = data['groups']
    if data.get('cabinet'):
        params['cabinet'] = str(data['cabinet'])
    if data.get('period'):
        params['period'] = data['period']
    if data.get('start'):
        params['start'] = data['start']
    if data.get('end'):
        params['end'] = data['end']
    if data.get('drill'):
        params['drill'] = data['drill']
    if data.get('drill_value'):
        params['drill_value'] = data['drill_value']
    if data.get('drill_currency'):
        params['drill_currency'] = data['drill_currency']
    return urlencode(params)


def build_statistics_context(request):
    today = datetime.date.today()
    period = _normalize_stat_period(request.GET.get('period'))
    start_raw = (request.GET.get('start') or '').strip()
    end_raw = (request.GET.get('end') or '').strip()
    selected_currency = (request.GET.get('currency') or '').strip()
    selected_status = (request.GET.get('status') or '').strip()
    selected_group = (request.GET.get('group') or '').strip()
    selected_cabinet = (request.GET.get('cabinet') or '').strip()

    period_start, period_end = _get_period_bounds(period, start_raw, end_raw, today)
    period_start_display = period_start.isoformat()
    period_end_display = period_end.isoformat()

    base_queryset = Pay.objects.select_related('cabinet').filter(
        paid_up_to__gte=period_start,
        paid_up_to__lte=period_end,
    )
    if selected_currency:
        base_queryset = base_queryset.filter(currency=selected_currency)
    if selected_status in {'active', 'not active'}:
        base_queryset = base_queryset.filter(status=selected_status)
    if selected_group:
        base_queryset = base_queryset.filter(groups=selected_group)
    if selected_cabinet:
        try:
            base_queryset = base_queryset.filter(cabinet_id=int(selected_cabinet))
        except (TypeError, ValueError):
            selected_cabinet = ''

    currency_options = list(
        Pay.objects.exclude(currency__exact='').values_list('currency', flat=True).distinct().order_by('currency')
    )
    group_options = list(
        Pay.objects.exclude(groups__isnull=True).exclude(groups__exact='').values_list('groups', flat=True).distinct().order_by('groups')
    )
    cabinet_options = Cabinet.objects.order_by('login').values('id', 'login')

    active_queryset = base_queryset.filter(status='active')
    inactive_queryset = base_queryset.filter(status='not active')

    burn_by_currency = []
    for row in active_queryset.values('currency').annotate(monthly_burn=Coalesce(Sum('price_per_month'), 0.0)).order_by('currency'):
        monthly_burn = Decimal(str(row['monthly_burn'] or 0))
        burn_by_currency.append({
            'currency': row['currency'] or 'N/A',
            'monthly_burn': monthly_burn,
            'annualized': monthly_burn * Decimal('12'),
        })

    expired_count = active_queryset.filter(paid_up_to__lt=today).count()
    expiring_7_count = active_queryset.filter(
        paid_up_to__gte=today,
        paid_up_to__lte=today + datetime.timedelta(days=7),
    ).count()
    expiring_30_count = active_queryset.filter(
        paid_up_to__gte=today,
        paid_up_to__lte=today + datetime.timedelta(days=30),
    ).count()
    expiry_pipeline = [
        {'label': 'Expired', 'key': 'expired', 'count': expired_count},
        {'label': '0–7 days', 'key': 'd0_7', 'count': expiring_7_count},
        {'label': '8–30 days', 'key': 'd8_30', 'count': active_queryset.filter(paid_up_to__gt=today + datetime.timedelta(days=7), paid_up_to__lte=today + datetime.timedelta(days=30)).count()},
        {'label': '31–60 days', 'key': 'd31_60', 'count': active_queryset.filter(paid_up_to__gt=today + datetime.timedelta(days=30), paid_up_to__lte=today + datetime.timedelta(days=60)).count()},
        {'label': '61+ days', 'key': 'd61_plus', 'count': active_queryset.filter(paid_up_to__gt=today + datetime.timedelta(days=60)).count()},
    ]
    max_pipeline_count = max((item['count'] for item in expiry_pipeline), default=0) or 1
    for item in expiry_pipeline:
        item['percent'] = round((item['count'] / max_pipeline_count) * 100, 2) if item['count'] else 0

    group_cost = list(
        active_queryset.values('currency', 'groups').annotate(total=Coalesce(Sum('price_per_month'), 0.0)).order_by('currency', '-total', 'groups')
    )
    top_cabinets = list(
        active_queryset.values('currency', 'cabinet_id', 'cabinet__login').annotate(total=Coalesce(Sum('price_per_month'), 0.0)).order_by('currency', '-total', 'cabinet__login')[:8]
    )

    max_group_total = max((item['total'] for item in group_cost), default=0) or 1
    for item in group_cost:
        item['group_name'] = item['groups'] or 'No group'
        item['percent'] = round((item['total'] / max_group_total) * 100, 2) if item['total'] else 0

    max_cabinet_total = max((item['total'] for item in top_cabinets), default=0) or 1
    for item in top_cabinets:
        item['cabinet_name'] = item['cabinet__login'] or f"Cabinet #{item['cabinet_id']}"
        item['percent'] = round((item['total'] / max_cabinet_total) * 100, 2) if item['total'] else 0

    month_points = []
    max_month_total = Decimal('0')
    for month_start in _iter_month_starts(period_start, period_end):
        month_end = _end_of_month(month_start)
        month_label = month_start.strftime('%b %Y')
        month_totals = active_queryset.filter(
            create_date__lte=month_end,
            paid_up_to__gte=month_start,
        ).values('currency').annotate(total=Coalesce(Sum('price_per_month'), 0.0)).order_by('currency')
        for row in month_totals:
            total_decimal = Decimal(str(row['total'] or 0))
            max_month_total = max(max_month_total, total_decimal)
            month_points.append({
                'month': month_start.strftime('%Y-%m'),
                'month_label': month_label,
                'currency': row['currency'] or 'N/A',
                'total': total_decimal,
            })
    if max_month_total <= 0:
        max_month_total = Decimal('1')
    for point in month_points:
        point['percent'] = round((point['total'] / max_month_total) * 100, 2) if point['total'] else 0

    status_mix = [
        {'label': 'Active', 'key': 'active', 'count': active_queryset.count()},
        {'label': 'Inactive', 'key': 'inactive', 'count': inactive_queryset.count()},
    ]
    max_status_count = max((item['count'] for item in status_mix), default=0) or 1
    for item in status_mix:
        item['percent'] = round((item['count'] / max_status_count) * 100, 2) if item['count'] else 0

    drill = (request.GET.get('drill') or '').strip()
    drill_value = (request.GET.get('drill_value') or '').strip()
    drill_currency = (request.GET.get('drill_currency') or '').strip()
    detail_queryset = base_queryset
    drill_caption = 'Showing filtered services.'

    if drill_currency:
        detail_queryset = detail_queryset.filter(currency=drill_currency)
    if drill == 'expired':
        detail_queryset = detail_queryset.filter(status='active', paid_up_to__lt=today)
        drill_caption = 'Expired active services.'
    elif drill == 'expiring_7':
        detail_queryset = detail_queryset.filter(status='active', paid_up_to__gte=today, paid_up_to__lte=today + datetime.timedelta(days=7))
        drill_caption = 'Active services expiring in 7 days.'
    elif drill == 'd0_7':
        detail_queryset = detail_queryset.filter(status='active', paid_up_to__gte=today, paid_up_to__lte=today + datetime.timedelta(days=7))
        drill_caption = 'Active services expiring in 0–7 days.'
    elif drill == 'expiring_30':
        detail_queryset = detail_queryset.filter(status='active', paid_up_to__gte=today, paid_up_to__lte=today + datetime.timedelta(days=30))
        drill_caption = 'Active services expiring in 30 days.'
    elif drill == 'd8_30':
        detail_queryset = detail_queryset.filter(status='active', paid_up_to__gt=today + datetime.timedelta(days=7), paid_up_to__lte=today + datetime.timedelta(days=30))
        drill_caption = 'Active services expiring in 8–30 days.'
    elif drill == 'd31_60':
        detail_queryset = detail_queryset.filter(status='active', paid_up_to__gt=today + datetime.timedelta(days=30), paid_up_to__lte=today + datetime.timedelta(days=60))
        drill_caption = 'Active services expiring in 31–60 days.'
    elif drill == 'd61_plus':
        detail_queryset = detail_queryset.filter(status='active', paid_up_to__gt=today + datetime.timedelta(days=60))
        drill_caption = 'Active services expiring in 61+ days.'
    elif drill == 'group' and drill_value:
        detail_queryset = detail_queryset.filter(groups=drill_value)
        drill_caption = f'Services for group: {drill_value}.'
    elif drill == 'cabinet' and drill_value:
        try:
            detail_queryset = detail_queryset.filter(cabinet_id=int(drill_value))
            drill_caption = f'Services for cabinet ID: {drill_value}.'
        except (TypeError, ValueError):
            pass
    elif drill == 'month' and drill_value:
        month_start = _parse_iso_date(f'{drill_value}-01')
        if month_start:
            detail_queryset = detail_queryset.filter(
                create_date__lte=_end_of_month(month_start),
                paid_up_to__gte=month_start,
            )
            drill_caption = f'Services contributing to projected burn in {month_start.strftime("%b %Y")}.' 
    elif drill == 'status' and drill_value in {'active', 'not active'}:
        detail_queryset = detail_queryset.filter(status=drill_value)
        drill_caption = f'Services with status: {drill_value}.'

    detail_rows = []
    for service in detail_queryset.order_by('paid_up_to', 'service')[:300]:
        days_to_expiry = (service.paid_up_to - today).days if service.paid_up_to else None
        detail_rows.append({
            'id': service.id,
            'service': service.service,
            'cabinet': service.cabinet.login if service.cabinet_id else '-',
            'cabinet_id': service.cabinet_id,
            'group': service.groups or '-',
            'status': service.status or '-',
            'currency': service.currency or '-',
            'price_per_month': service.price_per_month or 0,
            'paid_up_to': service.paid_up_to,
            'days_to_expiry': days_to_expiry,
        })

    query_state = {
        'currency': selected_currency,
        'status': selected_status,
        'groups': selected_group,
        'cabinet': selected_cabinet,
        'period': period,
        'start': period_start_display if period == STAT_PERIOD_CUSTOM else '',
        'end': period_end_display if period == STAT_PERIOD_CUSTOM else '',
    }
    content = {
        'period': period,
        'period_start': period_start_display,
        'period_end': period_end_display,
        'selected_currency': selected_currency,
        'selected_status': selected_status,
        'selected_group': selected_group,
        'selected_cabinet': selected_cabinet,
        'currency_options': currency_options,
        'group_options': group_options,
        'cabinet_options': cabinet_options,
        'burn_by_currency': burn_by_currency,
        'active_count': active_queryset.count(),
        'inactive_count': inactive_queryset.count(),
        'expired_count': expired_count,
        'expiring_7_count': expiring_7_count,
        'expiring_30_count': expiring_30_count,
        'cabinets_count': base_queryset.values('cabinet_id').distinct().count(),
        'group_cost': group_cost,
        'top_cabinets': top_cabinets,
        'expiry_pipeline': expiry_pipeline,
        'status_mix': status_mix,
        'month_points': month_points,
        'detail_rows': detail_rows,
        'drill_caption': drill_caption,
        'base_querystring': _build_statistics_query_params(query_state),
    }
    content.update(get_common_context())
    return content
