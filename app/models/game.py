"""
Game database model.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime
from app.database import Base


class Game(Base):
    """Game model for available study games."""

    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    image = Column(String, nullable=False)  # URL to game image
    category = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)  # easy, medium, hard
    likes = Column(Integer, default=0)  # Number of likes
    rating = Column(Integer, default=0)  # Rating out of 5
    estimated_time = Column(Integer, nullable=False)  # in minutes
    xp_reward = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Game(id={self.id}, title={self.title}, category={self.category})>"
