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

    CHECK_INTERVAL_HOURS: int = 24
    USER_AGENT: str = "Mozilla/5.0"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
