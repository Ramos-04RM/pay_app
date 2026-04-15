import json
import calendar
import datetime
import cryptocode
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q, Count, F, Value, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import PayForm, CabinetForm, TagForm, CabinetTagAssignForm
from .models import Pay, Cabinet, Tag, CabinetTag


PAY_MODE_ALL = 'all'
PAY_MODE_UPCOMING = 'upcoming'
PAY_MODE_OVERDUE = 'overdue'
PAY_MODES = {PAY_MODE_ALL, PAY_MODE_UPCOMING, PAY_MODE_OVERDUE}

PAY_SORT_MAP = {
    'id_asc': ('id',),
    'id_desc': ('-id',),
    'groups_asc': ('groups', 'id'),
    'groups_desc': ('-groups', 'id'),
    'create_date_asc': ('create_date', 'id'),
    'create_date_desc': ('-create_date', 'id'),
    'service_asc': ('service', 'id'),
    'service_desc': ('-service', 'id'),
    'type_source_asc': ('type_source', 'id'),
    'type_source_desc': ('-type_source', 'id'),
    'price_per_month_asc': ('price_per_month', 'id'),
    'price_per_month_desc': ('-price_per_month', 'id'),
    'currency_asc': ('currency', 'id'),
    'currency_desc': ('-currency', 'id'),
    'cabinet_balance_asc': ('cabinet_balance_for_sort', 'id'),
    'cabinet_balance_desc': ('-cabinet_balance_for_sort', 'id'),
    'cabinet_currency_asc': ('cabinet__currency', 'id'),
    'cabinet_currency_desc': ('-cabinet__currency', 'id'),
    'pay_sys_asc': ('pay_sys', 'id'),
    'pay_sys_desc': ('-pay_sys', 'id'),
    'paid_up_to_asc': ('paid_up_to', 'id'),
    'paid_up_to_desc': ('-paid_up_to', 'id'),
    'email_login_asc': ('email_login', 'id'),
    'email_login_desc': ('-email_login', 'id'),
    'status_asc': ('status', 'id'),
    'status_desc': ('-status', 'id'),
}
PAY_SORT_DEFAULT = 'id_asc'

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

    # Sidebar: only overdue items for the last 31 days.
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

STAT_PERIOD_MONTH = 'month'
STAT_PERIOD_YEAR = 'year'
STAT_PERIOD_LAST_12 = 'last12'
STAT_PERIOD_CUSTOM = 'custom'
STAT_PERIOD_CHOICES = {STAT_PERIOD_MONTH, STAT_PERIOD_YEAR, STAT_PERIOD_LAST_12, STAT_PERIOD_CUSTOM}


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


def get_default_statuses_for_mode(mode):
    if mode == PAY_MODE_OVERDUE:
        return ['active', 'not active']
    return ['active']


def get_pay_base_url_name(mode):
    if mode == PAY_MODE_UPCOMING:
        return 'app:filter_by_date'
    if mode == PAY_MODE_OVERDUE:
        return 'app:overdue_payments'
    return 'app:index'


def get_pay_base_url(mode):
    url_name = get_pay_base_url_name(mode)
    if url_name in {'app:filter_by_date', 'app:overdue_payments'}:
        return reverse(url_name, args=('1',))
    return reverse(url_name)


def build_pay_list_url(
    *,
    mode=PAY_MODE_ALL,
    statuses=None,
    q='',
    sort='',
    pay_sys='',
    type_source='',
    balance_gt_payment=None,
    daily_payment=None,
):
    statuses = statuses or []
    params = {}

    if mode != PAY_MODE_ALL:
        params['mode'] = mode
    if q:
        params['q'] = q
    if sort and sort != PAY_SORT_DEFAULT:
        params['sort'] = sort
    if pay_sys:
        params['pay_sys'] = pay_sys
    if type_source:
        params['type_source'] = type_source

    balance_gt_payment = balance_gt_payment or []
    normalized_balance_gt_payment = [
        item
        for item in balance_gt_payment
        if item in {'yes', 'no'}
    ]
    if normalized_balance_gt_payment:
        params['balance_gt_payment'] = normalized_balance_gt_payment

    daily_payment = daily_payment or []
    normalized_daily_payment = [
        item
        for item in daily_payment
        if item in {'yes', 'no'}
    ]
    if normalized_daily_payment:
        params['daily_payment'] = normalized_daily_payment

    if statuses:
        params['status'] = list(statuses)

    base_url = get_pay_base_url(mode)
    query_string = urlencode(params, doseq=True)
    return f'{base_url}?{query_string}' if query_string else base_url


def get_pay_list_state(request, default_mode=PAY_MODE_ALL, overrides=None):
    query_data = request.GET.copy()
    overrides = overrides or {}

    for key, value in overrides.items():
        if isinstance(value, (list, tuple)):
            query_data.setlist(key, [str(item) for item in value])
        elif value is None:
            query_data.pop(key, None)
        else:
            query_data[key] = str(value)

    mode = (query_data.get('mode') or default_mode or PAY_MODE_ALL).strip().lower()
    if mode not in PAY_MODES:
        mode = default_mode if default_mode in PAY_MODES else PAY_MODE_ALL

    selected_statuses = [
        status
        for status in query_data.getlist('status')
        if status in {'active', 'not active'}
    ]
    if not selected_statuses:
        selected_statuses = get_default_statuses_for_mode(mode)

    search_query = (query_data.get('q') or '').strip()

    current_sort = (query_data.get('sort') or PAY_SORT_DEFAULT).strip()
    if current_sort not in PAY_SORT_MAP:
        current_sort = PAY_SORT_DEFAULT

    selected_pay_sys = (query_data.get('pay_sys') or '').strip()
    selected_type_source = (query_data.get('type_source') or '').strip()

    balance_gt_payment = [
        item.strip().lower()
        for item in query_data.getlist('balance_gt_payment')
        if item.strip().lower() in {'yes', 'no'}
    ]
    if not balance_gt_payment:
        balance_gt_payment = ['yes', 'no']

    daily_payment = [
        item.strip().lower()
        for item in query_data.getlist('daily_payment')
        if item.strip().lower() in {'yes', 'no'}
    ]
    if not daily_payment:
        daily_payment = ['yes', 'no']

    return {
        'mode': mode,
        'selected_statuses': selected_statuses,
        'search_query': search_query,
        'current_sort': current_sort,
        'selected_pay_sys': selected_pay_sys,
        'selected_type_source': selected_type_source,
        'balance_gt_payment': balance_gt_payment,
        'daily_payment': daily_payment,
    }


