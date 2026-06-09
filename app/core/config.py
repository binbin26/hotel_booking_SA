from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    DATABASE_URL: str
    APP_NAME: str = "Hotel Booking API"
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_TOKEN_COOKIE_NAME: str = "admin_session"
    ADMIN_TOKEN_COOKIE_MAX_AGE: int = 60 * 60 * 8  # 8 hours
    ADMIN_COOKIE_SECURE: bool = False

    # ── Internationalization (Babel / gettext) ─────────────────────────────
    BABEL_DEFAULT_LOCALE: str = "en"
    BABEL_TRANSLATION_DIRECTORY: str = "lang"
    SUPPORTED_LOCALES: list[str] = ["en", "vi"]
    LANGUAGE_COOKIE_NAME: str = "locale"
    LANGUAGE_COOKIE_MAX_AGE: int = 60 * 60 * 24 * 30  # 30 days

    # ── Email (SMTP invoice delivery) ────────────────────────────────────────
    APP_BASE_URL: str = "http://localhost:8000"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@hotel.com"
    SMTP_USE_TLS: bool = True
    SMTP_ENABLED: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
