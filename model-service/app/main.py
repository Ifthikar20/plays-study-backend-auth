"""
Internal ML Recommendation Service
This service is NOT exposed to the public - only accessible from the main FastAPI app via internal networking.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI(
    title="PlayStudy ML Service",
    description="Internal recommendation engine - not public facing",
    version="1.0.0"
)

# Health check for ECS
@app.get("/health")
def health_check():
    """ECS health check endpoint"""
    return {"status": "healthy", "service": "ml-recommendation"}


# ===== REQUEST/RESPONSE MODELS =====

class GameFeature(BaseModel):
    """Game with features for ML processing"""
    id: int
    category: str
    difficulty: str  # easy, medium, hard
    estimated_time: int
    xp_reward: int
    rating: float
    likes: int
    title: str


class UserPlayHistory(BaseModel):
    """User's game play history"""
    game_id: int
    play_count: int


class RecommendationRequest(BaseModel):
    """Request payload from main app"""
    user_play_history: List[UserPlayHistory]
    all_games: List[GameFeature]
    limit: int = 6


class RecommendationResponse(BaseModel):
    """Response payload to main app"""
    game_ids: List[int]
    scores: List[float]
    explanations: List[str]


# ===== ML LOGIC =====

class ContentBasedRecommender:
    """
    Content-based recommendation using cosine similarity.
    Runs in isolation from main app.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self.difficulty_map = {'easy': 1, 'medium': 2, 'hard': 3}

    def create_feature_vectors(self, games: List[GameFeature]) -> np.ndarray:
        """
        Convert game attributes to numerical feature vectors.

        Features:
        - difficulty (1=easy, 2=medium, 3=hard)
        - estimated_time (normalized)
        - xp_reward (normalized)
        - rating (0-5)
        - likes (normalized)
        - category (one-hot encoded)
        """
        # Get unique categories
        categories = list(set(g.category for g in games))
        category_map = {cat: i for i, cat in enumerate(categories)}

        # Build feature matrix
        features = []
        for game in games:
            feature_vector = [
                self.difficulty_map.get(game.difficulty.lower(), 2),
                game.estimated_time,
                game.xp_reward,
                game.rating,
                game.likes,
                category_map.get(game.category, 0)
            ]
            features.append(feature_vector)

        # Normalize features
        feature_matrix = self.scaler.fit_transform(np.array(features))
        return feature_matrix, category_map

    def get_favorite_games(self, play_history: List[UserPlayHistory], min_plays: int = 2) -> List[int]:
        """
        Identify user's favorite games (played multiple times).
        """
        favorites = [
            ph.game_id for ph in play_history
            if ph.play_count >= min_plays
        ]
        return favorites if favorites else [ph.game_id for ph in play_history[:3]]

    def recommend(
        self,
        play_history: List[UserPlayHistory],
        all_games: List[GameFeature],
        limit: int = 6
    ) -> tuple[List[int], List[float], List[str]]:
        """
        Generate recommendations based on similarity to user's favorites.

        Returns:
            (game_ids, similarity_scores, explanations)
        """
        if not play_history or len(all_games) < 2:
            # Not enough data - return popular games
            sorted_games = sorted(all_games, key=lambda g: (g.rating, g.likes), reverse=True)
            return (
                [g.id for g in sorted_games[:limit]],
                [0.0] * limit,
                ["Popular game"] * limit
            )

        # Create feature vectors
        feature_matrix, category_map = self.create_feature_vectors(all_games)

        # Find user's favorite games
        favorite_game_ids = self.get_favorite_games(play_history)
        played_game_ids = [ph.game_id for ph in play_history]

        # Map game IDs to indices
        game_id_to_idx = {g.id: i for i, g in enumerate(all_games)}

        # Get indices of favorite games
        favorite_indices = [
            game_id_to_idx[gid] for gid in favorite_game_ids
            if gid in game_id_to_idx
        ]

        if not favorite_indices:
            # Fallback to popular games
            sorted_games = sorted(all_games, key=lambda g: (g.rating, g.likes), reverse=True)
            unplayed = [g for g in sorted_games if g.id not in played_game_ids]
            return (
                [g.id for g in unplayed[:limit]],
                [0.0] * limit,
                ["Popular game"] * limit
            )

        # Calculate average feature vector of favorites
        favorite_vectors = feature_matrix[favorite_indices]
        avg_favorite_vector = np.mean(favorite_vectors, axis=0).reshape(1, -1)

        # Calculate similarity to all games
        similarities = cosine_similarity(avg_favorite_vector, feature_matrix)[0]

        # Get recommendations (exclude already played)
        recommendations = []
        for idx, similarity_score in enumerate(similarities):
            game = all_games[idx]
            if game.id not in played_game_ids:
                # Generate explanation
                favorite_game = all_games[favorite_indices[0]]
                explanation = self._explain_recommendation(game, favorite_game)

                recommendations.append({
                    'game_id': game.id,
                    'score': float(similarity_score),
                    'explanation': explanation
                })

        # Sort by similarity score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        recommendations = recommendations[:limit]

        # Extract parallel arrays
        game_ids = [r['game_id'] for r in recommendations]
        scores = [r['score'] for r in recommendations]
        explanations = [r['explanation'] for r in recommendations]

        return game_ids, scores, explanations

    def _explain_recommendation(self, recommended_game: GameFeature, favorite_game: GameFeature) -> str:
        """Generate human-readable explanation"""
        reasons = []

        if recommended_game.category == favorite_game.category:
            reasons.append(f"same category: {recommended_game.category}")

        if recommended_game.difficulty == favorite_game.difficulty:
            reasons.append(f"same difficulty: {recommended_game.difficulty}")

        if reasons:
            return f"Similar to {favorite_game.title} ({', '.join(reasons)})"
        else:
            return f"Similar to {favorite_game.title}"


# ===== API ENDPOINTS (Internal Only) =====

recommender = ContentBasedRecommender()


@app.post("/recommend", response_model=RecommendationResponse)
def get_recommendations(request: RecommendationRequest):
    """
    Generate game recommendations.

    **INTERNAL ONLY** - Called by main FastAPI app, not by frontend.
    """
    try:
        game_ids, scores, explanations = recommender.recommend(
            play_history=request.user_play_history,
            all_games=request.all_games,
            limit=request.limit
        )

        return RecommendationResponse(
            game_ids=game_ids,
            scores=scores,
            explanations=explanations
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")


@app.get("/")
def root():
    """Service info"""
    return {
        "service": "PlayStudy ML Recommendation Service",
        "status": "running",
        "note": "This service is internal only - not exposed to public internet"
    }
