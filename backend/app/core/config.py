from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pydantic import field_validator
import json

class Settings(BaseSettings):
    APP_NAME: str = "Abhinav Group AI Intelligence Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/oauth/callback"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GMAIL_LABEL: str = "Director's AI Assistant"
    ALLOWED_ORIGINS: str = "http://localhost:8000"
    MAX_ATTACHMENT_SIZE_MB: int = 100
    UPLOAD_DIR: str = "./uploads"
    RATE_LIMIT_PER_MINUTE: int = 60
    # Access control (Option A): comma-separated allowlist of emails permitted to register.
    # Empty string means registration is fully closed (fail-safe default).
    ALLOWED_REGISTRATION_EMAILS: str = ""
    FIRST_DIRECTOR_EMAIL: str = ""
    FIRST_DIRECTOR_NAME: str = ""
    FIRST_DIRECTOR_PASSWORD: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [x.strip() for x in self.ALLOWED_ORIGINS.split(",") if x.strip()]

    @property
    def allowed_registration_emails_list(self) -> list[str]:
        return [x.strip().lower() for x in self.ALLOWED_REGISTRATION_EMAILS.split(",") if x.strip()]

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

@lru_cache()
def get_settings() -> Settings:
    return Settings()
