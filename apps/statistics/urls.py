from django.urls import path

from apps.statistics import views


urlpatterns = [
    path('statistics/', views.statistics_page, name='statistics'),
]
