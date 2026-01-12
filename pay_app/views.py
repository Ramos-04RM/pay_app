from django.db.models import Q, QuerySet
from django.db import IntegrityError
from .models import Pay, Cabinet
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from datetime import timedelta
import datetime
from django.http import HttpResponseRedirect, HttpResponseNotFound
import cryptocode
from .forms import PayForm, CabinetForm
from django.contrib.auth.decorators import login_required

today = datetime.date.today()
month = today + timedelta(days=31)
week = today + timedelta(days=7)
weeks = [today, week]

nt_pd = today - timedelta(days=31)
nt_pds = [nt_pd, today]

last_dt = Pay.objects.filter(Q(status='active') & Q(paid_up_to__range=weeks)).order_by('paid_up_to')[
          :5]  # оплата в найближчому часі
not_paid = Pay.objects.filter(Q(status='active') & Q(paid_up_to__range=nt_pds)).order_by(
    'paid_up_to')[:5]  # просрочені оплати for month

cont = {
    'week': week,
    'today': today,
    'last_dt': last_dt,
    'not_paid': not_paid,
    'month': month,
}


def decrypt(object_l):  # decrypt psw adn log in pay
    user_psw = User.objects.get(username='admin').password
    for i in object_l:  # decrypt log_and_psw
        i.password = cryptocode.decrypt(i.password, user_psw)
        i.email_login = cryptocode.decrypt(i.email_login, user_psw)


def decrypt_cabinet(object_k):  # decrypt psw adn log in cabinet
    user_psw = User.objects.get(username='admin')
    for i in object_k:
        i.password = cryptocode.decrypt(i.password, user_psw.password)
        i.email_password = cryptocode.decrypt(i.email_password, user_psw.password)


@login_required
def pay_new(request):
    if request.method == "POST":
        form_pay = PayForm(request.POST)
        if form_pay.is_valid():
            post = form_pay.save(commit=False)
            post.save()
            return redirect('app:pay_new')
    else:
        if Cabinet.objects.all().count() > 0:
            lst_id = Cabinet.objects.all().last().id  # last id
            form_pay = PayForm(initial={"cabinet": lst_id,
                                        'create_date': today})  # default value for few collums
        else:
            form_pay = PayForm()
    content = {
        'form_pay': form_pay
    }
    content.update(cont)
    return render(request, 'add_pay.html', content)


def cabinet_new(request):
    if request.method == "POST":
        form_pay = PayForm(request.POST)
        form_cabinet = CabinetForm(request.POST)
        if form_cabinet.is_valid():
            post = form_cabinet.save(commit=False)
            post.save()
            return redirect('app:pay_new')
    else:
        form_cabinet = CabinetForm()
        form_pay = PayForm()
    content = {
        'form_cabinet': form_cabinet,
        'form_pay': form_pay
    }
    content.update(cont)
    return render(request, 'add_pay.html', content)


@login_required
def cabinet_edit(request, id):
    post = get_object_or_404(Cabinet, pk=id)
    user_psw = User.objects.get(username='admin').password
    post.password = cryptocode.decrypt(post.password, user_psw)   # decrypt Cabinet.psw
    post.email_password = cryptocode.decrypt(post.email_password, user_psw)  # decrypt Cabinet.email_psw
    if request.method == "POST":
        form_cabinet_edit = CabinetForm(request.POST, instance=post)
        if form_cabinet_edit.is_valid():
            post = form_cabinet_edit.save(commit=False)
            post.save()
            return redirect('app:cabinet_page')
    else:
        form_cabinet_edit = CabinetForm(instance=post)
    content = {
        'form_cabinet_edit': form_cabinet_edit,
    }
    content.update(cont)
    return render(request, 'cabinet.html', content)


