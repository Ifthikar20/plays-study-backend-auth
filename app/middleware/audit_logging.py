"""
Audit Logging Middleware
Tracks WHO did WHAT, WHEN for compliance and security
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Optional
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Audit logging middleware for compliance tracking.

    Logs all user actions with:
    - WHO: user_id, username, email
    - WHAT: action (method + path), resource accessed/modified
    - WHEN: timestamp
    - WHERE: IP address, user agent
    - RESULT: status code, success/failure

    Use cases:
    - GDPR compliance (track data access)
    - HIPAA compliance (audit trail)
    - Security investigations
    - User activity monitoring
    """

    def __init__(
        self,
        app: ASGIApp,
        log_read_operations: bool = False,  # Log GET requests?
        log_to_database: bool = False,  # Store in database instead of just logs?
    ):
        super().__init__(app)
        self.log_read_operations = log_read_operations
        self.log_to_database = log_to_database

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip audit logging for health checks and static files
        if self._should_skip_audit(request):
            return await call_next(request)

        # Extract user info (if authenticated)
        user_info = self._extract_user_info(request)

        # Process request
        response = await call_next(request)

        # Log audit trail for write operations (or all if configured)
        if self._should_log_action(request.method):
            await self._log_audit_trail(request, response, user_info)

        return response

    def _should_skip_audit(self, request: Request) -> bool:
        """Skip audit logging for certain paths"""
        skip_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
        ]
        return any(request.url.path.startswith(path) for path in skip_paths)

    def _should_log_action(self, method: str) -> bool:
        """Determine if this HTTP method should be audited"""
        # Always log write operations
        write_methods = ["POST", "PUT", "PATCH", "DELETE"]
        if method in write_methods:
            return True

        # Only log read operations if configured
        if method == "GET" and self.log_read_operations:
            return True

        return False

    def _extract_user_info(self, request: Request) -> dict:
        """Extract user information from request state"""
        user_info = {
            "user_id": None,
            "username": None,
            "email": None,
        }

        # Try to get user from request state (set by auth dependency)
        if hasattr(request.state, "user"):
            user = request.state.user
            user_info["user_id"] = getattr(user, "id", None)
            user_info["username"] = getattr(user, "username", None)
            user_info["email"] = getattr(user, "email", None)

        return user_info

    def _extract_resource_info(self, request: Request, response: Response) -> dict:
        """Extract information about the resource being accessed/modified"""
        resource_info = {
            "path": request.url.path,
            "resource_type": self._get_resource_type(request.url.path),
            "resource_id": self._extract_resource_id(request.url.path),
        }

        # For POST requests, try to get created resource ID from response
        if request.method == "POST" and response.status_code == 201:
            # Could extract from Location header or response body
            location = response.headers.get("location")
            if location:
                resource_info["created_resource"] = location

        return resource_info

    def _get_resource_type(self, path: str) -> Optional[str]:
        """Determine resource type from path"""
        # Extract resource type from path like /api/games/123 -> "games"
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[1]  # /api/{resource}/...
        return None

    def _extract_resource_id(self, path: str) -> Optional[str]:
        """Extract resource ID from path if present"""
        # Extract ID from path like /api/games/123 -> "123"
        parts = path.strip("/").split("/")
        if len(parts) >= 3:
            # Check if last part is numeric (likely an ID)
            last_part = parts[-1]
            if last_part.isdigit():
                return last_part
        return None

    def _get_action_description(self, method: str, resource_type: Optional[str]) -> str:
        """Generate human-readable action description"""
        action_map = {
            "GET": "accessed",
            "POST": "created",
            "PUT": "updated",
            "PATCH": "modified",
            "DELETE": "deleted",
        }

        action_verb = action_map.get(method, "performed action on")

        if resource_type:
            return f"{action_verb} {resource_type}"
        else:
            return f"{action_verb} resource"

    async def _log_audit_trail(
        self,
        request: Request,
        response: Response,
        user_info: dict
    ):
        """Log audit trail entry"""

        # Extract additional context
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        resource_info = self._extract_resource_info(request, response)

        # Build audit log entry
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "USER_ACTION",

            # WHO
            "user_id": user_info["user_id"],
            "username": user_info["username"],
            "email": user_info["email"],

            # WHAT
            "action": f"{request.method} {request.url.path}",
            "action_description": self._get_action_description(
                request.method,
                resource_info["resource_type"]
            ),
            "resource_type": resource_info["resource_type"],
            "resource_id": resource_info["resource_id"],

            # WHEN
            "timestamp_unix": datetime.utcnow().timestamp(),

            # WHERE
            "ip_address": ip_address,
            "user_agent": user_agent,

            # RESULT
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,

            # ADDITIONAL CONTEXT
            "query_params": dict(request.query_params) if request.query_params else None,
        }

        # Log to structured logger (CloudWatch will parse JSON)
        logger.info(
            f"AUDIT: {audit_entry['action_description']}",
            extra={"audit": audit_entry}
        )

        # Optionally store in database for long-term retention
        if self.log_to_database:
            await self._store_audit_in_database(audit_entry)

    async def _store_audit_in_database(self, audit_entry: dict):
        """Store audit log in database for compliance"""
        # TODO: Implement database storage
        # Example:
        # async with get_db() as db:
        #     audit_log = AuditLog(**audit_entry)
        #     db.add(audit_log)
        #     await db.commit()
        pass


# Optional: Database model for audit logs
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # WHO
    user_id = Column(Integer, index=True)
    username = Column(String)
    email = Column(String)

    # WHAT
    action = Column(String, nullable=False)
    action_description = Column(String)
    resource_type = Column(String, index=True)
    resource_id = Column(String, index=True)

    # WHERE
    ip_address = Column(String)
    user_agent = Column(String)

    # RESULT
    status_code = Column(Integer)
    success = Column(Boolean)

    # CONTEXT
    query_params = Column(JSON)
"""
