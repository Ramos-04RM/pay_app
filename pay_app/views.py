from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CabinetForm, CabinetTagAssignForm, PayForm, TagForm
from .models import Cabinet, Pay, Tag
from . import services


@require_POST
@login_required
def decrypt_item(request):
    payload, error_response = services.decrypt_item_payload(request)
    if error_response:
        return error_response
    return services.decrypt_secret(request.user, payload)


@login_required
def pay_new(request):
    context_dates = services.get_common_context()
    group_options = services.get_pay_group_options()

    if request.method == 'POST':
        form_pay = PayForm(request.POST)
        if form_pay.is_valid():
            pay = form_pay.save(commit=False)
            pay.save()
            return redirect('app:pay_new')
    else:
        form_pay = PayForm(initial=services.get_pay_create_initial())

    content = {'form_pay': form_pay, 'group_options': group_options}
    content.update(context_dates)
    content.update(services.get_default_pay_context(request))
    return render(request, 'add_pay.html', content)


@login_required
def cabinet_new(request):
    context_dates = services.get_cabinet_create_context()
    if request.method == 'POST':
        submit_action = request.POST.get('submit_action')

        if submit_action == 'create_tag':
            form_pay = PayForm()
            tag_form = TagForm(request.POST, prefix='new_tag')
            selected_tag_ids = services.parse_tag_ids(request.POST.getlist('selected_tags'))
            cabinet_form_data = services.extract_prefixed_cabinet_form_data(request.POST)
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
                cabinet = form_cabinet.save(commit=False)
                cabinet.save()
                services.replace_cabinet_tags(cabinet, tag_assign_form.cleaned_data['tags'])
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
    content.update(services.get_default_pay_context(request))
    return render(request, 'add_pay.html', content)


@login_required
def cabinet_edit(request, id):
    cabinet = get_object_or_404(Cabinet, pk=id)
    services.decrypt_cabinet_secrets(cabinet)
    selected_tag_ids = services.get_selected_cabinet_tag_ids(cabinet)

    if request.method == 'POST':
        form_cabinet_edit = CabinetForm(request.POST, instance=cabinet)
        tag_assign_form = CabinetTagAssignForm(request.POST)
        tag_form = TagForm(request.POST, prefix='new_tag')
        submit_action = request.POST.get('submit_action')

        if submit_action == 'save_tags':
            tag_form = TagForm(prefix='new_tag')
            if form_cabinet_edit.is_valid() and tag_assign_form.is_valid():
                cabinet = form_cabinet_edit.save(commit=False)
                cabinet.save()
                services.replace_cabinet_tags(cabinet, tag_assign_form.cleaned_data['tags'])
                return redirect('app:cabinet_page')
        elif submit_action == 'create_tag':
            if tag_form.is_valid():
                new_tag = tag_form.save()
                merged_ids = set(services.get_selected_cabinet_tag_ids(cabinet))
                merged_ids.add(new_tag.id)
                form_cabinet_edit = CabinetForm(request.POST, instance=cabinet)
                tag_assign_form = CabinetTagAssignForm(initial={'tags': list(merged_ids)})
            else:
                form_cabinet_edit = CabinetForm(request.POST, instance=cabinet)
                tag_assign_form = CabinetTagAssignForm(initial={'tags': selected_tag_ids})
        else:
            tag_form = TagForm(prefix='new_tag')
            if form_cabinet_edit.is_valid() and tag_assign_form.is_valid():
                cabinet = form_cabinet_edit.save(commit=False)
                cabinet.save()
                services.replace_cabinet_tags(cabinet, tag_assign_form.cleaned_data['tags'])
                return redirect('app:cabinet_page')
    else:
        form_cabinet_edit = CabinetForm(instance=cabinet)
        tag_assign_form = CabinetTagAssignForm(initial={'tags': selected_tag_ids})
        tag_form = TagForm(prefix='new_tag')

    content = {
        'form_cabinet_edit': form_cabinet_edit,
        'tag_assign_form': tag_assign_form,
        'tag_form': tag_form,
    }
    content.update(services.get_cabinet_sidebar_context())
    content.update(services.get_common_context())
    return render(request, 'cabinet.html', content)


@login_required
def statistics_page(request):
    return render(request, 'statistics.html', services.build_statistics_context(request))


@login_required
def pay_edit(request, id):
    pay = get_object_or_404(Pay, pk=id)
    cabinet = get_object_or_404(Cabinet, pk=pay.cabinet_id)
    services.decrypt_pay_secrets(pay)
    services.decrypt_cabinet_secrets(cabinet)

    if request.method == 'POST':
        form_edit_pay = PayForm(request.POST, instance=pay)
        form_edit_cabinet = CabinetForm(request.POST, instance=cabinet)

        if form_edit_pay.is_valid():
            pay = form_edit_pay.save(commit=False)
            pay.save()
            return redirect('app:home_page_with_cabinet', id=id)

        if form_edit_cabinet.is_valid():
            cabinet = form_edit_cabinet.save(commit=False)
            cabinet.save()
            return redirect('app:home_page_with_cabinet', id=id)
    else:
        form_edit_pay = PayForm(instance=pay)
        form_edit_cabinet = CabinetForm(instance=cabinet)

    content = {'form_edit_pay': form_edit_pay, 'form_edit_cabinet': form_edit_cabinet}
    content.update(services.get_common_context())
    content.update(services.get_default_pay_context(request))
    return render(request, 'index.html', content)


@login_required
def home_page(request):
    return render(request, 'index.html', services.build_pay_list_context(request))


