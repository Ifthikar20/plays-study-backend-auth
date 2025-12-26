"""
Game Recommendation Endpoints
Proxies requests to internal ML service - does NOT expose ML service to public.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import httpx
import os

from app.database import get_db
from app.models.user import User
from app.models.game import Game
from app.models.study_session import StudySession
from app.core.auth import get_current_user
from app.schemas.game import GameResponse

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Internal ML service URL (only accessible within VPC, not from internet)
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8001")


# ===== HELPER FUNCTIONS =====

def get_user_play_history(db: Session, user_id: int):
    """Get user's game play history (how many times they played each game)"""
    play_counts = db.query(
        StudySession.game_id,
        func.count(StudySession.id).label('play_count')
    ).filter(
        StudySession.user_id == user_id,
        StudySession.game_id.isnot(None)
    ).group_by(
        StudySession.game_id
    ).all()

    return [{"game_id": pc.game_id, "play_count": pc.play_count} for pc in play_counts]


def get_all_active_games(db: Session) -> List[Game]:
    """Get all active games"""
    return db.query(Game).filter(Game.is_active == True).all()


async def call_ml_service(user_play_history: list, all_games: list, limit: int):
    """
    Call internal ML service to get recommendations.

    This is an INTERNAL call - ML service is NOT exposed to public internet.
    Communication happens within AWS VPC using private networking.
    """
    # Prepare payload for ML service
    payload = {
        "user_play_history": user_play_history,
        "all_games": [
            {
                "id": g.id,
                "category": g.category,
                "difficulty": g.difficulty,
                "estimated_time": g.estimated_time,
                "xp_reward": g.xp_reward,
                "rating": float(g.rating),
                "likes": g.likes,
                "title": g.title
            }
            for g in all_games
        ],
        "limit": limit
    }

    # Call internal ML service
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{ML_SERVICE_URL}/recommend",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=503,
                detail=f"ML service unavailable: {str(e)}"
            )


# ===== PUBLIC API ENDPOINTS =====

@router.get("/similar", response_model=List[GameResponse])
async def get_similar_games(
    limit: int = Query(default=6, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get game recommendations based on what you've played before.

    **How it works:**
    - Analyzes games you've played and enjoyed
    - Finds other games with similar attributes (category, difficulty, duration)
    - Returns games you haven't played yet that match your preferences

    **Example:**
    If you've played:
    - "Algebra Quiz" (Math, Medium, 15 min)
    - "Geometry Challenge" (Math, Hard, 20 min)

    You might get:
    - "Calculus Practice" (Math, Hard, 18 min) ← Similar category & difficulty
    - "Math Word Problems" (Math, Medium, 15 min) ← Similar category & duration

    **Parameters:**
    - limit: Number of recommendations (1-20, default 6)

    **Returns:**
    List of recommended games with full details
    """
    # Get data from database
    play_history = get_user_play_history(db, current_user.id)
    all_games = get_all_active_games(db)

    # Call internal ML service (not exposed to public)
    ml_response = await call_ml_service(play_history, all_games, limit)

    # Get recommended games by ID
    recommended_game_ids = ml_response["game_ids"]
    games = db.query(Game).filter(Game.id.in_(recommended_game_ids)).all()

    # Preserve order from ML service
    game_dict = {g.id: g for g in games}
    ordered_games = [game_dict[gid] for gid in recommended_game_ids if gid in game_dict]

    return [GameResponse.from_db_model(g) for g in ordered_games]


@router.get("/similar/explained", response_model=List[dict])
async def get_similar_games_with_explanation(
    limit: int = Query(default=6, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recommendations WITH explanations of why each was recommended.

    **Returns:**
    ```json
    [
        {
            "game": { ... game details ... },
            "reason": "Similar to Algebra Quiz (same category: Math)",
            "similarity_score": 0.87
        },
        ...
    ]
    ```

    Useful for showing users WHY you're recommending each game.
    """
    # Get data from database
    play_history = get_user_play_history(db, current_user.id)
    all_games = get_all_active_games(db)

    # Call internal ML service
    ml_response = await call_ml_service(play_history, all_games, limit)

    # Get recommended games
    recommended_game_ids = ml_response["game_ids"]
    scores = ml_response["scores"]
    explanations = ml_response["explanations"]

    games = db.query(Game).filter(Game.id.in_(recommended_game_ids)).all()
    game_dict = {g.id: g for g in games}

    # Build response with explanations
    results = []
    for i, game_id in enumerate(recommended_game_ids):
        if game_id in game_dict:
            results.append({
                "game": GameResponse.from_db_model(game_dict[game_id]),
                "reason": explanations[i],
                "similarity_score": scores[i]
            })

    return results


@router.get("/favorites", response_model=List[GameResponse])
async def get_user_favorite_games(
    limit: int = Query(default=5, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the games this user has played most (their favorites).

    Useful for:
    - Showing "Your favorite games" section
    - Understanding user preferences
    - Debugging recommendations

    **Returns:**
    Games ordered by number of times played (most played first)
    """
    # Get play counts
    play_counts = db.query(
        StudySession.game_id,
        func.count(StudySession.id).label('play_count')
    ).filter(
        StudySession.user_id == current_user.id,
        StudySession.game_id.isnot(None)
    ).group_by(
        StudySession.game_id
    ).order_by(
        func.count(StudySession.id).desc()
    ).limit(limit).all()

    if not play_counts:
        return []

    # Get games
    game_ids = [pc.game_id for pc in play_counts]
    games = db.query(Game).filter(Game.id.in_(game_ids)).all()

    # Preserve order by play count
    game_dict = {g.id: g for g in games}
    ordered_games = [game_dict[pc.game_id] for pc in play_counts if pc.game_id in game_dict]

    return [GameResponse.from_db_model(g) for g in ordered_games]


@router.get("/health")
async def health_check():
    """Check if ML service is reachable"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ML_SERVICE_URL}/health")
            response.raise_for_status()
            return {
                "status": "healthy",
                "ml_service": response.json()
            }
    except Exception as e:
        return {
            "status": "degraded",
            "ml_service": "unavailable",
            "error": str(e)
        }
