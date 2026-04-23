"""Folder URL configuration."""
from django.urls import path
from . import views

urlpatterns = [
    path('folders/', views.folder_list_create, name='folder-list'),
    path('folders/<int:folder_id>/', views.folder_detail, name='folder-detail'),
]
