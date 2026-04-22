from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CabinetForm, CabinetTagAssignForm, PayForm, TagForm
from .logging_helpers import log_event
from .models import Cabinet, Pay, Tag
from . import services


# ── Helpers ───────────────────────────────────────────────────────────────────

def _base_ctx(request: HttpRequest) -> dict:
    """Merge common + default-pay context into one dict."""
    ctx = services.get_common_context()
    ctx.update(services.get_default_pay_context(request))
    return ctx


def _append_query_param(url: str, key: str, value: str) -> str:
    """Append or replace a query parameter on a relative or same-host URL."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[key] = value
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _get_safe_next_url(request: HttpRequest, default_url: str) -> str:
    """Return a safe redirect target from next/referer or fallback."""
    for candidate in (request.POST.get('next'), request.GET.get('next'), request.META.get('HTTP_REFERER')):
        if candidate and url_has_allowed_host_and_scheme(
            url=candidate,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return candidate
    return default_url


# ── Auth / Decrypt ────────────────────────────────────────────────────────────

@require_POST
@login_required
def decrypt_item(request: HttpRequest) -> JsonResponse:
    """Decrypt an allowed secret field via staff-protected JSON endpoint."""
    payload, error_response = services.decrypt_item_payload(request)
    if error_response:
        return error_response
    if payload is None:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    return services.decrypt_secret(request.user, payload)


# ── Pay CRUD ──────────────────────────────────────────────────────────────────

@login_required
def pay_new(request: HttpRequest) -> HttpResponse:
    """Render and process the pay creation form."""
    if request.method == 'POST':
        form_pay = PayForm(request.POST)
        if form_pay.is_valid():
            form_pay.save()
            return redirect('app:pay_new')
    else:
        form_pay = PayForm(initial=services.get_pay_create_initial())

    ctx = {'form_pay': form_pay, 'group_options': services.get_pay_group_options()}
    ctx.update(services.get_common_context())
    ctx.update(_base_ctx(request))
    return render(request, 'add_pay.html', ctx)


@login_required
def pay_edit(request: HttpRequest, id: int) -> HttpResponse:
    """Edit a pay record and its cabinet details on a single page."""
    pay = get_object_or_404(Pay, pk=id)
    cabinet = get_object_or_404(Cabinet, pk=pay.cabinet_id)
    services.decrypt_pay_secrets(pay)
    services.decrypt_cabinet_secrets(cabinet)

    if request.method == 'POST':
        form_edit_pay = PayForm(request.POST, instance=pay)
        form_edit_cabinet = CabinetForm(request.POST, instance=cabinet)
        if form_edit_pay.is_valid():
            form_edit_pay.save()
            return redirect('app:home_page_with_cabinet', id=id)
        if form_edit_cabinet.is_valid():
            form_edit_cabinet.save()
            return redirect('app:home_page_with_cabinet', id=id)
    else:
        form_edit_pay = PayForm(instance=pay)
        form_edit_cabinet = CabinetForm(instance=cabinet)

    ctx = {'form_edit_pay': form_edit_pay, 'form_edit_cabinet': form_edit_cabinet}
    ctx.update(_base_ctx(request))
    return render(request, 'index.html', ctx)


@login_required
def edit_dt(request: HttpRequest, id: int) -> HttpResponse:
    """Edit only `paid_up_to` date for a pay record."""
    item = get_object_or_404(Pay, id=id)

    if request.method == 'POST':
        paid_up_to = parse_date((request.POST.get('paid_up_to') or '').strip())
        if not paid_up_to:
            ctx = {'object_l': item, 'date_error': True}
            ctx.update(_base_ctx(request))
            return render(request, 'edit_dt.html', ctx)
        # Date-only update avoids touching encrypted secret fields.
        Pay.objects.filter(id=item.id).update(paid_up_to=paid_up_to)
        return redirect('app:index')

    ctx = {'object_l': item}
    ctx.update(_base_ctx(request))
    return render(request, 'edit_dt.html', ctx)


@login_required
def edit_page(request: HttpRequest) -> HttpResponse:
    """Render compact page with all pay records for edit-navigation."""
    ctx = {
        'object_l': Pay.objects.all().order_by('id'),
        'cabinet': Cabinet.objects.all(),
    }
    ctx.update(services.get_common_context())
    return render(request, 'edit_page.html', ctx)


@login_required
def edit_table(request: HttpRequest, id: int) -> HttpResponse:
    """Render and process full pay edit form for the selected record."""
    item = services.decrypt_pay_secrets(get_object_or_404(Pay, id=id))

    if request.method == 'POST':
        form_edit_pay = PayForm(request.POST, instance=item)
        if form_edit_pay.is_valid():
            form_edit_pay.save()
            return redirect('app:edit_page')
    else:
        form_edit_pay = PayForm(instance=item)

    return render(request, 'edit_table.html', {'object_l': item, 'form_edit_pay': form_edit_pay})


@login_required
def delete(request: HttpRequest, id: int) -> HttpResponse:
    """Delete a pay record. Returns JSON for AJAX requests, otherwise redirects."""
    pay = get_object_or_404(Pay, id=id)
    service_name = pay.service
    pay_id = pay.id
    cabinet_id = pay.cabinet_id
    pay.delete()
    log_event(
        event='pay.delete.request',
        message='Pay delete endpoint executed',
        pay_id=pay_id,
        cabinet_id=cabinet_id,
        service=service_name,
    )
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'message': f'Service "{service_name}" deleted successfully.'})

    redirect_to = _get_safe_next_url(request, reverse('app:index'))
    return redirect(_append_query_param(redirect_to, 'deleted_service', service_name))


# ── Cabinet CRUD ──────────────────────────────────────────────────────────────

@login_required
def cabinet_new(request: HttpRequest) -> HttpResponse:
    """Render and process cabinet creation with optional inline tag creation."""
    if request.method == 'POST':
        submit_action = request.POST.get('submit_action')

        if submit_action == 'create_tag':
            tag_form = TagForm(request.POST, prefix='new_tag')
            selected_tag_ids = services.parse_tag_ids(request.POST.getlist('selected_tags'))
            cabinet_form_data = services.extract_prefixed_cabinet_form_data(request.POST)
            form_cabinet = CabinetForm(cabinet_form_data or None)
            if tag_form.is_valid():
                new_tag = tag_form.save()
                selected_tag_ids = sorted(set(selected_tag_ids + [new_tag.id]))
                tag_form = TagForm(prefix='new_tag')
            tag_assign_form = CabinetTagAssignForm(initial={'tags': selected_tag_ids})
            form_pay = PayForm()
        else:
            form_pay = PayForm()
            form_cabinet = CabinetForm(request.POST)
            tag_assign_form = CabinetTagAssignForm(request.POST)
            tag_form = TagForm(prefix='new_tag')
            if form_cabinet.is_valid() and tag_assign_form.is_valid():
                cabinet = form_cabinet.save()
                services.replace_cabinet_tags(cabinet, tag_assign_form.cleaned_data['tags'])
                return redirect('app:pay_new')
    else:
        form_pay = PayForm()
        form_cabinet = CabinetForm()
        tag_assign_form = CabinetTagAssignForm()
        tag_form = TagForm(prefix='new_tag')

    ctx = {
        'form_cabinet': form_cabinet,
        'form_pay': form_pay,
        'tag_assign_form': tag_assign_form,
        'tag_form': tag_form,
    }
    ctx.update(services.get_cabinet_create_context())
    ctx.update(_base_ctx(request))
    return render(request, 'add_pay.html', ctx)


@login_required
def cabinet_edit(request: HttpRequest, id: int) -> HttpResponse:
    """Edit cabinet fields and assigned tags for an existing cabinet."""
    cabinet = get_object_or_404(Cabinet, pk=id)
    services.decrypt_cabinet_secrets(cabinet)
    selected_tag_ids = services.get_selected_cabinet_tag_ids(cabinet)

    if request.method == 'POST':
        submit_action = request.POST.get('submit_action')

        if submit_action == 'create_tag':
            cabinet_form_data = services.extract_prefixed_cabinet_form_data(request.POST)
            draft_selected_tag_ids = services.parse_tag_ids(request.POST.getlist('selected_tags')) or selected_tag_ids
            form_cabinet_edit = CabinetForm(cabinet_form_data, instance=cabinet) if cabinet_form_data else CabinetForm(instance=cabinet)
            tag_assign_form = CabinetTagAssignForm(initial={'tags': draft_selected_tag_ids})
            tag_form = TagForm(request.POST, prefix='new_tag')
            if tag_form.is_valid():
                new_tag = tag_form.save()
                merged_ids = sorted(set(draft_selected_tag_ids) | {new_tag.id})
                tag_assign_form = CabinetTagAssignForm(initial={'tags': merged_ids})
                tag_form = TagForm(prefix='new_tag')
        else:
            form_cabinet_edit = CabinetForm(request.POST, instance=cabinet)
            tag_assign_form = CabinetTagAssignForm(request.POST)
            tag_form = TagForm(prefix='new_tag')
            if form_cabinet_edit.is_valid() and tag_assign_form.is_valid():
                cabinet = form_cabinet_edit.save()
                services.replace_cabinet_tags(cabinet, tag_assign_form.cleaned_data['tags'])
                return redirect('app:cabinet_page')
    else:
        form_cabinet_edit = CabinetForm(instance=cabinet)
        tag_assign_form = CabinetTagAssignForm(initial={'tags': selected_tag_ids})
        tag_form = TagForm(prefix='new_tag')

    ctx = {
        'form_cabinet_edit': form_cabinet_edit,
        'tag_assign_form': tag_assign_form,
        'tag_form': tag_form,
    }
    ctx.update(services.get_cabinet_sidebar_context())
    ctx.update(services.get_common_context())
    return render(request, 'cabinet.html', ctx)


@login_required
def cabinet_page(request: HttpRequest) -> HttpResponse:
    """Render cabinet list with advanced filtering, sorting, and counters."""
    return render(request, 'cabinet.html', services.build_cabinet_page_context(request))


@login_required
def sort_by_name_cabinet(request: HttpRequest, name: str) -> HttpResponse:
    """Render cabinet page sorted by the requested field name."""
    ctx = services.build_cabinet_page_context(request)
    # Override sort with the legacy positional sort name
    ctx['object_k'] = ctx['object_k'].order_by(name)
    return render(request, 'cabinet.html', ctx)


@login_required
def delete_cabinet(request: HttpRequest, id: int) -> HttpResponse:
    """Delete cabinet when possible, handling linked-record integrity failures."""
    try:
        get_object_or_404(Cabinet, id=id).delete()
        log_event(
            event='cabinet.delete.request',
            message='Cabinet delete endpoint executed',
            cabinet_id=id,
            outcome='deleted',
        )
        return redirect('app:cabinet_page')
    except IntegrityError:
        log_event(
            event='cabinet.delete.blocked',
            message='Cabinet delete blocked by linked records',
            cabinet_id=id,
            outcome='blocked_integrity_error',
        )
        return HttpResponseNotFound(
            '<h2>Дане поле неможливо видалити!! Поле зв\'язане із елементом у іншій таблиці</h2>'
        )


# ── Home / Pay list ───────────────────────────────────────────────────────────

@login_required
def home_page(request: HttpRequest) -> HttpResponse:
    """Render default pay list page with active filters and sidebar context."""
    return render(request, 'index.html', services.build_pay_list_context(request))


@login_required
def home_page_with_cabinet(request: HttpRequest, id: int) -> HttpResponse:
    """Render pay list scoped to a specific pay ID for quick detail viewing."""
    ctx = {
        'object_l': Pay.objects.filter(id=id),
        'cabinet_obj': Pay.objects.filter(id=id),
    }
    ctx.update(_base_ctx(request))
    return render(request, 'index.html', ctx)


@login_required
def sort_by_name(request: HttpRequest, name: str) -> HttpResponse:
    """Apply legacy pay sort parameter and render updated pay list."""
    legacy_sort = f'{name}_asc'
    if legacy_sort not in services.PAY_SORT_MAP:
        legacy_sort = services.PAY_SORT_DEFAULT
    default_mode = request.GET.get('mode') or services.PAY_MODE_ALL
    return render(
        request, 'index.html',
        services.build_pay_list_context(request, default_mode=default_mode, overrides={'sort': legacy_sort}),
    )


@login_required
def filter_by_date(request: HttpRequest, name: str) -> HttpResponse:
    """Render pay list in upcoming mode (legacy route compatibility)."""
    return render(request, 'index.html', services.build_pay_list_context(request, default_mode=services.PAY_MODE_UPCOMING))


@login_required
def overdue_payments(request: HttpRequest, name: str) -> HttpResponse:
    """Render pay list in overdue mode (legacy route compatibility)."""
    return render(request, 'index.html', services.build_pay_list_context(request, default_mode=services.PAY_MODE_OVERDUE))


@login_required
def filter_by_pay_sys(request: HttpRequest, name: str) -> HttpResponse:
    """Filter pay list by payment system while preserving current mode."""
    default_mode = request.GET.get('mode') or services.PAY_MODE_ALL
    return render(
        request, 'index.html',
        services.build_pay_list_context(request, default_mode=default_mode, overrides={'pay_sys': name}),
    )


@login_required
def filter_by_type_source(request: HttpRequest, name: str) -> HttpResponse:
    """Filter pay list by source type while preserving current mode."""
    default_mode = request.GET.get('mode') or services.PAY_MODE_ALL
    return render(
        request, 'index.html',
        services.build_pay_list_context(request, default_mode=default_mode, overrides={'type_source': name}),
    )


@login_required
def filter_by_active(request: HttpRequest, name: str) -> HttpResponse:
    """Filter pay list by active/inactive status value."""
    default_mode = request.GET.get('mode') or services.PAY_MODE_ALL
    return render(
        request, 'index.html',
        services.build_pay_list_context(request, default_mode=default_mode, overrides={'status': [name]}),
    )


@login_required
def searching(request: HttpRequest, name: str) -> HttpResponse:
    """Run pay list text search from legacy route/query parameter variants."""
    q = (request.GET.get('g') or request.GET.get('q') or '').strip()
    default_mode = request.GET.get('mode') or services.PAY_MODE_ALL
    return render(
        request, 'index.html',
        services.build_pay_list_context(request, default_mode=default_mode, overrides={'q': q}),
    )


# ── Statistics ────────────────────────────────────────────────────────────────

@login_required
def statistics_page(request: HttpRequest) -> HttpResponse:
    """Render statistics dashboard with filter-aware analytics context."""
    return render(request, 'statistics.html', services.build_statistics_context(request))


# ── Tags CRUD ─────────────────────────────────────────────────────────────────

@login_required
def tags_page(request: HttpRequest) -> HttpResponse:
    """Render tag list with search and sidebar context data."""
    from django.db.models import Count, Q
    all_tags = Tag.objects.annotate(
        cabinets_count=Count('cabinet_tags__cabinet', distinct=True),
    ).order_by('name')

    q = request.GET.get('q', '').strip()
    tags = all_tags.filter(Q(name__icontains=q) | Q(note__icontains=q)) if q else all_tags

    ctx = {'tags': tags, 'all_tags': all_tags, 'search_query': q}
    ctx.update(_base_ctx(request))
    return render(request, 'tags/tag_list.html', ctx)


@login_required
def tag_create(request: HttpRequest) -> HttpResponse:
    """Render and process creation form for a new tag."""
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('app:tags_page')
    else:
        form = TagForm()

    ctx = {'form': form}
    ctx.update(_base_ctx(request))
    return render(request, 'tags/tag_form.html', ctx)


@login_required
def tag_edit(request: HttpRequest, id: int) -> HttpResponse:
    """Render and process edit form for an existing tag."""
    tag = get_object_or_404(Tag, pk=id)

    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            return redirect('app:tags_page')
    else:
        form = TagForm(instance=tag)

    ctx = {'form': form, 'tag': tag}
    ctx.update(_base_ctx(request))
    return render(request, 'tags/tag_form.html', ctx)


@login_required
def tag_delete(request: HttpRequest, id: int) -> HttpResponse:
    """Render confirmation and delete the selected tag on POST."""
    tag = get_object_or_404(Tag, pk=id)
    if request.method == 'POST':
        tag.delete()
        return redirect('app:tags_page')

    ctx = {'tag': tag}
    ctx.update(_base_ctx(request))
    return render(request, 'tags/tag_confirm_delete.html', ctx)


# ── Healthz ───────────────────────────────────────────────────────────────────

def healthz(request: HttpRequest) -> JsonResponse:
    """Return lightweight liveness response for probes and smoke checks."""
    return JsonResponse({'status': 'ok'})
