"""Router for Audio WebSocket Endpoint

This router provides the production audio WebSocket endpoint at /ws/audio/{session_id}
for premium users to have voice conversations with the MC Agent.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, WebSocket, Request, Depends, HTTPException, status, Query

from app.audio.premium_middleware import check_audio_access, get_fallback_mode
from app.audio.websocket_handler import audio_websocket_endpoint
from app.config import get_settings
from app.models.user import UserProfile
from app.services.user_service import get_user_by_email
from app.utils.logger import get_logger

router = APIRouter(prefix="/ws", tags=["audio"])
logger = get_logger(__name__)
settings = get_settings()


async def get_user_from_session(request: Request) -> Optional[UserProfile]:
    """Get user profile from session.

    This is used for HTTP endpoints. WebSocket uses auth_token.

    Args:
        request: FastAPI request

    Returns:
        UserProfile if authenticated, None otherwise
    """
    email = getattr(request.state, "user_email", None)
    if not email:
        return None

    return await get_user_by_email(email)


async def require_premium_audio(
    user: Optional[UserProfile] = Depends(get_user_from_session),
) -> UserProfile:
    """Dependency to require premium audio access.

    Args:
        user: User from session

    Returns:
        UserProfile if allowed

    Raises:
        HTTPException: If not allowed
    """
    access = await check_audio_access(user)

    if not access.allowed:
        fallback = get_fallback_mode(user)
        raise HTTPException(
            status_code=access.status_code or 403,
            detail={
                "error": access.error,
                "fallback_mode": fallback.mode,
                "fallback_message": fallback.message,
            },
        )

    return user


@router.websocket("/audio/{session_id}")
async def websocket_audio(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None, description="OAuth session token"),
):
    """WebSocket endpoint for real-time audio streaming.

    Path: /ws/audio/{session_id}

    Query Parameters:
        token: OAuth session token for authentication

    Message Protocol:

    **Client -> Server:**
    ```json
    {
        "type": "audio/pcm",
        "audio": "base64-encoded-pcm16-data"
    }
    ```
    or
    ```json
    {
        "type": "text",
        "text": "Hello, MC!"
    }
    ```
    or
    ```json
    {
        "type": "control",
        "action": "start_listening" | "stop_listening"
    }
    ```

    **Server -> Client:**
    ```json
    {
        "type": "audio",
        "data": "base64-encoded-pcm16-data",
        "sample_rate": 24000
    }
    ```
    or
    ```json
    {
        "type": "transcription",
        "text": "Hello!",
        "is_final": true,
        "role": "agent"
    }
    ```
    or
    ```json
    {
        "type": "error",
        "code": "ERROR_CODE",
        "message": "Error description"
    }
    ```
    """
    logger.info(
        "WebSocket audio connection initiated",
        session_id=session_id,
        has_token=token is not None,
    )

    await audio_websocket_endpoint(websocket, session_id, token)


# Health check endpoint for audio service
audio_health_router = APIRouter(prefix="/api/audio", tags=["audio"])


@audio_health_router.get("/health", status_code=status.HTTP_200_OK)
async def audio_health() -> Dict[str, Any]:
    """Health check for audio service.

    Returns:
        200 OK with service status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "audio",
        "version": "1.0.0",
        "features": {
            "websocket": True,
            "adk_live_api": True,
            "voice_synthesis": True,
            "transcription": True,
        },
        "voice": "Aoede",
    }


@audio_health_router.get("/access-check")
async def check_access(
    user: Optional[UserProfile] = Depends(get_user_from_session),
) -> Dict[str, Any]:
    """Check if current user has audio access.

    Returns:
        Access status and fallback info if denied
    """
    access = await check_audio_access(user)

    if access.allowed:
        return {
            "allowed": True,
            "remaining_seconds": access.remaining_seconds,
            "warning": access.warning,
        }
    else:
        fallback = get_fallback_mode(user)
        return {
            "allowed": False,
            "error": access.error,
            "fallback_mode": fallback.mode,
            "fallback_message": fallback.message,
        }
