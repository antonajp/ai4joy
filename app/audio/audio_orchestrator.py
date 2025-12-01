"""Audio Stream Orchestrator for ADK Live API Integration

This module provides the AudioStreamOrchestrator service that integrates
ADK's InMemoryRunner.run_live() with WebSocket streaming for real-time
audio conversations with the MC Agent.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, AsyncGenerator

from google.adk.runners import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.genai import types

from app.agents.mc_agent import create_mc_agent_for_audio
from app.agents.partner_agent import create_partner_agent_for_audio
from app.agents.room_agent import create_room_agent_for_audio
from app.agents.stage_manager import determine_partner_phase
from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel
from app.audio.audio_mixer import AudioMixer
from app.audio.premium_middleware import check_audio_access, track_audio_usage
from app.audio.turn_manager import AgentTurnManager
from app.audio.voice_config import get_voice_config
from app.config import get_settings
from app.services.adk_session_service import get_adk_session_service
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
        user_id: ADK user identifier (for run_live)
        user_email: User's email address
        game_name: Selected game name for scene context
        queue: LiveRequestQueue for this session
        active: Whether session is active
        usage_seconds: Accumulated audio usage
        turn_count: Number of completed turns in this session
        current_agent: Current active agent type ("mc", "partner", or "room")
        turn_manager: Turn manager for agent coordination
        mc_agent: MC Agent instance for this session
        partner_agent: Partner Agent instance for this session
        room_agent: Room Agent instance for ambient commentary
        partner_phase: Current phase for Partner Agent
        pending_agent_switch: Agent to switch to after current turn (None if no switch pending)
        scene_context: Context from MC's _start_scene call for Partner
        audio_mixer: AudioMixer for combining multiple agent streams
        ambient_trigger: AmbientAudioTrigger for sentiment-based Room activation
        last_user_input: Most recent user transcription for ambient context
        last_agent_response: Most recent agent transcription for ambient context
    """

    session_id: str
    user_id: str
    user_email: str
    game_name: Optional[str] = None
    queue: Any = None  # LiveRequestQueue
    active: bool = True
    usage_seconds: int = 0
    turn_count: int = 0
    current_agent: str = "mc"  # Start with MC
    turn_manager: Optional[Any] = None  # AgentTurnManager
    mc_agent: Any = None  # MC Agent instance
    partner_agent: Any = None  # Partner Agent instance
    room_agent: Any = None  # Room Agent instance for ambient commentary
    partner_phase: int = 1  # Current phase for Partner Agent
    pending_agent_switch: Optional[str] = None  # "partner" or "mc" if switch pending
    scene_context: Optional[Dict[str, Any]] = None  # Context from _start_scene
    audio_mixer: Any = None  # AudioMixer for multi-stream mixing
    ambient_trigger: Any = None  # AmbientAudioTrigger for Room activation
    last_user_input: Optional[str] = None  # Recent user transcription
    last_agent_response: Optional[str] = None  # Recent agent transcription