@login_required
def pay_edit(request, id):
    post = get_object_or_404(Pay, pk=id)
    id_pay = Cabinet.objects.get(pay__id=id).id
    post_cabinet = get_object_or_404(Cabinet, pk=id_pay)
    user_psw = User.objects.get(username='admin').password  #
    post.password = cryptocode.decrypt(post.password, user_psw)  # decrypt Pay.psw
    post.email_login = cryptocode.decrypt(post.email_login, user_psw)  # decrypt Pay.
    post_cabinet.password = cryptocode.decrypt(post_cabinet.password, user_psw)  # decrypt Cabinet.psw
    post_cabinet.email_password = cryptocode.decrypt(post_cabinet.email_password, user_psw)  # decrypt Cabinet.email_psw
    if request.method == "POST":
        form_edit_pay = PayForm(request.POST, instance=post)
        form_edit_cabinet = CabinetForm(request.POST, instance=post_cabinet)
        if form_edit_pay.is_valid():
            post = form_edit_pay.save(commit=False)
            post.save()
            return redirect('app:index')
        if form_edit_cabinet.is_valid():
            post_cabinet = form_edit_cabinet.save(commit=False)
            post_cabinet.save()
            return redirect('app:pay_edit', id)
    else:
        form_edit_pay = PayForm(instance=post)  # для завнення класу своїми даними
        form_edit_cabinet = CabinetForm(instance=post_cabinet)
    content = {
        'form_edit_pay': form_edit_pay,
        'form_edit_cabinet': form_edit_cabinet,
    }
    content.update(cont)
    return render(request, 'index.html', content)


@login_required
def home_page(request):  # home page
    object_l = Pay.objects.all().order_by('id')
    decrypt(object_l)
    content = {
        'object_l': object_l,
    }
    content.update(cont)
    return render(request, 'index.html', content)


@login_required
def home_page_with_cabinet(request, id):  # home page+cabinet_id
    user_psw = User.objects.get(username='admin').password
    object_l = Pay.objects.filter(id=id)
    decrypt(object_l)
    cabinet_obj = Pay.objects.filter(id=id)
    for i in cabinet_obj:
        i.cabinet.password = cryptocode.decrypt(i.cabinet.password, user_psw)
        i.cabinet.email_password = cryptocode.decrypt(i.cabinet.email_password, user_psw)
    content = {
        'object_l': object_l,
        'cabinet_obj': cabinet_obj,
    }
    content.update(cont)
    return render(request, 'index.html', content)


@login_required
def cabinet_page(request):  # for cabinet.html
    object_k = Cabinet.objects.all().order_by('id')
    decrypt_cabinet(object_k)
    content = {
        'object_k': object_k,
    }
    content.update(cont)

    return render(request, 'cabinet.html', content)


# sort <tr> title table
@login_required
def sort_by_name(request, name):
    sort_groups = Pay.objects.all().order_by(name)
    decrypt(sort_groups)
    content = {
        'object_l': sort_groups,
    }
    content.update(cont)
    return render(request, 'index.html', content)


def sort_by_name_cabinet(request, name):
    sort_cabinet = Cabinet.objects.all().order_by(name)
    decrypt_cabinet(sort_cabinet)
    content = {
        'object_k': sort_cabinet,
    }
    content.update(cont)
    return render(request, 'cabinet.html', content)


#  filter (оплата найближчем часом)
def filter_by_date(request, name):
    dt = Pay.objects.filter(Q(status='active') & Q(paid_up_to__range=weeks)).order_by('paid_up_to')
    decrypt(dt)
    content = {
        'object_l': dt,
    }
    content.update(cont)
    return render(request, 'index.html', content)


# filter (оплата найближчем часом)
def overdue_payments(request, name):
    dt = Pay.objects.filter(Q(status='active') & Q(paid_up_to__range=nt_pds)).order_by('paid_up_to')
    decrypt(dt)
    content = {
        'object_l': dt,
    }
    content.update(cont)
    return render(request, 'index.html', content)


def filter_by_pay_sys(request, name):
    pay_sys = Pay.objects.filter(pay_sys=name)
    decrypt(pay_sys)
    content = {
        'object_l': pay_sys,
    }
    content.update(cont)
    return render(request, 'index.html', content)


def filter_by_type_source(request, name):
    pay_type_source = Pay.objects.filter(type_source=name)
    decrypt(pay_type_source)
    content = {
        'object_l': pay_type_source,
    }
    content.update(cont)
    return render(request, 'index.html', content)


def filter_by_active(request, name):
    active = Pay.objects.filter(status=name)
    decrypt(active)
    content = {
        'object_l': active,
    }
    content.update(cont)
    return render(request, 'index.html', content)


def searching(request, name):
    name = request.GET.get("g")
    filter_items = Pay.objects.filter(Q(ip__contains=name) | Q(service=name)
                                      | Q(ip=name) | Q(type_source=name)
                                      | Q(pay_sys=name) | Q(status=name)
                                      | Q(currency=name) | Q(groups=name))
    decrypt(filter_items)
    content = {
        'object_l': filter_items,
    }
    content.update(cont)
    return render(request, 'index.html', content)


