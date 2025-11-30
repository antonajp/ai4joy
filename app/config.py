"""Application Configuration Management"""

import os
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

    # Tool Data Collections - stores game database, improv principles, and archetypes
    firestore_games_collection: str = "improv_games"
    firestore_principles_collection: str = "improv_principles"
    firestore_archetypes_collection: str = "audience_archetypes"
    firestore_sentiment_keywords_collection: str = "sentiment_keywords"

    # Model configuration
    # See: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions
    #
    # Live API model supports both text AND audio interactions, so we use it
    # as the primary model for all agents. This avoids dual maintenance.
    # Options: gemini-live-2.5-flash-preview-native-audio-09-2025 (public preview)
    #          gemini-live-2.5-flash (private GA, requires access request)
    vertexai_live_model: str = os.getenv(
        "VERTEXAI_LIVE_MODEL", "gemini-live-2.5-flash-preview-native-audio-09-2025"
    )

    # Legacy model settings (for agents that don't need audio support)
    vertexai_flash_model: str = "gemini-2.0-flash"
    vertexai_pro_model: str = "gemini-2.0-flash"  # gemini-1.5-pro deprecated April 2025

    rate_limit_daily_sessions: int = int(os.getenv("RATE_LIMIT_DAILY_SESSIONS", "10"))
    rate_limit_concurrent_sessions: int = int(
        os.getenv("RATE_LIMIT_CONCURRENT_SESSIONS", "3")
    )

    session_timeout_minutes: int = 60

    # OAuth Configuration
    oauth_client_id: str = os.getenv("OAUTH_CLIENT_ID", "")
    oauth_client_secret: str = os.getenv("OAUTH_CLIENT_SECRET", "")
    oauth_redirect_uri: str = os.getenv(
        "OAUTH_REDIRECT_URI", "http://localhost:8080/auth/callback"
    )
    session_secret_key: str = os.getenv("SESSION_SECRET_KEY", "")

    # Access Control - Comma-separated list of allowed email addresses
    # Example: "user1@example.com,user2@example.com"
    allowed_users: str = os.getenv("ALLOWED_USERS", "")

    # Firestore-based user management (Phase 0.5)
    # When enabled, uses Firestore users collection instead of ALLOWED_USERS env var
    use_firestore_auth: bool = (
        os.getenv("USE_FIRESTORE_AUTH", "false").lower() == "true"
    )
    firestore_users_collection: str = "users"

    @property
    def allowed_users_list(self) -> list[str]:
        """Parse comma-separated allowed users into a list"""
        if not self.allowed_users:
            return []
        return [
            email.strip() for email in self.allowed_users.split(",") if email.strip()
        ]

    # Authentication bypass paths (no auth required)
    auth_bypass_paths: list = [
        "/health",
        "/ready",
        "/auth/login",
        "/auth/callback",
        "/auth/logout",
        "/auth/user",
        "/auth/ws-token",
        "/",
        "/static/index.html",
        "/static/chat.html",
        "/static/styles.css",
        "/static/app.js",
    ]

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
    alert_error_rate_threshold: float = float(
        os.getenv("ALERT_ERROR_RATE_THRESHOLD", "0.05")
    )
    alert_cache_hit_rate_threshold: float = float(
        os.getenv("ALERT_CACHE_HIT_RATE_THRESHOLD", "0.50")
    )

    # ADK Session Database Configuration
    # SQLite file path for ADK session persistence
    # IMPORTANT: In Cloud Run, /tmp is ephemeral and instance-specific. Sessions created
    # in one instance won't be visible to another. The TurnOrchestrator.execute_turn()
    # method handles this by ensuring ADK sessions are created from Firestore data before
    # each turn execution. This makes SQLite effectively a local cache, with Firestore as
    # the source of truth. For production scale, consider using Cloud SQL for ADK sessions.
    adk_database_url: str = os.getenv(
        "ADK_DATABASE_URL", "sqlite+aiosqlite:////tmp/adk_sessions.db"
    )

    # ADK Memory Service Configuration
    memory_service_enabled: bool = (
        os.getenv("MEMORY_SERVICE_ENABLED", "false").lower() == "true"
    )
    agent_engine_id: str = os.getenv("AGENT_ENGINE_ID", "")
    use_in_memory_memory_service: bool = (
        os.getenv("USE_IN_MEMORY_MEMORY_SERVICE", "true").lower() == "true"
    )

    # Performance Tuning Configuration
    perf_agent_timeout: int = int(os.getenv("PERF_AGENT_TIMEOUT", "30"))
    perf_cache_ttl: int = int(os.getenv("PERF_CACHE_TTL", "300"))
    perf_max_context_tokens: int = int(os.getenv("PERF_MAX_CONTEXT_TOKENS", "4000"))
    perf_batch_write_threshold: int = int(os.getenv("PERF_BATCH_WRITE_THRESHOLD", "5"))
    perf_max_concurrent_sessions: int = int(
        os.getenv("PERF_MAX_CONCURRENT_SESSIONS", "10")
    )
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
        firestore_batch_size=settings.perf_firestore_batch_size,
    )
