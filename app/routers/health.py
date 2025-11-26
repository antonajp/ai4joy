"""Health Check Endpoints"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Dict, Any, Union
from google.cloud import firestore  # type: ignore[attr-defined]

from app.config import get_settings
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    Bypasses IAP authentication for load balancer health checks.

    Returns:
        200 OK with basic status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": settings.app_name,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Union[Dict[str, Any], JSONResponse]:
    """
    Readiness check with dependency validation.
    Checks connectivity to Firestore and other critical services.

    Returns:
        200 OK if all dependencies are healthy
        503 Service Unavailable if any dependency fails
    """
    checks = {"firestore": False, "vertexai": False}

    try:
        db = firestore.Client(
            project=settings.gcp_project_id, database=settings.firestore_database
        )

        test_collection = db.collection("_health_check")
        test_doc = test_collection.document("ping")
        test_doc.set({"timestamp": datetime.utcnow().isoformat()})
        test_doc.delete()

        checks["firestore"] = True
        logger.debug("Firestore connectivity check passed")

    except Exception as e:
        logger.error("Firestore connectivity check failed", error=str(e))

    try:
        import vertexai

        vertexai.init(project=settings.gcp_project_id, location=settings.gcp_location)
        checks["vertexai"] = True
        logger.debug("VertexAI initialization check passed")

    except Exception as e:
        logger.error("VertexAI initialization check failed", error=str(e))

    all_healthy = all(checks.values())

    response = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
    }

    if not all_healthy:
        logger.warning("Readiness check failed", checks=checks)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=response
        )

    return response
