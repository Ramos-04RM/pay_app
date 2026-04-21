from urllib.parse import urlencode
from collections.abc import Iterable, Mapping
from typing import Any

from django.db.models import Count, DecimalField, Q, Value
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from django.urls import reverse

from ..models import Cabinet, CabinetTag, Pay, Tag
from .common import get_common_context
from .constants import CABINET_SORT_MAP


def build_cabinet_page_url(
    q: str = '',
    has_active: bool = False,
    has_inactive: bool = False,
    without_active: bool = False,
    no_services: bool = False,
    daily_payment_yes: bool = False,
    daily_payment_no: bool = False,
    tag_ids: list[int] | None = None,
    sort: str = '',
    currency: str = '',
    balance_min: str = '',
    balance_max: str = '',
) -> str:
    """Build a cabinet list URL with active filter/sort query parameters."""
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
    *,
    q: str = '',
    has_active: bool = False,
    has_inactive: bool = False,
    without_active: bool = False,
    no_services: bool = False,
    daily_payment_yes: bool = False,
    daily_payment_no: bool = False,
    tag_ids: list[int] | None = None,
    current_sort: str = '',
    field_name: str,
    currency: str = '',
    balance_min: str = '',
    balance_max: str = '',
) -> str:
    """Return a cabinet list URL that toggles the requested sort field direction."""
    asc_sort = f'{field_name}_asc'
    desc_sort = f'{field_name}_desc'
    next_sort = desc_sort if current_sort == asc_sort else asc_sort
    return build_cabinet_page_url(
        q=q,
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
    search_query: str = '',
    has_active: bool = False,
    has_inactive: bool = False,
    without_active: bool = False,
    no_services: bool = False,
    daily_payment_yes: bool = False,
    daily_payment_no: bool = False,
    current_sort: str = '',
    tag_ids: list[int] | None = None,
    currency: str = '',
    balance_min: str = '',
    balance_max: str = '',
) -> dict[str, Any]:
    """Assemble sidebar counters, selected filters, and navigation links for cabinet page."""
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

    _url_base = dict(
        q=search_query,
        has_active=has_active,
        has_inactive=has_inactive,
        without_active=without_active,
        no_services=no_services,
        daily_payment_yes=daily_payment_yes,
        daily_payment_no=daily_payment_no,
        tag_ids=tag_ids,
        currency=currency,
        balance_min=balance_min,
        balance_max=balance_max,
    )

    def _sort_url(field: str) -> str:
        return get_cabinet_sort_url(
            **_url_base,
            current_sort=current_sort,
            field_name=field,
        )

    def _page_url(sort: str) -> str:
        return build_cabinet_page_url(**_url_base, sort=sort)

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
        'cabinet_login_sort_url': _sort_url('login'),
        'cabinet_link_sort_url': _sort_url('link'),
        'cabinet_email_sort_url': _sort_url('email_login'),
        'cabinet_note_sort_url': _sort_url('note'),
        'cabinet_services_sort_asc_url': _page_url('services_asc'),
        'cabinet_services_sort_desc_url': _page_url('services_desc'),
        'cabinet_balance_sort_asc_url': _page_url('balance_asc'),
        'cabinet_balance_sort_desc_url': _page_url('balance_desc'),
        'cabinet_tags_sort_asc_url': _page_url('tags_asc'),
        'cabinet_tags_sort_desc_url': _page_url('tags_desc'),
    }


def parse_tag_ids(raw_tag_ids: Iterable[object]) -> list[int]:
    """Parse raw tag IDs into integers, skipping invalid values."""
    tag_ids = []
    for raw_tag_id in raw_tag_ids:
        try:
            tag_ids.append(int(raw_tag_id))
        except (TypeError, ValueError):
            continue
    return tag_ids


def get_selected_cabinet_tag_ids(cabinet: Cabinet) -> list[int]:
    """Return IDs of tags currently attached to the given cabinet."""
    return list(CabinetTag.objects.filter(cabinet=cabinet).values_list('tag_id', flat=True))


def replace_cabinet_tags(cabinet: Cabinet, tags: Iterable[Tag]) -> None:
    """Replace cabinet-tag relations with the provided tag collection."""
    CabinetTag.objects.filter(cabinet=cabinet).delete()
    CabinetTag.objects.bulk_create([
        CabinetTag(cabinet=cabinet, tag=tag)
        for tag in tags
    ])


def extract_prefixed_cabinet_form_data(
    post_data: Mapping[str, object],
    prefix: str = 'cabinet_',
) -> dict[str, object]:
    """Extract fields prefixed for cabinet form reconstruction from mixed POST payload."""
    cabinet_form_data: dict[str, object] = {}
    for key, value in post_data.items():
        if key.startswith(prefix):
            cabinet_form_data[key.replace(prefix, '', 1)] = value
    return cabinet_form_data


def get_cabinet_create_context() -> dict[str, object]:
    """Return base context for cabinet creation pages."""
    return get_common_context()


def build_cabinet_page_context(request: HttpRequest) -> dict[str, Any]:
    """Build full cabinet list context from query filters, counters, and sorting state."""
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