def get_pay_sort_url(state, field_name):
    asc_sort = f'{field_name}_asc'
    desc_sort = f'{field_name}_desc'
    next_sort = desc_sort if state['current_sort'] == asc_sort else asc_sort
    return build_pay_list_url(
        mode=state['mode'],
        statuses=state['selected_statuses'],
        q=state['search_query'],
        sort=next_sort,
        pay_sys=state['selected_pay_sys'],
        type_source=state['selected_type_source'],
        balance_gt_payment=state['balance_gt_payment'],
        daily_payment=state['daily_payment'],
    )


def toggle_balance_gt_payment_filter(selected_values, value):
    normalized = [
        item
        for item in (selected_values or [])
        if item in {'yes', 'no'}
    ]

    if value in normalized:
        normalized = [item for item in normalized if item != value]
    else:
        normalized.append(value)

    ordered = []
    for item in ['yes', 'no']:
        if item in normalized:
            ordered.append(item)

    return ordered


def toggle_daily_payment_filter(selected_values, value):
    normalized = [
        item
        for item in (selected_values or [])
        if item in {'yes', 'no'}
    ]

    if value in normalized:
        normalized = [item for item in normalized if item != value]
    else:
        normalized.append(value)

    ordered = []
    for item in ['yes', 'no']:
        if item in normalized:
            ordered.append(item)

    return ordered


