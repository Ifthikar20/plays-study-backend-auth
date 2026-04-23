"""Games admin registration."""
from django.contrib import admin
from .models import Game, GameCompletion


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'game_type', 'difficulty', 'is_active')
    list_filter = ('game_type', 'difficulty')


@admin.register(GameCompletion)
class GameCompletionAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'score', 'xp_earned', 'completed_at')
    list_filter = ('game',)
