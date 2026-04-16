from django.urls import path

from apps.cabinets import views


urlpatterns = [
    path('cabinet/', views.cabinet_page, name='cabinet_page'),
    path('cabinet/new/', views.cabinet_new, name='cabinet_new'),
    path('cabinet_edit/<int:id>', views.cabinet_edit, name='cabinet_edit'),
    path('sort_cabinet/<str:name>', views.sort_by_name_cabinet, name='sort_by_name_cabinet'),
    path('delete_cabinet/<int:id>', views.delete_cabinet, name='delete_cabinet'),
]
