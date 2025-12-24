"""
Authentication API endpoints for user registration and login.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional
from app.database import get_db
from app.schemas.user import UserCreate, UserLogin, Token
from app.models.user import User
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.recaptcha import verify_recaptcha, is_human
from app.config import settings
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Register a new user account with reCAPTCHA v3 bot protection.

    Args:
        body: Request body containing email, name, password, and optional recaptchaToken
        db: Database session

    Returns:
        JWT access token for the new user

    Raises:
        HTTPException: If email already exists or bot detection fails
    """
    # Parse request body
    email = body.get("email")
    name = body.get("name")
    password = body.get("password")
    recaptcha_token = body.get("recaptchaToken")

    if not email or not name or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email, name, and password are required"
        )

    # Verify reCAPTCHA (Layer 1: Bot Detection)
    if settings.RECAPTCHA_ENABLED and recaptcha_token:
        try:
            recaptcha_result = await verify_recaptcha(recaptcha_token, expected_action="register")

            if not recaptcha_result.success:
                logger.warning(f"🤖 Registration blocked - reCAPTCHA verification failed: {recaptcha_result.error_codes}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Failed bot detection. Please try again.",
                )

            if not is_human(recaptcha_result.score):
                logger.warning(
                    f"🤖 Registration blocked - Low reCAPTCHA score: {recaptcha_result.score:.2f} "
                    f"(threshold: {settings.RECAPTCHA_MIN_SCORE})"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Failed bot detection. Please try again.",
                )

            logger.info(f"✅ reCAPTCHA passed for registration - Score: {recaptcha_result.score:.2f}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ reCAPTCHA verification error: {str(e)}")
            # Allow registration to proceed if reCAPTCHA service is down
            logger.warning("⚠️ Proceeding with registration despite reCAPTCHA error")
    elif settings.RECAPTCHA_ENABLED and not recaptcha_token:
        logger.warning("⚠️ Registration attempt without reCAPTCHA token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot detection token required",
        )

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    hashed_password = get_password_hash(password)
    new_user = User(
        email=email,
        name=name,
        hashed_password=hashed_password,
        xp=0,
        level=1,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(new_user.id), "email": new_user.email},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/login", response_model=Token)
async def login_user(
    body: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Authenticate a user and return JWT token with reCAPTCHA v3 bot protection.

    Args:
        body: Request body containing email, password, and optional recaptchaToken
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid or bot detection fails
    """
    # Parse request body
    email = body.get("email")
    password = body.get("password")
    recaptcha_token = body.get("recaptchaToken")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    logger.info(f"🔑 Login attempt for email: {email}")

    # Verify reCAPTCHA (Layer 1: Bot Detection)
    if settings.RECAPTCHA_ENABLED and recaptcha_token:
        try:
            recaptcha_result = await verify_recaptcha(recaptcha_token, expected_action="login")

            if not recaptcha_result.success:
                logger.warning(f"🤖 Login blocked - reCAPTCHA verification failed: {recaptcha_result.error_codes}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Failed bot detection. Please try again.",
                )

            if not is_human(recaptcha_result.score):
                logger.warning(
                    f"🤖 Login blocked - Low reCAPTCHA score: {recaptcha_result.score:.2f} "
                    f"(threshold: {settings.RECAPTCHA_MIN_SCORE})"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Failed bot detection. Please try again.",
                )

            logger.info(f"✅ reCAPTCHA passed for login - Score: {recaptcha_result.score:.2f}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ reCAPTCHA verification error: {str(e)}")
            # Allow login to proceed if reCAPTCHA service is down
            logger.warning("⚠️ Proceeding with login despite reCAPTCHA error")
    elif settings.RECAPTCHA_ENABLED and not recaptcha_token:
        logger.warning("⚠️ Login attempt without reCAPTCHA token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bot detection token required",
        )

    # Get user by email
    user = db.query(User).filter(User.email == email).first()

    if not user:
        logger.warning(f"🔑 Login failed: User not found for email {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"🔑 User found: ID={user.id}, Name={user.name}, Active={user.is_active}")
    logger.debug(f"🔑 Stored hash (first 20 chars): {user.hashed_password[:20]}...")

    # Verify password
    password_valid = verify_password(password, user.hashed_password)

    if not password_valid:
        logger.warning(f"🔑 Login failed: Invalid password for {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"🔑 Password verified successfully for {email}")

    # Check if user is active
    if not user.is_active:
        logger.warning(f"🔑 Login failed: Account inactive for {email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    logger.debug(f"🔑 Creating access token with {settings.ACCESS_TOKEN_EXPIRE_MINUTES} min expiry")

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires,
    )

    logger.info(f"🔑 Login successful for {email}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
