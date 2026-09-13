"""Backend configuration management using Pydantic Settings."""

from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


# Base directories
BACKEND_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BACKEND_DIR.parent
DEFAULT_UPLOAD_DIR = BACKEND_DIR / "uploads" / "evidence"


class Settings(BaseSettings):
    """Application settings and environment configuration."""

    PROJECT_NAME: str = "okDRIVER Pothole API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database configuration
    # Primary: PostgreSQL. Default URL uses psycopg2 / psycopg
    DATABASE_URL: str = "postgresql+psycopg2://postgres:1230@localhost:5432/pothole_detection"

    # Automatic fallback to SQLite if PostgreSQL is unreachable during local dev / testing
    ENABLE_SQLITE_FALLBACK: bool = True
    SQLITE_FALLBACK_URL: str = f"sqlite:///{BACKEND_DIR / 'okdriver_dev.db'}"

    # Storage paths
    UPLOAD_DIR: Path = DEFAULT_UPLOAD_DIR
    STATIC_URL_PREFIX: str = "/static/evidence"

    # CORS configuration
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Model / detection confidence threshold
    DEFAULT_CONF_THRESHOLD: float = 0.25

    # ── SMTP Email Settings ──────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_USE_TLS: bool = True   # STARTTLS on port 587

    # ── Telegram & Frontend Settings ─────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = "8837174299:AAGbvuRoW8h13Wt46Dhz_T_TN0x4MCbWNSc"
    TELEGRAM_DEFAULT_CHAT_ID: Optional[str] = None
    FRONTEND_URL: str = "http://127.0.0.1:3000"

    # ── Cloudflare R2 / AWS S3 Object Storage ────────────────────────────────
    ENABLE_R2_STORAGE: bool = True  # Enable Cloudflare R2 remote storage
    R2_ENDPOINT_URL: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = "potholeimage"
    R2_PUBLIC_URL_PREFIX: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure uploads directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
