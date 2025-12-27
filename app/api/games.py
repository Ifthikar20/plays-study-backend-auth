"""
Educational Games API endpoints for reinforcement learning.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.dependencies import get_current_active_user, get_db
from app.models.user import User
from app.models.topic import Topic
from app.models.game_completion import GameCompletion
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== PYDANTIC MODELS =====

class GameDefinition(BaseModel):
    """Definition of an educational game type."""
    game_type: str
    title: str
    description: str
    icon: str  # Emoji or icon identifier
    estimated_time: int  # in minutes
    xp_reward: int
    difficulty: str  # easy, medium, hard


class GameRecommendation(BaseModel):
    """Recommended game for a specific topic."""
    game_type: str
    title: str
    description: str
    icon: str
    topic_id: int
    topic_title: str
    estimated_time: int
    xp_reward: int
    difficulty: str
    completed: bool
    score: Optional[int] = None


class StartGameRequest(BaseModel):
    """Request to start a game for a topic."""
    topic_id: int
    game_type: str


class CompleteGameRequest(BaseModel):
    """Request to complete a game."""
    topic_id: int
    game_type: str
    score: int = Field(..., ge=0, le=100)
    time_spent: int = Field(..., ge=0)  # seconds
    game_data: Optional[Dict[str, Any]] = None


class GameCompletionResponse(BaseModel):
    """Response after completing a game."""
    success: bool
    game_type: str
    topic_id: int
    score: int
    xp_earned: int
    message: str


# ===== GAME DEFINITIONS =====

AVAILABLE_GAMES = {
    "memory_match": GameDefinition(
        game_type="memory_match",
        title="Memory Match",
        description="Match pairs of concepts and definitions to reinforce your understanding",
        icon="🧠",
        estimated_time=5,
        xp_reward=50,
        difficulty="easy"
    ),
    "true_false": GameDefinition(
        game_type="true_false",
        title="True or False Challenge",
        description="Test your knowledge with real-world scenarios - true or false?",
        icon="✓",
        estimated_time=3,
        xp_reward=30,
        difficulty="easy"
    ),
    "word_scramble": GameDefinition(
        game_type="word_scramble",
        title="Word Scramble",
        description="Unscramble key terms and concepts from your study material",
        icon="🔤",
        estimated_time=4,
        xp_reward=40,
        difficulty="medium"
    ),
    "quick_quiz": GameDefinition(
        game_type="quick_quiz",
        title="Quick Fire Quiz",
        description="Rapid-fire questions to test your recall speed",
        icon="⚡",
        estimated_time=5,
        xp_reward=60,
        difficulty="medium"
    ),
    "concept_map": GameDefinition(
        game_type="concept_map",
        title="Concept Connector",
        description="Connect related concepts to build your understanding",
        icon="🔗",
        estimated_time=7,
        xp_reward=70,
        difficulty="hard"
    )
}


# ===== API ENDPOINTS =====

@router.get("/available", response_model=List[GameDefinition])
async def get_available_games(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of all available educational game types.

    Returns:
        List of game definitions with details about each game type
    """
    return list(AVAILABLE_GAMES.values())


