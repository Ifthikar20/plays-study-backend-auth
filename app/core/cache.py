"""
Redis caching utilities.
"""
import json
import redis
from typing import Optional, Any
from app.config import settings

# Create Redis client (graceful — works without Redis for local dev)
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
    import logging
    logging.getLogger(__name__).info("[Cache] ✅ Redis connected")
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"[Cache] ⚠️ Redis unavailable, caching disabled: {e}")
    redis_client = None


def get_cache(key: str) -> Optional[Any]:
    """
    Get a value from Redis cache.

    Args:
        key: The cache key

    Returns:
        The cached value if exists, None otherwise
    """
    if redis_client is None:
        return None
    try:
        value = redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except (redis.RedisError, json.JSONDecodeError):
        return None


def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Set a value in Redis cache with optional TTL.

    Args:
        key: The cache key
        value: The value to cache (will be JSON serialized)
        ttl: Time to live in seconds (defaults to settings.CACHE_TTL)

    Returns:
        True if successful, False otherwise
    """
    if redis_client is None:
        return False
    try:
        ttl = ttl or settings.CACHE_TTL
        serialized = json.dumps(value)
        redis_client.setex(key, ttl, serialized)
        return True
    except (redis.RedisError, TypeError, ValueError):
        return False


def delete_cache(key: str) -> bool:
    """
    Delete a key from Redis cache.

    Args:
        key: The cache key to delete

    Returns:
        True if successful, False otherwise
    """
    if redis_client is None:
        return False
    try:
        redis_client.delete(key)
        return True
    except redis.RedisError:
        return False


def invalidate_user_cache(user_id: int) -> bool:
    """
    Invalidate all cache entries for a specific user.

    Args:
        user_id: The user ID

    Returns:
        True if successful, False otherwise
    """
    cache_key = f"app_data:{user_id}"
    return delete_cache(cache_key)
