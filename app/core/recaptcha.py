"""
Google reCAPTCHA v3 verification utility.

This module provides verification for reCAPTCHA v3 tokens to prevent
automated bot attacks on authentication endpoints.
"""

import httpx
import logging
from typing import Optional
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class RecaptchaResponse(BaseModel):
    """reCAPTCHA verification response model."""
    success: bool
    score: float
    action: str
    challenge_ts: str
    hostname: str
    error_codes: Optional[list] = None


async def verify_recaptcha(token: str, expected_action: str = None) -> RecaptchaResponse:
    """
    Verify a reCAPTCHA v3 token with Google's API.

    Args:
        token: The reCAPTCHA token from the frontend
        expected_action: Expected action name (e.g., 'register', 'login')

    Returns:
        RecaptchaResponse with verification results

    Raises:
        Exception: If verification request fails
    """
    # Skip verification if disabled or no secret key configured
    if not settings.RECAPTCHA_ENABLED:
        logger.warning("⚠️ reCAPTCHA verification is disabled")
        return RecaptchaResponse(
            success=True,
            score=1.0,
            action=expected_action or "unknown",
            challenge_ts="",
            hostname="",
        )

    if not settings.RECAPTCHA_SECRET_KEY:
        logger.warning("⚠️ RECAPTCHA_SECRET_KEY not configured, skipping verification")
        return RecaptchaResponse(
            success=True,
            score=1.0,
            action=expected_action or "unknown",
            challenge_ts="",
            hostname="",
        )

    try:
        # Make request to Google reCAPTCHA API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": settings.RECAPTCHA_SECRET_KEY,
                    "response": token,
                },
                timeout=10.0,
            )

            if response.status_code != 200:
                logger.error(f"❌ reCAPTCHA API returned status {response.status_code}")
                raise Exception(f"reCAPTCHA verification failed with status {response.status_code}")

            data = response.json()

            # Parse response
            result = RecaptchaResponse(
                success=data.get("success", False),
                score=data.get("score", 0.0),
                action=data.get("action", ""),
                challenge_ts=data.get("challenge_ts", ""),
                hostname=data.get("hostname", ""),
                error_codes=data.get("error-codes"),
            )

            # Log verification result
            if result.success:
                logger.info(
                    f"✅ reCAPTCHA verified - Score: {result.score:.2f}, "
                    f"Action: {result.action}, Hostname: {result.hostname}"
                )
            else:
                logger.warning(
                    f"⚠️ reCAPTCHA verification failed - "
                    f"Errors: {result.error_codes}"
                )

            # Verify action matches expected
            if expected_action and result.action != expected_action:
                logger.warning(
                    f"⚠️ reCAPTCHA action mismatch - "
                    f"Expected: {expected_action}, Got: {result.action}"
                )

            return result

    except httpx.TimeoutException:
        logger.error("❌ reCAPTCHA verification timeout")
        raise Exception("reCAPTCHA verification timeout")
    except Exception as e:
        logger.error(f"❌ reCAPTCHA verification error: {str(e)}")
        raise


def is_human(score: float) -> bool:
    """
    Determine if a reCAPTCHA score indicates a human user.

    Args:
        score: reCAPTCHA score (0.0 = bot, 1.0 = human)

    Returns:
        True if score indicates human, False otherwise
    """
    return score >= settings.RECAPTCHA_MIN_SCORE