#  update_date_paid_up_to
def update_date(request, name):
    name = request.GET.get("q")
    pay_type_source = Pay.objects.filter(paid_up_to=name)
    decrypt(pay_type_source)
    content = {
        'object_l': pay_type_source,
    }
    content.update(cont)
    return render(request, 'index.html', content)


def edit_dt(request, id):  # редактор дати
    try:
        item = Pay.objects.get(id=id)
        user_psw = User.objects.get(username='admin')
        item.password = cryptocode.decrypt(item.password, user_psw.password)
        item.email_login = cryptocode.decrypt(item.email_login, user_psw.password)
        if request.method == "POST":
            item.paid_up_to = request.POST.get('paid_up_to')
            item.save()
            return HttpResponseRedirect("/")
        else:
            return render(request, "edit_dt.html", {"object_l": item})
    except Pay.DoesNotExist:
        return HttpResponseNotFound("<h2> not found</h2>")


def edit_page(request):
    object_l = Pay.objects.all().order_by('id')
    decrypt(object_l)
    cabinet = Cabinet.objects.all()
    content = {
        'object_l': object_l,
        'cabinet': cabinet,
    }
    content.update(cont)
    return render(request, 'edit_page.html', content)


def edit_table(request, id):
    try:
        item = Pay.objects.get(id=id)
        user_psw = User.objects.get(username='admin')
        item.password = cryptocode.decrypt(item.password, user_psw.password)
        item.email_login = cryptocode.decrypt(item.email_login, user_psw.password)
        if request.method == "POST":
            item.groups = request.POST.get('groups')
            item.service = request.POST.get('service')
            item.create_date = request.POST.get('create_date')
            item.type_source = request.POST.get("type_source")
            item.price_per_month = request.POST.get('price_per_month')
            item.currency = request.POST.get('currency')
            item.pay_sys = request.POST.get('pay_sys')
            item.paid_up_to = request.POST.get('paid_up_to')
            item.status = request.POST.get('status')
            item.email_login = request.POST.get('email_login')
            item.password = request.POST.get('password')
            item.ip = request.POST.get('ip')
            item.save()
            content = {
                'object_l': item,
            }
            content.update(cont)
            return HttpResponseRedirect("/edit_page/", content)
        else:
            return render(request, "edit_table.html", {"object_l": item})
    except Pay.DoesNotExist:
        return HttpResponseNotFound("<h2> not found</h2>")


def delete(request, id):
    try:
        item = Pay.objects.get(id=id)
        item.delete()
        return HttpResponseRedirect("/edit_page/")
    except Pay.DoesNotExist:
        return HttpResponseNotFound("<h2>Pay not found</h2>")


def delete_cabinet(request, id):
    try:
        item = get_object_or_404(Cabinet, id=id)
        item.delete()
        return HttpResponseRedirect("/cabinet/")
    except IntegrityError:
        return HttpResponseNotFound("<h2>Дане поле неможливо видалити!! Поле зв'язане із елементом у іншій таблиці</h2>")
    except Cabinet.DoesNotExist:
        return HttpResponseNotFound("<h2>Pay not found</h2>")


# save  data in db
# def create(request):
#     global content
#     # cabinet = Cabinet.objects.get(name=cabinet_name)
#     # cabinet = Cabinet.objects.all().last()
#     item = Pay()
#     if request.method == "POST":
#         item.id = request.POST.get('id')
#         # item.cabinet = request.POST.get(cabinet)
#         item.groups = request.POST.get('groups')
#         item.create_date = request.POST.get('create_date')
#         item.service = request.POST.get('service')
#         item.type_source = request.POST.get("type_source")
#         item.price_per_month = request.POST.get('price_per_month')
#         item.currency = request.POST.get('currency')
#         item.pay_sys = request.POST.get('pay_sys')
#         item.paid_up_to = request.POST.get('paid_up_to')
#         item.status = request.POST.get('status')
#         item.email_login = request.POST.get('email_login')
#         item.password = request.POST.get('password')
#         item.ip = request.POST.get('ip')
#         item.save()
#     return HttpResponseRedirect("/edit_page/")