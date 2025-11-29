"""WebSocket Handler for Real-Time Audio Streaming

This module provides the AudioWebSocketHandler for managing WebSocket
connections for real-time audio conversations with the MC Agent.
"""

import json
from typing import Dict, Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.audio.audio_orchestrator import AudioStreamOrchestrator
from app.audio.premium_middleware import check_audio_access
from app.audio.codec import decode_base64_to_pcm16, AudioCodecError
from app.models.user import UserProfile
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AudioWebSocketHandler:
    """Handler for real-time audio WebSocket connections with ADK integration.

    Manages:
    - WebSocket connection lifecycle
    - OAuth authentication validation
    - Premium tier gating
    - Bidirectional audio streaming
    - Error handling and graceful disconnects
    """

    # Audio format constants
    INPUT_SAMPLE_RATE = 16000  # 16kHz input from client
    OUTPUT_SAMPLE_RATE = 24000  # 24kHz output from ADK

    def __init__(self):
        """Initialize the handler."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.orchestrator = AudioStreamOrchestrator()

        logger.info("AudioWebSocketHandler initialized")

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        auth_token: Optional[str] = None,
    ) -> bool:
        """Accept and register a WebSocket connection.

        Per WebSocket RFC 6455, we must accept() before close().
        This ensures proper protocol handling across all browsers.

        Args:
            websocket: WebSocket connection
            session_id: Unique session identifier
            auth_token: OAuth session token for authentication

        Returns:
            True if connection accepted, False if rejected
        """
        # IMPORTANT: Accept connection first (required by WebSocket protocol)
        await websocket.accept()

        # Validate authentication
        if not auth_token:
            logger.warning(
                "WebSocket connection rejected: No auth token",
                session_id=session_id,
            )
            await websocket.close(code=4001, reason="Authentication required")
            return False

        user_profile = await self.validate_authentication(auth_token)
        if not user_profile:
            logger.warning(
                "WebSocket connection rejected: Invalid auth",
                session_id=session_id,
            )
            await websocket.close(code=4001, reason="Invalid authentication")
            return False

        # Check premium access
        if not await self.can_connect(user_profile):
            logger.info(
                "WebSocket connection rejected: Not premium",
                session_id=session_id,
                email=user_profile.email,
            )
            await websocket.close(code=4003, reason="Premium subscription required")
            return False

        # Register connection
        self.active_connections[session_id] = websocket

        # Start audio session
        await self.orchestrator.start_session(session_id, user_profile.email)

        logger.info(
            "WebSocket connection established",
            session_id=session_id,
            email=user_profile.email,
            active_connections=len(self.active_connections),
        )

        return True

    async def disconnect(self, session_id: str) -> None:
        """Disconnect and cleanup a session.

        Args:
            session_id: Session to disconnect
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]

        await self.orchestrator.handle_disconnect(session_id)

        logger.info(
            "WebSocket connection closed",
            session_id=session_id,
            active_connections=len(self.active_connections),
        )

    async def validate_authentication(
        self,
        auth_token: str,
    ) -> Optional[UserProfile]:
        """Validate OAuth session token.

        Args:
            auth_token: OAuth session token

        Returns:
            UserProfile if valid, None otherwise
        """
        try:
            from app.middleware.oauth_auth import validate_session_token
            from app.services.user_service import get_user_by_email

            # Validate the session token
            session_data = validate_session_token(auth_token)
            if not session_data:
                return None

            email = session_data.get("email")
            if not email:
                return None

            # Get user profile from Firestore
            user_profile = await get_user_by_email(email)
            return user_profile

        except Exception as e:
            logger.error(
                "Authentication validation error",
                error=str(e),
            )
            return None

    async def can_connect(self, user_profile: Optional[UserProfile]) -> bool:
        """Check if user can connect to audio.

        Args:
            user_profile: User's profile

        Returns:
            True if premium user with access
        """
        access = await check_audio_access(user_profile)
        return access.allowed

    async def process_audio_message(
        self,
        session_id: str,
        audio_bytes: bytes,
    ) -> Dict[str, Any]:
        """Process incoming audio from client.

        Args:
            session_id: Session identifier
            audio_bytes: PCM16 audio data at 16kHz

        Returns:
            Processing result
        """
        try:
            result = await self.orchestrator.send_audio_chunk(session_id, audio_bytes)
            return result
        except Exception as e:
            logger.error(
                "Error processing audio message",
                session_id=session_id,
                error=str(e),
            )
            return {"error": True, "message": str(e)}

    async def handle_connection_error(
        self,
        session_id: str,
        error_message: str,
    ) -> None:
        """Handle connection error gracefully.

        Args:
            session_id: Session with error
            error_message: Error description
        """
        logger.error(
            "WebSocket connection error",
            session_id=session_id,
            error=error_message,
        )

        await self.orchestrator.handle_disconnect(session_id)

        if session_id in self.active_connections:
            del self.active_connections[session_id]

    def get_message_type(self, message: Dict[str, Any]) -> str:
        """Get the type of a WebSocket message.

        Args:
            message: Parsed JSON message

        Returns:
            Message type string
        """
        return message.get("type", "unknown")

    def get_output_sample_rate(self) -> int:
        """Get output audio sample rate.

        Returns:
            24000 Hz (ADK Live API output format)
        """
        return self.OUTPUT_SAMPLE_RATE

    async def handle_message(
        self,
        websocket: WebSocket,
        session_id: str,
        message: Dict[str, Any],
    ) -> None:
        """Handle incoming WebSocket message.

        Args:
            websocket: WebSocket connection
            session_id: Session identifier
            message: Parsed JSON message
        """
        msg_type = self.get_message_type(message)

        try:
            if msg_type == "audio/pcm":
                await self._handle_audio_message(websocket, session_id, message)

            elif msg_type == "text":
                await self._handle_text_message(websocket, session_id, message)

            elif msg_type == "control":
                await self._handle_control_message(websocket, session_id, message)

            else:
                await websocket.send_json({
                    "type": "error",
                    "code": "UNSUPPORTED_MESSAGE_TYPE",
                    "message": f"Unsupported message type: {msg_type}",
                })

        except Exception as e:
            logger.error(
                "Error handling message",
                session_id=session_id,
                message_type=msg_type,
                error=str(e),
            )
            await websocket.send_json({
                "type": "error",
                "code": "PROCESSING_ERROR",
                "message": "Error processing message",
            })

    async def _handle_audio_message(
        self,
        websocket: WebSocket,
        session_id: str,
        message: Dict[str, Any],
    ) -> None:
        """Handle audio/pcm message.

        Args:
            websocket: WebSocket connection
            session_id: Session identifier
            message: Audio message with base64 data
        """
        encoded_audio = message.get("audio")
        if not encoded_audio:
            await websocket.send_json({
                "type": "error",
                "code": "MISSING_AUDIO",
                "message": "Missing audio data in message",
            })
            return

        try:
            # Decode base64 to PCM bytes
            audio_bytes = decode_base64_to_pcm16(encoded_audio)

            # Process through orchestrator
            result = await self.process_audio_message(session_id, audio_bytes)

            if result.get("error"):
                await websocket.send_json({
                    "type": "error",
                    "code": "AUDIO_PROCESSING_ERROR",
                    "message": result.get("message", "Failed to process audio"),
                })

        except AudioCodecError as e:
            logger.warning(
                "Audio codec error",
                session_id=session_id,
                error=str(e),
            )
            await websocket.send_json({
                "type": "error",
                "code": "DECODE_ERROR",
                "message": str(e),
            })
        except Exception as e:
            logger.error(
                "Unexpected error processing audio",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await websocket.send_json({
                "type": "error",
                "code": "INTERNAL_ERROR",
                "message": "Internal error processing audio",
            })

    async def _handle_text_message(
        self,
        websocket: WebSocket,
        session_id: str,
        message: Dict[str, Any],
    ) -> None:
        """Handle text message (for mixed mode).

        Args:
            websocket: WebSocket connection
            session_id: Session identifier
            message: Text message
        """
        text = message.get("text", "")
        logger.debug(
            "Text message received",
            session_id=session_id,
            text_length=len(text),
        )
        # Text messages can be forwarded to orchestrator for processing

    async def _handle_control_message(
        self,
        websocket: WebSocket,
        session_id: str,
        message: Dict[str, Any],
    ) -> None:
        """Handle control message (start/stop listening).

        Args:
            websocket: WebSocket connection
            session_id: Session identifier
            message: Control message with action
        """
        action = message.get("action")

        if action == "start_listening":
            logger.debug("Start listening", session_id=session_id)
            await websocket.send_json({
                "type": "control",
                "action": "listening_started",
            })

        elif action == "stop_listening":
            logger.debug("Stop listening", session_id=session_id)
            await websocket.send_json({
                "type": "control",
                "action": "listening_stopped",
            })

        else:
            await websocket.send_json({
                "type": "error",
                "code": "UNKNOWN_ACTION",
                "message": f"Unknown control action: {action}",
            })


# Singleton handler instance
audio_handler = AudioWebSocketHandler()


async def audio_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    auth_token: Optional[str] = None,
) -> None:
    """WebSocket endpoint for real-time audio streaming.

    This endpoint:
    1. Validates OAuth authentication
    2. Checks premium tier access
    3. Manages bidirectional audio streaming
    4. Handles disconnects gracefully

    Args:
        websocket: WebSocket connection
        session_id: Unique session identifier
        auth_token: OAuth session token
    """
    # Connect with authentication
    connected = await audio_handler.connect(websocket, session_id, auth_token)
    if not connected:
        return

    try:
        # Main message loop
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await audio_handler.handle_message(websocket, session_id, message)

    except WebSocketDisconnect:
        logger.info("Client disconnected normally", session_id=session_id)

    except Exception as e:
        logger.error(
            "WebSocket error",
            session_id=session_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        await audio_handler.handle_connection_error(session_id, str(e))

    finally:
        await audio_handler.disconnect(session_id)
