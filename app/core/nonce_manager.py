"""
Nonce Manager

Manages nonces for replay attack protection.
Uses Redis for distributed nonce tracking with automatic expiry.
"""

import logging
from typing import Optional
from datetime import timedelta

logger = logging.getLogger(__name__)

# Default nonce TTL: 5 minutes
DEFAULT_NONCE_TTL = 300


class NonceManager:
    """Manages nonces to prevent replay attacks"""

    def __init__(self, redis_client=None):
        """
        Initialize nonce manager

        Args:
            redis_client: Redis client instance (optional)
        """
        self.redis = redis_client
        self._fallback_store = {}  # In-memory fallback if Redis unavailable

    def verify_nonce(self, nonce: str, ttl: int = DEFAULT_NONCE_TTL) -> bool:
        """
        Verify and store nonce (returns True if nonce is valid/unused)

        Args:
            nonce: Unique nonce string (UUID recommended)
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)

        Returns:
            True if nonce is valid (not seen before), False if replay detected
        """
        if not nonce or len(nonce) < 10:
            logger.warning("[NonceManager] Invalid nonce format")
            return False

        key = f"nonce:{nonce}"

        # Try Redis first
        if self.redis:
            try:
                # SET if not exists (NX) with expiry
                result = self.redis.set(key, "1", ex=ttl, nx=True)

                if result is None or result is False:
                    logger.warning(f"[NonceManager] ⚠️ Replay attempt detected: {nonce[:16]}...")
                    return False

                logger.debug(f"[NonceManager] ✅ Nonce accepted: {nonce[:16]}...")
                return True

            except Exception as e:
                logger.error(f"[NonceManager] Redis error, using fallback: {e}")
                # Fall through to in-memory fallback

        # Fallback to in-memory store (not distributed, for development only)
        if nonce in self._fallback_store:
            logger.warning(f"[NonceManager] ⚠️ Replay attempt detected (fallback): {nonce[:16]}...")
            return False

        self._fallback_store[nonce] = True
        logger.debug(f"[NonceManager] ✅ Nonce accepted (fallback): {nonce[:16]}...")

        # Clean up old entries periodically (simple approach)
        if len(self._fallback_store) > 10000:
            logger.warning("[NonceManager] Fallback store size limit reached, clearing old entries")
            self._fallback_store.clear()

        return True

    def store_nonce(self, nonce: str, ttl: int = DEFAULT_NONCE_TTL) -> None:
        """
        Store nonce manually (alternative to verify_nonce)

        Args:
            nonce: Unique nonce string
            ttl: Time-to-live in seconds
        """
        key = f"nonce:{nonce}"

        if self.redis:
            try:
                self.redis.setex(key, ttl, "1")
                logger.debug(f"[NonceManager] Stored nonce: {nonce[:16]}...")
                return
            except Exception as e:
                logger.error(f"[NonceManager] Redis error: {e}")

        # Fallback
        self._fallback_store[nonce] = True

    def is_nonce_used(self, nonce: str) -> bool:
        """
        Check if nonce has been used before

        Args:
            nonce: Nonce to check

        Returns:
            True if nonce has been used, False otherwise
        """
        key = f"nonce:{nonce}"

        if self.redis:
            try:
                return self.redis.exists(key) > 0
            except Exception as e:
                logger.error(f"[NonceManager] Redis error: {e}")

        # Fallback
        return nonce in self._fallback_store

    def cleanup_expired(self) -> int:
        """
        Clean up expired nonces (Redis handles this automatically)

        Returns:
            Number of entries cleaned (always 0 for Redis)
        """
        if self.redis:
            # Redis handles expiry automatically
            return 0

        # Fallback: Clear all (no expiry tracking in memory)
        count = len(self._fallback_store)
        self._fallback_store.clear()
        logger.info(f"[NonceManager] Cleared {count} nonces from fallback store")
        return count

    def get_stats(self) -> dict:
        """
        Get nonce manager statistics

        Returns:
            Dictionary with statistics
        """
        stats = {
            "backend": "redis" if self.redis else "memory",
            "fallback_count": len(self._fallback_store)
        }

        if self.redis:
            try:
                # Count nonce keys in Redis
                nonce_keys = self.redis.keys("nonce:*")
                stats["redis_nonce_count"] = len(nonce_keys) if nonce_keys else 0
            except Exception as e:
                logger.error(f"[NonceManager] Redis stats error: {e}")
                stats["redis_error"] = str(e)

        return stats


# Global singleton instance (will be initialized with Redis in main.py)
nonce_manager = NonceManager()


def get_nonce_manager() -> NonceManager:
    """Get the global nonce manager instance"""
    return nonce_manager
