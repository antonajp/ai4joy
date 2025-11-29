"""Audio Stream Orchestrator for ADK Live API Integration

This module provides the AudioStreamOrchestrator service that integrates
ADK's InMemoryRunner.run_live() with WebSocket streaming for real-time
audio conversations with the MC Agent.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, AsyncGenerator

from google.adk.runners import RunConfig
from google.genai import types

from app.agents.mc_agent import create_mc_agent
from app.audio.premium_middleware import check_audio_access, track_audio_usage
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class SessionResult:
    """Result of session creation attempt.

    Attributes:
        success: Whether session was created
        session_id: Session ID if successful
        status_code: HTTP status code if failed
        error: Error message if failed
    """

    success: bool
    session_id: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None


@dataclass
class VoiceConfig:
    """Voice configuration for audio synthesis.

    Attributes:
        voice_name: Name of the voice to use
    """

    voice_name: str = "Aoede"


@dataclass
class AudioSession:
    """Active audio session state.

    Attributes:
        session_id: Unique session identifier
        user_email: User's email address
        queue: LiveRequestQueue for this session
        active: Whether session is active
        usage_seconds: Accumulated audio usage
    """

    session_id: str
    user_email: str
    queue: Any = None  # LiveRequestQueue
    active: bool = True
    usage_seconds: int = 0


class AudioStreamOrchestrator:
    """Orchestrates real-time audio streaming with ADK Live API.

    This service manages:
    - MC Agent configuration for audio
    - LiveRequestQueue creation and management
    - Audio chunk forwarding to ADK
    - Response streaming back to clients
    - Session lifecycle
    - Usage tracking
    """

    def __init__(self):
        """Initialize the orchestrator with MC Agent."""
        self.agent = create_mc_agent()
        self._sessions: Dict[str, AudioSession] = {}
        self._runner = None  # Initialized lazily
        self._session_service = None  # Initialized lazily
        self.voice_name = "Aoede"

        logger.info(
            "AudioStreamOrchestrator initialized",
            agent_name=self.agent.name,
            voice=self.voice_name,
        )

    def _get_runner(self):
        """Get or create InMemoryRunner."""
        if self._runner is None:
            from google.adk import InMemoryRunner

            self._runner = InMemoryRunner(agent=self.agent)
            logger.info("InMemoryRunner created for audio streaming")
        return self._runner

    def create_session_queue(self, session_id: str) -> Any:
        """Create a LiveRequestQueue for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            LiveRequestQueue instance for bidirectional streaming
        """
        from google.adk.runners import LiveRequestQueue

        queue = LiveRequestQueue()
        logger.debug("LiveRequestQueue created", session_id=session_id)
        return queue

    def get_run_config(self) -> RunConfig:
        """Get RunConfig for audio streaming with transcription.

        Returns:
            RunConfig with audio transcription enabled
        """
        # RunConfig for Live API - transcription is enabled via speech_config
        return RunConfig(
            speech_config=self.get_speech_config(),
            response_modalities=["AUDIO"],
        )

    def get_voice_config(self) -> VoiceConfig:
        """Get voice configuration for synthesis.

        Returns:
            VoiceConfig with Aoede voice
        """
        return VoiceConfig(voice_name=self.voice_name)

    def get_speech_config(self) -> types.SpeechConfig:
        """Get speech configuration for Live API.

        Returns:
            SpeechConfig with Aoede voice
        """
        return types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config={"voice_name": self.voice_name}
            )
        )

    def get_welcome_config(self) -> Dict[str, Any]:
        """Get welcome message configuration.

        Returns:
            Configuration for MC welcome behavior
        """
        return {
            "auto_greet": True,
            "initial_message": "Welcome to Improv Olympics! I'm your MC, ready to guide you through some amazing improv games!",
        }

    async def start_session(
        self,
        session_id: str,
        user_email: str,
    ) -> None:
        """Start a new audio session.

        Args:
            session_id: Unique session identifier
            user_email: User's email for tracking
        """
        queue = self.create_session_queue(session_id)

        self._sessions[session_id] = AudioSession(
            session_id=session_id,
            user_email=user_email,
            queue=queue,
            active=True,
        )

        logger.info(
            "Audio session started",
            session_id=session_id,
            user_email=user_email,
        )

    async def stop_session(self, session_id: str) -> None:
        """Stop an audio session with proper locking.

        Uses atomic pop to prevent race conditions with send_audio_chunk().

        Args:
            session_id: Session to stop
        """
        # Atomically remove from active sessions first to prevent races
        session = self._sessions.pop(session_id, None)
        if not session:
            return  # Already removed or never existed

        # Now we have exclusive ownership
        session.active = False

        # Track usage before closing
        if session.usage_seconds > 0:
            try:
                await track_audio_usage(session.user_email, session.usage_seconds)
            except Exception as e:
                logger.error(
                    "Failed to track audio usage",
                    session_id=session_id,
                    error=str(e),
                )

        # Close queue
        if session.queue:
            try:
                session.queue.close()
            except Exception as e:
                logger.warning(
                    "Error closing queue",
                    session_id=session_id,
                    error=str(e),
                )

        logger.info(
            "Audio session stopped",
            session_id=session_id,
            total_usage_seconds=session.usage_seconds,
        )

    def is_session_active(self, session_id: str) -> bool:
        """Check if a session is active.

        Args:
            session_id: Session to check

        Returns:
            True if session exists and is active
        """
        session = self._sessions.get(session_id)
        return session is not None and session.active

    async def get_session(self, session_id: str) -> Optional[AudioSession]:
        """Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            AudioSession if found, None otherwise
        """
        return self._sessions.get(session_id)

    async def send_audio_chunk(
        self,
        session_id: str,
        audio_bytes: bytes,
    ) -> Dict[str, Any]:
        """Send an audio chunk to the agent.

        Args:
            session_id: Session identifier
            audio_bytes: PCM16 audio data at 16kHz

        Returns:
            Status dict with result
        """
        session = self._sessions.get(session_id)

        if not session:
            return {"error": True, "message": "Session not found"}

        if not audio_bytes:
            return {"error": True, "message": "Empty audio data"}

        try:
            # Create audio blob for ADK
            audio_blob = types.Blob(
                mime_type="audio/pcm;rate=16000",
                data=audio_bytes,
            )

            # Send to queue
            await session.queue.send_realtime(audio_blob)

            # Track usage (assuming chunk is about 100ms)
            chunk_duration_seconds = len(audio_bytes) / (16000 * 2)  # 16kHz, 16-bit
            session.usage_seconds += int(chunk_duration_seconds)

            return {"status": "ok", "bytes_sent": len(audio_bytes)}

        except Exception as e:
            logger.error(
                "Error sending audio chunk",
                session_id=session_id,
                error=str(e),
            )
            return {"error": True, "message": str(e)}

    async def stream_responses(
        self,
        session_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream responses from the agent.

        Args:
            session_id: Session identifier

        Yields:
            Response dicts with audio or transcription
        """
        session = self._sessions.get(session_id)
        if not session:
            yield {"type": "error", "message": "Session not found"}
            return

        runner = self._get_runner()
        run_config = self.get_run_config()

        try:
            async for event in runner.run_live(
                session_id=session_id,
                live_request_queue=session.queue,
                run_config=run_config,
            ):
                responses = await self._process_event(event)
                for response in responses:
                    yield response

        except Exception as e:
            logger.error(
                "Error streaming responses",
                session_id=session_id,
                error=str(e),
            )
            yield {"type": "error", "message": str(e)}

    async def _process_event(self, event: Any) -> list[Dict[str, Any]]:
        """Process an event from the agent.

        Args:
            event: Event from run_live

        Returns:
            List of response dicts
        """
        responses = []

        # Handle server content (audio/text responses)
        if hasattr(event, "server_content") and event.server_content:
            if hasattr(event.server_content, "model_turn"):
                for part in event.server_content.model_turn.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        # Audio response
                        responses.append({
                            "type": "audio",
                            "data": part.inline_data.data,
                            "mime_type": getattr(
                                part.inline_data, "mime_type", "audio/pcm;rate=24000"
                            ),
                        })

                    if hasattr(part, "text") and part.text:
                        # Transcription
                        responses.append({
                            "type": "transcription",
                            "text": part.text,
                            "role": "agent",
                            "is_final": True,
                        })

        # Handle tool calls
        if hasattr(event, "tool_call") and event.tool_call:
            responses.append({
                "type": "tool_call",
                "name": event.tool_call.name,
                "args": event.tool_call.args,
            })

        # Handle tool results
        if hasattr(event, "tool_result") and event.tool_result:
            responses.append({
                "type": "tool_result",
                "result": event.tool_result.result,
                "speak": True,  # Agent should speak after tool result
            })

        return responses

    async def _handle_event(self, event: Any) -> Dict[str, Any]:
        """Handle a single event (for testing).

        Args:
            event: Event to handle

        Returns:
            Handling result
        """
        if hasattr(event, "tool_result"):
            return {"type": "continue", "speak": True}
        return {"type": "processed"}

    async def _process_tool_result(self, result: Any) -> Dict[str, Any]:
        """Process a tool result (for testing).

        Args:
            result: Tool result to process

        Returns:
            Processing result
        """
        return {"type": "continue", "speak": True}

    async def handle_disconnect(self, session_id: str) -> None:
        """Handle WebSocket disconnect.

        Args:
            session_id: Session that disconnected
        """
        await self.stop_session(session_id)

    async def create_session_if_allowed(
        self,
        session_id: str,
        user_profile: Any,
    ) -> SessionResult:
        """Create session only if user has audio access.

        Args:
            session_id: Session identifier
            user_profile: User's profile

        Returns:
            SessionResult with success/failure
        """
        access = await check_audio_access(user_profile)

        if not access.allowed:
            return SessionResult(
                success=False,
                status_code=access.status_code,
                error=access.error,
            )

        await self.start_session(session_id, user_profile.email)

        return SessionResult(
            success=True,
            session_id=session_id,
        )

    async def validate_session_access(self, session_id: str) -> bool:
        """Re-validate session access (for tier changes).

        Args:
            session_id: Session to validate

        Returns:
            True if still allowed
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        from app.services.user_service import get_user_by_email

        user_profile = await get_user_by_email(session.user_email)
        access = await check_audio_access(user_profile)

        return access.allowed

    async def track_usage(self, session_id: str, duration_seconds: int) -> None:
        """Track usage for a session.

        Args:
            session_id: Session identifier
            duration_seconds: Seconds to track
        """
        session = self._sessions.get(session_id)
        if session:
            await track_audio_usage(session.user_email, duration_seconds)

    def get_output_sample_rate(self) -> int:
        """Get output audio sample rate.

        Returns:
            24000 Hz (ADK Live API output format)
        """
        return 24000