@login_required
def home_page_with_cabinet(request, id):
    content = {
        'object_l': Pay.objects.filter(id=id),
        'cabinet_obj': Pay.objects.filter(id=id),
    }
    content.update(services.get_common_context())
    content.update(services.get_default_pay_context(request))
    return render(request, 'index.html', content)


@login_required
def cabinet_page(request):
    return render(request, 'cabinet.html', services.build_cabinet_page_context(request))


@login_required
def sort_by_name(request, name):
    legacy_sort = f'{name}_asc'
    if legacy_sort not in services.PAY_SORT_MAP:
        legacy_sort = services.PAY_SORT_DEFAULT
    default_mode = request.GET.get('mode') or services.PAY_MODE_ALL
    return render(
        request,
        'index.html',
        services.build_pay_list_context(request, default_mode=default_mode, overrides={'sort': legacy_sort}),
    )


@login_required
def sort_by_name_cabinet(request, name):
    sort_cabinet = Cabinet.objects.annotate(
        services_count=Count('pay', distinct=True),
        active_services_count=Count('pay', filter=Q(pay__status='active'), distinct=True),
        inactive_services_count=Count('pay', filter=Q(pay__status='not active'), distinct=True),
        tags_count=Count('cabinet_tags__tag', distinct=True),
    ).prefetch_related('pay_set', 'cabinet_tags__tag').order_by(name)

    content = {'object_k': sort_cabinet}
    content.update(services.get_cabinet_sidebar_context())
    content.update(services.get_common_context())
    return render(request, 'cabinet.html', content)


@login_required
def filter_by_date(request, name):
    return render(request, 'index.html', services.build_pay_list_context(request, default_mode=services.PAY_MODE_UPCOMING))


@login_required
def overdue_payments(request, name):
    return render(request, 'index.html', services.build_pay_list_context(request, default_mode=services.PAY_MODE_OVERDUE))


@login_required
def filter_by_pay_sys(request, name):
    default_mode = request.GET.get('mode') or services.PAY_MODE_ALL
    return render(
        request,
        'index.html',
        services.build_pay_list_context(request, default_mode=default_mode, overrides={'pay_sys': name}),
    )


@login_required
def filter_by_type_source(request, name):
    default_mode = request.GET.get('mode') or services.PAY_MODE_ALL
    return render(
        request,
        'index.html',
        services.build_pay_list_context(request, default_mode=default_mode, overrides={'type_source': name}),
    )


@login_required
def filter_by_active(request, name):
    default_mode = request.GET.get('mode') or services.PAY_MODE_ALL
    return render(
        request,
        'index.html',
        services.build_pay_list_context(request, default_mode=default_mode, overrides={'status': [name]}),
    )


@login_required
def searching(request, name):
    q = (request.GET.get('g') or request.GET.get('q') or '').strip()
    default_mode = request.GET.get('mode') or services.PAY_MODE_ALL
    return render(
        request,
        'index.html',
        services.build_pay_list_context(request, default_mode=default_mode, overrides={'q': q}),
    )


@login_required
def edit_dt(request, id):
    try:
        item = services.decrypt_pay_secrets(Pay.objects.get(id=id))
        if request.method == 'POST':
            item.paid_up_to = request.POST.get('paid_up_to')
            item.save()
            return redirect('app:index')
        content = {'object_l': item}
        content.update(services.get_common_context())
        content.update(services.get_default_pay_context(request))
        return render(request, 'edit_dt.html', content)
    except Pay.DoesNotExist:
        return HttpResponseNotFound('<h2> not found</h2>')


@login_required
def edit_page(request):
    content = {
        'object_l': Pay.objects.all().order_by('id'),
        'cabinet': Cabinet.objects.all(),
    }
    content.update(services.get_common_context())
    return render(request, 'edit_page.html', content)


@login_required
def edit_table(request, id):
    try:
        item = services.decrypt_pay_secrets(Pay.objects.get(id=id))
        if request.method == 'POST':
            form_edit_pay = PayForm(request.POST, instance=item)
            if form_edit_pay.is_valid():
                item = form_edit_pay.save(commit=False)
                item.save()
                return redirect('app:edit_page')
            else:
                # Якщо помилка валідації, повертаємо форму із помилками
                return render(request, 'edit_table.html', {'object_l': item, 'form_edit_pay': form_edit_pay})
        else:
            form_edit_pay = PayForm(instance=item)
        return render(request, 'edit_table.html', {'object_l': item, 'form_edit_pay': form_edit_pay})
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
    # Get all tags first (for sidebar) - WITH cabinets count
    all_tags = Tag.objects.annotate(
        cabinets_count=Count('cabinet_tags__cabinet', distinct=True),
    ).order_by('name')
    
    # Start with all tags
    tags = all_tags

    # Handle search by name or note
    q = request.GET.get('q', '').strip()
    if q:
        tags = tags.filter(Q(name__icontains=q) | Q(note__icontains=q))

    content = {
        'tags': tags, 
        'all_tags': all_tags, 
        'search_query': q
    }
    content.update(services.get_common_context())
    content.update(services.get_default_pay_context(request))
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
    content.update(services.get_common_context())
    content.update(services.get_default_pay_context(request))
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
    content.update(services.get_common_context())
    content.update(services.get_default_pay_context(request))
    return render(request, 'tags/tag_form.html', content)


@login_required
def tag_delete(request, id):
    tag = get_object_or_404(Tag, pk=id)

    if request.method == 'POST':
        tag.delete()
        return redirect('app:tags_page')

    content = {'tag': tag}
    content.update(services.get_common_context())
    content.update(services.get_default_pay_context(request))
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


def healthz(request):
    return JsonResponse({'status': 'ok'})
