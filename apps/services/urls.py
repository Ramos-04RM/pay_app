from django.urls import path

from apps.services import views


urlpatterns = [
    path('', views.home_page, name='index'),
    path('cabinet/<int:id>', views.home_page_with_cabinet, name='home_page_with_cabinet'),
    path('pay_edit/<int:id>', views.pay_edit, name='pay_edit'),
    path('sort/<str:name>', views.sort_by_name, name='sorted_by_name'),
    path('filter/<str:name>', views.filter_by_date, name='filter_by_date'),
    path('filter_overdue_payments/<str:name>', views.overdue_payments, name='overdue_payments'),
    path('filter_pay_sys/<str:name>', views.filter_by_pay_sys, name='filter_by_pay_sys'),
    path('filter_type_source/<str:name>', views.filter_by_type_source, name='filter_by_type_source'),
    path('filter_type_sourse/<str:name>', views.filter_by_type_source),
    path('filter_by_active/<str:name>', views.filter_by_active, name='filter_by_active'),
    path('searching/<str:name>', views.searching, name='searching'),
    path('edit_dt/<int:id>', views.edit_dt, name='edit_dt'),
    path('edit_page/', views.edit_page, name='edit_page'),
    path('pay/new/', views.pay_new, name='pay_new'),
    path('edit_table/<int:id>', views.edit_table, name='edit_table'),
    path('edit_tb/<int:id>', views.edit_table, name='edit_tb'),
    path('delete/<int:id>', views.delete, name='delete'),
]
