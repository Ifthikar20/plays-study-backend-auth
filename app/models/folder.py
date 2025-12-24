"""
Folder database model for organizing study sessions.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Folder(Base):
    """Folder model for organizing study sessions."""

    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    color = Column(String, default="#3B82F6")  # Hex color code for folder
    icon = Column(String, default="📁")  # Emoji icon
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="folders")
    study_sessions = relationship("StudySession", back_populates="folder", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Folder(id={self.id}, name={self.name}, user_id={self.user_id})>"
