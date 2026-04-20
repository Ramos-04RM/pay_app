import calendar
import datetime
from decimal import Decimal
from urllib.parse import urlencode
from django.utils.translation import gettext as _

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


def _calculate_proportional_cost(service, month_start, month_end):
    """
    Calculate proportional cost of a service based on its active days within a month.

    Args:
    - service: Pay object
    - month_start: start of month (datetime.date)
    - month_end: end of month (datetime.date)

    Returns: (Decimal) proportional cost of service for the period it was active in the month

    Logic:
    1. Define the actual bounds of service activity within the month:
       - Actual start = max(create_date, month_start)
       - Actual end = min(paid_up_to, month_end)
    2. If service was not active in this month - return 0
    3. Calculate the number of active days (inclusive of both days)
    4. Calculate proportion: active_days / total_days_in_month
    5. Return: price_per_month * proportion
    """
    price = Decimal(str(service.price_per_month or 0))

    # Determine the actual bounds of service activity within the month
    active_start = max(service.create_date, month_start)
    active_end = min(service.paid_up_to, month_end)

    # Check if service was active in this month
    if active_start > active_end:
        return Decimal('0')

    # Calculate the number of active days (inclusive)
    active_days = (active_end - active_start).days + 1

    # Calculate the number of days in the month
    days_in_month = (month_end - month_start).days + 1

    # Calculate proportion and return result
    proportion = Decimal(active_days) / Decimal(days_in_month)
    return price * proportion


