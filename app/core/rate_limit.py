"""
Rate limiting utilities using SlowAPI.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def get_user_id_or_ip(request: Request):
    """
    Get user ID from request if authenticated, otherwise use IP address.
    This allows for user-specific rate limiting.

    Skip rate limiting for OPTIONS requests (CORS preflight).
    """
    # Skip rate limiting for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return None

    # Try to get user ID from request state (set by auth middleware)
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"

    # Fallback to IP address
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(key_func=get_user_id_or_ip)
