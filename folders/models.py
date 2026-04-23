"""Folder model for organizing study sessions."""
from django.conf import settings
from django.db import models


class Folder(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='folders')
    color = models.CharField(max_length=20, default='#3B82F6')
    icon = models.CharField(max_length=10, default='📁')
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'folders'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
