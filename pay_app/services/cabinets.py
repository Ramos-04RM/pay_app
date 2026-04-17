from urllib.parse import urlencode

from django.db.models import Count, DecimalField, Q, Value
from django.db.models.functions import Coalesce
from django.urls import reverse

from ..models import Cabinet, CabinetTag, Pay, Tag
from .common import get_common_context
from .constants import CABINET_SORT_MAP


def build_cabinet_page_url(
    q='',
    has_active=False,
    has_inactive=False,
    without_active=False,
    no_services=False,
    daily_payment_yes=False,
    daily_payment_no=False,
    tag_ids=None,
    sort='',
    currency='',
    balance_min='',
    balance_max='',
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
    if balance_min != '':
        params['balance_min'] = balance_min
    if balance_max != '':
        params['balance_max'] = balance_max
    base_url = reverse('app:cabinet_page')
    query_string = urlencode(params, doseq=True)
    return f'{base_url}?{query_string}' if query_string else base_url


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
    currency='',
    balance_min='',
    balance_max='',
):
    asc_sort = f'{field_name}_asc'
    desc_sort = f'{field_name}_desc'
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
    search_query='',
    has_active=False,
    has_inactive=False,
    without_active=False,
    no_services=False,
    daily_payment_yes=False,
    daily_payment_no=False,
    current_sort='',
    tag_ids=None,
    currency='',
    balance_min='',
    balance_max='',
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
        'cabinet_services_sort_asc_url': build_cabinet_page_url(q=search_query, has_active=has_active, has_inactive=has_inactive, without_active=without_active, no_services=no_services, daily_payment_yes=daily_payment_yes, daily_payment_no=daily_payment_no, tag_ids=tag_ids, sort='services_asc', currency=currency, balance_min=balance_min, balance_max=balance_max),
        'cabinet_services_sort_desc_url': build_cabinet_page_url(q=search_query, has_active=has_active, has_inactive=has_inactive, without_active=without_active, no_services=no_services, daily_payment_yes=daily_payment_yes, daily_payment_no=daily_payment_no, tag_ids=tag_ids, sort='services_desc', currency=currency, balance_min=balance_min, balance_max=balance_max),
        'cabinet_balance_sort_asc_url': build_cabinet_page_url(q=search_query, has_active=has_active, has_inactive=has_inactive, without_active=without_active, no_services=no_services, daily_payment_yes=daily_payment_yes, daily_payment_no=daily_payment_no, tag_ids=tag_ids, sort='balance_asc', currency=currency, balance_min=balance_min, balance_max=balance_max),
        'cabinet_balance_sort_desc_url': build_cabinet_page_url(q=search_query, has_active=has_active, has_inactive=has_inactive, without_active=without_active, no_services=no_services, daily_payment_yes=daily_payment_yes, daily_payment_no=daily_payment_no, tag_ids=tag_ids, sort='balance_desc', currency=currency, balance_min=balance_min, balance_max=balance_max),
        'cabinet_tags_sort_asc_url': build_cabinet_page_url(q=search_query, has_active=has_active, has_inactive=has_inactive, without_active=without_active, no_services=no_services, daily_payment_yes=daily_payment_yes, daily_payment_no=daily_payment_no, tag_ids=tag_ids, sort='tags_asc', currency=currency, balance_min=balance_min, balance_max=balance_max),
        'cabinet_tags_sort_desc_url': build_cabinet_page_url(q=search_query, has_active=has_active, has_inactive=has_inactive, without_active=without_active, no_services=no_services, daily_payment_yes=daily_payment_yes, daily_payment_no=daily_payment_no, tag_ids=tag_ids, sort='tags_desc', currency=currency, balance_min=balance_min, balance_max=balance_max),
    }


def parse_tag_ids(raw_tag_ids):
    tag_ids = []
    for raw_tag_id in raw_tag_ids:
        try:
            tag_ids.append(int(raw_tag_id))
        except (TypeError, ValueError):
            continue
    return tag_ids


def get_selected_cabinet_tag_ids(cabinet):
    return list(CabinetTag.objects.filter(cabinet=cabinet).values_list('tag_id', flat=True))


def replace_cabinet_tags(cabinet, tags):
    CabinetTag.objects.filter(cabinet=cabinet).delete()
    CabinetTag.objects.bulk_create([
        CabinetTag(cabinet=cabinet, tag=tag)
        for tag in tags
    ])


def extract_prefixed_cabinet_form_data(post_data, prefix='cabinet_'):
    cabinet_form_data = {}
    for key, value in post_data.items():
        if key.startswith(prefix):
            cabinet_form_data[key.replace(prefix, '', 1)] = value
    return cabinet_form_data


def get_cabinet_create_context():
    return get_common_context()


def build_cabinet_page_context(request):
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
    tag_ids = parse_tag_ids(request.GET.getlist('tag_id'))
    highlight_id = request.GET.get('highlight')

    try:
        highlight_id = int(highlight_id) if highlight_id else None
    except ValueError:
        highlight_id = None

    queryset = Cabinet.objects.annotate(
        balance_value=Coalesce(
            'balance',
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

    if search_query:
        service_match_ids = Pay.objects.filter(service__icontains=search_query).values_list('cabinet_id', flat=True)
        tag_match_ids = CabinetTag.objects.filter(tag__name__icontains=search_query).values_list('cabinet_id', flat=True)
        queryset = queryset.filter(
            Q(login__icontains=search_query)
            | Q(link__icontains=search_query)
            | Q(email_login__icontains=search_query)
            | Q(note__icontains=search_query)
            | Q(id__in=service_match_ids)
            | Q(id__in=tag_match_ids)
        ).distinct()

    queryset = queryset.annotate(
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
        queryset = queryset.filter(selected_filter)

    if tag_ids:
        queryset = queryset.annotate(
            matched_tag_count=Count(
                'cabinet_tags__tag',
                filter=Q(cabinet_tags__tag_id__in=tag_ids),
                distinct=True,
            )
        ).filter(matched_tag_count=len(tag_ids))

    if selected_currency:
        queryset = queryset.filter(currency=selected_currency)

    try:
        balance_min = float(balance_min_raw) if balance_min_raw != '' else None
    except (TypeError, ValueError):
        balance_min = None
    try:
        balance_max = float(balance_max_raw) if balance_max_raw != '' else None
    except (TypeError, ValueError):
        balance_max = None

    if balance_min is not None:
        queryset = queryset.filter(balance_value__gte=balance_min)
    if balance_max is not None:
        queryset = queryset.filter(balance_value__lte=balance_max)

    queryset = queryset.order_by(*CABINET_SORT_MAP.get(current_sort, ('id',))).distinct()

    content = {'object_k': queryset, 'highlight_id': highlight_id}
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
    return content
