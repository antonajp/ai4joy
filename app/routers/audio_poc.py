"""Router for audio streaming PoC endpoints"""

from fastapi import APIRouter, WebSocket, status
from datetime import datetime
from typing import Dict, Any

from app.config import get_settings
from app.utils.logger import get_logger
from app.audio.poc_websocket import audio_websocket_endpoint

router = APIRouter(prefix="/api/audio/poc", tags=["audio-poc"])
logger = get_logger(__name__)
settings = get_settings()


@router.get("/health", status_code=status.HTTP_200_OK)
async def audio_poc_health() -> Dict[str, Any]:
    """
    Health check for audio PoC service.

    Returns:
        200 OK with service status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "audio-poc",
        "version": "0.1.0-poc",
        "features": {
            "websocket": True,
            "audio_codec": True,
            "adk_integration": False
        }
    }


@router.websocket("/ws/{session_id}")
async def websocket_audio_poc(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time audio streaming PoC.

    Path: /ws/audio/poc/{session_id}

    Message format:
    ```json
    {
        "type": "text/plain",
        "text": "Hello, world!"
    }
    ```
    or
    ```json
    {
        "type": "audio/pcm",
        "audio": "base64-encoded-pcm16-data"
    }
    ```

    Response format matches input type with added latency metrics.
    """
    logger.info("WebSocket connection initiated", session_id=session_id)
    await audio_websocket_endpoint(websocket, session_id)
