"""
Application configuration settings.
"""
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str
    CACHE_TTL: int = 300  # 5 minutes

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # reCAPTCHA v3 (disabled by default - set RECAPTCHA_ENABLED=true in .env to enable)
    RECAPTCHA_SECRET_KEY: Optional[str] = None
    RECAPTCHA_ENABLED: bool = False
    RECAPTCHA_MIN_SCORE: float = 0.5

    # Encryption at Rest
    FIELD_ENCRYPTION_KEY: Optional[str] = None

    # Encryption in Transit
    RSA_PRIVATE_KEY_PEM: Optional[str] = None
    ENCRYPTION_REQUIRED: bool = False

    # CORS
    ALLOWED_ORIGINS: str
    ALLOWED_CREDENTIALS: bool = True

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # App
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # AI Providers
    DEEPSEEK_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # TTS Providers (Optional)
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_API_KEY: Optional[str] = None

    # Unsplash Image Search (Optional)
    UNSPLASH_ACCESS_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated origins string to list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


# Create global settings instance
settings = Settings()

# Enhanced TTS configuration logging (both logger and print for visibility)
print("\n" + "=" * 70)
print("🔊 TTS PROVIDERS CONFIGURATION CHECK")
print("=" * 70)
logger.info("=" * 70)
logger.info("🔊 TTS PROVIDERS CONFIGURATION CHECK")
logger.info("=" * 70)

# Check OpenAI TTS
print("\n📌 OpenAI TTS:")
openai_configured = bool(settings.OPENAI_API_KEY)
if openai_configured:
    print(f"✅ Status: CONFIGURED")
    print(f"🔑 API Key: {settings.OPENAI_API_KEY[:7]}...{settings.OPENAI_API_KEY[-4:]}")
    logger.info(f"[OpenAI TTS] CONFIGURED - Key: {settings.OPENAI_API_KEY[:7]}...")
else:
    print(f"❌ Status: NOT CONFIGURED")
    print(f"⚠️  Add OPENAI_API_KEY to backend/.env")
    logger.warning("[OpenAI TTS] NOT CONFIGURED")

# Check Google Cloud TTS
print("\n📌 Google Cloud TTS:")
google_key_exists = bool(settings.GOOGLE_CLOUD_API_KEY)
google_is_placeholder = settings.GOOGLE_CLOUD_API_KEY == "your-google-cloud-api-key-here" if settings.GOOGLE_CLOUD_API_KEY else False
google_configured = google_key_exists and not google_is_placeholder

if google_configured:
    print(f"✅ Status: CONFIGURED")
    print(f"🔑 API Key: {settings.GOOGLE_CLOUD_API_KEY[:15]}...{settings.GOOGLE_CLOUD_API_KEY[-8:]}")
    logger.info(f"[Google Cloud TTS] CONFIGURED - Key: {settings.GOOGLE_CLOUD_API_KEY[:15]}...")
elif google_is_placeholder:
    print(f"❌ Status: NOT CONFIGURED (placeholder detected)")
    logger.warning("[Google Cloud TTS] NOT CONFIGURED (placeholder)")
else:
    print(f"❌ Status: NOT CONFIGURED")
    print(f"⚠️  Add GOOGLE_CLOUD_API_KEY to backend/.env")
    logger.warning("[Google Cloud TTS] NOT CONFIGURED")

print("\n" + "=" * 70 + "\n")
logger.info("=" * 70)
