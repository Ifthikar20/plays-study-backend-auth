"""Game models."""
from django.conf import settings
from django.db import models


class Game(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    game_type = models.CharField(max_length=50)
    difficulty = models.CharField(max_length=20, default='medium')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'games'

    def __str__(self):
        return self.name


class GameCompletion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='game_completions')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='completions')
    score = models.IntegerField(default=0)
    time_taken = models.IntegerField(default=0)
    xp_earned = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'game_completions'
        ordering = ['-completed_at']

    def __str__(self):
        return f'{self.user.email} - {self.game.name}: {self.score}'
