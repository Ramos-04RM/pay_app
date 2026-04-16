from django.urls import include, path

urlpatterns = [
    path('', include('apps.security.urls')),
    path('', include('apps.services.urls')),
    path('', include('apps.cabinets.urls')),
    path('', include('apps.tags.urls')),
    path('', include('apps.statistics.urls')),
]
