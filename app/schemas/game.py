"""
Game Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime


class GameBase(BaseModel):
    """Base game schema with common fields."""
    title: str = Field(..., min_length=1, max_length=200)
    description: str
    image: str  # URL to game image
    category: str
    difficulty: str  # Easy, Medium, or Hard
    likes: int = Field(default=0, ge=0)
    rating: float = Field(default=0.0, ge=0, le=5)  # Rating out of 5
    estimated_time: int = Field(..., gt=0)  # in minutes
    xp_reward: int = Field(..., ge=0)


class GameCreate(GameBase):
    """Schema for creating a new game."""
    pass


class GameUpdate(BaseModel):
    """Schema for updating a game."""
    title: str | None = None
    description: str | None = None
    image: str | None = None
    category: str | None = None
    difficulty: str | None = None
    likes: int | None = None
    rating: float | None = None
    estimated_time: int | None = None
    xp_reward: int | None = None
    is_active: bool | None = None


class GameResponse(BaseModel):
    """Schema for game response - matches frontend interface."""
    id: int
    title: str
    description: str
    category: str
    likes: int
    rating: float
    image: str
    difficulty: str
    questionCount: int  # For frontend compatibility
    points: int  # For frontend compatibility (same as xp_reward)

    class Config:
        from_attributes = True

    @classmethod
    def from_db_model(cls, game):
        """Create response from database model."""
        # Capitalize difficulty for frontend display
        difficulty_display = game.difficulty.capitalize() if game.difficulty else "Medium"

        return cls(
            id=game.id,
            title=game.title,
            description=game.description,
            category=game.category,
            likes=game.likes,
            rating=float(game.rating),
            image=game.image,
            difficulty=difficulty_display,
            questionCount=10,  # Default question count
            points=game.xp_reward,  # Use xp_reward as points
        )
