from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "SEO Studio"
    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./seo_studio.db"
    
    CHECK_INTERVAL_HOURS: int = 24
    USER_AGENT: str = "Mozilla/5.0"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
