"""
Study Session Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class StudySessionBase(BaseModel):
    """Base study session schema."""
    title: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=1, max_length=200)
    duration: int = Field(..., ge=0)  # in seconds
    progress: int = Field(default=0, ge=0, le=100)
    topics_count: int = Field(default=0, ge=0)
    game_id: Optional[int] = None
    accuracy: Optional[int] = Field(None, ge=0, le=100)
    has_full_study: bool = Field(default=True)
    has_speed_run: bool = Field(default=True)
    has_quiz: bool = Field(default=True)


class StudySessionCreate(StudySessionBase):
    """Schema for creating a study session."""
    pass


class StudySessionUpdate(BaseModel):
    """Schema for updating a study session."""
    duration: int | None = Field(None, ge=0)
    accuracy: int | None = Field(None, ge=0, le=100)
    status: str | None = None
    is_completed: bool | None = None
    completed_at: datetime | None = None


class StudySessionResponse(BaseModel):
    """Schema for study session response - matches frontend interface."""
    id: str  # Convert to string for frontend
    title: str
    progress: int
    topics: int  # Alias for topics_count
    time: str  # Formatted time string
    hasFullStudy: bool
    hasSpeedRun: bool
    hasQuiz: bool
    folderId: Optional[int] = None  # Folder organization
    createdAt: Optional[int] = None  # Unix timestamp in milliseconds for NEW badge
    extractedTopics: list = []  # Full topic hierarchy with questions

    class Config:
        from_attributes = True

    @classmethod
    def from_db_model(cls, session: "StudySession", db=None):
        """Create response from database model with proper formatting."""
        from datetime import datetime, timezone

        # Calculate time difference
        now = datetime.now(timezone.utc)
        created = session.created_at.replace(tzinfo=timezone.utc) if session.created_at.tzinfo is None else session.created_at
        diff = now - created

        # Format time string
        if diff.days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                time_str = "Just now"
            elif hours == 1:
                time_str = "1 hour ago"
            else:
                time_str = f"{hours} hours ago"
        elif diff.days == 1:
            time_str = "Yesterday"
        else:
            time_str = f"{diff.days} days ago"

        # Build topic hierarchy if db session is provided
        extracted_topics = []
        if db:
            from app.api.study_sessions import build_topic_hierarchy
            extracted_topics = build_topic_hierarchy(session, db)

        return cls(
            id=str(session.id),
            title=session.title,
            progress=session.progress,
            topics=session.topics_count,
            time=time_str,
            hasFullStudy=session.has_full_study,
            hasSpeedRun=session.has_speed_run,
            hasQuiz=session.has_quiz,
            folderId=session.folder_id,
            createdAt=int(session.created_at.timestamp() * 1000) if session.created_at else None,
            extractedTopics=extracted_topics,
        )
