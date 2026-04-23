"""Folders admin registration."""
from django.contrib import admin
from .models import Folder


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'color', 'is_archived', 'created_at')
    list_filter = ('is_archived',)
    search_fields = ('name', 'user__email')
