from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Encryption
    CREDENTIAL_ENCRYPTION_KEY: str

    # WhatsApp (Gupshup)
    GUPSHUP_API_KEY: str
    GUPSHUP_APP_NAME: str
    GUPSHUP_SOURCE_NUMBER: str

    # Email (Resend)
    RESEND_API_KEY: str
    EMAIL_FROM: str = "renewals@veekayfinserve.com"
    EMAIL_FROM_NAME: str = "Veekay Finserve"

    # Agent alerts
    AGENT_ALERT_EMAILS: str = ""  # comma-separated

    # Scheduler
    SCHEDULER_TIMEZONE: str = "Asia/Kolkata"

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"

    @property
    def agent_alert_email_list(self) -> List[str]:
        return [e.strip() for e in self.AGENT_ALERT_EMAILS.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
