"""Application Configuration Management"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    app_name: str = "Improv Olympics"
    debug: bool = False

    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "coherent-answer-479115-e1")
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

    # OAuth Configuration
    oauth_client_id: str = os.getenv("OAUTH_CLIENT_ID", "")
    oauth_client_secret: str = os.getenv("OAUTH_CLIENT_SECRET", "")
    oauth_redirect_uri: str = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080/auth/callback")
    session_secret_key: str = os.getenv("SESSION_SECRET_KEY", "")

    # Access Control - Comma-separated list of allowed email addresses
    # Example: "user1@example.com,user2@example.com"
    allowed_users: str = os.getenv("ALLOWED_USERS", "")

    @property
    def allowed_users_list(self) -> list[str]:
        """Parse comma-separated allowed users into a list"""
        if not self.allowed_users:
            return []
        return [email.strip() for email in self.allowed_users.split(",") if email.strip()]

    # Authentication bypass paths (no auth required)
    auth_bypass_paths: list = ["/health", "/ready", "/auth/login", "/auth/callback", "/auth/logout", "/"]

    # IAP Header Configuration
    # These headers are injected by Google Identity-Aware Proxy (IAP).
    # FastAPI/Starlette normalizes all headers to lowercase, so we use lowercase here.
    # IAP JWT validation provides defense-in-depth to prevent header spoofing.
    # See: https://cloud.google.com/iap/docs/signed-headers-howto
    iap_header_email: str = "x-goog-authenticated-user-email"
    iap_header_user_id: str = "x-goog-authenticated-user-id"

    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Monitoring and Observability
    otel_enabled: bool = os.getenv("OTEL_ENABLED", "true").lower() == "true"
    alert_latency_threshold: float = float(os.getenv("ALERT_LATENCY_THRESHOLD", "8.0"))
    alert_error_rate_threshold: float = float(os.getenv("ALERT_ERROR_RATE_THRESHOLD", "0.05"))
    alert_cache_hit_rate_threshold: float = float(os.getenv("ALERT_CACHE_HIT_RATE_THRESHOLD", "0.50"))

    # Performance Tuning Configuration
    perf_agent_timeout: int = int(os.getenv("PERF_AGENT_TIMEOUT", "30"))
    perf_cache_ttl: int = int(os.getenv("PERF_CACHE_TTL", "300"))
    perf_max_context_tokens: int = int(os.getenv("PERF_MAX_CONTEXT_TOKENS", "4000"))
    perf_batch_write_threshold: int = int(os.getenv("PERF_BATCH_WRITE_THRESHOLD", "5"))
    perf_max_concurrent_sessions: int = int(os.getenv("PERF_MAX_CONCURRENT_SESSIONS", "10"))
    perf_firestore_batch_size: int = int(os.getenv("PERF_FIRESTORE_BATCH_SIZE", "500"))

    class Config:
        env_file = ".env.local"  # Use .env.local for local dev
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


@lru_cache()
def get_performance_config():
    """Get performance configuration from settings"""
    from app.services.performance_tuning import PerformanceConfig

    settings = get_settings()
    return PerformanceConfig(
        agent_timeout_seconds=settings.perf_agent_timeout,
        cache_ttl_seconds=settings.perf_cache_ttl,
        max_context_tokens=settings.perf_max_context_tokens,
        batch_write_threshold=settings.perf_batch_write_threshold,
        max_concurrent_sessions_per_instance=settings.perf_max_concurrent_sessions,
        firestore_batch_size=settings.perf_firestore_batch_size
    )
