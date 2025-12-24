"""
Folder Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class FolderBase(BaseModel):
    """Base folder schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#3B82F6", pattern="^#[0-9A-Fa-f]{6}$")
    icon: str = Field(default="📁", max_length=10)


class FolderCreate(FolderBase):
    """Schema for creating a new folder."""
    pass


class FolderUpdate(BaseModel):
    """Schema for updating a folder."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=10)
    is_archived: Optional[bool] = None


class FolderResponse(BaseModel):
    """Schema for folder response."""
    id: int
    name: str
    color: str
    icon: str
    is_archived: bool
    created_at: datetime
    session_count: int = 0  # Number of sessions in this folder

    class Config:
        from_attributes = True

    @classmethod
    def from_db_model(cls, folder, session_count: int = 0):
        """Create response from database model."""
        return cls(
            id=folder.id,
            name=folder.name,
            color=folder.color,
            icon=folder.icon,
            is_archived=folder.is_archived,
            created_at=folder.created_at,
            session_count=session_count,
        )
