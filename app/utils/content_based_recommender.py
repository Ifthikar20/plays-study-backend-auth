"""
Content-Based Game Recommender
Finds games similar to what user has played before
"""

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Tuple
from app.models.game import Game
from app.models.study_session import StudySession


class ContentBasedRecommender:
    """
    Recommends games based on similarity to user's play history.

    How it works:
    1. Get games user played and liked (completed/high score)
    2. Create feature vectors for all games
    3. Find games most similar to user's favorites
    4. Recommend the most similar ones they haven't played
    """

    def __init__(self, db: Session):
        self.db = db
        self.scaler = StandardScaler()

    def create_game_features(self, games: List[Game]) -> Tuple[np.ndarray, dict, dict]:
        """
        Convert game attributes into numerical feature vectors.

        Features used:
        - difficulty (easy=1, medium=2, hard=3)
        - estimated_time (normalized)
        - xp_reward (normalized)
        - rating (0-5)
        - likes (normalized)
        - category (one-hot encoded)

        Returns:
            - Feature matrix (numpy array)
            - Difficulty mapping
            - Category mapping
        """
        # Create mappings
        difficulty_map = {'easy': 1, 'medium': 2, 'hard': 3}
        categories = list(set(g.category for g in games))
        category_map = {cat: i for i, cat in enumerate(categories)}

        features = []
        for game in games:
            feature_vector = [
                difficulty_map.get(game.difficulty.lower(), 2),  # Default to medium
                game.estimated_time,
                game.xp_reward,
                game.rating,
                game.likes,
                category_map.get(game.category, 0)
            ]
            features.append(feature_vector)

        # Normalize features so they're on same scale
        feature_matrix = self.scaler.fit_transform(np.array(features))

        return feature_matrix, difficulty_map, category_map

    def get_user_favorite_games(self, user_id: int, limit: int = 5) -> List[Game]:
        """
        Get games user played and likely enjoyed.

        Criteria for "favorite":
        - Completed the session (or spent significant time)
        - Played multiple times
        - Recent plays
        """
        # Get games with play statistics
        favorite_game_ids = self.db.query(
            StudySession.game_id,
            func.count(StudySession.id).label('play_count'),
            func.max(StudySession.completed_at).label('last_played')
        )\
            .filter(StudySession.user_id == user_id)\
            .filter(StudySession.game_id.isnot(None))\
            .group_by(StudySession.game_id)\
            .order_by(
                desc('play_count'),  # Played multiple times = liked it
                desc('last_played')  # Recent plays
            )\
            .limit(limit)\
            .all()

        if not favorite_game_ids:
            return []

        game_ids = [g[0] for g in favorite_game_ids]

        # Fetch the actual game objects
        favorites = self.db.query(Game)\
            .filter(Game.id.in_(game_ids))\
            .all()

        return favorites

    def calculate_similarity_scores(
        self,
        target_games: List[Game],
        all_games: List[Game],
        feature_matrix: np.ndarray
    ) -> List[Tuple[Game, float]]:
        """
        Calculate how similar each game is to user's favorites.

        Returns list of (game, similarity_score) tuples
        """
        game_ids = [g.id for g in all_games]

        # Get indices of target games
        target_indices = []
        for target in target_games:
            try:
                idx = game_ids.index(target.id)
                target_indices.append(idx)
            except ValueError:
                continue

        if not target_indices:
            return []

        # Calculate similarity between each game and user's favorites
        target_features = feature_matrix[target_indices]

        # Average similarity to all favorites
        similarities = cosine_similarity(feature_matrix, target_features)
        avg_similarities = similarities.mean(axis=1)

        # Create (game, score) pairs
        game_scores = list(zip(all_games, avg_similarities))

        return game_scores

    def recommend_similar_games(
        self,
        user_id: int,
        limit: int = 6
    ) -> List[Game]:
        """
        Main recommendation function.

        Process:
        1. Get user's favorite games
        2. Get all available games
        3. Calculate similarity scores
        4. Return top N most similar (excluding already played)

        Example:
            User played:
            - "Algebra Quiz" (Math, Medium, 4.5★)
            - "Geometry Challenge" (Math, Hard, 4.3★)

            System finds similar:
            - "Calculus Practice" (Math, Hard, 4.6★) ← Similar category + difficulty
            - "Math Word Problems" (Math, Medium, 4.4★) ← Similar category
            - "Physics Equations" (Science, Hard, 4.5★) ← Similar difficulty + complexity
        """
        # Get user's favorite games (what they played/liked)
        favorites = self.get_user_favorite_games(user_id, limit=5)

        if not favorites:
            # New user - fall back to popular games
            return self.db.query(Game)\
                .filter(Game.is_active == True)\
                .order_by(desc(Game.rating), desc(Game.likes))\
                .limit(limit)\
                .all()

        # Get games user already played
        played_game_ids = [
            g[0] for g in self.db.query(StudySession.game_id)
            .filter(StudySession.user_id == user_id)
            .filter(StudySession.game_id.isnot(None))
            .distinct()
        ]

        # Get all active games
        all_games = self.db.query(Game)\
            .filter(Game.is_active == True)\
            .all()

        if len(all_games) < 2:
            return all_games

        # Create feature vectors for all games
        feature_matrix, _, _ = self.create_game_features(all_games)

        # Calculate similarity scores
        game_scores = self.calculate_similarity_scores(
            favorites,
            all_games,
            feature_matrix
        )

        # Filter out already played games and sort by similarity
        recommendations = [
            game for game, score in sorted(game_scores, key=lambda x: x[1], reverse=True)
            if game.id not in played_game_ids
        ]

        return recommendations[:limit]

    def explain_recommendation(
        self,
        recommended_game: Game,
        user_favorites: List[Game]
    ) -> str:
        """
        Explain WHY a game was recommended.
        Useful for showing users: "Because you played X, we recommend Y"

        Returns a human-readable explanation.
        """
        # Find which favorite it's most similar to
        reasons = []

        # Check category match
        matching_categories = [f for f in user_favorites if f.category == recommended_game.category]
        if matching_categories:
            reasons.append(f"Similar to {matching_categories[0].title} (same category: {recommended_game.category})")

        # Check difficulty match
        matching_difficulty = [f for f in user_favorites if f.difficulty == recommended_game.difficulty]
        if matching_difficulty:
            reasons.append(f"Matches your preferred difficulty: {recommended_game.difficulty}")

        # Check time match
        avg_time = sum(f.estimated_time for f in user_favorites) / len(user_favorites)
        if abs(recommended_game.estimated_time - avg_time) < 5:
            reasons.append(f"Similar duration to games you enjoy (~{recommended_game.estimated_time} min)")

        if not reasons:
            reasons.append(f"Highly rated game in a related category")

        return " • ".join(reasons)


def get_similar_game_recommendations(
    db: Session,
    user_id: int,
    limit: int = 6
) -> List[Game]:
    """
    Convenience function for easy API integration.

    Usage in API:
        from app.utils.content_based_recommender import get_similar_game_recommendations

        @router.get("/recommendations/similar")
        def get_similar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
            return get_similar_game_recommendations(db, user.id)
    """
    recommender = ContentBasedRecommender(db)
    return recommender.recommend_similar_games(user_id, limit)
