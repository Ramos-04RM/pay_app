from pay_app import views
from django.urls import path

app_name = "app"

urlpatterns = [
    path(r'', views.home_page, name='index'),
    path(r'cabinet/<int:id>', views.home_page_with_cabinet, name='home_page_with_cabinet'),
    path(r'cabinet/', views.cabinet_page, name='cabinet_page'),  # for cabinet.html
    path(r'cabinet_edit/<int:id>', views.cabinet_edit, name='cabinet_edit'),  # for cabinet.edit
    path(r'pay_edit/<int:id>', views.pay_edit, name='pay_edit'),  # for .edit.item
    path(r'sort/<str:name>', views.sort_by_name, name='sorted_by_name'),  # sotr_colums_table
    path(r'sort_cabinet/<str:name>', views.sort_by_name_cabinet, name='sort_by_name_cabinet'),  # sotr_colums_table
    path(r'filter/<str:name>', views.filter_by_date, name='filter_by_date'),  # filter_data(1_week)
    path(r'filter_overdue_payments/<str:name>', views.overdue_payments, name='overdue_payments'),
    # overdue_payments(1_month)
    path(r'filter_pay_sys/<str:name>', views.filter_by_pay_sys, name='filter_by_pay_sys'),  # filter_pay_sys(3 items)
    path(r'filter_type_sourse/<str:name>', views.filter_by_type_source, name='filter_by_type_source'),
    # filter_by_type_source(3 items)
    path(r'filter_by_active/<str:name>', views.filter_by_active, name='filter_by_active'),
    path(r'searching/<str:name>', views.searching, name='searching'),  # filter_by_groups(*)
    # path(r'create/', views.create, name='create'), #
    path(r'edit_dt/<int:id>', views.edit_dt, name='edit_dt'),
    path(r'edit_page/', views.edit_page, name='edit_page'),
    path(r'cabinet/new/', views.cabinet_new, name='cabinet_new'),  # new_items
    path(r'pay/new/', views.pay_new, name='pay_new'),  # new_items
    path(r'edit_tb/<int:id>', views.edit_table, name='edit_tb'),
    path(r'delete/<int:id>', views.delete, name='delete'),
    path(r'delete_cabinet/<int:id>', views.delete_cabinet, name='delete_cabinet'),

]