@router.get("/topics/{topic_id}/recommended", response_model=List[GameRecommendation])
async def get_recommended_games_for_topic(
    topic_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get recommended games for a specific topic.

    Games are recommended when:
    - The topic's quiz has been completed (workflow_stage = 'flashcard_review' or 'completed')
    - Games reinforce the learned concepts

    Args:
        topic_id: Database ID of the topic

    Returns:
        List of recommended games with completion status
    """
    # Verify topic exists and belongs to user's session
    topic = db.query(Topic).join(
        Topic.study_session
    ).filter(
        Topic.id == topic_id,
        Topic.study_session.has(user_id=current_user.id)
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Check if topic quiz has been completed
    if topic.workflow_stage not in ['flashcard_review', 'completed']:
        logger.info(f"Topic {topic_id} not ready for games (stage: {topic.workflow_stage})")
        return []

    # Get user's game completions for this topic
    completions = db.query(GameCompletion).filter(
        GameCompletion.user_id == current_user.id,
        GameCompletion.topic_id == topic_id
    ).all()

    completion_map = {gc.game_type: gc for gc in completions}

    # Recommend games based on topic characteristics
    recommended_games = []

    # Always recommend Memory Match and True/False as primary reinforcement games
    primary_games = ['memory_match', 'true_false']

    # Add additional games based on topic complexity
    question_count = len(topic.questions) if hasattr(topic, 'questions') else 0
    if question_count > 10:
        primary_games.append('quick_quiz')
    if question_count > 15:
        primary_games.append('word_scramble')

    for game_type in primary_games:
        if game_type in AVAILABLE_GAMES:
            game_def = AVAILABLE_GAMES[game_type]
            completion = completion_map.get(game_type)

            recommended_games.append(GameRecommendation(
                game_type=game_def.game_type,
                title=game_def.title,
                description=game_def.description,
                icon=game_def.icon,
                topic_id=topic.id,
                topic_title=topic.title,
                estimated_time=game_def.estimated_time,
                xp_reward=game_def.xp_reward,
                difficulty=game_def.difficulty,
                completed=completion.completed if completion else False,
                score=completion.score if completion and completion.completed else None
            ))

    logger.info(f"Recommended {len(recommended_games)} games for topic {topic_id} ({topic.title})")
    return recommended_games


@router.post("/start", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def start_game(
    request: Request,
    data: StartGameRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Start a game session for a topic.

    Creates or updates a GameCompletion record to track the session.

    Returns:
        Game session details including questions/content for the game
    """
    # Verify topic exists and belongs to user
    topic = db.query(Topic).join(
        Topic.study_session
    ).filter(
        Topic.id == data.topic_id,
        Topic.study_session.has(user_id=current_user.id)
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Verify game type exists
    if data.game_type not in AVAILABLE_GAMES:
        raise HTTPException(status_code=400, detail=f"Unknown game type: {data.game_type}")

    # Check or create game completion record
    game_completion = db.query(GameCompletion).filter(
        GameCompletion.user_id == current_user.id,
        GameCompletion.topic_id == data.topic_id,
        GameCompletion.game_type == data.game_type
    ).first()

    if not game_completion:
        game_completion = GameCompletion(
            user_id=current_user.id,
            topic_id=data.topic_id,
            game_type=data.game_type,
            started_at=datetime.utcnow()
        )
        db.add(game_completion)
    else:
        # Reset for new attempt
        game_completion.started_at = datetime.utcnow()
        game_completion.attempts += 1

    db.commit()
    db.refresh(game_completion)

    game_def = AVAILABLE_GAMES[data.game_type]

    logger.info(f"Started {data.game_type} game for topic {data.topic_id} by user {current_user.id}")

    return {
        "success": True,
        "game_completion_id": game_completion.id,
        "game_type": data.game_type,
        "topic_id": data.topic_id,
        "topic_title": topic.title,
        "estimated_time": game_def.estimated_time,
        "xp_reward": game_def.xp_reward,
        "message": f"Started {game_def.title} for {topic.title}"
    }


@router.post("/complete", response_model=GameCompletionResponse)
@limiter.limit("30/minute")
async def complete_game(
    request: Request,
    data: CompleteGameRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark a game as completed and award XP.

    Updates the game completion record and awards XP to the user.

    Returns:
        Completion details including XP earned
    """
    # Verify topic exists
    topic = db.query(Topic).join(
        Topic.study_session
    ).filter(
        Topic.id == data.topic_id,
        Topic.study_session.has(user_id=current_user.id)
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get game completion record
    game_completion = db.query(GameCompletion).filter(
        GameCompletion.user_id == current_user.id,
        GameCompletion.topic_id == data.topic_id,
        GameCompletion.game_type == data.game_type
    ).first()

    if not game_completion:
        # Create if doesn't exist (in case start wasn't called)
        game_completion = GameCompletion(
            user_id=current_user.id,
            topic_id=data.topic_id,
            game_type=data.game_type
        )
        db.add(game_completion)

    # Calculate XP based on score
    game_def = AVAILABLE_GAMES.get(data.game_type)
    if not game_def:
        raise HTTPException(status_code=400, detail=f"Unknown game type: {data.game_type}")

    # XP = base_reward * (score / 100)
    xp_earned = int(game_def.xp_reward * (data.score / 100))

    # Update game completion
    game_completion.completed = True
    game_completion.score = data.score
    game_completion.time_spent = data.time_spent
    game_completion.game_data = data.game_data
    game_completion.completed_at = datetime.utcnow()

    # Award XP to user
    current_user.xp += xp_earned

    db.commit()

    logger.info(f"✅ User {current_user.id} completed {data.game_type} for topic {data.topic_id} - Score: {data.score}, XP: {xp_earned}")

    return GameCompletionResponse(
        success=True,
        game_type=data.game_type,
        topic_id=data.topic_id,
        score=data.score,
        xp_earned=xp_earned,
        message=f"Great job! You earned {xp_earned} XP!"
    )


@router.get("/topic/{topic_id}/status", response_model=List[Dict[str, Any]])
async def get_game_status_for_topic(
    topic_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get completion status of all games for a specific topic.

    Returns:
        List of game completions with status and scores
    """
    # Verify topic exists
    topic = db.query(Topic).join(
        Topic.study_session
    ).filter(
        Topic.id == topic_id,
        Topic.study_session.has(user_id=current_user.id)
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get all game completions for this topic
    completions = db.query(GameCompletion).filter(
        GameCompletion.user_id == current_user.id,
        GameCompletion.topic_id == topic_id
    ).all()

    return [
        {
            "game_type": gc.game_type,
            "completed": gc.completed,
            "score": gc.score,
            "time_spent": gc.time_spent,
            "attempts": gc.attempts,
            "completed_at": gc.completed_at.isoformat() if gc.completed_at else None
        }
        for gc in completions
    ]
