"""
Improv Olympics - Main FastAPI Application

This application provides the backend infrastructure for the Improv Olympics
AI-powered social gym, featuring:

- Google OAuth 2.0 authentication
- Per-user rate limiting (10 sessions/day, 3 concurrent)
- Session management with Firestore persistence
- ADK agent integration with Gemini models
- Workload Identity for secure API access
- OpenTelemetry observability with Cloud Trace integration
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import sys

from app.config import get_settings
from app.utils.logger import get_logger
from app.middleware.oauth_auth import OAuthSessionMiddleware
from app.middleware.performance import PerformanceMiddleware
from app.services.adk_observability import initialize_adk_observability, get_adk_observability
from app.routers import health, sessions, agent, auth, static

settings = get_settings()

# Initialize OpenTelemetry BEFORE creating logger so trace context is available
adk_obs = initialize_adk_observability(enabled=settings.otel_enabled)

logger = get_logger(__name__, level=settings.log_level)

app = FastAPI(
    title="Improv Olympics API",
    description="AI-powered social gym for rebuilding collaboration skills",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

logger.info(
    "Application starting",
    app_name=settings.app_name,
    gcp_project=settings.gcp_project_id,
    debug=settings.debug
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ai4joy.org", "https://www.ai4joy.org", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Starlette SessionMiddleware for OAuth state management
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key or "dev-secret-key-change-in-production",
    max_age=3600  # 1 hour for OAuth state
)

app.add_middleware(OAuthSessionMiddleware)

# Add performance tracking middleware (includes trace ID propagation)
app.add_middleware(PerformanceMiddleware, slow_request_threshold=5.0)

logger.info("OAuth session authentication and performance middleware registered")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(agent.router)
app.include_router(static.router)

logger.info("All routers registered")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later."
        }
    )


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(
        "Application startup complete",
        python_version=sys.version,
        project=settings.gcp_project_id,
        firestore_db=settings.firestore_database
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event - flush OpenTelemetry data"""
    logger.info("Application shutting down")

    # Flush OpenTelemetry data before shutdown
    obs = get_adk_observability()
    if obs:
        obs.shutdown()


# Root endpoint is now handled by static router to serve index.html


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        log_level=settings.log_level.lower(),
        access_log=True
    )
