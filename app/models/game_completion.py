"""
Game Completion database model for tracking user progress through educational games.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.models.study_session import GUID


class GameCompletion(Base):
    """Track completion of educational games linked to study topics."""

    __tablename__ = "game_completions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    game_type = Column(String, nullable=False)  # 'memory_match', 'true_false', 'word_scramble', etc.

    # Game completion details
    completed = Column(Boolean, default=False)
    score = Column(Integer, nullable=True)  # Score achieved (0-100)
    time_spent = Column(Integer, nullable=True)  # Time spent in seconds
    attempts = Column(Integer, default=0)  # Number of attempts

    # Game-specific data (flexible JSON field for different game types)
    game_data = Column(JSON, nullable=True)  # Stores game-specific results

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="game_completions")
    topic = relationship("Topic", backref="game_completions")

    def __repr__(self):
        return f"<GameCompletion(id={self.id}, user_id={self.user_id}, topic_id={self.topic_id}, game_type={self.game_type}, completed={self.completed})>"
