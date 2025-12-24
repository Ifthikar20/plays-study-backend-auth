"""
Security utilities for authentication and authorization.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Password hashing context with bcrypt, with fallback for compatibility
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    # Fallback to pbkdf2 if bcrypt has issues
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    logger.debug(f"🔐 Verifying password (length: {len(plain_password)})")
    logger.debug(f"🔐 Hashed password (first 20 chars): {hashed_password[:20]}...")

    try:
        result = pwd_context.verify(plain_password, hashed_password)
        logger.debug(f"🔐 Password verification with bcrypt: {result}")
        return result
    except Exception as e:
        # Fallback for development: simple hash comparison
        logger.warning(f"🔐 Bcrypt failed, using SHA256 fallback: {e}")
        import hashlib
        simple_hash = hashlib.sha256(plain_password.encode()).hexdigest()
        result = simple_hash == hashed_password
        logger.debug(f"🔐 SHA256 hash: {simple_hash[:20]}...")
        logger.debug(f"🔐 Password verification with SHA256: {result}")
        return result


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt (with fallback).

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        # Fallback for development
        import hashlib
        print(f"Warning: Using fallback password hashing due to: {e}")
        return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    logger.debug(f"🎫 Creating access token for user: {data.get('email', 'unknown')}")
    logger.debug(f"🎫 Token data: {to_encode}")
    logger.debug(f"🎫 Token expires at: {expire}")

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    logger.debug(f"🎫 Created token (first 50 chars): {encoded_jwt[:50]}...")

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.

    Args:
        token: The JWT token to decode

    Returns:
        Dictionary of decoded token data, or None if invalid
    """
    logger.debug(f"🔓 Decoding access token (first 50 chars): {token[:50]}...")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.debug(f"🔓 Token decoded successfully: {payload}")
        return payload
    except JWTError as e:
        logger.error(f"🔓 Token decode failed: {e}")
        return None
