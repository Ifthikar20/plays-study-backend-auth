"""Accounts admin registration."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'xp', 'level', 'is_active', 'created_at')
    list_filter = ('is_active', 'level')
    search_fields = ('email', 'name')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('name', 'xp', 'level')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2'),
        }),
    )
