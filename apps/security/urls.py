from django.urls import path

from apps.security import views


urlpatterns = [
    path('healthz/', views.healthz, name='healthz'),
    path('decrypt_item/', views.decrypt_item, name='decrypt_item'),
]
