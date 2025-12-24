"""
Folder API endpoints for organizing study sessions.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import logging
import uuid

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.models.folder import Folder
from app.models.study_session import StudySession
from app.schemas.folder import FolderCreate, FolderUpdate, FolderResponse
from app.core.rate_limit import limiter
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/folders", response_model=List[FolderResponse])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_folders(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all folders for the current user.

    Returns folders with session counts.
    """
    logger.info(f"📁 Getting folders for user {current_user.id}")

    # Get all folders for user with session counts in a single optimized query
    # Query 1: Get folder IDs and session counts using aggregate
    session_counts_subquery = db.query(
        StudySession.folder_id,
        func.count(StudySession.id).label('session_count')
    ).group_by(StudySession.folder_id).subquery()

    # Query 2: Get folders with their session counts
    folders_with_counts = db.query(
        Folder,
        func.coalesce(session_counts_subquery.c.session_count, 0).label('session_count')
    ).outerjoin(
        session_counts_subquery,
        Folder.id == session_counts_subquery.c.folder_id
    ).filter(
        Folder.user_id == current_user.id,
        Folder.is_archived == False
    ).order_by(Folder.created_at.desc()).all()

    # Build response objects
    folder_responses = [
        FolderResponse.from_db_model(folder, session_count=session_count)
        for folder, session_count in folders_with_counts
    ]

    logger.info(f"📁 Found {len(folder_responses)} folders")
    return folder_responses


@router.post("/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_folder(
    request: Request,
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new folder for organizing study sessions.
    """
    logger.info(f"📁 Creating folder '{folder_data.name}' for user {current_user.id}")

    # Check if folder name already exists for this user
    existing = db.query(Folder).filter(
        Folder.user_id == current_user.id,
        Folder.name == folder_data.name,
        Folder.is_archived == False
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A folder with this name already exists"
        )

    # Create new folder
    new_folder = Folder(
        name=folder_data.name,
        color=folder_data.color,
        icon=folder_data.icon,
        user_id=current_user.id
    )

    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)

    logger.info(f"📁 Created folder {new_folder.id}")
    return FolderResponse.from_db_model(new_folder, session_count=0)


@router.put("/folders/{folder_id}", response_model=FolderResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def update_folder(
    request: Request,
    folder_id: int,
    folder_data: FolderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update a folder's properties.
    """
    logger.info(f"📁 Updating folder {folder_id}")

    # Get folder
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == current_user.id
    ).first()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )

    # Update fields
    if folder_data.name is not None:
        # Check for name conflicts
        existing = db.query(Folder).filter(
            Folder.user_id == current_user.id,
            Folder.name == folder_data.name,
            Folder.id != folder_id,
            Folder.is_archived == False
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A folder with this name already exists"
            )
        folder.name = folder_data.name

    if folder_data.color is not None:
        folder.color = folder_data.color

    if folder_data.icon is not None:
        folder.icon = folder_data.icon

    if folder_data.is_archived is not None:
        folder.is_archived = folder_data.is_archived

    db.commit()
    db.refresh(folder)

    # Get session count efficiently (reuse the same pattern as get_folders)
    session_count = db.query(func.count(StudySession.id)).filter(
        StudySession.folder_id == folder.id
    ).scalar() or 0

    logger.info(f"📁 Updated folder {folder_id}")
    return FolderResponse.from_db_model(folder, session_count=session_count)


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def delete_folder(
    request: Request,
    folder_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a folder. Study sessions in the folder will be moved to root (no folder).
    """
    logger.info(f"📁 Deleting folder {folder_id}")

    # Get folder
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == current_user.id
    ).first()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )

    # Move all sessions to root (no folder)
    db.query(StudySession).filter(
        StudySession.folder_id == folder_id
    ).update({StudySession.folder_id: None})

    # Delete folder
    db.delete(folder)
    db.commit()

    logger.info(f"📁 Deleted folder {folder_id}")
    return None


@router.post("/folders/{folder_id}/sessions/{session_id}", status_code=status.HTTP_200_OK)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def move_session_to_folder(
    request: Request,
    folder_id: int,
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Move a study session into a folder.
    """
    logger.info(f"📁 Moving session {session_id} to folder {folder_id}")

    # Validate UUID format
    try:
        uuid_obj = uuid.UUID(session_id)
    except ValueError:
        logger.error(f"❌ Invalid session ID format: {session_id} (expected UUID)")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid session ID format. Expected UUID, got: '{session_id}'."
        )

    # Verify folder exists and belongs to user
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == current_user.id
    ).first()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )

    # Verify session exists and belongs to user
    session = db.query(StudySession).filter(
        StudySession.id == uuid_obj,
        StudySession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found"
        )

    # Move session to folder
    session.folder_id = folder_id
    db.commit()

    logger.info(f"📁 Moved session {session_id} to folder {folder_id}")
    return {"success": True}


@router.delete("/folders/{folder_id}/sessions/{session_id}", status_code=status.HTTP_200_OK)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def remove_session_from_folder(
    request: Request,
    folder_id: int,
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Remove a study session from a folder (move to root).
    """
    logger.info(f"📁 Removing session {session_id} from folder {folder_id}")

    # Validate UUID format
    try:
        uuid_obj = uuid.UUID(session_id)
    except ValueError:
        logger.error(f"❌ Invalid session ID format: {session_id} (expected UUID)")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid session ID format. Expected UUID, got: '{session_id}'."
        )

    # Verify session exists and belongs to user
    session = db.query(StudySession).filter(
        StudySession.id == uuid_obj,
        StudySession.user_id == current_user.id,
        StudySession.folder_id == folder_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study session not found in this folder"
        )

    # Remove from folder
    session.folder_id = None
    db.commit()

    logger.info(f"📁 Removed session {session_id} from folder")
    return {"success": True}
