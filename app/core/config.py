from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "SEO Studio"
    SECRET_KEY: str = "secret"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = ""
    SESSION_COOKIE_NAME: str = "seo_session"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 7
    PORT: int = 8090

    DATABASE_URL: str = "sqlite+aiosqlite:///./seo_studio.db"

    CHECK_INTERVAL_HOURS: int = 2
    USER_AGENT: str = "Mozilla/5.0"

    HTTP_CONCURRENCY: int = 5
    HTTP_CACHE_TTL_SECONDS: int = 60 * 60

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_USE_TLS: bool = True

    DEFAULT_PLAN: str = "pro"
    TESTING: bool = False

    AI_PROVIDER: str = "auto"
    AI_MODEL: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    AI_TIMEOUT_SECONDS: float = 8.0

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
