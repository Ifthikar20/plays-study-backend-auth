"""Games URL configuration."""
from django.urls import path
from . import views

urlpatterns = [
    path('games/', views.game_list, name='game-list'),
    path('games/<int:game_id>/complete', views.game_complete, name='game-complete'),
]