def _get_period_bounds(period, start_raw, end_raw, today):
    """
    Calculate period bounds based on the selected period type.

    Returns: (period_start, period_end) - closed bounds inclusive

    Period 'month': current month
    Period 'year': current year (January 1 - December 31)
    Period 'last12': last 12 months from today
    Period 'custom': user-defined range or fallback to current month on error
    """
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
    """
    Build statistics context for payment metrics.

    FILTERING LOGIC:
    ================
    1. Period: user selects period (current month, year, 12 months, custom)
    2. Base set: filter services active within this period
       - Condition: create_date <= period_end AND paid_up_to >= period_start
       - This ensures correct display of active services in the period

    3. Active services: base set + status='active'
    4. Inactive services: base set + status='not active'

    METRICS:
    ========
    - burn_by_currency: monthly cost of active services by currency
    - month_points: monthly burn for each month in the period
    - expiry_pipeline: distribution of active services by expiration date
    - status_mix: distribution of active/inactive services
    """
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
        create_date__lte=period_end,    # Service created before period end
        paid_up_to__gte=period_start,   # Service active from period start
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

    # Select appropriate queryset for burn calculation based on status filter
    # If no status selected, include both active and inactive services
    # If status selected, use only that subset
    if selected_status in {'active', 'not active'}:
        burn_queryset = base_queryset.filter(status=selected_status)
    else:
        # When no status filter is applied, calculate for all services
        burn_queryset = base_queryset

    # Calculate burn_by_currency considering proportional costs over the period
    # For each currency, calculate the average monthly burn
    burn_by_currency_dict = {}
    for service in burn_queryset:
        currency = service.currency or 'N/A'
        if currency not in burn_by_currency_dict:
            burn_by_currency_dict[currency] = Decimal('0')

        # Calculate proportional cost for the entire period
        total_proportional_cost = Decimal('0')
        month_count = 0
        for month_start in _iter_month_starts(period_start, period_end):
            month_end = _end_of_month(month_start)
            cost = _calculate_proportional_cost(service, month_start, month_end)
            total_proportional_cost += cost
            if cost > 0:
                month_count += 1

        # If active in at least one month, add to category
        if month_count > 0:
            # Calculate average monthly burn for the period
            avg_monthly = total_proportional_cost / Decimal(month_count)
            burn_by_currency_dict[currency] += avg_monthly

    burn_by_currency = []
    for currency in sorted(burn_by_currency_dict.keys()):
        monthly_burn = burn_by_currency_dict[currency]
        burn_by_currency.append({
            'currency': currency,
            'monthly_burn': monthly_burn,
            'annualized': monthly_burn * Decimal('12'),
        })

    expired_count = active_queryset.filter(paid_up_to__lt=today).count()
    expiring_7_count = active_queryset.filter(
        paid_up_to__gte=today,
        paid_up_to__lte=today + datetime.timedelta(days=7),
    ).count()
    # FIXED: expiring_30_count now shows 8-30 days, not 0-30
    # This eliminates duplication and makes KPI correct
    expiring_8_30_count = active_queryset.filter(
        paid_up_to__gt=today + datetime.timedelta(days=7),
        paid_up_to__lte=today + datetime.timedelta(days=30),
    ).count()
    expiring_31_60_count = active_queryset.filter(
        paid_up_to__gt=today + datetime.timedelta(days=30),
        paid_up_to__lte=today + datetime.timedelta(days=60),
    ).count()
    expiring_61_plus_count = active_queryset.filter(
        paid_up_to__gt=today + datetime.timedelta(days=60),
    ).count()

    expiring_30_count = expiring_8_30_count

    expiry_pipeline = [
        {'label': _('Expired'), 'key': 'expired', 'count': expired_count},
        {'label': _('0–7 days'), 'key': 'd0_7', 'count': expiring_7_count},
        {'label': _('8–30 days'), 'key': 'd8_30', 'count': expiring_8_30_count},
        {'label': _('31–60 days'), 'key': 'd31_60', 'count': expiring_31_60_count},
        {'label': _('61+ days'), 'key': 'd61_plus', 'count': expiring_61_plus_count},
    ]
    max_pipeline_count = max((item['count'] for item in expiry_pipeline), default=0) or 1
    for item in expiry_pipeline:
        item['percent'] = round((item['count'] / max_pipeline_count) * 100, 2) if item['count'] else 0

    # Calculate group_cost considering proportional costs over the period
    group_cost_dict = {}
    for service in active_queryset:
        currency = service.currency or 'N/A'
        group = service.groups or 'No group'
        key = (currency, group)

        if key not in group_cost_dict:
            group_cost_dict[key] = Decimal('0')

        # Calculate proportional cost for the entire period
        total_proportional = Decimal('0')
        for month_start in _iter_month_starts(period_start, period_end):
            month_end = _end_of_month(month_start)
            cost = _calculate_proportional_cost(service, month_start, month_end)
            total_proportional += cost

        group_cost_dict[key] += total_proportional

    group_cost = [
        {
            'currency': key[0],
            'groups': key[1],
            'group_name': key[1],
            'total': total,
        }
        for key, total in group_cost_dict.items()
        if total > 0
    ]
    group_cost = sorted(group_cost, key=lambda x: (x['currency'], -x['total'], x['groups']))

    # Calculate top_cabinets considering proportional costs over the period
    cabinet_cost_dict = {}
    for service in active_queryset:
        currency = service.currency or 'N/A'
        cabinet_id = service.cabinet_id
        cabinet_login = service.cabinet.login if service.cabinet_id else f"Cabinet #{cabinet_id}"
        key = (currency, cabinet_id, cabinet_login)

        if key not in cabinet_cost_dict:
            cabinet_cost_dict[key] = Decimal('0')

        # Calculate proportional cost for the entire period
        total_proportional = Decimal('0')
        for month_start in _iter_month_starts(period_start, period_end):
            month_end = _end_of_month(month_start)
            cost = _calculate_proportional_cost(service, month_start, month_end)
            total_proportional += cost

        cabinet_cost_dict[key] += total_proportional

    top_cabinets = [
        {
            'currency': key[0],
            'cabinet_id': key[1],
            'cabinet__login': key[2],
            'cabinet_name': key[2],
            'total': total,
        }
        for key, total in cabinet_cost_dict.items()
        if total > 0
    ]
    top_cabinets = sorted(top_cabinets, key=lambda x: (x['currency'], -x['total'], x['cabinet__login']))[:8]


    max_group_total = max((item['total'] for item in group_cost), default=Decimal('0'))
    if max_group_total <= 0:
        max_group_total = Decimal('1')
    for item in group_cost:
        item['percent'] = round((item['total'] / max_group_total) * 100, 2) if item['total'] else 0

    max_cabinet_total = max((item['total'] for item in top_cabinets), default=Decimal('0'))
    if max_cabinet_total <= 0:
        max_cabinet_total = Decimal('1')
    for item in top_cabinets:
        item['percent'] = round((item['total'] / max_cabinet_total) * 100, 2) if item['total'] else 0

    month_points = []
    max_month_total = Decimal('0')
    for month_start in _iter_month_starts(period_start, period_end):
        month_end = _end_of_month(month_start)
        month_label = month_start.strftime('%b %Y')

        # Calculate proportional costs for each currency in this month
        month_costs_by_currency = {}
        for service in active_queryset.filter(
            create_date__lte=month_end,
            paid_up_to__gte=month_start,
        ):
            currency = service.currency or 'N/A'
            if currency not in month_costs_by_currency:
                month_costs_by_currency[currency] = Decimal('0')

            # Calculate proportional cost for this month
            proportional_cost = _calculate_proportional_cost(service, month_start, month_end)
            month_costs_by_currency[currency] += proportional_cost

        # Add points for each currency
        for currency, total in month_costs_by_currency.items():
            if total > 0:  # Add only non-zero values
                max_month_total = max(max_month_total, total)
                month_points.append({
                    'month': month_start.strftime('%Y-%m'),
                    'month_label': month_label,
                    'currency': currency,
                    'total': total,
                })

    if max_month_total <= 0:
        max_month_total = Decimal('1')
    for point in month_points:
        point['percent'] = round((point['total'] / max_month_total) * 100, 2) if point['total'] else 0

    status_mix = [
        {'label': _('Active'), 'key': 'active', 'count': active_queryset.count()},
        {'label': _('Inactive'), 'key': 'inactive', 'count': inactive_queryset.count()},
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
