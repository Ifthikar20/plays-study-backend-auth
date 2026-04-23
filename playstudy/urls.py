"""PlayStudy URL Configuration — all API routes under /api/"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({'status': 'healthy', 'version': '2.0.0', 'framework': 'django'})


def root(request):
    return JsonResponse({'message': 'PlayStudy API', 'version': '2.0.0', 'docs': '/admin/', 'health': '/health'})


urlpatterns = [
    path('', root),
    path('health', health_check),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('study.urls')),
    path('api/', include('folders.urls')),
    path('api/', include('games.urls')),
]
