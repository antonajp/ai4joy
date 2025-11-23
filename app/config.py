"""Application Configuration Management"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    app_name: str = "Improv Olympics"
    debug: bool = False

    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "improvOlympics")
    gcp_project_number: str = os.getenv("GCP_PROJECT_NUMBER", "")
    gcp_location: str = os.getenv("GCP_LOCATION", "us-central1")

    firestore_database: str = os.getenv("FIRESTORE_DATABASE", "(default)")
    firestore_sessions_collection: str = "sessions"
    firestore_user_limits_collection: str = "user_limits"

    vertexai_flash_model: str = "gemini-1.5-flash"
    vertexai_pro_model: str = "gemini-1.5-pro"

    rate_limit_daily_sessions: int = int(os.getenv("RATE_LIMIT_DAILY_SESSIONS", "10"))
    rate_limit_concurrent_sessions: int = int(os.getenv("RATE_LIMIT_CONCURRENT_SESSIONS", "3"))

    session_timeout_minutes: int = 60

    iap_header_email: str = "X-Goog-Authenticated-User-Email"
    iap_header_user_id: str = "X-Goog-Authenticated-User-ID"

    health_check_bypass_paths: list = ["/health", "/ready"]

    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
