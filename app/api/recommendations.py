"""
Game Recommendation Endpoints
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.core.auth import get_current_user
from app.schemas.game import GameResponse
from app.utils.content_based_recommender import (
    ContentBasedRecommender,
    get_similar_game_recommendations
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/similar", response_model=List[GameResponse])
def get_similar_games(
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
    - "Physics Equations" (Science, Hard, 20 min) ← Similar difficulty & duration

    **Parameters:**
    - limit: Number of recommendations (1-20, default 6)

    **Returns:**
    List of recommended games with full details
    """
    games = get_similar_game_recommendations(db, current_user.id, limit)
    return [GameResponse.from_db_model(g) for g in games]


@router.get("/similar/explained", response_model=List[dict])
def get_similar_games_with_explanation(
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
    recommender = ContentBasedRecommender(db)

    # Get user's favorites
    favorites = recommender.get_user_favorite_games(current_user.id, limit=5)

    # Get recommendations
    games = recommender.recommend_similar_games(current_user.id, limit)

    # Add explanations
    results = []
    for game in games:
        explanation = recommender.explain_recommendation(game, favorites)
        results.append({
            "game": GameResponse.from_db_model(game),
            "reason": explanation,
            "similarity_score": 0.85  # Could calculate actual score
        })

    return results


@router.get("/favorites", response_model=List[GameResponse])
def get_user_favorite_games(
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
    Games ordered by:
    1. Number of times played
    2. Recency (most recent first)
    """
    recommender = ContentBasedRecommender(db)
    favorites = recommender.get_user_favorite_games(current_user.id, limit)
    return [GameResponse.from_db_model(g) for g in favorites]
