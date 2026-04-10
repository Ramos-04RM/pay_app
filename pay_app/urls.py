from django.urls import path
from pay_app import views

app_name = "app"

urlpatterns = [
    path("", views.home_page, name="index"),
    path("cabinet/<int:id>", views.home_page_with_cabinet, name="home_page_with_cabinet"),
    path("cabinet/", views.cabinet_page, name="cabinet_page"),
    path("cabinet_edit/<int:id>", views.cabinet_edit, name="cabinet_edit"),
    path("pay_edit/<int:id>", views.pay_edit, name="pay_edit"),

    # Pay list helpers / legacy compatibility
    path("sort/<str:name>", views.sort_by_name, name="sorted_by_name"),
    path("filter/<str:name>", views.filter_by_date, name="filter_by_date"),
    path("filter_overdue_payments/<str:name>", views.overdue_payments, name="overdue_payments"),
    path("filter_pay_sys/<str:name>", views.filter_by_pay_sys, name="filter_by_pay_sys"),
    path("filter_type_source/<str:name>", views.filter_by_type_source, name="filter_by_type_source"),
    path("filter_type_sourse/<str:name>", views.filter_by_type_source),  # legacy typo alias
    path("filter_by_active/<str:name>", views.filter_by_active, name="filter_by_active"),
    path("searching/<str:name>", views.searching, name="searching"),

    # Cabinet list helpers
    path("sort_cabinet/<str:name>", views.sort_by_name_cabinet, name="sort_by_name_cabinet"),

    # CRUD
    path("edit_dt/<int:id>", views.edit_dt, name="edit_dt"),
    path("edit_page/", views.edit_page, name="edit_page"),
    path("cabinet/new/", views.cabinet_new, name="cabinet_new"),
    path("pay/new/", views.pay_new, name="pay_new"),
    path("edit_table/<int:id>", views.edit_table, name="edit_table"),
    path("edit_tb/<int:id>", views.edit_table, name="edit_tb"),  # legacy alias
    path("delete/<int:id>", views.delete, name="delete"),
    path("delete_cabinet/<int:id>", views.delete_cabinet, name="delete_cabinet"),
    path("decrypt_item/", views.decrypt_item, name="decrypt_item"),
]
