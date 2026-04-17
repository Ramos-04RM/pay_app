from urllib.parse import urlencode

from django.db.models import DecimalField, F, Q, Value
from django.db.models.functions import Coalesce
from django.urls import reverse

from ..models import Cabinet, Pay
from .common import add_one_month, get_common_context
from .constants import (
    PAY_MODE_ALL,
    PAY_MODE_OVERDUE,
    PAY_MODE_UPCOMING,
    PAY_MODES,
    PAY_SORT_DEFAULT,
    PAY_SORT_MAP,
)


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

    normalized_balance_gt_payment = [
        item for item in (balance_gt_payment or []) if item in {'yes', 'no'}
    ]
    if normalized_balance_gt_payment:
        params['balance_gt_payment'] = normalized_balance_gt_payment

    normalized_daily_payment = [
        item for item in (daily_payment or []) if item in {'yes', 'no'}
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

    current_sort = (query_data.get('sort') or PAY_SORT_DEFAULT).strip()
    if current_sort not in PAY_SORT_MAP:
        current_sort = PAY_SORT_DEFAULT

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
        'search_query': (query_data.get('q') or '').strip(),
        'current_sort': current_sort,
        'selected_pay_sys': (query_data.get('pay_sys') or '').strip(),
        'selected_type_source': (query_data.get('type_source') or '').strip(),
        'balance_gt_payment': balance_gt_payment,
        'daily_payment': daily_payment,
    }


def toggle_binary_filter(selected_values, value):
    normalized = [item for item in (selected_values or []) if item in {'yes', 'no'}]
    if value in normalized:
        normalized = [item for item in normalized if item != value]
    else:
        normalized.append(value)
    return [item for item in ['yes', 'no'] if item in normalized]


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
        queryset = queryset.filter(paid_up_to__gte=today, paid_up_to__lte=week)
    elif state['mode'] == PAY_MODE_OVERDUE:
        queryset = queryset.filter(paid_up_to__lt=today)

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
            balance_gt_payment=toggle_binary_filter(state['balance_gt_payment'], 'yes'),
            daily_payment=state['daily_payment'],
        ),
        'pay_balance_gt_payment_no_url': build_pay_list_url(
            mode=state['mode'],
            statuses=state['selected_statuses'],
            q=state['search_query'],
            sort=state['current_sort'],
            pay_sys=state['selected_pay_sys'],
            type_source=state['selected_type_source'],
            balance_gt_payment=toggle_binary_filter(state['balance_gt_payment'], 'no'),
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
            daily_payment=toggle_binary_filter(state['daily_payment'], 'yes'),
        ),
        'pay_daily_payment_no_url': build_pay_list_url(
            mode=state['mode'],
            statuses=state['selected_statuses'],
            q=state['search_query'],
            sort=state['current_sort'],
            pay_sys=state['selected_pay_sys'],
            type_source=state['selected_type_source'],
            balance_gt_payment=state['balance_gt_payment'],
            daily_payment=toggle_binary_filter(state['daily_payment'], 'no'),
        ),
    }


def get_default_pay_context(request, default_mode=PAY_MODE_ALL, overrides=None):
    state = get_pay_list_state(request, default_mode=default_mode, overrides=overrides)
    return get_pay_sidebar_context(state)


def build_pay_list_context(request, default_mode=PAY_MODE_ALL, overrides=None):
    object_l, state, context_dates = build_pay_queryset(
        request,
        default_mode=default_mode,
        overrides=overrides,
    )
    content = {'object_l': object_l}
    content.update(context_dates)
    content.update(get_pay_sidebar_context(state))
    return content


def get_pay_group_options():
    return list(
        Pay.objects.exclude(groups__isnull=True)
        .exclude(groups__exact='')
        .order_by('groups')
        .values_list('groups', flat=True)
        .distinct()
    )


def get_pay_create_initial():
    context_dates = get_common_context()
    initial = {
        'create_date': context_dates['today'],
        'paid_up_to': add_one_month(context_dates['today']),
    }
    last_cabinet = Cabinet.objects.order_by('id').last()
    if last_cabinet:
        initial['cabinet'] = last_cabinet.id
    return initial
