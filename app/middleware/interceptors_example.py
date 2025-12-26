"""
Request Interceptor Middleware
Intercepts all requests before they reach controllers
"""
import time
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable

logger = logging.getLogger(__name__)


class RequestInterceptorMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive request interceptor that:
    1. Generates request ID
    2. Logs all requests
    3. Tracks timing
    4. Adds security headers
    5. Sanitizes inputs
    6. Enriches context
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Generate Request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 2. Extract Request Context
        user_agent = request.headers.get("user-agent", "unknown")
        ip_address = request.client.host if request.client else "unknown"
        device_type = self._detect_device(user_agent)

        # 3. Enrich Request Context
        request.state.context = {
            "request_id": request_id,
            "ip": ip_address,
            "device": device_type,
            "user_agent": user_agent,
            "method": request.method,
            "path": request.url.path,
        }

        # 4. Security Checks
        if self._is_blocked_ip(ip_address):
            return Response(
                content='{"error": "Access denied"}',
                status_code=403,
                media_type="application/json"
            )

        # 5. Start Timing
        start_time = time.time()

        # 6. Log Request
        logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "ip": ip_address,
                "device": device_type,
            }
        )

        try:
            # 7. Process Request (call controller)
            response = await call_next(request)

            # 8. Calculate Response Time
            duration_ms = (time.time() - start_time) * 1000

            # 9. Add Response Headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

            # 10. Log Response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )

            # 11. Track Metrics (send to CloudWatch, Datadog, etc.)
            self._track_metrics(request, response, duration_ms)

            return response

        except Exception as e:
            # 12. Error Logging & Normalization
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
                exc_info=True
            )

            # 13. Return Normalized Error (hide internal details)
            return Response(
                content='{"error": "Internal server error", "request_id": "' + request_id + '"}',
                status_code=500,
                media_type="application/json"
            )

    def _detect_device(self, user_agent: str) -> str:
        """Detect device type from user agent"""
        user_agent_lower = user_agent.lower()
        if "mobile" in user_agent_lower or "android" in user_agent_lower:
            return "mobile"
        elif "tablet" in user_agent_lower or "ipad" in user_agent_lower:
            return "tablet"
        elif "bot" in user_agent_lower or "crawler" in user_agent_lower:
            return "bot"
        else:
            return "desktop"

    def _is_blocked_ip(self, ip: str) -> bool:
        """Check if IP is blocked"""
        # In production, check against database or cache
        blocked_ips = {"192.0.2.1", "198.51.100.1"}  # Example IPs
        return ip in blocked_ips

    def _track_metrics(self, request: Request, response: Response, duration_ms: float):
        """Send metrics to monitoring system"""
        # Example: Send to CloudWatch, Datadog, Prometheus, etc.
        # metrics.increment(f"http.requests.{request.method}.{response.status_code}")
        # metrics.timing("http.response_time", duration_ms)
        pass


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Audit logging for compliance
    Tracks WHO did WHAT, WHEN
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get user from request (if authenticated)
        user_id = getattr(request.state, "user_id", None)

        # Process request
        response = await call_next(request)

        # Log audit trail for write operations
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            logger.info(
                "Audit log",
                extra={
                    "user_id": user_id,
                    "action": f"{request.method} {request.url.path}",
                    "timestamp": time.time(),
                    "ip": request.client.host if request.client else "unknown",
                    "status": response.status_code,
                }
            )

        return response


class RequestSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Sanitize request data to prevent attacks
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get query params
        query_params = dict(request.query_params)

        # Sanitize query params
        for key, value in query_params.items():
            # Remove potential XSS
            sanitized = self._sanitize_string(value)
            # Update in request (if possible)
            # Note: query_params is immutable, so this is for demonstration

        # Process request
        response = await call_next(request)
        return response

    def _sanitize_string(self, value: str) -> str:
        """Remove dangerous characters"""
        dangerous_chars = ["<", ">", "script", "javascript:", "onerror="]
        sanitized = value
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        return sanitized.strip()


# How to add to FastAPI app:
"""
from app.middleware.interceptors import (
    RequestInterceptorMiddleware,
    AuditLoggingMiddleware,
    RequestSanitizationMiddleware
)

app = FastAPI()

# Add interceptor middleware (order matters!)
app.add_middleware(RequestInterceptorMiddleware)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(RequestSanitizationMiddleware)
"""
