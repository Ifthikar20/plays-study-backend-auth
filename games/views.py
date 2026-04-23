"""Game views — IDOR-safe."""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Game, GameCompletion


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_list(request):
    """GET /api/games/ — list available games."""
    games = Game.objects.filter(is_active=True)
    return Response([{
        'id': g.id,
        'name': g.name,
        'description': g.description,
        'gameType': g.game_type,
        'difficulty': g.difficulty,
    } for g in games])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def game_complete(request, game_id):
    """POST /api/games/<id>/complete — record a game completion."""
    from django.shortcuts import get_object_or_404
    game = get_object_or_404(Game, id=game_id)

    completion = GameCompletion.objects.create(
        user=request.user,
        game=game,
        score=request.data.get('score', 0),
        time_taken=request.data.get('timeTaken', 0),
        xp_earned=request.data.get('xpEarned', 0),
    )

    # Award XP
    request.user.xp += completion.xp_earned
    request.user.save(update_fields=['xp'])

    return Response({
        'id': completion.id,
        'score': completion.score,
        'xpEarned': completion.xp_earned,
        'totalXP': request.user.xp,
    })
