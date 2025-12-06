"""WebSocket Handler for Real-Time Audio Streaming

This module provides the AudioWebSocketHandler for managing WebSocket
connections for real-time audio conversations with the MC Agent.

Phase 3 - IQS-65: Enhanced with freemium session tracking.
"""

import asyncio
import base64
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
        self.active_user_emails: Dict[str, str] = (
            {}
        )  # session_id -> email mapping for cleanup
        self.orchestrator = AudioStreamOrchestrator()

        logger.info("AudioWebSocketHandler initialized")

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        auth_token: Optional[str] = None,
        game_name: Optional[str] = None,
    ) -> bool:
        """Accept and register a WebSocket connection.

        Per WebSocket RFC 6455, we must accept() before close().
        This ensures proper protocol handling across all browsers.

        Args:
            websocket: WebSocket connection
            session_id: Unique session identifier
            auth_token: OAuth session token for authentication
            game_name: Selected game name for scene context

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

        # Register connection and store user email for session tracking
        self.active_connections[session_id] = websocket
        self.active_user_emails[session_id] = user_profile.email

        # IQS-81: Check for existing session state in Firestore to support reconnection
        # If session exists with turn_count > 0, this is a reconnection
        starting_turn_count = 0
        is_reconnect = False

        try:
            from app.services.session_manager import get_session_manager

            session_manager = get_session_manager()
            existing_session = await session_manager.get_session(session_id)

            if existing_session and existing_session.turn_count > 0:
                starting_turn_count = existing_session.turn_count
                is_reconnect = True
                logger.info(
                    "Resuming audio session from Firestore state",
                    session_id=session_id,
                    turn_count=starting_turn_count,
                    is_reconnect=is_reconnect,
                )
        except Exception as e:
            logger.warning(
                "Could not retrieve existing session state, starting fresh",
                session_id=session_id,
                error=str(e),
            )

        # Start audio session with user_id for ADK run_live
        await self.orchestrator.start_session(
            session_id,
            user_profile.user_id,
            user_profile.email,
            game_name,
            starting_turn_count=starting_turn_count,
            is_reconnect=is_reconnect,
        )

        logger.info(
            "WebSocket connection established",
            session_id=session_id,
            user_id=user_profile.user_id,
            email=user_profile.email,
            game=game_name,
            active_connections=len(self.active_connections),
        )

        return True

    async def disconnect(self, session_id: str) -> None:
        """Disconnect and cleanup a session.

        Phase 3 - IQS-65: Increments session counter for freemium users.

        Args:
            session_id: Session to disconnect
        """
        # Track session completion for freemium users
        user_email = self.active_user_emails.get(session_id)
        if user_email:
            try:
                from app.services.freemium_session_limiter import (
                    increment_session_count,
                )

                # Increment session count (only applies to freemium users)
                success = await increment_session_count(user_email)
                if success:
                    logger.info(
                        "Session completion tracked",
                        session_id=session_id,
                        email=user_email,
                    )
            except Exception as e:
                logger.error(
                    "Failed to track session completion",
                    session_id=session_id,
                    email=user_email,
                    error=str(e),
                )

            # Cleanup email mapping
            del self.active_user_emails[session_id]

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
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "UNSUPPORTED_MESSAGE_TYPE",
                        "message": f"Unsupported message type: {msg_type}",
                    }
                )

        except Exception as e:
            logger.error(
                "Error handling message",
                session_id=session_id,
                message_type=msg_type,
                error=str(e),
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "PROCESSING_ERROR",
                    "message": "Error processing message",
                }
            )

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
        logger.info(
            "Received audio message from client",
            session_id=session_id,
            has_audio=bool(encoded_audio),
            audio_length=len(encoded_audio) if encoded_audio else 0,
        )
        if not encoded_audio:
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "MISSING_AUDIO",
                    "message": "Missing audio data in message",
                }
            )
            return

        try:
            # Decode base64 to PCM bytes
            audio_bytes = decode_base64_to_pcm16(encoded_audio)

            # Process through orchestrator
            result = await self.process_audio_message(session_id, audio_bytes)

            if result.get("error"):
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "AUDIO_PROCESSING_ERROR",
                        "message": result.get("message", "Failed to process audio"),
                    }
                )

        except AudioCodecError as e:
            logger.warning(
                "Audio codec error",
                session_id=session_id,
                error=str(e),
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "DECODE_ERROR",
                    "message": str(e),
                }
            )
        except Exception as e:
            logger.error(
                "Unexpected error processing audio",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "INTERNAL_ERROR",
                    "message": "Internal error processing audio",
                }
            )

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
        """Handle control message (start/stop listening, agent switching).

        For push-to-talk, we send activity signals to the ADK Live API:
        - start_listening -> send_activity_start (user started speaking)
        - stop_listening -> send_activity_end (user finished speaking)

        For multi-agent coordination:
        - switch_to_partner -> transition from MC to Partner for scene work
        - switch_to_mc -> transition from Partner back to MC for hosting

        Args:
            websocket: WebSocket connection
            session_id: Session identifier
            message: Control message with action
        """
        action = message.get("action")

        if action == "start_listening":
            logger.info(
                "Start listening - sending activity_start", session_id=session_id
            )
            # Signal to ADK that user is starting to speak
            await self.orchestrator.send_activity_start(session_id)
            await websocket.send_json(
                {
                    "type": "control",
                    "action": "listening_started",
                }
            )

        elif action == "stop_listening":
            logger.info("Stop listening - sending activity_end", session_id=session_id)
            # Signal to ADK that user has finished speaking
            # This triggers the agent to process the audio and respond
            await self.orchestrator.send_activity_end(session_id)
            await websocket.send_json(
                {
                    "type": "control",
                    "action": "listening_stopped",
                }
            )

        elif action == "switch_to_partner":
            logger.info("Switching to Partner Agent", session_id=session_id)
            result = await self.orchestrator.start_scene_with_partner(session_id)

            if result.get("error"):
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "AGENT_SWITCH_FAILED",
                        "message": result.get("message", "Failed to switch to Partner"),
                    }
                )
            else:
                # Notify frontend of agent switch
                await websocket.send_json(
                    {
                        "type": "agent_switch",
                        "agent": "partner",
                        "phase": result.get("phase", 1),
                    }
                )
                logger.info(
                    "Agent switched to Partner",
                    session_id=session_id,
                    phase=result.get("phase"),
                )

        elif action == "switch_to_mc":
            logger.info("Switching to MC Agent", session_id=session_id)
            result = await self.orchestrator.switch_to_mc(session_id)

            if result.get("error"):
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "AGENT_SWITCH_FAILED",
                        "message": result.get("message", "Failed to switch to MC"),
                    }
                )
            else:
                # Notify frontend of agent switch
                await websocket.send_json(
                    {
                        "type": "agent_switch",
                        "agent": "mc",
                    }
                )
                logger.info("Agent switched to MC", session_id=session_id)

        else:
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "UNKNOWN_ACTION",
                    "message": f"Unknown control action: {action}",
                }
            )


# Singleton handler instance
audio_handler = AudioWebSocketHandler()


async def _stream_responses_to_client(
    websocket: WebSocket,
    session_id: str,
    orchestrator: AudioStreamOrchestrator,
) -> None:
    """Background task to stream ADK responses back to the client.

    IQS-81: This task now automatically restarts the run_live() loop when it
    completes (which can happen due to Gemini Live API timeouts or errors).
    This ensures continuous audio streaming without losing session context.

    Args:
        websocket: WebSocket connection
        session_id: Session identifier
        orchestrator: Audio orchestrator instance
    """
    restart_count = 0
    max_restarts = 10  # Prevent infinite restart loops
    restart_delay = 1.0  # Seconds to wait between restarts

    while restart_count < max_restarts:
        try:
            stream_ended_normally = False

            async for response in orchestrator.stream_responses(session_id):
                response_type = response.get("type")

                if response_type == "audio":
                    # Encode audio bytes to base64 for transmission
                    audio_data = response.get("data")
                    if audio_data:
                        if isinstance(audio_data, bytes):
                            encoded_audio = base64.b64encode(audio_data).decode("utf-8")
                        else:
                            encoded_audio = audio_data

                        await websocket.send_json(
                            {
                                "type": "audio",
                                "data": encoded_audio,
                                "sample_rate": 24000,
                            }
                        )

                elif response_type == "transcription":
                    await websocket.send_json(
                        {
                            "type": "transcription",
                            "text": response.get("text", ""),
                            "role": response.get("role", "agent"),
                            "agent": response.get("agent", "mc"),  # Include agent type
                            "is_final": response.get("is_final", True),
                        }
                    )

                elif response_type == "error":
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "STREAM_ERROR",
                            "message": response.get("message", "Unknown error"),
                        }
                    )

                elif response_type == "tool_call":
                    logger.debug(
                        "Tool call in response stream",
                        session_id=session_id,
                        tool_name=response.get("name"),
                    )

                elif response_type == "tool_result":
                    logger.debug(
                        "Tool result in response stream",
                        session_id=session_id,
                    )

                elif response_type == "room_vibe":
                    # Forward audience reaction to frontend for visual display
                    await websocket.send_json(
                        {
                            "type": "room_vibe",
                            "analysis": response.get("analysis", ""),
                            "mood_metrics": response.get("mood_metrics", {}),
                            "timestamp": response.get("timestamp"),
                        }
                    )

                    logger.info(
                        "Room vibe sent to client",
                        session_id=session_id,
                        analysis_preview=response.get("analysis", "")[:50],
                    )

                elif response_type == "turn_complete":
                    # Forward turn completion to client for UI updates
                    turn_data = {
                        "type": "turn_complete",
                        "turn_count": response.get("turn_count", 0),
                        "phase": response.get("phase", 1),
                        "agent": response.get("agent", "mc"),
                    }

                    # Include phase change notification if applicable
                    if response.get("phase_changed"):
                        turn_data["phase_changed"] = True

                    await websocket.send_json(turn_data)

                    logger.info(
                        "Turn complete sent to client",
                        session_id=session_id,
                        turn_count=response.get("turn_count"),
                        phase=response.get("phase"),
                        phase_changed=response.get("phase_changed", False),
                        agent=response.get("agent"),
                    )

                elif response_type == "agent_switch":
                    # Agent has switched (MC -> Partner or Partner -> MC)
                    await websocket.send_json(
                        {
                            "type": "agent_switch",
                            "from_agent": response.get("from_agent"),
                            "to_agent": response.get("to_agent"),
                            "phase": response.get("phase", 1),
                        }
                    )

                    logger.info(
                        "Agent switch sent to client",
                        session_id=session_id,
                        from_agent=response.get("from_agent"),
                        to_agent=response.get("to_agent"),
                        phase=response.get("phase"),
                    )

                elif response_type == "agent_switch_pending":
                    # Agent switch is pending (tool call detected)
                    await websocket.send_json(
                        {
                            "type": "agent_switch_pending",
                            "from_agent": response.get("from_agent"),
                            "to_agent": response.get("to_agent"),
                            "game_name": response.get("game_name"),
                            "scene_premise": response.get("scene_premise"),
                            "reason": response.get("reason"),
                        }
                    )

                    logger.info(
                        "Agent switch pending sent to client",
                        session_id=session_id,
                        from_agent=response.get("from_agent"),
                        to_agent=response.get("to_agent"),
                    )

            # Stream ended normally (run_live completed)
            stream_ended_normally = True

            # IQS-81: Check if session is still active before restarting
            if not orchestrator.is_session_active(session_id):
                logger.info(
                    "Session no longer active, stopping stream restart loop",
                    session_id=session_id,
                    restart_count=restart_count,
                )
                break

            # IQS-81: run_live() completed - restart to maintain continuous streaming
            restart_count += 1
            logger.warning(
                "run_live stream ended, restarting to maintain session",
                session_id=session_id,
                restart_count=restart_count,
                max_restarts=max_restarts,
            )

            # Notify client about the stream restart
            await websocket.send_json(
                {
                    "type": "stream_restart",
                    "message": "Audio stream restarting - session continues",
                    "restart_count": restart_count,
                }
            )

            # Brief delay before restart to prevent tight loops
            await asyncio.sleep(restart_delay)

            # Reinitialize the session queue to get a fresh run_live instance
            await orchestrator.reinitialize_session_for_restart(session_id)

        except asyncio.CancelledError:
            logger.debug("Response streaming cancelled", session_id=session_id)
            raise

        except Exception as e:
            logger.error(
                "Error streaming responses to client",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
                restart_count=restart_count,
            )

            # Check if we should retry
            restart_count += 1
            if restart_count < max_restarts:
                logger.info(
                    "Retrying stream after error",
                    session_id=session_id,
                    restart_count=restart_count,
                )
                await asyncio.sleep(restart_delay)

                # Try to reinitialize session
                try:
                    await orchestrator.reinitialize_session_for_restart(session_id)
                except Exception as reinit_error:
                    logger.error(
                        "Failed to reinitialize session for restart",
                        session_id=session_id,
                        error=str(reinit_error),
                    )
                    break
            else:
                break

    if restart_count >= max_restarts:
        logger.error(
            "Max stream restarts reached, stopping",
            session_id=session_id,
            restart_count=restart_count,
        )
        await websocket.send_json(
            {
                "type": "error",
                "code": "MAX_RESTARTS_REACHED",
                "message": "Audio stream has been restarted too many times. Please refresh the page.",
            }
        )


async def audio_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    auth_token: Optional[str] = None,
    game_name: Optional[str] = None,
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
        game_name: Selected game name for scene context
    """
    # Connect with authentication
    connected = await audio_handler.connect(
        websocket, session_id, auth_token, game_name
    )
    if not connected:
        return

    # Start background task to stream responses from ADK to client
    response_task = asyncio.create_task(
        _stream_responses_to_client(
            websocket,
            session_id,
            audio_handler.orchestrator,
        )
    )

    try:
        # Main message loop - receives audio from client
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
        # Cancel the response streaming task
        response_task.cancel()
        try:
            await response_task
        except asyncio.CancelledError:
            pass

        await audio_handler.disconnect(session_id)
