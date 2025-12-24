"""
FastAPI dependencies for authentication and authorization.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
import logging

# Configure logging
logger = logging.getLogger(__name__)

# HTTP Bearer token security
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    logger.debug("👤 get_current_user called")

    token = credentials.credentials
    logger.debug(f"👤 Received token (first 50 chars): {token[:50]}...")

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        logger.error("👤 Token decode failed - payload is None")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"👤 Token payload: {payload}")

    # Extract user ID from token (convert string to int)
    user_id_str = payload.get("sub")
    if user_id_str is None:
        logger.error("👤 No user ID in token payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        logger.error(f"👤 Invalid user ID format in token: {user_id_str}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"👤 Looking up user with ID: {user_id}")

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.error(f"👤 User not found in database with ID: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"👤 User found: {user.email}, Active: {user.is_active}")

    # Check if user is active
    if not user.is_active:
        logger.warning(f"👤 User {user.email} is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    logger.info(f"👤 Authentication successful for: {user.email}")

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to ensure the current user is active.
    This is an additional layer on top of get_current_user.

    Args:
        current_user: The current user from get_current_user

    Returns:
        The active User object

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user
