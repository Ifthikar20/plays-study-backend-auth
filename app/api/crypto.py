"""
Crypto API Endpoints

Provides cryptography-related endpoints:
- Public key retrieval for encryption
- Key version information
- Encryption status
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from app.core.crypto import crypto_service
from app.core.nonce_manager import nonce_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crypto", tags=["crypto"])


class PublicKeyResponse(BaseModel):
    """Response model for public key endpoint"""
    public_key: str
    version: str
    algorithm: str = "RSA-2048"
    key_exchange: str = "RSA-OAEP-SHA256"
    encryption: str = "AES-256-GCM"


class KeyVersionResponse(BaseModel):
    """Response model for key version endpoint"""
    version: str
    created_at: str = None


class NonceStatsResponse(BaseModel):
    """Response model for nonce statistics"""
    backend: str
    fallback_count: int
    redis_nonce_count: int = None


@router.get("/public-key", response_model=PublicKeyResponse)
async def get_public_key():
    """
    Get RSA public key for encrypting requests

    This endpoint returns the server's RSA public key in PEM format.
    Clients use this key to encrypt AES session keys.

    Returns:
        PublicKeyResponse with public key and metadata
    """
    try:
        logger.info("[Crypto API] Public key requested")

        public_key_pem = crypto_service.get_public_key_pem()
        key_version = crypto_service.get_key_version()

        return PublicKeyResponse(
            public_key=public_key_pem,
            version=key_version
        )

    except Exception as e:
        logger.error(f"[Crypto API] Failed to retrieve public key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve public key"
        )


@router.get("/key-version", response_model=KeyVersionResponse)
async def get_key_version():
    """
    Get current encryption key version

    Useful for clients to check if they need to refresh their cached public key.

    Returns:
        KeyVersionResponse with current version
    """
    try:
        version = crypto_service.get_key_version()

        return KeyVersionResponse(
            version=version
        )

    except Exception as e:
        logger.error(f"[Crypto API] Failed to get key version: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve key version"
        )


@router.get("/nonce-stats", response_model=NonceStatsResponse)
async def get_nonce_stats():
    """
    Get nonce manager statistics (for monitoring/debugging)

    Returns:
        NonceStatsResponse with nonce statistics
    """
    try:
        stats = nonce_manager.get_stats()

        return NonceStatsResponse(
            backend=stats.get("backend", "unknown"),
            fallback_count=stats.get("fallback_count", 0),
            redis_nonce_count=stats.get("redis_nonce_count")
        )

    except Exception as e:
        logger.error(f"[Crypto API] Failed to get nonce stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve nonce statistics"
        )


@router.get("/health")
async def crypto_health():
    """
    Check if crypto service is healthy

    Returns:
        Health status
    """
    try:
        # Try to get public key (verifies crypto service is working)
        public_key = crypto_service.get_public_key_pem()

        return {
            "status": "healthy",
            "crypto_initialized": bool(public_key),
            "key_version": crypto_service.get_key_version()
        }

    except Exception as e:
        logger.error(f"[Crypto API] Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
