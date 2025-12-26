"""
Main FastAPI application with CORS, security headers, and route configuration.
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.core.rate_limit import limiter
from app.core.cache import redis_client
from app.core.nonce_manager import nonce_manager
from app.middleware.encryption_middleware import EncryptionMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.audit_logging import AuditLoggingMiddleware
from app.api import auth, app_data, questions, study_sessions, tts, crypto, folders, recommendations
from app.database import Base, engine
import logging

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize nonce manager with Redis
try:
    nonce_manager.redis = redis_client
    logger.info("[Startup] ✅ Nonce manager initialized with Redis")
except Exception as e:
    logger.warning(f"[Startup] ⚠️ Redis connection failed, using fallback: {e}")

# Create FastAPI application
app = FastAPI(
    title="Playstudy API",
    description="Backend API for Playstudy.ai with consolidated data architecture",
    version="1.0.0",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add comprehensive security headers middleware
app.add_middleware(SecurityHeadersMiddleware)
logger.info("[Startup] ✅ Security headers middleware registered")

# Add audit logging middleware (logs WHO did WHAT, WHEN)
app.add_middleware(
    AuditLoggingMiddleware,
    log_read_operations=False,  # Only log write operations (POST, PUT, PATCH, DELETE)
    log_to_database=False,  # Just log to CloudWatch for now
)
logger.info("[Startup] ✅ Audit logging middleware registered")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=settings.ALLOWED_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# Encryption middleware (for encrypted API requests)
app.add_middleware(EncryptionMiddleware)
logger.info("[Startup] ✅ Encryption middleware registered")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "api_version": "1.0.0",
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Playstudy API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_PREFIX}/docs",
        "health": "/health",
    }


# Register API routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"],
)

app.include_router(
    app_data.router,
    prefix=settings.API_V1_PREFIX,
    tags=["App Data"],
)

app.include_router(
    questions.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Questions"],
)

app.include_router(
    study_sessions.router,
    prefix=f"{settings.API_V1_PREFIX}/study-sessions",
    tags=["Study Sessions"],
)

app.include_router(
    tts.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Text-to-Speech"],
)

app.include_router(
    crypto.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Cryptography"],
)

app.include_router(
    folders.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Folders"],
)

app.include_router(
    recommendations.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Recommendations"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors gracefully."""
    # Log the error (in production, use proper logging)
    if settings.DEBUG:
        print(f"Error: {str(exc)}")

    # Return generic error message
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred" if not settings.DEBUG else str(exc)
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        limit_max_requests=1000,  # Allow more concurrent requests
        timeout_keep_alive=120,   # Keep connections alive longer for large uploads
    )
