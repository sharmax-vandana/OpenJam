import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    """Application configuration."""

    # YouTube Data API v3 (free key from https://console.cloud.google.com)
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./openjam.db")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")

    # CORS configuration
    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8000",
    ).split(",")

    # Token revocation set (in production, use Redis)
    REVOKED_TOKENS: set = set()


settings = Settings()

if not settings.YOUTUBE_API_KEY:
    logger.warning("⚠️  YOUTUBE_API_KEY not set — YouTube video ID lookup will fail")
    logger.warning("    Get a free key at: https://console.cloud.google.com (YouTube Data API v3)")
