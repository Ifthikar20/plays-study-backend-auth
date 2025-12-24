"""
User Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    """Schema for user profile data."""
    id: str  # Convert to string for frontend
    email: str
    name: str
    xp: int
    level: int

    class Config:
        from_attributes = True

    @classmethod
    def from_db_model(cls, user):
        """Create response from database model."""
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            xp=user.xp,
            level=user.level,
        )


class UserStats(BaseModel):
    """Schema for user statistics - matches frontend interface."""
    totalSessions: int
    averageAccuracy: int  # Rounded percentage
    questionsAnswered: int
    totalStudyTime: str  # Formatted as "18hrs" or "2.5hrs"

    @classmethod
    def from_calculations(cls, total_sessions: int, avg_accuracy: float,
                         questions_answered: int, total_time_seconds: int):
        """Create stats from calculated values with proper formatting."""
        # Format total study time
        hours = total_time_seconds / 3600
        if hours < 1:
            time_str = f"{int(hours * 60)}min"
        elif hours == int(hours):
            time_str = f"{int(hours)}hrs"
        else:
            time_str = f"{hours:.1f}hrs"

        return cls(
            totalSessions=total_sessions,
            averageAccuracy=round(avg_accuracy),
            questionsAnswered=questions_answered,
            totalStudyTime=time_str,
        )


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Schema for token payload data."""
    user_id: Optional[int] = None
    email: Optional[str] = None
