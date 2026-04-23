"""Study app URL configuration."""
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('app-data', views.app_data, name='app-data'),

    # Study sessions
    path('study-sessions/', views.session_list, name='session-list'),
    path('study-sessions/<uuid:session_id>', views.session_detail, name='session-detail'),
    path('study-sessions/<uuid:session_id>/delete', views.session_delete, name='session-delete'),
    path('study-sessions/<uuid:session_id>/progress', views.update_progress, name='session-progress'),

    # AI endpoints
    path('study-sessions/analyze-content', views.analyze_content, name='analyze-content'),
    path('study-sessions/create-with-ai', views.create_with_ai, name='create-with-ai'),
]