class AudioStreamOrchestrator:
    """Orchestrates real-time audio streaming with ADK Live API.

    This service manages:
    - MC Agent and Partner Agent configuration for audio
    - Multi-agent turn-taking coordination
    - LiveRequestQueue creation and management
    - Audio chunk forwarding to ADK
    - Response streaming back to clients
    - Session lifecycle
    - Usage tracking
    - Phase transitions (Phase 1: Supportive, Phase 2: Fallible)

    Note: Agents are now per-session to avoid cross-session interference.
    Each session gets its own MC and Partner agent instances.
    """

    def __init__(self):
        """Initialize the orchestrator.

        Note: Agents are created per-session in start_session() to ensure
        session isolation. The orchestrator only manages session storage
        and shared services.
        """
        self._sessions: Dict[str, AudioSession] = {}
        self._session_service = get_adk_session_service()

        logger.info("AudioStreamOrchestrator initialized with per-session agents")

    def _create_runner_for_session(self, session: AudioSession) -> Any:
        """Create a Runner for a specific session with its current agent.

        Creates a new Runner instance for each session to ensure proper
        agent isolation. The runner is tied to the session's current agent.

        Args:
            session: AudioSession with the agent to use

        Returns:
            Runner instance configured for this session
        """
        from google.adk.runners import Runner

        # Use the current agent for this session (MC, Partner, or Room)
        if session.current_agent == "mc":
            current_agent = session.mc_agent
        elif session.current_agent == "partner":
            current_agent = session.partner_agent
        elif session.current_agent == "room":
            current_agent = session.room_agent
        else:
            logger.warning(
                "Unknown agent type, defaulting to MC",
                session_id=session.session_id,
                agent_type=session.current_agent,
            )
            current_agent = session.mc_agent

        runner = Runner(
            agent=current_agent,
            session_service=self._session_service,
            app_name=settings.app_name,
        )
        logger.info(
            "Runner created for session",
            session_id=session.session_id,
            agent_type=session.current_agent,
            app_name=settings.app_name,
        )
        return runner

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

    def get_run_config(self, session_id: Optional[str] = None) -> RunConfig:
        """Get RunConfig for audio streaming with transcription.

        For push-to-talk, we disable automatic VAD and use manual activity
        signals (send_activity_start/end) to control when the user is speaking.

        Args:
            session_id: Optional session ID to get agent-specific voice config

        Returns:
            RunConfig with BIDI streaming mode and disabled VAD
        """
        # RunConfig for Live API with BIDI mode for bidirectional streaming
        # BIDI mode keeps the run_live generator active for multi-turn conversations
        # Disable VAD for push-to-talk - we use manual activity signals instead
        return RunConfig(
            streaming_mode=StreamingMode.BIDI,
            speech_config=self.get_speech_config(session_id),
            response_modalities=["AUDIO"],
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=True
                )
            ),
        )

    def get_current_agent_type(self, session_id: str) -> str:
        """Get current active agent type for a session.

        Args:
            session_id: Session identifier

        Returns:
            "mc" or "partner"
        """
        session = self._sessions.get(session_id)
        if not session or not session.turn_manager:
            return "mc"  # Default to MC

        return session.turn_manager.get_current_agent_type()

    def switch_to_mc(self, session_id: str) -> Dict[str, Any]:
        """Switch to MC Agent for hosting.

        Args:
            session_id: Session identifier

        Returns:
            Status dict with transition info
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": True, "message": "Session not found"}

        if not session.turn_manager:
            return {"error": True, "message": "Turn manager not initialized"}

        # Switch agent in turn manager
        result = session.turn_manager.start_mc_turn()

        # Update session state - agent is now per-session
        session.current_agent = "mc"

        logger.info(
            "Switched to MC Agent",
            session_id=session_id,
            turn_count=session.turn_manager.turn_count,
        )

        return result

    def switch_to_partner(self, session_id: str) -> Dict[str, Any]:
        """Switch to Partner Agent for scene work.

        Args:
            session_id: Session identifier

        Returns:
            Status dict with transition info
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": True, "message": "Session not found"}

        if not session.turn_manager:
            return {"error": True, "message": "Turn manager not initialized"}

        # Check if we need to update Partner Agent for phase transition
        # Use turn_count + 1 since we're starting a new turn
        new_phase = determine_partner_phase(session.turn_manager.turn_count)

        if new_phase != session.partner_phase:
            # Recreate Partner Agent with new phase (per-session)
            session.partner_agent = create_partner_agent_for_audio(phase=new_phase)
            session.partner_phase = new_phase
            logger.info(
                "Partner Agent recreated for phase transition",
                session_id=session_id,
                old_phase=session.partner_phase,
                new_phase=new_phase,
            )

        # Switch agent in turn manager
        result = session.turn_manager.start_partner_turn()

        # Update session state - agent is now per-session
        session.current_agent = "partner"

        logger.info(
            "Switched to Partner Agent",
            session_id=session_id,
            turn_count=session.turn_manager.turn_count,
            phase=new_phase,
        )

        return result

    def start_scene_with_partner(self, session_id: str) -> Dict[str, Any]:
        """Transition from MC to Partner after game selection.

        This is called after the MC has helped select a game and the user
        is ready to start scene work.

        Args:
            session_id: Session identifier

        Returns:
            Status dict with transition info
        """
        result = self.switch_to_partner(session_id)

        if not result.get("error"):
            logger.info(
                "Started scene with Partner Agent",
                session_id=session_id,
            )

        return result

    def get_voice_config(self, session_id: Optional[str] = None) -> VoiceConfig:
        """Get voice configuration for synthesis.

        Args:
            session_id: Optional session ID to get agent-specific voice

        Returns:
            VoiceConfig with appropriate voice for current agent
        """
        if session_id:
            agent_type = self.get_current_agent_type(session_id)
            return get_voice_config(agent_type)

        # Default to MC voice
        return get_voice_config("mc")

    def get_speech_config(self, session_id: Optional[str] = None) -> types.SpeechConfig:
        """Get speech configuration for Live API.

        Args:
            session_id: Optional session ID to get agent-specific voice

        Returns:
            SpeechConfig with appropriate voice for current agent
        """
        voice_config = self.get_voice_config(session_id)

        return types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config={"voice_name": voice_config.voice_name}
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
        user_id: str,
        user_email: str,
        game_name: Optional[str] = None,
        starting_turn_count: int = 0,
    ) -> None:
        """Start a new audio session.

        Ensures the ADK session exists in the DatabaseSessionService before
        audio streaming begins. This is required because run_live() expects
        the session to exist.

        After setup, sends an initial greeting prompt to trigger the MC to speak.

        Args:
            session_id: Unique session identifier
            user_id: ADK user identifier (for run_live)
            user_email: User's email for tracking
            game_name: Selected game name for scene context
            starting_turn_count: Starting turn count (for resuming sessions)
        """
        # Ensure ADK session exists (create if not found)
        await self._ensure_adk_session(session_id, user_id, user_email)

        queue = self.create_session_queue(session_id)

        # Initialize turn manager for multi-agent coordination
        turn_manager = AgentTurnManager(starting_turn_count=starting_turn_count)

        # Create per-session agents to ensure isolation between concurrent sessions
        mc_agent = create_mc_agent_for_audio()
        partner_agent = create_partner_agent_for_audio(phase=1)
        room_agent = create_room_agent_for_audio()

        # Create audio mixer for multi-stream mixing (Room at 30% volume)
        audio_mixer = AudioMixer()

        # Create ambient audio trigger for sentiment-based Room activation
        ambient_trigger = AmbientAudioTrigger(cooldown_seconds=15.0)

        self._sessions[session_id] = AudioSession(
            session_id=session_id,
            user_id=user_id,
            user_email=user_email,
            game_name=game_name,
            queue=queue,
            active=True,
            turn_count=starting_turn_count,
            current_agent="mc",  # Always start with MC
            turn_manager=turn_manager,
            mc_agent=mc_agent,
            partner_agent=partner_agent,
            room_agent=room_agent,
            partner_phase=1,
            audio_mixer=audio_mixer,
            ambient_trigger=ambient_trigger,
        )

        # Send initial greeting prompt to trigger MC to speak first
        # The Live API requires us to send something to get a response
        self._send_initial_greeting(queue, game_name)

        logger.info(
            "Audio session started with per-session agents",
            session_id=session_id,
            user_id=user_id,
            user_email=user_email,
            game=game_name,
            starting_turn_count=starting_turn_count,
            current_agent="mc",
            mc_agent_name=mc_agent.name,
            partner_agent_name=partner_agent.name,
            room_agent_name=room_agent.name,
            room_volume=audio_mixer.get_volume("room"),
        )

    def _send_initial_greeting(self, queue: Any, game_name: Optional[str] = None) -> None:
        """Send initial greeting prompt to trigger MC to speak.

        Uses send_content() to send a turn-based message that triggers
        the MC agent to generate a welcome greeting with game context.

        Args:
            queue: LiveRequestQueue for the session
            game_name: Selected game name for scene context
        """
        # Create a prompt that triggers the MC to introduce themselves
        # Include game context if a game was selected
        if game_name:
            greeting_text = (
                f"[Voice mode activated. The player has selected '{game_name}' as their improv game. "
                f"Please greet them as the MC, acknowledge their game choice, and get them ready to play. "
                f"Ask how they're feeling and help them warm up for the scene.]"
            )
        else:
            greeting_text = (
                "[Voice mode activated. Please greet me as the MC and ask how I'm feeling today.]"
            )

        greeting_prompt = types.Content(
            role="user",
            parts=[types.Part.from_text(text=greeting_text)]
        )
        queue.send_content(greeting_prompt)
        logger.debug(
            "Sent initial greeting prompt to trigger MC response",
            game=game_name,
        )

    async def _ensure_adk_session(
        self,
        session_id: str,
        user_id: str,
        user_email: str,
    ) -> None:
        """Ensure ADK session exists in DatabaseSessionService.

        Creates the session if it doesn't exist, which is required for
        run_live() to function properly.

        Args:
            session_id: Session identifier
            user_id: User identifier
            user_email: User's email for state
        """
        # Check if session already exists
        existing = await self._session_service.get_session(
            app_name=settings.app_name,
            user_id=user_id,
            session_id=session_id,
        )

        if existing:
            logger.debug(
                "ADK session already exists for audio",
                session_id=session_id,
                user_id=user_id,
            )
            return

        # Create new ADK session for audio streaming
        await self._session_service.create_session(
            app_name=settings.app_name,
            user_id=user_id,
            session_id=session_id,
            state={
                "user_email": user_email,
                "audio_mode": True,
            },
        )

        logger.info(
            "ADK session created for audio streaming",
            session_id=session_id,
            user_id=user_id,
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

    async def send_activity_start(self, session_id: str) -> Dict[str, Any]:
        """Signal that the user has started speaking (push-to-talk).

        This tells the Live API to start listening for user input.
        Must be called before sending audio chunks.

        Args:
            session_id: Session identifier

        Returns:
            Status dict with result
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(
                "send_activity_start: Session not found",
                session_id=session_id,
            )
            return {"error": True, "message": "Session not found"}

        try:
            session.queue.send_activity_start()
            logger.info(
                "Activity start signal sent",
                session_id=session_id,
            )
            return {"status": "ok"}
        except Exception as e:
            logger.error(
                "Error sending activity start",
                session_id=session_id,
                error=str(e),
            )
            return {"error": True, "message": str(e)}

    async def send_activity_end(self, session_id: str) -> Dict[str, Any]:
        """Signal that the user has stopped speaking (push-to-talk).

        This tells the Live API that the user has finished their turn,
        and it should now process the audio and generate a response.

        Args:
            session_id: Session identifier

        Returns:
            Status dict with result
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(
                "send_activity_end: Session not found",
                session_id=session_id,
            )
            return {"error": True, "message": "Session not found"}

        try:
            session.queue.send_activity_end()
            logger.info(
                "Activity end signal sent",
                session_id=session_id,
            )
            return {"status": "ok"}
        except Exception as e:
            logger.error(
                "Error sending activity end",
                session_id=session_id,
                error=str(e),
            )
            return {"error": True, "message": str(e)}

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
            logger.warning(
                "send_audio_chunk: Session not found",
                session_id=session_id,
            )
            return {"error": True, "message": "Session not found"}

        if not audio_bytes:
            return {"error": True, "message": "Empty audio data"}

        try:
            # Create audio blob for ADK
            audio_blob = types.Blob(
                mime_type="audio/pcm;rate=16000",
                data=audio_bytes,
            )

            # Send to queue (send_realtime is synchronous)
            logger.info(
                "Sending audio chunk to ADK queue",
                session_id=session_id,
                audio_bytes_length=len(audio_bytes),
                mime_type="audio/pcm;rate=16000",
            )
            session.queue.send_realtime(audio_blob)

            # Track usage (assuming chunk is about 100ms)
            chunk_duration_seconds = len(audio_bytes) / (16000 * 2)  # 16kHz, 16-bit
            session.usage_seconds += int(chunk_duration_seconds)

            logger.info(
                "Audio chunk sent to queue successfully",
                session_id=session_id,
                bytes_sent=len(audio_bytes),
                duration_seconds=chunk_duration_seconds,
                total_usage_seconds=session.usage_seconds,
            )

            return {"status": "ok", "bytes_sent": len(audio_bytes)}

        except Exception as e:
            logger.error(
                "Error sending audio chunk",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {"error": True, "message": str(e)}

    async def stream_responses(
        self,
        session_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream responses from the agent with automatic agent switching.

        Supports MC -> Partner handoff when MC calls _start_scene tool.
        When a switch is detected, the stream restarts with the new agent.

        Args:
            session_id: Session identifier

        Yields:
            Response dicts with audio, transcription, or agent switch notifications
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.error("stream_responses: Session not found", session_id=session_id)
            yield {"type": "error", "message": "Session not found"}
            return

        # Outer loop handles agent switching
        while session.active:
            # Create per-session runner with the session's current agent
            runner = self._create_runner_for_session(session)
            run_config = self.get_run_config(session_id)

            logger.info(
                "Starting run_live stream",
                session_id=session_id,
                user_id=session.user_id,
                current_agent=session.current_agent,
                response_modalities=run_config.response_modalities,
            )

            # Reset pending switch flag
            session.pending_agent_switch = None
            agent_switch_needed = False

            try:
                event_count = 0
                logger.info(
                    "Entering run_live event loop",
                    session_id=session_id,
                    user_id=session.user_id,
                    streaming_mode="BIDI",
                    current_agent=session.current_agent,
                )

                # If switching to Partner, send initial scene context
                if session.current_agent == "partner" and session.scene_context:
                    await self._send_partner_scene_start(session)

                # ADK run_live requires both user_id and session_id
                async for event in runner.run_live(
                    user_id=session.user_id,
                    session_id=session_id,
                    live_request_queue=session.queue,
                    run_config=run_config,
                ):
                    event_count += 1
                    logger.info(
                        "run_live yielded event",
                        session_id=session_id,
                        event_number=event_count,
                        event_type=type(event).__name__,
                        has_turn_complete=bool(getattr(event, "turn_complete", False)),
                        has_input_transcription=bool(getattr(event, "input_transcription", None)),
                        has_output_transcription=bool(getattr(event, "output_transcription", None)),
                        has_content=bool(getattr(event, "content", None)),
                        is_partial=bool(getattr(event, "partial", False)),
                        server_content=str(getattr(event, "server_content", None))[:100] if getattr(event, "server_content", None) else None,
                    )

                    responses = await self._process_event(event, session)

                    # Check for turn completion to track turns
                    if hasattr(event, "turn_complete") and event.turn_complete:
                        # Use turn manager to handle completion
                        if session.turn_manager:
                            turn_result = session.turn_manager.on_turn_complete()
                            session.turn_count = turn_result["turn_count"]

                            logger.info(
                                "Turn completed via turn manager",
                                session_id=session_id,
                                turn_count=session.turn_count,
                                phase=turn_result["phase"],
                                phase_changed=turn_result.get("phase_changed", False),
                                current_agent=session.current_agent,
                            )

                            # Emit turn_complete event with phase info
                            responses.append({
                                "type": "turn_complete",
                                "turn_count": session.turn_count,
                                "phase": turn_result["phase"],
                                "phase_changed": turn_result.get("phase_changed", False),
                                "agent": session.current_agent,
                            })
                        else:
                            # Fallback for sessions without turn manager
                            session.turn_count += 1
                            logger.info(
                                "Turn completed (no turn manager)",
                                session_id=session_id,
                                turn_count=session.turn_count,
                            )
                            responses.append({
                                "type": "turn_complete",
                                "turn_count": session.turn_count,
                            })

                        # Update turn count in Firestore for persistence
                        await self._update_session_turn_count(session_id, session.turn_count)

                        # Trigger audience reaction after Partner turns
                        # This adds ambient commentary based on sentiment/energy
                        if session.current_agent == "partner":
                            logger.info(
                                "Triggering audience reaction after Partner turn",
                                session_id=session_id,
                                has_user_input=bool(session.last_user_input),
                                has_agent_response=bool(session.last_agent_response),
                            )
                            # Fire and forget - don't block the main stream
                            import asyncio
                            asyncio.create_task(
                                self.trigger_audience_reaction(
                                    session=session,
                                    user_input=session.last_user_input,
                                    partner_response=session.last_agent_response,
                                )
                            )
                            # Emit event to frontend so UI knows audience is reacting
                            responses.append({
                                "type": "audience_reaction_triggered",
                                "session_id": session_id,
                                "turn_count": session.turn_count,
                            })

                        # Check if agent switch is pending after turn completion
                        if session.pending_agent_switch:
                            agent_switch_needed = True
                            logger.info(
                                "Agent switch triggered after turn completion",
                                session_id=session_id,
                                from_agent=session.current_agent,
                                to_agent=session.pending_agent_switch,
                            )

                    if responses:
                        logger.debug(
                            "Sending responses to client",
                            session_id=session_id,
                            response_count=len(responses),
                            response_types=[r.get("type") for r in responses],
                        )

                    for response in responses:
                        yield response

                    # Yield any pending Room Agent audio
                    if hasattr(session, "pending_room_audio") and session.pending_room_audio:
                        for room_audio in session.pending_room_audio:
                            logger.info(
                                "Yielding Room Agent audio",
                                session_id=session_id,
                                audio_bytes=len(room_audio.get("data", b"")),
                                sentiment=room_audio.get("sentiment"),
                            )
                            yield room_audio
                        session.pending_room_audio = []

                    # If agent switch is needed, break out of the inner loop
                    if agent_switch_needed:
                        break

                # If we get here without agent switch, the generator completed normally
                if not agent_switch_needed:
                    logger.info(
                        "run_live event loop completed",
                        session_id=session_id,
                        total_events=event_count,
                    )
                    return  # Exit the outer loop too

            except Exception as e:
                logger.error(
                    "Error streaming responses",
                    session_id=session_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                yield {"type": "error", "message": str(e)}
                return  # Exit on error

            # Handle agent switch if needed
            if agent_switch_needed and session.pending_agent_switch:
                new_agent = session.pending_agent_switch
                old_agent = session.current_agent

                # Perform the actual switch
                if new_agent == "partner":
                    self.switch_to_partner(session_id)
                else:
                    self.switch_to_mc(session_id)

                # Notify frontend of the switch
                yield {
                    "type": "agent_switch",
                    "from_agent": old_agent,
                    "to_agent": new_agent,
                    "phase": session.partner_phase if new_agent == "partner" else 1,
                }

                logger.info(
                    "Agent switch completed, restarting stream",
                    session_id=session_id,
                    from_agent=old_agent,
                    to_agent=new_agent,
                )

                # Create new queue for the new agent
                # The old queue is tied to the old run_live session
                session.queue = self.create_session_queue(session_id)

                # Continue the outer loop with the new agent
                continue

            # No agent switch needed and stream completed normally
            break

    async def _send_partner_scene_start(self, session: AudioSession) -> None:
        """Send initial scene context to Partner Agent when starting scene.

        Args:
            session: Audio session with scene context from MC
        """
        if not session.scene_context:
            return

        game_name = session.scene_context.get("game_name", "improv scene")
        scene_premise = session.scene_context.get("scene_premise", "")
        game_rules = session.scene_context.get("game_rules", "")

        # Construct the opening prompt for Partner with game rules
        rules_section = ""
        if game_rules:
            rules_section = f"GAME RULES: {game_rules}\n\n"

        if scene_premise:
            opening_text = (
                f"[Scene starting! You are the scene partner for '{game_name}'.\n\n"
                f"{rules_section}"
                f"The premise is: {scene_premise}.\n\n"
                f"IMPORTANT: Follow the game rules throughout the scene! "
                f"Start the scene by making the first offer - set the location, "
                f"relationship, or situation. Be specific and give your partner "
                f"something interesting to respond to. Go!]"
            )
        else:
            opening_text = (
                f"[Scene starting! You are the scene partner for '{game_name}'.\n\n"
                f"{rules_section}"
                f"IMPORTANT: Follow the game rules throughout the scene! "
                f"Start the scene by making the first offer - set the location, "
                f"relationship, or situation. Be specific and give your partner "
                f"something interesting to respond to. Go!]"
            )

        opening_prompt = types.Content(
            role="user",
            parts=[types.Part.from_text(text=opening_text)]
        )
        session.queue.send_content(opening_prompt)

        logger.info(
            "Sent scene start prompt to Partner Agent",
            session_id=session.session_id,
            game_name=game_name,
            has_premise=bool(scene_premise),
            has_rules=bool(game_rules),
        )

    async def _process_event(self, event: Any, session: AudioSession) -> list[Dict[str, Any]]:
        """Process an event from the agent.

        ADK run_live events have these key attributes:
        - event.content.parts: Contains text/audio/function_call parts
        - event.input_transcription: User's transcribed speech
        - event.output_transcription: Agent's transcribed speech
        - event.partial: Whether this is a streaming chunk
        - event.turn_complete: Whether agent finished responding
        - event.error_code/error_message: Error information

        Args:
            event: Event from run_live
            session: Audio session for agent type tracking

        Returns:
            List of response dicts
        """
        responses = []

        # Get current agent type for labeling responses
        agent_type = session.current_agent if session else "mc"

        # Log event for debugging (safely convert to strings)
        logger.debug(
            "Processing run_live event",
            event_type=str(type(event).__name__),
            has_content=bool(hasattr(event, "content") and event.content is not None),
            has_input_transcription=bool(
                hasattr(event, "input_transcription") and event.input_transcription
            ),
            has_output_transcription=bool(
                hasattr(event, "output_transcription") and event.output_transcription
            ),
            has_error=bool(hasattr(event, "error_code") and event.error_code),
        )

        # Check for errors first
        if hasattr(event, "error_code") and event.error_code:
            logger.error(
                "ADK event error",
                error_code=event.error_code,
                error_message=getattr(event, "error_message", "Unknown error"),
            )
            responses.append({
                "type": "error",
                "code": event.error_code,
                "message": getattr(event, "error_message", "Unknown error"),
            })
            return responses

        # Handle user transcription (what the user said)
        # ADK returns Transcription objects with .text and .finished properties
        if hasattr(event, "input_transcription") and event.input_transcription:
            transcription = event.input_transcription
            # Extract text from Transcription object or use as string
            text = getattr(transcription, "text", None) or str(transcription)
            is_final = getattr(transcription, "finished", True)
            if text:
                # Track user input for ambient context
                if is_final and session:
                    session.last_user_input = text
                logger.info(
                    "User transcription received",
                    text=text[:100] if len(text) > 100 else text,
                    is_final=is_final,
                )
                responses.append({
                    "type": "transcription",
                    "text": text,
                    "role": "user",
                    "is_final": is_final,
                })

        # Handle agent transcription (what the agent said)
        # ADK returns Transcription objects with .text and .finished properties
        if hasattr(event, "output_transcription") and event.output_transcription:
            transcription = event.output_transcription
            # Extract text from Transcription object or use as string
            text = getattr(transcription, "text", None) or str(transcription)
            is_final = getattr(transcription, "finished", True)
            if text:
                # Track agent response for ambient context (Partner only, not MC)
                if is_final and session and agent_type == "partner":
                    session.last_agent_response = text
                logger.info(
                    "Agent transcription received",
                    agent_type=agent_type,
                    text=text[:100] if len(text) > 100 else text,
                    is_final=is_final,
                )
                responses.append({
                    "type": "transcription",
                    "text": text,
                    "role": "agent",
                    "agent": agent_type,  # Include which agent is speaking
                    "is_final": is_final,
                })

        # Handle content (audio/text responses)
        if hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts") and event.content.parts:
                for part in event.content.parts:
                    # Check for inline audio data
                    if hasattr(part, "inline_data") and part.inline_data:
                        audio_data = getattr(part.inline_data, "data", None)
                        data_len = (
                            len(audio_data)
                            if audio_data and isinstance(audio_data, (bytes, bytearray))
                            else 0
                        )
                        logger.debug(
                            "Audio data received",
                            mime_type=str(
                                getattr(part.inline_data, "mime_type", "unknown")
                            ),
                            data_length=data_len,
                        )
                        responses.append({
                            "type": "audio",
                            "data": part.inline_data.data,
                            "mime_type": getattr(
                                part.inline_data, "mime_type", "audio/pcm;rate=24000"
                            ),
                        })

                    # Check for text content
                    if hasattr(part, "text") and part.text:
                        is_partial = bool(getattr(event, "partial", False))
                        text_val = part.text
                        text_len = (
                            len(text_val) if isinstance(text_val, str) else 0
                        )
                        logger.debug(
                            "Text content received",
                            agent_type=agent_type,
                            text_length=text_len,
                            partial=is_partial,
                        )
                        responses.append({
                            "type": "transcription",
                            "text": part.text,
                            "role": "agent",
                            "agent": agent_type,  # Include which agent is speaking
                            "is_final": not is_partial,
                        })

                    # Check for function calls
                    if hasattr(part, "function_call") and part.function_call:
                        func_name = part.function_call.name
                        func_args = getattr(part.function_call, "args", {})

                        logger.info(
                            "Function call in event",
                            function_name=func_name,
                            function_args=func_args,
                        )

                        # Check for scene transition tool calls
                        if func_name == "_start_scene":
                            # MC is handing off to Partner Agent
                            session.pending_agent_switch = "partner"
                            session.scene_context = func_args
                            logger.info(
                                "MC called _start_scene - pending switch to Partner",
                                session_id=session.session_id,
                                game_name=func_args.get("game_name"),
                                scene_premise=func_args.get("scene_premise"),
                            )
                            # Signal frontend that agent switch is coming
                            responses.append({
                                "type": "agent_switch_pending",
                                "from_agent": "mc",
                                "to_agent": "partner",
                                "game_name": func_args.get("game_name"),
                                "scene_premise": func_args.get("scene_premise"),
                            })

                        elif func_name == "_resume_scene":
                            # MC is resuming scene with Partner Agent (after interjection)
                            session.pending_agent_switch = "partner"
                            # Don't overwrite scene_context - preserve existing context
                            logger.info(
                                "MC called _resume_scene - pending switch to Partner",
                                session_id=session.session_id,
                                message=func_args.get("message"),
                            )
                            responses.append({
                                "type": "agent_switch_pending",
                                "from_agent": "mc",
                                "to_agent": "partner",
                                "reason": "scene_resume",
                            })

                        elif func_name == "_end_scene":
                            # Partner is handing back to MC
                            session.pending_agent_switch = "mc"
                            logger.info(
                                "Partner called _end_scene - pending switch to MC",
                                session_id=session.session_id,
                                reason=func_args.get("reason"),
                            )
                            responses.append({
                                "type": "agent_switch_pending",
                                "from_agent": "partner",
                                "to_agent": "mc",
                                "reason": func_args.get("reason"),
                            })

                        responses.append({
                            "type": "tool_call",
                            "name": func_name,
                            "args": func_args,
                        })

        # Handle function responses (legacy format)
        if hasattr(event, "tool_call") and event.tool_call:
            responses.append({
                "type": "tool_call",
                "name": event.tool_call.name,
                "args": event.tool_call.args,
            })

        if hasattr(event, "tool_result") and event.tool_result:
            responses.append({
                "type": "tool_result",
                "result": event.tool_result.result,
                "speak": True,
            })

        # Log turn completion for debugging
        if hasattr(event, "turn_complete") and event.turn_complete:
            logger.info("Agent turn completed")

        if hasattr(event, "interrupted") and event.interrupted:
            logger.info("Agent was interrupted by user")

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
            user_profile: User's profile (must have user_id and email)

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

        await self.start_session(session_id, user_profile.user_id, user_profile.email)

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

    async def _update_session_turn_count(self, session_id: str, turn_count: int) -> None:
        """Update session turn count in Firestore.

        Args:
            session_id: Session identifier
            turn_count: New turn count value
        """
        try:
            from app.services.session_manager import get_session_manager

            session_manager = get_session_manager()
            await session_manager.update_session_turn_count(
                session_id=session_id,
                turn_count=turn_count,
            )
            logger.debug(
                "Session turn count updated in Firestore",
                session_id=session_id,
                turn_count=turn_count,
            )
        except Exception as e:
            logger.error(
                "Failed to update session turn count",
                session_id=session_id,
                turn_count=turn_count,
                error=str(e),
            )

    def get_output_sample_rate(self) -> int:
        """Get output audio sample rate.

        Returns:
            24000 Hz (ADK Live API output format)
        """
        return 24000

    # Room Agent Methods (Phase 3)

    def get_room_volume(self, session_id: str) -> float:
        """Get Room Agent volume level for a session.

        Args:
            session_id: Session identifier

        Returns:
            Volume level (0.0-1.0), defaults to 0.3 for Room
        """
        session = self._sessions.get(session_id)
        if not session or not session.audio_mixer:
            return 0.3  # Default Room volume
        return session.audio_mixer.get_volume("room")

    def set_room_volume(self, session_id: str, volume: float) -> Dict[str, Any]:
        """Set Room Agent volume level for a session.

        Args:
            session_id: Session identifier
            volume: Volume level (0.0-1.0)

        Returns:
            Status dict with result
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": True, "message": "Session not found"}

        if not session.audio_mixer:
            return {"error": True, "message": "Audio mixer not initialized"}

        session.audio_mixer.set_volume("room", volume)
        logger.info(
            "Room Agent volume updated",
            session_id=session_id,
            volume=volume,
        )
        return {"status": "ok", "volume": session.audio_mixer.get_volume("room")}

    def should_trigger_ambient(
        self,
        session_id: str,
        sentiment: str,
        energy_level: float,
    ) -> bool:
        """Check if Room Agent ambient commentary should be triggered.

        Uses the session's AmbientAudioTrigger to determine if the current
        sentiment and energy level warrant ambient commentary.

        Args:
            session_id: Session identifier
            sentiment: Sentiment level ("very_positive", "positive", etc.)
            energy_level: Energy level from 0.0 to 1.0

        Returns:
            True if ambient commentary should be triggered
        """
        session = self._sessions.get(session_id)
        if not session or not session.ambient_trigger:
            return False

        # Convert string sentiment to SentimentLevel enum
        sentiment_map = {
            "very_positive": SentimentLevel.VERY_POSITIVE,
            "positive": SentimentLevel.POSITIVE,
            "neutral": SentimentLevel.NEUTRAL,
            "negative": SentimentLevel.NEGATIVE,
            "very_negative": SentimentLevel.VERY_NEGATIVE,
        }
        sentiment_level = sentiment_map.get(sentiment.lower(), SentimentLevel.NEUTRAL)

        return session.ambient_trigger.should_trigger(
            sentiment=sentiment_level,
            energy_level=energy_level,
        )

    def get_ambient_prompt(
        self,
        session_id: str,
        sentiment: str,
        energy_level: float,
        context: Optional[str] = None,
    ) -> str:
        """Get commentary prompt for Room Agent ambient audio.

        Args:
            session_id: Session identifier
            sentiment: Sentiment level ("very_positive", "positive", etc.)
            energy_level: Energy level from 0.0 to 1.0
            context: Optional context about what's happening

        Returns:
            Prompt string for Room Agent
        """
        session = self._sessions.get(session_id)
        if not session or not session.ambient_trigger:
            return ""

        # Convert string sentiment to SentimentLevel enum
        sentiment_map = {
            "very_positive": SentimentLevel.VERY_POSITIVE,
            "positive": SentimentLevel.POSITIVE,
            "neutral": SentimentLevel.NEUTRAL,
            "negative": SentimentLevel.NEGATIVE,
            "very_negative": SentimentLevel.VERY_NEGATIVE,
        }
        sentiment_level = sentiment_map.get(sentiment.lower(), SentimentLevel.NEUTRAL)

        return session.ambient_trigger.get_commentary_prompt(
            sentiment=sentiment_level,
            energy_level=energy_level,
            context=context,
        )

    def mix_audio_streams(
        self,
        session_id: str,
        streams: Dict[str, bytes],
    ) -> bytes:
        """Mix multiple audio streams using the session's AudioMixer.

        Args:
            session_id: Session identifier
            streams: Dictionary mapping agent type to audio bytes

        Returns:
            Mixed audio bytes
        """
        session = self._sessions.get(session_id)
        if not session or not session.audio_mixer:
            # Return first non-empty stream if no mixer
            for audio in streams.values():
                if audio:
                    return audio
            return b""

        return session.audio_mixer.mix_streams(streams)

    def reset_ambient_trigger(self, session_id: str) -> Dict[str, Any]:
        """Reset the ambient audio trigger cooldown for a session.

        Args:
            session_id: Session identifier

        Returns:
            Status dict with result
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": True, "message": "Session not found"}

        if not session.ambient_trigger:
            return {"error": True, "message": "Ambient trigger not initialized"}

        session.ambient_trigger.reset()
        logger.info(
            "Ambient audio trigger reset",
            session_id=session_id,
        )
        return {"status": "ok"}

    async def trigger_audience_reaction(
        self,
        session: AudioSession,
        user_input: Optional[str] = None,
        partner_response: Optional[str] = None,
    ) -> None:
        """Trigger Room Agent ambient reaction after a turn completes.

        Checks if audience should react based on sentiment/energy, and if so,
        sends a prompt to the Room Agent to generate brief ambient commentary.
        The audio is mixed at 30% volume with ongoing audio.

        This is called asynchronously after Partner/User turns to add ambient
        atmosphere without blocking the main conversation flow.

        Args:
            session: Audio session with Room Agent and ambient trigger
            user_input: Optional transcription of what the user said
            partner_response: Optional transcription of Partner's response
        """
        if not session.ambient_trigger or not session.room_agent:
            logger.debug(
                "Ambient trigger or Room Agent not available",
                session_id=session.session_id,
            )
            return

        # Build context from recent conversation
        context_parts = []
        if user_input:
            context_parts.append(f"User: {user_input[:100]}")
        if partner_response:
            context_parts.append(f"Partner: {partner_response[:100]}")
        context = " | ".join(context_parts) if context_parts else None

        # Analyze sentiment and energy from the conversation
        # For now, use simple heuristics (could be enhanced with sentiment analysis)
        sentiment = "neutral"
        energy_level = 0.5

        # Simple energy detection based on text length and exclamation marks
        if context:
            energy_level = min(1.0, len(context) / 200.0)  # Longer = higher energy
            if "!" in context or "?" in context:
                energy_level = min(1.0, energy_level + 0.2)

        # Simple sentiment detection
        positive_words = ["great", "awesome", "love", "yes", "amazing", "perfect"]
        negative_words = ["no", "stop", "bad", "wrong", "difficult"]
        if context:
            context_lower = context.lower()
            if any(word in context_lower for word in positive_words):
                sentiment = "positive"
            elif any(word in context_lower for word in negative_words):
                sentiment = "negative"

        # Check if we should trigger ambient commentary
        should_trigger = self.should_trigger_ambient(
            session_id=session.session_id,
            sentiment=sentiment,
            energy_level=energy_level,
        )

        if not should_trigger:
            logger.debug(
                "Ambient trigger conditions not met",
                session_id=session.session_id,
                sentiment=sentiment,
                energy_level=energy_level,
            )
            return

        # Send ambient prompt to Room Agent
        await self._send_audience_prompt(
            session=session,
            sentiment=sentiment,
            energy_level=energy_level,
            context=context,
        )

    async def _send_audience_prompt(
        self,
        session: AudioSession,
        sentiment: str,
        energy_level: float,
        context: Optional[str] = None,
    ) -> None:
        """Generate and queue Room Agent ambient commentary audio.

        Uses Gemini TTS to generate brief audio reactions based on
        sentiment/energy, then queues them for streaming to the client.

        Args:
            session: Audio session with Room Agent
            sentiment: Sentiment level ("positive", "neutral", "negative")
            energy_level: Energy level from 0.0 to 1.0
            context: Optional context about what's happening
        """
        from app.audio.room_tts import get_room_tts

        try:
            # Get the Room Agent TTS generator
            room_tts = get_room_tts()

            # Generate ambient reaction audio
            audio_data = await room_tts.generate_ambient_reaction(
                sentiment=sentiment,
                energy_level=energy_level,
                context=context,
            )

            if audio_data:
                # Queue the Room Agent audio for streaming
                # It will be sent as a separate audio chunk with "room" agent type
                # The frontend can mix it at 30% volume
                if hasattr(session, "room_audio_queue"):
                    await session.room_audio_queue.put({
                        "type": "room_audio",
                        "data": audio_data,
                        "mime_type": "audio/pcm;rate=24000",
                        "sentiment": sentiment,
                        "energy_level": energy_level,
                    })
                    logger.info(
                        "Room Agent audio queued for streaming",
                        session_id=session.session_id,
                        audio_bytes=len(audio_data),
                        sentiment=sentiment,
                    )
                else:
                    # Log for debugging - room audio queue not set up
                    logger.warning(
                        "Room audio queue not available - storing for next yield",
                        session_id=session.session_id,
                    )
                    # Store in session for next response yield
                    if not hasattr(session, "pending_room_audio"):
                        session.pending_room_audio = []
                    session.pending_room_audio.append({
                        "type": "room_audio",
                        "data": audio_data,
                        "mime_type": "audio/pcm;rate=24000",
                        "sentiment": sentiment,
                    })
            else:
                logger.debug(
                    "No Room Agent audio generated",
                    session_id=session.session_id,
                    sentiment=sentiment,
                )

        except Exception as e:
            logger.error(
                "Failed to generate Room Agent audio",
                session_id=session.session_id,
                error=str(e),
            )
