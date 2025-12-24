"""
Study Session database model.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available, otherwise uses
    CHAR(36) to store UUID as a string.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


class StudySession(Base):
    """Study session model for tracking user study activity."""

    __tablename__ = "study_sessions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="SET NULL"), nullable=True)
    folder_id = Column(Integer, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)  # Folder organization
    title = Column(String, nullable=False)  # Study session title
    topic = Column(String, nullable=False)
    study_content = Column(Text, nullable=True)  # Extracted text content
    file_content = Column(Text, nullable=True)  # Original uploaded file (base64)
    file_type = Column(String, nullable=True)  # File type: pdf, pptx, docx, txt
    pdf_content = Column(Text, nullable=True)  # Converted PDF for PPTX files (base64)
    duration = Column(Integer, nullable=False, default=0)  # in seconds
    progress = Column(Integer, default=0)  # percentage 0-100
    topics_count = Column(Integer, default=0)  # Number of topics in session
    xp_earned = Column(Integer, default=0)
    accuracy = Column(Integer, nullable=True)  # percentage 0-100
    status = Column(String, default="in_progress")  # completed, in_progress, abandoned
    is_completed = Column(Boolean, default=False)
    has_full_study = Column(Boolean, default=False)
    has_speed_run = Column(Boolean, default=False)
    has_quiz = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="study_sessions")
    folder = relationship("Folder", back_populates="study_sessions")
    topics = relationship("Topic", back_populates="study_session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StudySession(id={self.id}, user_id={self.user_id}, topic={self.topic})>"
