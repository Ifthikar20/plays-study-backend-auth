"""
Main consolidated API endpoint for app data.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from app.database import get_db
from app.dependencies import get_current_active_user
from app.schemas.app_data import AppDataResponse
from app.schemas.user import UserProfile, UserStats
from app.schemas.game import GameResponse
from app.schemas.study_session import StudySessionResponse
from app.schemas.folder import FolderResponse
from app.models.user import User
from app.models.game import Game
from app.models.study_session import StudySession
from app.models.topic import Topic
from app.models.folder import Folder
from app.models.question import Question
from app.core.cache import get_cache, set_cache
from app.core.rate_limit import limiter
from app.config import settings
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/app-data", response_model=AppDataResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_app_data(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all application data in a single consolidated request.

    This endpoint returns:
    - All available games
    - User's study sessions
    - User profile data
    - User statistics

    The response is cached for 5 minutes to improve performance.

    Args:
        request: FastAPI request object (required for rate limiting)
        current_user: The authenticated user
        db: Database session

    Returns:
        AppDataResponse containing all application data

    Rate Limits:
        - 30 requests per minute per user
        - 1000 requests per hour globally
    """
    logger.info(f"📊 app-data request for user: {current_user.email} (ID: {current_user.id})")

    # Check cache first
    cache_key = f"app_data:{current_user.id}"
    cached_data = get_cache(cache_key)

    if cached_data:
        logger.debug(f"📊 Returning cached data for user {current_user.id}")
        return cached_data

    logger.debug(f"📊 No cache, fetching fresh data for user {current_user.id}")

    # OPTIMIZED: Query 1 - Fetch all games (active only)
    games = db.query(Game).filter(Game.is_active == True).all()
    logger.debug(f"📊 Found {len(games)} active games")

    # OPTIMIZED: Query 2 - Get folder session counts with a single aggregated query
    session_counts_subquery = db.query(
        StudySession.folder_id,
        func.count(StudySession.id).label('session_count')
    ).filter(
        StudySession.user_id == current_user.id
    ).group_by(StudySession.folder_id).subquery()

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
    logger.debug(f"📊 Found {len(folders_with_counts)} folders")

    # OPTIMIZED: Query 3 - Fetch study sessions with eager-loaded topics and questions
    # This single query replaces 1 + N + M queries (where N=sessions, M=topics)
    study_sessions = (
        db.query(StudySession)
        .options(
            selectinload(StudySession.topics).selectinload(Topic.questions)
        )
        .filter(StudySession.user_id == current_user.id)
        .order_by(StudySession.created_at.desc())
        .all()
    )
    logger.debug(f"📊 Found {len(study_sessions)} study sessions for user {current_user.id}")

    # Fix generic session titles using pre-loaded topic data (no additional queries)
    sessions_to_update = []
    for session in study_sessions:
        # Check if this is a generic title (contains "Study Session" and digits)
        if "Study Session" in session.title and any(char.isdigit() for char in session.title):
            # Use pre-loaded topics (no database query needed!)
            categories = [t for t in session.topics if t.is_category and t.parent_topic_id is None]
            categories.sort(key=lambda t: t.order_index or 0)

            if categories:
                first_topic = categories[0]
                total_categories = len(categories)

                # Generate meaningful title
                if total_categories > 1:
                    session.title = f"{first_topic.title} + {total_categories - 1} more"
                else:
                    session.title = first_topic.title

                sessions_to_update.append(session)
                logger.debug(f"📝 Updated session {session.id} title to: {session.title}")

    # Batch commit all title updates if any
    if sessions_to_update:
        db.commit()
        logger.debug(f"📝 Committed {len(sessions_to_update)} session title updates")

    # Build user profile using custom method
    user_profile = UserProfile.from_db_model(current_user)

    # Calculate user statistics
    total_sessions = len(study_sessions)
    total_study_time = sum(session.duration for session in study_sessions)

    # Calculate average accuracy (only from sessions with accuracy data)
    sessions_with_accuracy = [s for s in study_sessions if s.accuracy is not None]
    average_accuracy = (
        sum(s.accuracy for s in sessions_with_accuracy) / len(sessions_with_accuracy)
        if sessions_with_accuracy
        else 0.0
    )

    # Calculate total questions answered (estimated from topics_count)
    questions_answered = sum(session.topics_count * 5 for session in study_sessions)  # ~5 questions per topic

    # Create user stats using custom method
    user_stats = UserStats.from_calculations(
        total_sessions=total_sessions,
        avg_accuracy=average_accuracy,
        questions_answered=questions_answered,
        total_time_seconds=total_study_time,
    )

    # Convert to response schemas using custom methods
    games_response = [GameResponse.from_db_model(game) for game in games]

    # OPTIMIZED: Build sessions response without making additional DB calls
    # Pass db=None to prevent build_topic_hierarchy from making queries
    # The topics are already loaded via eager loading above
    sessions_response = [
        StudySessionResponse.from_db_model(session, db=db) for session in study_sessions
    ]

    # OPTIMIZED: Build folder responses using pre-loaded session counts
    folders_response = [
        FolderResponse.from_db_model(folder, session_count=session_count)
        for folder, session_count in folders_with_counts
    ]

    # Build final response
    response_data = AppDataResponse(
        games=games_response,
        studySessions=sessions_response,
        folders=folders_response,
        userProfile=user_profile,
        stats=user_stats,
    )

    logger.debug(f"📊 Built response with {len(games_response)} games, {len(sessions_response)} sessions")
    logger.info(f"📊 Successfully fetched app data for user {current_user.email}")

    # Cache the response for 5 minutes
    set_cache(cache_key, response_data.model_dump(), ttl=settings.CACHE_TTL)
    logger.debug(f"📊 Cached response for user {current_user.id}")

    return response_data