def build_pay_queryset(request, default_mode=PAY_MODE_ALL, overrides=None):
    state = get_pay_list_state(request, default_mode=default_mode, overrides=overrides)
    context_dates = get_common_context()
    today = context_dates['today']
    week = context_dates['week']

    queryset = Pay.objects.annotate(
        cabinet_balance_for_sort=Coalesce(
            'cabinet__balance',
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

    if state['mode'] == PAY_MODE_UPCOMING:
        queryset = queryset.filter(
            paid_up_to__gte=today,
            paid_up_to__lte=week,
        )
    elif state['mode'] == PAY_MODE_OVERDUE:
        queryset = queryset.filter(
            paid_up_to__lt=today,
        )

    queryset = queryset.filter(status__in=state['selected_statuses'])

    if state['search_query']:
        q = state['search_query']
        search_filter = (
            Q(groups__icontains=q)
            | Q(service__icontains=q)
            | Q(type_source__icontains=q)
            | Q(pay_sys__icontains=q)
            | Q(status__icontains=q)
            | Q(currency__icontains=q)
            | Q(cabinet__currency__icontains=q)
            | Q(ip__icontains=q)
            | Q(note_pay__icontains=q)
        )
        try:
            search_balance = float(q)
        except (TypeError, ValueError):
            search_balance = None
        if search_balance is not None:
            search_filter |= Q(cabinet_balance_for_sort=search_balance)
        queryset = queryset.filter(search_filter)

    if state['selected_pay_sys']:
        queryset = queryset.filter(pay_sys=state['selected_pay_sys'])

    if state['selected_type_source']:
        queryset = queryset.filter(type_source=state['selected_type_source'])

    balance_filter_values = set(state['balance_gt_payment'])
    if balance_filter_values == {'yes'}:
        queryset = queryset.filter(cabinet_balance_for_sort__gte=F('price_per_month'))
    elif balance_filter_values == {'no'}:
        queryset = queryset.filter(cabinet_balance_for_sort__lt=F('price_per_month'))

    daily_payment_values = set(state['daily_payment'])
    if daily_payment_values == {'yes'}:
        queryset = queryset.filter(cabinet__is_daily_payment=True)
    elif daily_payment_values == {'no'}:
        queryset = queryset.filter(cabinet__is_daily_payment=False)

    queryset = queryset.order_by(*PAY_SORT_MAP[state['current_sort']])
    return queryset, state, context_dates


def get_pay_sidebar_context(state):
    pay_sys_options = ['BTC', 'WM', 'BTC|WM']
    type_source_options = ['VPS', 'site', 'proxy']

    return {
        'pay_current_mode': state['mode'],
        'pay_search_query': state['search_query'],
        'pay_sort': state['current_sort'],
        'selected_statuses': state['selected_statuses'],
        'selected_pay_sys': state['selected_pay_sys'],
        'selected_type_source': state['selected_type_source'],
        'balance_gt_payment': state['balance_gt_payment'],
        'daily_payment': state['daily_payment'],
        'pay_list_base_url': get_pay_base_url(state['mode']),
        'pay_reset_url': get_pay_base_url(state['mode']),
        'pay_upcoming_url': build_pay_list_url(
            mode=PAY_MODE_UPCOMING,
            statuses=state['selected_statuses'],
            q=state['search_query'],
            sort=state['current_sort'],
            pay_sys=state['selected_pay_sys'],
            type_source=state['selected_type_source'],
            balance_gt_payment=state['balance_gt_payment'],
            daily_payment=state['daily_payment'],
        ),
        'pay_overdue_url': build_pay_list_url(
            mode=PAY_MODE_OVERDUE,
            statuses=state['selected_statuses'],
            q=state['search_query'],
            sort=state['current_sort'],
            pay_sys=state['selected_pay_sys'],
            type_source=state['selected_type_source'],
            balance_gt_payment=state['balance_gt_payment'],
            daily_payment=state['daily_payment'],
        ),
        'pay_sort_groups_url': get_pay_sort_url(state, 'groups'),
        'pay_sort_create_date_url': get_pay_sort_url(state, 'create_date'),
        'pay_sort_service_url': get_pay_sort_url(state, 'service'),
        'pay_sort_type_source_url': get_pay_sort_url(state, 'type_source'),
        'pay_sort_price_per_month_url': get_pay_sort_url(state, 'price_per_month'),
        'pay_sort_currency_url': get_pay_sort_url(state, 'currency'),
        'pay_sort_pay_sys_url': get_pay_sort_url(state, 'pay_sys'),
        'pay_sort_paid_up_to_url': get_pay_sort_url(state, 'paid_up_to'),
        'pay_sort_email_login_url': get_pay_sort_url(state, 'email_login'),
        'pay_sys_links': [
            {
                'value': item,
                'url': build_pay_list_url(
                    mode=state['mode'],
                    statuses=state['selected_statuses'],
                    q=state['search_query'],
                    sort=state['current_sort'],
                    pay_sys='' if state['selected_pay_sys'] == item else item,
                    type_source=state['selected_type_source'],
                    balance_gt_payment=state['balance_gt_payment'],
                    daily_payment=state['daily_payment'],
                ),
                'selected': state['selected_pay_sys'] == item,
            }
            for item in pay_sys_options
        ],
        'type_source_links': [
            {
                'value': item,
                'url': build_pay_list_url(
                    mode=state['mode'],
                    statuses=state['selected_statuses'],
                    q=state['search_query'],
                    sort=state['current_sort'],
                    pay_sys=state['selected_pay_sys'],
                    type_source='' if state['selected_type_source'] == item else item,
                    balance_gt_payment=state['balance_gt_payment'],
                    daily_payment=state['daily_payment'],
                ),
                'selected': state['selected_type_source'] == item,
            }
            for item in type_source_options
        ],
        'pay_balance_gt_payment_yes_selected': 'yes' in state['balance_gt_payment'],
        'pay_balance_gt_payment_no_selected': 'no' in state['balance_gt_payment'],
        'pay_balance_gt_payment_yes_url': build_pay_list_url(
            mode=state['mode'],
            statuses=state['selected_statuses'],
            q=state['search_query'],
            sort=state['current_sort'],
            pay_sys=state['selected_pay_sys'],
            type_source=state['selected_type_source'],
            balance_gt_payment=toggle_balance_gt_payment_filter(
                state['balance_gt_payment'],
                'yes',
            ),
            daily_payment=state['daily_payment'],
        ),
        'pay_balance_gt_payment_no_url': build_pay_list_url(
            mode=state['mode'],
            statuses=state['selected_statuses'],
            q=state['search_query'],
            sort=state['current_sort'],
            pay_sys=state['selected_pay_sys'],
            type_source=state['selected_type_source'],
            balance_gt_payment=toggle_balance_gt_payment_filter(
                state['balance_gt_payment'],
                'no',
            ),
            daily_payment=state['daily_payment'],
        ),
        'pay_daily_payment_yes_selected': 'yes' in state['daily_payment'],
        'pay_daily_payment_no_selected': 'no' in state['daily_payment'],
        'pay_daily_payment_yes_url': build_pay_list_url(
            mode=state['mode'],
            statuses=state['selected_statuses'],
            q=state['search_query'],
            sort=state['current_sort'],
            pay_sys=state['selected_pay_sys'],
            type_source=state['selected_type_source'],
            balance_gt_payment=state['balance_gt_payment'],
            daily_payment=toggle_daily_payment_filter(
                state['daily_payment'],
                'yes',
            ),
        ),
        'pay_daily_payment_no_url': build_pay_list_url(
            mode=state['mode'],
            statuses=state['selected_statuses'],
            q=state['search_query'],
            sort=state['current_sort'],
            pay_sys=state['selected_pay_sys'],
            type_source=state['selected_type_source'],
            balance_gt_payment=state['balance_gt_payment'],
            daily_payment=toggle_daily_payment_filter(
                state['daily_payment'],
                'no',
            ),
        ),
    }


def get_default_pay_context(request, default_mode=PAY_MODE_ALL, overrides=None):
    state = get_pay_list_state(request, default_mode=default_mode, overrides=overrides)
    return get_pay_sidebar_context(state)


def render_pay_list(request, default_mode=PAY_MODE_ALL, overrides=None):
    object_l, state, context_dates = build_pay_queryset(
        request,
        default_mode=default_mode,
        overrides=overrides,
    )
    content = {'object_l': object_l}
    content.update(context_dates)
    content.update(get_pay_sidebar_context(state))
    return render(request, 'index.html', content)


def build_cabinet_page_url(
    q="",
    has_active=False,
    has_inactive=False,
    without_active=False,
    no_services=False,
    daily_payment_yes=False,
    daily_payment_no=False,
    tag_ids=None,
    sort="",
    currency="",
    balance_min="",
    balance_max="",
):
    params = {}
    if q:
        params['q'] = q
    if has_active:
        params['has_active'] = '1'
    if has_inactive:
        params['has_inactive'] = '1'
    if without_active:
        params['without_active'] = '1'
    if no_services:
        params['no_services'] = '1'
    if daily_payment_yes:
        params['daily_payment_yes'] = '1'
    if daily_payment_no:
        params['daily_payment_no'] = '1'
    if tag_ids:
        params['tag_id'] = [str(tag_id) for tag_id in tag_ids]
    if sort:
        params['sort'] = sort
    if currency:
        params['currency'] = currency
    if balance_min != "":
        params['balance_min'] = balance_min
    if balance_max != "":
        params['balance_max'] = balance_max
    base_url = reverse('app:cabinet_page')
    query_string = urlencode(params, doseq=True)
    return f"{base_url}?{query_string}" if query_string else base_url


def get_cabinet_sort_url(
    search_query,
    has_active,
    has_inactive,
    without_active,
    no_services,
    daily_payment_yes,
    daily_payment_no,
    tag_ids,
    current_sort,
    field_name,
    currency="",
    balance_min="",
    balance_max="",
):
    asc_sort = f"{field_name}_asc"
    desc_sort = f"{field_name}_desc"
    next_sort = desc_sort if current_sort == asc_sort else asc_sort
    return build_cabinet_page_url(
        q=search_query,
        has_active=has_active,
        has_inactive=has_inactive,
        without_active=without_active,
        no_services=no_services,
        daily_payment_yes=daily_payment_yes,
        daily_payment_no=daily_payment_no,
        tag_ids=tag_ids,
        sort=next_sort,
        currency=currency,
        balance_min=balance_min,
        balance_max=balance_max,
    )


def get_cabinet_sidebar_context(
    search_query="",
    has_active=False,
    has_inactive=False,
    without_active=False,
    no_services=False,
    daily_payment_yes=False,
    daily_payment_no=False,
    current_sort="",
    tag_ids=None,
    currency="",
    balance_min="",
    balance_max="",
):
    tag_ids = [int(tag_id) for tag_id in (tag_ids or [])]

    cabinet_stats = Cabinet.objects.annotate(
        services_count=Count('pay', distinct=True),
        active_services_count=Count('pay', filter=Q(pay__status='active'), distinct=True),
        inactive_services_count=Count('pay', filter=Q(pay__status='not active'), distinct=True),
        tags_count=Count('cabinet_tags__tag', distinct=True),
    )

    selected_tags = Tag.objects.filter(id__in=tag_ids).order_by('name')

    tag_options = Tag.objects.annotate(
        cabinets_count=Count('cabinet_tags__cabinet', distinct=True),
    ).order_by('name')

    currency_options = list(
        Cabinet.objects.exclude(currency__exact='')
        .values_list('currency', flat=True)
        .distinct()
        .order_by('currency')
    )

    return {
        'cabinet_search_query': search_query,
        'cabinet_has_active': has_active,
        'cabinet_has_inactive': has_inactive,
        'cabinet_without_active': without_active,
        'cabinet_no_services': no_services,
        'cabinet_daily_payment_yes': daily_payment_yes,
        'cabinet_daily_payment_no': daily_payment_no,
        'cabinet_sort': current_sort,
        'cabinet_selected_tag_ids': tag_ids,
        'cabinet_selected_tags': selected_tags,
        'cabinet_tag_options': tag_options,
        'cabinet_currency_options': currency_options,
        'cabinet_selected_currency': currency,
        'cabinet_balance_min': balance_min,
        'cabinet_balance_max': balance_max,
        'cabinet_total': cabinet_stats.count(),
        'cabinets_with_active': cabinet_stats.filter(active_services_count__gt=0).count(),
        'cabinets_with_inactive': cabinet_stats.filter(inactive_services_count__gt=0).count(),
        'cabinets_without_active': cabinet_stats.filter(active_services_count=0).count(),
        'cabinets_without_services': cabinet_stats.filter(services_count=0).count(),
        'cabinets_daily_payment_yes_count': cabinet_stats.filter(is_daily_payment=True).count(),
        'cabinets_daily_payment_no_count': cabinet_stats.filter(is_daily_payment=False).count(),
        'cabinet_reset_url': reverse('app:cabinet_page'),
        'cabinet_login_sort_url': get_cabinet_sort_url(search_query, has_active, has_inactive, without_active, no_services, daily_payment_yes, daily_payment_no, tag_ids, current_sort, 'login', currency, balance_min, balance_max),
        'cabinet_link_sort_url': get_cabinet_sort_url(search_query, has_active, has_inactive, without_active, no_services, daily_payment_yes, daily_payment_no, tag_ids, current_sort, 'link', currency, balance_min, balance_max),
        'cabinet_email_sort_url': get_cabinet_sort_url(search_query, has_active, has_inactive, without_active, no_services, daily_payment_yes, daily_payment_no, tag_ids, current_sort, 'email_login', currency, balance_min, balance_max),
        'cabinet_note_sort_url': get_cabinet_sort_url(search_query, has_active, has_inactive, without_active, no_services, daily_payment_yes, daily_payment_no, tag_ids, current_sort, 'note', currency, balance_min, balance_max),
        'cabinet_services_sort_asc_url': build_cabinet_page_url(
            q=search_query,
            has_active=has_active,
            has_inactive=has_inactive,
            without_active=without_active,
            no_services=no_services,
            daily_payment_yes=daily_payment_yes,
            daily_payment_no=daily_payment_no,
            tag_ids=tag_ids,
            sort='services_asc',
            currency=currency,
            balance_min=balance_min,
            balance_max=balance_max,
        ),
        'cabinet_services_sort_desc_url': build_cabinet_page_url(
            q=search_query,
            has_active=has_active,
            has_inactive=has_inactive,
            without_active=without_active,
            no_services=no_services,
            daily_payment_yes=daily_payment_yes,
            daily_payment_no=daily_payment_no,
            tag_ids=tag_ids,
            sort='services_desc',
            currency=currency,
            balance_min=balance_min,
            balance_max=balance_max,
        ),
        'cabinet_balance_sort_asc_url': build_cabinet_page_url(
            q=search_query,
            has_active=has_active,
            has_inactive=has_inactive,
            without_active=without_active,
            no_services=no_services,
            daily_payment_yes=daily_payment_yes,
            daily_payment_no=daily_payment_no,
            tag_ids=tag_ids,
            sort='balance_asc',
            currency=currency,
            balance_min=balance_min,
            balance_max=balance_max,
        ),
        'cabinet_balance_sort_desc_url': build_cabinet_page_url(
            q=search_query,
            has_active=has_active,
            has_inactive=has_inactive,
            without_active=without_active,
            no_services=no_services,
            daily_payment_yes=daily_payment_yes,
            daily_payment_no=daily_payment_no,
            tag_ids=tag_ids,
            sort='balance_desc',
            currency=currency,
            balance_min=balance_min,
            balance_max=balance_max,
        ),
        'cabinet_tags_sort_asc_url': build_cabinet_page_url(
            q=search_query,
            has_active=has_active,
            has_inactive=has_inactive,
            without_active=without_active,
            no_services=no_services,
            daily_payment_yes=daily_payment_yes,
            daily_payment_no=daily_payment_no,
            tag_ids=tag_ids,
            sort='tags_asc',
            currency=currency,
            balance_min=balance_min,
            balance_max=balance_max,
        ),
        'cabinet_tags_sort_desc_url': build_cabinet_page_url(
            q=search_query,
            has_active=has_active,
            has_inactive=has_inactive,
            without_active=without_active,
            no_services=no_services,
            daily_payment_yes=daily_payment_yes,
            daily_payment_no=daily_payment_no,
            tag_ids=tag_ids,
            sort='tags_desc',
            currency=currency,
            balance_min=balance_min,
            balance_max=balance_max,
        ),
    }


@require_POST
@login_required
def decrypt_item(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    model = (payload.get('model') or '').strip().lower()
    field = (payload.get('field') or '').strip()
    obj_id = payload.get('id')

    allowed = {
        'pay': {'cls': Pay, 'fields': {'password', 'email_login'}},
        'cabinet': {'cls': Cabinet, 'fields': {'password', 'email_password', 'email_login'}},
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

    user_psw = User.objects.get(username='admin').password
    decrypted_value = cryptocode.decrypt(encrypted_value, user_psw)
    if decrypted_value is False or decrypted_value is None or decrypted_value == '':
        return JsonResponse({'error': 'Decryption failed'}, status=400)

    return JsonResponse({'value': decrypted_value})


@login_required
def pay_new(request):
    context_dates = get_common_context()
    group_options = list(
        Pay.objects.exclude(groups__isnull=True)
        .exclude(groups__exact='')
        .order_by('groups')
        .values_list('groups', flat=True)
        .distinct()
    )

    if request.method == 'POST':
        form_pay = PayForm(request.POST)
        if form_pay.is_valid():
            post = form_pay.save(commit=False)
            post.save()
            return redirect('app:pay_new')
    else:
        if Cabinet.objects.all().count() > 0:
            lst_id = Cabinet.objects.all().last().id
            form_pay = PayForm(initial={
                    'cabinet': lst_id,
                    'create_date': context_dates['today'],
                    'paid_up_to': add_one_month(context_dates['today']),
                })
        else:
            form_pay = PayForm(initial={
                'create_date': context_dates['today'],
                'paid_up_to': add_one_month(context_dates['today']),
            })

    content = {'form_pay': form_pay, 'group_options': group_options}
    content.update(context_dates)
    content.update(get_default_pay_context(request))
    return render(request, 'add_pay.html', content)


@login_required
def cabinet_new(request):
    context_dates = get_common_context()
    if request.method == 'POST':
        submit_action = request.POST.get('submit_action')

        if submit_action == 'create_tag':
            form_pay = PayForm()
            tag_form = TagForm(request.POST, prefix='new_tag')

            selected_tag_ids = []
            for raw_tag_id in request.POST.getlist('selected_tags'):
                try:
                    selected_tag_ids.append(int(raw_tag_id))
                except (TypeError, ValueError):
                    continue

            cabinet_form_data = {}
            for key, value in request.POST.items():
                if key.startswith('cabinet_'):
                    cabinet_form_data[key.replace('cabinet_', '', 1)] = value

            form_cabinet = CabinetForm(cabinet_form_data or None)

            if tag_form.is_valid():
                new_tag = tag_form.save()
                selected_tag_ids = sorted(set(selected_tag_ids + [new_tag.id]))
                tag_assign_form = CabinetTagAssignForm(initial={'tags': selected_tag_ids})
                tag_form = TagForm(prefix='new_tag')
            else:
                tag_assign_form = CabinetTagAssignForm(initial={'tags': selected_tag_ids})

        else:
            form_pay = PayForm()
            form_cabinet = CabinetForm(request.POST)
            tag_assign_form = CabinetTagAssignForm(request.POST)
            tag_form = TagForm(prefix='new_tag')

            if form_cabinet.is_valid() and tag_assign_form.is_valid():
                post = form_cabinet.save(commit=False)
                post.save()

                CabinetTag.objects.bulk_create([
                    CabinetTag(cabinet=post, tag=tag)
                    for tag in tag_assign_form.cleaned_data['tags']
                ])
                return redirect('app:pay_new')
    else:
        form_pay = PayForm()
        form_cabinet = CabinetForm()
        tag_assign_form = CabinetTagAssignForm()
        tag_form = TagForm(prefix='new_tag')

    content = {
        'form_cabinet': form_cabinet,
        'form_pay': form_pay,
        'tag_assign_form': tag_assign_form,
        'tag_form': tag_form,
    }
    content.update(context_dates)
    content.update(get_default_pay_context(request))
    return render(request, 'add_pay.html', content)


@login_required
def cabinet_edit(request, id):
    post = get_object_or_404(Cabinet, pk=id)
    user_psw = User.objects.get(username='admin').password
    post.password = cryptocode.decrypt(post.password, user_psw)
    post.email_password = cryptocode.decrypt(post.email_password, user_psw)

    selected_tag_ids = list(
        CabinetTag.objects.filter(cabinet=post).values_list('tag_id', flat=True)
    )

    if request.method == 'POST':
        form_cabinet_edit = CabinetForm(request.POST, instance=post)
        tag_assign_form = CabinetTagAssignForm(request.POST)
        tag_form = TagForm(request.POST, prefix='new_tag')

        submit_action = request.POST.get('submit_action')

        if submit_action == 'save_tags':
            tag_form = TagForm(prefix='new_tag')
            if form_cabinet_edit.is_valid() and tag_assign_form.is_valid():
                post = form_cabinet_edit.save(commit=False)
                post.save()

                CabinetTag.objects.filter(cabinet=post).delete()
                CabinetTag.objects.bulk_create([
                    CabinetTag(cabinet=post, tag=tag)
                    for tag in tag_assign_form.cleaned_data['tags']
                ])
                return redirect('app:cabinet_page')

        elif submit_action == 'create_tag':
            if tag_form.is_valid():
                new_tag = tag_form.save()
                merged_ids = set(
                    CabinetTag.objects.filter(cabinet=post).values_list('tag_id', flat=True)
                )
                merged_ids.add(new_tag.id)
                form_cabinet_edit = CabinetForm(request.POST, instance=post)
                tag_assign_form = CabinetTagAssignForm(initial={'tags': list(merged_ids)})
            else:
                form_cabinet_edit = CabinetForm(request.POST, instance=post)
                tag_assign_form = CabinetTagAssignForm(initial={'tags': selected_tag_ids})
        else:
            tag_form = TagForm(prefix='new_tag')
            if form_cabinet_edit.is_valid() and tag_assign_form.is_valid():
                post = form_cabinet_edit.save(commit=False)
                post.save()

                CabinetTag.objects.filter(cabinet=post).delete()
                CabinetTag.objects.bulk_create([
                    CabinetTag(cabinet=post, tag=tag)
                    for tag in tag_assign_form.cleaned_data['tags']
                ])
                return redirect('app:cabinet_page')
    else:
        form_cabinet_edit = CabinetForm(instance=post)
        tag_assign_form = CabinetTagAssignForm(initial={'tags': selected_tag_ids})
        tag_form = TagForm(prefix='new_tag')

    content = {
        'form_cabinet_edit': form_cabinet_edit,
        'tag_assign_form': tag_assign_form,
        'tag_form': tag_form,
    }
    content.update(get_cabinet_sidebar_context())
    content.update(get_common_context())
    return render(request, 'cabinet.html', content)


@login_required
def statistics_page(request):
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

    burn_by_currency_raw = active_queryset.values('currency').annotate(
        monthly_burn=Coalesce(Sum('price_per_month'), 0.0)
    ).order_by('currency')
    burn_by_currency = []
    for row in burn_by_currency_raw:
        monthly_burn = Decimal(str(row['monthly_burn'] or 0))
        burn_by_currency.append({
            'currency': row['currency'] or 'N/A',
            'monthly_burn': monthly_burn,
            'annualized': monthly_burn * Decimal('12'),
        })

    expired_count = active_queryset.filter(paid_up_to__lt=today).count()
    expiring_7_count = active_queryset.filter(paid_up_to__gte=today, paid_up_to__lte=today + datetime.timedelta(days=7)).count()
    expiring_30_count = active_queryset.filter(paid_up_to__gte=today, paid_up_to__lte=today + datetime.timedelta(days=30)).count()
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
        active_queryset.values('currency', 'groups').annotate(
            total=Coalesce(Sum('price_per_month'), 0.0)
        ).order_by('currency', '-total', 'groups')
    )
    top_cabinets = list(
        active_queryset.values('currency', 'cabinet_id', 'cabinet__login').annotate(
            total=Coalesce(Sum('price_per_month'), 0.0)
        ).order_by('currency', '-total', 'cabinet__login')[:8]
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
        ).values('currency').annotate(
            total=Coalesce(Sum('price_per_month'), 0.0)
        ).order_by('currency')
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
    base_querystring = _build_statistics_query_params(query_state)

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
        'base_querystring': base_querystring,
    }
    content.update(get_common_context())
    return render(request, 'statistics.html', content)

@login_required
def pay_edit(request, id):
    post = get_object_or_404(Pay, pk=id)
    id_pay = Cabinet.objects.get(pay__id=id).id
    post_cabinet = get_object_or_404(Cabinet, pk=id_pay)

    user_psw = User.objects.get(username='admin').password
    post.password = cryptocode.decrypt(post.password, user_psw)
    post.email_login = cryptocode.decrypt(post.email_login, user_psw)
    post_cabinet.password = cryptocode.decrypt(post_cabinet.password, user_psw)
    post_cabinet.email_password = cryptocode.decrypt(post_cabinet.email_password, user_psw)

    if request.method == 'POST':
        form_edit_pay = PayForm(request.POST, instance=post)
        form_edit_cabinet = CabinetForm(request.POST, instance=post_cabinet)

        if form_edit_pay.is_valid():
            post = form_edit_pay.save(commit=False)
            post.save()
            return redirect('app:home_page_with_cabinet', id=id)

        if form_edit_cabinet.is_valid():
            post_cabinet = form_edit_cabinet.save(commit=False)
            post_cabinet.save()
            return redirect('app:home_page_with_cabinet', id=id)
    else:
        form_edit_pay = PayForm(instance=post)
        form_edit_cabinet = CabinetForm(instance=post_cabinet)

    content = {'form_edit_pay': form_edit_pay, 'form_edit_cabinet': form_edit_cabinet}
    content.update(get_common_context())
    content.update(get_default_pay_context(request))
    return render(request, 'index.html', content)


@login_required
def home_page(request):
    return render_pay_list(request, default_mode=PAY_MODE_ALL)


@login_required
def home_page_with_cabinet(request, id):
    object_l = Pay.objects.filter(id=id)
    cabinet_obj = Pay.objects.filter(id=id)
    content = {'object_l': object_l, 'cabinet_obj': cabinet_obj}
    content.update(get_common_context())
    content.update(get_default_pay_context(request))
    return render(request, 'index.html', content)


@login_required
def cabinet_page(request):
    search_query = (request.GET.get('q') or '').strip()
    has_active = request.GET.get('has_active') == '1'
    has_inactive = request.GET.get('has_inactive') == '1'
    without_active = request.GET.get('without_active') == '1'
    no_services = request.GET.get('no_services') == '1'
    daily_payment_yes = request.GET.get('daily_payment_yes') == '1'
    daily_payment_no = request.GET.get('daily_payment_no') == '1'
    current_sort = (request.GET.get('sort') or '').strip()
    selected_currency = (request.GET.get('currency') or '').strip()
    balance_min_raw = (request.GET.get('balance_min') or '').strip()
    balance_max_raw = (request.GET.get('balance_max') or '').strip()
    tag_ids_raw = request.GET.getlist('tag_id')
    highlight_id = request.GET.get('highlight')

    try:
        highlight_id = int(highlight_id) if highlight_id else None
    except ValueError:
        highlight_id = None

    tag_ids = []
    for raw_tag_id in tag_ids_raw:
        try:
            tag_ids.append(int(raw_tag_id))
        except (TypeError, ValueError):
            continue

    object_k = Cabinet.objects.all()
    object_k = object_k.annotate(
        balance_value=Coalesce(
            'balance',
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

    if search_query:
        service_match_ids = Pay.objects.filter(service__icontains=search_query).values_list('cabinet_id', flat=True)
        tag_match_ids = CabinetTag.objects.filter(tag__name__icontains=search_query).values_list('cabinet_id', flat=True)
        object_k = object_k.filter(
            Q(login__icontains=search_query)
            | Q(link__icontains=search_query)
            | Q(email_login__icontains=search_query)
            | Q(note__icontains=search_query)
            | Q(id__in=service_match_ids)
            | Q(id__in=tag_match_ids)
        ).distinct()

    object_k = object_k.annotate(
        services_count=Count('pay', distinct=True),
        active_services_count=Count('pay', filter=Q(pay__status='active'), distinct=True),
        inactive_services_count=Count('pay', filter=Q(pay__status='not active'), distinct=True),
        tags_count=Count('cabinet_tags__tag', distinct=True),
    ).prefetch_related('pay_set', 'cabinet_tags__tag')

    selected_filter = Q()
    has_any_filter = False

    if has_active:
        selected_filter |= Q(active_services_count__gt=0)
        has_any_filter = True
    if has_inactive:
        selected_filter |= Q(inactive_services_count__gt=0)
        has_any_filter = True
    if without_active:
        selected_filter |= Q(active_services_count=0)
        has_any_filter = True
    if no_services:
        selected_filter |= Q(services_count=0)
        has_any_filter = True
    if daily_payment_yes:
        selected_filter |= Q(is_daily_payment=True)
        has_any_filter = True
    if daily_payment_no:
        selected_filter |= Q(is_daily_payment=False)
        has_any_filter = True

    if has_any_filter:
        object_k = object_k.filter(selected_filter)

    if tag_ids:
        object_k = object_k.annotate(
            matched_tag_count=Count(
                'cabinet_tags__tag',
                filter=Q(cabinet_tags__tag_id__in=tag_ids),
                distinct=True,
            )
        ).filter(matched_tag_count=len(tag_ids))

    if selected_currency:
        object_k = object_k.filter(currency=selected_currency)

    try:
        balance_min = float(balance_min_raw) if balance_min_raw != '' else None
    except (TypeError, ValueError):
        balance_min = None
    try:
        balance_max = float(balance_max_raw) if balance_max_raw != '' else None
    except (TypeError, ValueError):
        balance_max = None

    if balance_min is not None:
        object_k = object_k.filter(balance_value__gte=balance_min)
    if balance_max is not None:
        object_k = object_k.filter(balance_value__lte=balance_max)

    sort_map = {
        'login_asc': ('login', 'id'),
        'login_desc': ('-login', 'id'),
        'link_asc': ('link', 'id'),
        'link_desc': ('-link', 'id'),
        'email_login_asc': ('email_login', 'id'),
        'email_login_desc': ('-email_login', 'id'),
        'note_asc': ('note', 'id'),
        'note_desc': ('-note', 'id'),
        'services_asc': ('services_count', 'id'),
        'services_desc': ('-services_count', 'id'),
        'balance_asc': ('balance_value', 'id'),
        'balance_desc': ('-balance_value', 'id'),
        'currency_asc': ('currency', 'id'),
        'currency_desc': ('-currency', 'id'),
        'tags_asc': ('tags_count', 'login', 'id'),
        'tags_desc': ('-tags_count', 'login', 'id'),
    }
    object_k = object_k.order_by(*sort_map.get(current_sort, ('id',))).distinct()

    content = {'object_k': object_k, 'highlight_id': highlight_id}
    content.update(get_cabinet_sidebar_context(
        search_query=search_query,
        has_active=has_active,
        has_inactive=has_inactive,
        without_active=without_active,
        no_services=no_services,
        daily_payment_yes=daily_payment_yes,
        daily_payment_no=daily_payment_no,
        current_sort=current_sort,
        tag_ids=tag_ids,
        currency=selected_currency,
        balance_min=balance_min_raw,
        balance_max=balance_max_raw,
    ))
    content.update(get_common_context())
    return render(request, 'cabinet.html', content)


@login_required
def sort_by_name(request, name):
    legacy_sort = f'{name}_asc'
    if legacy_sort not in PAY_SORT_MAP:
        legacy_sort = PAY_SORT_DEFAULT
    default_mode = request.GET.get('mode') or PAY_MODE_ALL
    return render_pay_list(request, default_mode=default_mode, overrides={'sort': legacy_sort})


@login_required
def sort_by_name_cabinet(request, name):
    sort_cabinet = Cabinet.objects.annotate(
        services_count=Count('pay', distinct=True),
        active_services_count=Count('pay', filter=Q(pay__status='active'), distinct=True),
        inactive_services_count=Count('pay', filter=Q(pay__status='not active'), distinct=True),
        tags_count=Count('cabinet_tags__tag', distinct=True),
    ).prefetch_related('pay_set', 'cabinet_tags__tag').order_by(name)

    content = {'object_k': sort_cabinet}
    content.update(get_cabinet_sidebar_context())
    content.update(get_common_context())
    return render(request, 'cabinet.html', content)


@login_required
def filter_by_date(request, name):
    return render_pay_list(request, default_mode=PAY_MODE_UPCOMING)


@login_required
def overdue_payments(request, name):
    return render_pay_list(request, default_mode=PAY_MODE_OVERDUE)


@login_required
def filter_by_pay_sys(request, name):
    default_mode = request.GET.get('mode') or PAY_MODE_ALL
    return render_pay_list(request, default_mode=default_mode, overrides={'pay_sys': name})


@login_required
def filter_by_type_source(request, name):
    default_mode = request.GET.get('mode') or PAY_MODE_ALL
    return render_pay_list(request, default_mode=default_mode, overrides={'type_source': name})


@login_required
def filter_by_active(request, name):
    default_mode = request.GET.get('mode') or PAY_MODE_ALL
    return render_pay_list(request, default_mode=default_mode, overrides={'status': [name]})


@login_required
def searching(request, name):
    q = (request.GET.get('g') or request.GET.get('q') or '').strip()
    default_mode = request.GET.get('mode') or PAY_MODE_ALL
    return render_pay_list(request, default_mode=default_mode, overrides={'q': q})


@login_required
def edit_dt(request, id):
    try:
        item = Pay.objects.get(id=id)
        user_psw = User.objects.get(username='admin')
        item.password = cryptocode.decrypt(item.password, user_psw.password)
        item.email_login = cryptocode.decrypt(item.email_login, user_psw.password)
        if request.method == 'POST':
            item.paid_up_to = request.POST.get('paid_up_to')
            item.save()
            return redirect('app:index')
        content = {'object_l': item}
        content.update(get_common_context())
        content.update(get_default_pay_context(request))
        return render(request, 'edit_dt.html', content)
    except Pay.DoesNotExist:
        return HttpResponseNotFound('<h2> not found</h2>')


@login_required
def edit_page(request):
    object_l = Pay.objects.all().order_by('id')
    cabinet = Cabinet.objects.all()
    content = {'object_l': object_l, 'cabinet': cabinet}
    content.update(get_common_context())
    return render(request, 'edit_page.html', content)


@login_required
def edit_table(request, id):
    try:
        item = Pay.objects.get(id=id)
        user_psw = User.objects.get(username='admin')
        item.password = cryptocode.decrypt(item.password, user_psw.password)
        item.email_login = cryptocode.decrypt(item.email_login, user_psw.password)
        if request.method == 'POST':
            item.groups = request.POST.get('groups')
            item.service = request.POST.get('service')
            item.create_date = request.POST.get('create_date')
            item.type_source = request.POST.get('type_source')
            item.price_per_month = request.POST.get('price_per_month')
            item.currency = request.POST.get('currency')
            item.pay_sys = request.POST.get('pay_sys')
            item.paid_up_to = request.POST.get('paid_up_to')
            item.status = request.POST.get('status')
            item.email_login = request.POST.get('email_login')
            item.password = request.POST.get('password')
            item.ip = request.POST.get('ip')
            item.save()
            return redirect('app:edit_page')
        return render(request, 'edit_table.html', {'object_l': item})
    except Pay.DoesNotExist:
        return HttpResponseNotFound('<h2> not found</h2>')


@login_required
def delete(request, id):
    try:
        item = Pay.objects.get(id=id)
        item.delete()
        return redirect('app:edit_page')
    except Pay.DoesNotExist:
        return HttpResponseNotFound('<h2>Pay not found</h2>')


@login_required
def tags_page(request):
    tags = Tag.objects.annotate(
        cabinets_count=Count('cabinet_tags__cabinet', distinct=True),
    ).order_by('name')

    content = {'tags': tags}
    content.update(get_common_context())
    content.update(get_default_pay_context(request))
    return render(request, 'tags/tag_list.html', content)


@login_required
def tag_create(request):
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('app:tags_page')
    else:
        form = TagForm()

    content = {'form': form}
    content.update(get_common_context())
    content.update(get_default_pay_context(request))
    return render(request, 'tags/tag_form.html', content)


@login_required
def tag_edit(request, id):
    tag = get_object_or_404(Tag, pk=id)

    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            return redirect('app:tags_page')
    else:
        form = TagForm(instance=tag)

    content = {'form': form, 'tag': tag}
    content.update(get_common_context())
    content.update(get_default_pay_context(request))
    return render(request, 'tags/tag_form.html', content)


@login_required
def tag_delete(request, id):
    tag = get_object_or_404(Tag, pk=id)

    if request.method == 'POST':
        tag.delete()
        return redirect('app:tags_page')

    content = {'tag': tag}
    content.update(get_common_context())
    content.update(get_default_pay_context(request))
    return render(request, 'tags/tag_confirm_delete.html', content)


@login_required
def delete_cabinet(request, id):
    try:
        item = get_object_or_404(Cabinet, id=id)
        item.delete()
        return redirect('app:cabinet_page')
    except IntegrityError:
        return HttpResponseNotFound('<h2>Дане поле неможливо видалити!! Поле зв\\\'язане із елементом у іншій таблиці</h2>')
    except Cabinet.DoesNotExist:
        return HttpResponseNotFound('<h2>Pay not found</h2>')
