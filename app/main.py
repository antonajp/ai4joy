"""
Improv Olympics - Main FastAPI Application

This application provides the backend infrastructure for the Improv Olympics
AI-powered social gym, featuring:

- Identity-Aware Proxy (IAP) authentication
- Per-user rate limiting (10 sessions/day, 3 concurrent)
- Session management with Firestore persistence
- ADK agent integration with Gemini models
- Workload Identity for secure API access
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import sys

from app.config import get_settings
from app.utils.logger import get_logger
from app.middleware.iap_auth import IAPAuthMiddleware
from app.routers import health, sessions, agent

settings = get_settings()
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
    allow_origins=["https://ai4joy.org", "https://www.ai4joy.org"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_middleware(IAPAuthMiddleware)

logger.info("IAP authentication middleware registered")

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(agent.router)

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
    """Application shutdown event"""
    logger.info("Application shutting down")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        log_level=settings.log_level.lower(),
        access_log=True
    )
