"""
Security Headers Middleware
Adds essential security headers to all responses
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all HTTP responses to protect against common attacks.

    Headers added:
    - X-Content-Type-Options: nosniff (prevent MIME type sniffing)
    - X-Frame-Options: DENY (prevent clickjacking)
    - Strict-Transport-Security: enforce HTTPS
    - Content-Security-Policy: restrict resource loading
    - X-XSS-Protection: enable XSS filtering (legacy browsers)
    - Referrer-Policy: control referrer information
    """

    def __init__(
        self,
        app: ASGIApp,
        hsts_max_age: int = 31536000,  # 1 year in seconds
        include_subdomains: bool = True,
    ):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.include_subdomains = include_subdomains

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Process request
        response = await call_next(request)

        # Add security headers
        self._add_security_headers(response, request)

        return response

    def _add_security_headers(self, response: Response, request: Request):
        """Add all security headers to response"""

        # Prevent MIME type sniffing
        # Stops browsers from guessing content type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking attacks
        # Prevents site from being embedded in iframe
        response.headers["X-Frame-Options"] = "DENY"

        # Force HTTPS connections (only add if request is HTTPS)
        # Tells browsers to only access site via HTTPS for next year
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.include_subdomains:
                hsts_value += "; includeSubDomains"
            response.headers["Strict-Transport-Security"] = hsts_value

        # Content Security Policy
        # Restricts where resources can be loaded from
        # This is a basic policy - adjust based on your needs
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Allow inline scripts (for docs)
            "style-src 'self' 'unsafe-inline'; "  # Allow inline styles
            "img-src 'self' data: https:; "  # Allow images from self, data URIs, and HTTPS
            "font-src 'self' data:; "
            "connect-src 'self'; "  # API calls only to same origin
            "frame-ancestors 'none'; "  # Don't allow framing (same as X-Frame-Options)
            "base-uri 'self'; "  # Restrict <base> tag
            "form-action 'self'"  # Forms can only submit to same origin
        )
        response.headers["Content-Security-Policy"] = csp_policy

        # XSS Protection (legacy, but still good for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        # Don't send referrer to other origins
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature-Policy)
        # Disable unnecessary browser features
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy

        logger.debug(
            f"Added security headers to response for {request.method} {request.url.path}"
        )
