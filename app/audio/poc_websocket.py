"""WebSocket endpoint for real-time audio streaming PoC"""

import json
import time
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

from app.utils.logger import get_logger
from app.audio.codec import encode_pcm16_to_base64, decode_base64_to_pcm16

logger = get_logger(__name__)


class AudioWebSocketHandler:
    """Handler for real-time audio WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket

        logger.info(
            "WebSocket connection established",
            session_id=session_id,
            active_connections=len(self.active_connections),
        )

    def disconnect(self, session_id: str):
        """Remove WebSocket from active connections"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

        logger.info(
            "WebSocket connection closed",
            session_id=session_id,
            active_connections=len(self.active_connections),
        )

    async def handle_message(
        self, websocket: WebSocket, session_id: str, message: Dict[str, Any]
    ):
        """
        Process incoming WebSocket message and send response.

        Supported message types:
        - text/plain: Echo text back
        - audio/pcm: Decode, measure latency, echo back
        """
        msg_type = message.get("type")
        start_time = time.time()

        try:
            if msg_type == "text/plain":
                await self._handle_text_message(websocket, message, start_time)
            elif msg_type == "audio/pcm":
                await self._handle_audio_message(
                    websocket, session_id, message, start_time
                )
            else:
                await websocket.send_json(
                    {"type": "error", "error": f"Unsupported message type: {msg_type}"}
                )

        except Exception as e:
            logger.error(
                "Error handling WebSocket message",
                session_id=session_id,
                message_type=msg_type,
                error=str(e),
            )
            await websocket.send_json(
                {"type": "error", "error": "Internal server error processing message"}
            )

    async def _handle_text_message(
        self, websocket: WebSocket, message: Dict[str, Any], start_time: float
    ):
        """Handle text/plain message type - simple echo"""
        text = message.get("text", "")

        response = {
            "type": "text/plain",
            "text": f"Echo: {text}",
            "latency_ms": round((time.time() - start_time) * 1000, 2),
        }

        await websocket.send_json(response)

        logger.debug(
            "Text message processed",
            text_length=len(text),
            latency_ms=response["latency_ms"],
        )

    async def _handle_audio_message(
        self,
        websocket: WebSocket,
        session_id: str,
        message: Dict[str, Any],
        start_time: float,
    ):
        """Handle audio/pcm message type - decode, measure, echo"""
        encoded_audio = message.get("audio")

        if not encoded_audio:
            await websocket.send_json(
                {"type": "error", "error": "Missing audio data in audio/pcm message"}
            )
            return

        try:
            audio_bytes = decode_base64_to_pcm16(encoded_audio)
            decode_time = time.time()

            response_audio = encode_pcm16_to_base64(audio_bytes)
            encode_time = time.time()

            response = {
                "type": "audio/pcm",
                "audio": response_audio,
                "latency_ms": round((encode_time - start_time) * 1000, 2),
                "decode_ms": round((decode_time - start_time) * 1000, 2),
                "encode_ms": round((encode_time - decode_time) * 1000, 2),
                "audio_bytes": len(audio_bytes),
            }

            await websocket.send_json(response)

            logger.info(
                "Audio message processed",
                session_id=session_id,
                audio_bytes=len(audio_bytes),
                total_latency_ms=response["latency_ms"],
                decode_ms=response["decode_ms"],
                encode_ms=response["encode_ms"],
            )

        except Exception as e:
            logger.error(
                "Error processing audio data", session_id=session_id, error=str(e)
            )
            await websocket.send_json(
                {"type": "error", "error": "Failed to process audio data"}
            )


audio_handler = AudioWebSocketHandler()


async def audio_websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time audio streaming PoC.

    This is a proof-of-concept to:
    1. Verify WebSocket infrastructure works
    2. Test audio encoding/decoding
    3. Measure baseline WebSocket latency

    Does NOT integrate with ADK/google-genai yet.
    """
    await audio_handler.connect(websocket, session_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await audio_handler.handle_message(websocket, session_id, message)

    except WebSocketDisconnect:
        audio_handler.disconnect(session_id)
        logger.info("Client disconnected normally", session_id=session_id)

    except Exception as e:
        audio_handler.disconnect(session_id)
        logger.error(
            "WebSocket error",
            session_id=session_id,
            error=str(e),
            error_type=type(e).__name__,
        )
