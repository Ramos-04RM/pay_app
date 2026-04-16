from django.urls import path

from apps.tags import views


urlpatterns = [
    path('tags/', views.tags_page, name='tags_page'),
    path('tags/new/', views.tag_create, name='tag_create'),
    path('tags/<int:id>/edit/', views.tag_edit, name='tag_edit'),
    path('tags/<int:id>/delete/', views.tag_delete, name='tag_delete'),
]
