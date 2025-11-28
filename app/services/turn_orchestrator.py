"""Turn Orchestration Service - Coordinates ADK Agents for Session Turns"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import asyncio
import threading

from google.adk.runners import Runner
from google.genai import types

from app.agents import create_stage_manager, determine_partner_phase
from app.models.session import Session, SessionStatus
from app.services.session_manager import SessionManager
from app.services.agent_cache import get_agent_cache
from app.services.context_manager import get_context_manager
from app.services.adk_session_service import get_adk_session_service
from app.services.adk_memory_service import get_adk_memory_service, search_user_memories
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

_runner_instance: Optional[Runner] = None
_runner_lock = threading.Lock()


def get_singleton_runner(memory_service=None) -> Runner:
    """Get or create the singleton Runner instance.

    The Runner is application-scoped and shared across all requests.
    It is initialized with the shared DatabaseSessionService and optional MemoryService.

    Args:
        memory_service: Optional memory service instance to pass to Runner

    Returns:
        Runner: Singleton Runner instance
    """
    global _runner_instance

    if _runner_instance is not None:
        return _runner_instance

    with _runner_lock:
        if _runner_instance is None:
            logger.info("Initializing singleton Runner")
            stage_manager = create_stage_manager(turn_count=0)

            memory_svc = memory_service or get_adk_memory_service()

            _runner_instance = Runner(
                agent=stage_manager,
                app_name=settings.app_name,
                artifact_service=None,
                session_service=get_adk_session_service(),
                memory_service=memory_svc,
            )

            if memory_svc:
                logger.info("Singleton Runner initialized with memory service")
            else:
                logger.info("Singleton Runner initialized without memory service")

    return _runner_instance


def initialize_runner() -> Runner:
    """Initialize the singleton Runner at application startup.

    Call this during FastAPI startup to ensure the Runner is ready
    before serving requests.

    Returns:
        Runner: Initialized singleton Runner instance
    """
    return get_singleton_runner()


def reset_runner() -> None:
    """Reset the singleton Runner for testing purposes.

    This allows tests to reset the runner between test cases.
    Should NOT be used in production.
    """
    global _runner_instance
    with _runner_lock:
        _runner_instance = None
        logger.info("Singleton Runner reset")


class TurnOrchestrator:
    """
    Orchestrates agent execution for improv session turns.

    Responsibilities:
    - Create Stage Manager with correct turn count
    - Execute agent conversations
    - Manage phase transitions
    - Update session state
    - Track conversation history
    """

    def __init__(
        self,
        session_manager: SessionManager,
        use_cache: bool = True,
        use_parallel: bool = True,
    ):
        self.session_manager = session_manager
        self.use_cache = use_cache
        self.use_parallel = use_parallel
        self.agent_cache = get_agent_cache() if use_cache else None
        self.context_manager = get_context_manager()
        # Use shared DatabaseSessionService instead of per-request InMemorySessionService

    async def execute_turn(
        self, session: Session, user_input: str, turn_number: int
    ) -> Dict[str, Any]:
        """
        Execute a single turn in the improv session.

        Args:
            session: Current session state
            user_input: User's scene contribution
            turn_number: Turn number (1-indexed)

        Returns:
            Dict containing:
                - partner_response: Partner agent's scene contribution
                - room_vibe: Audience sentiment/engagement
                - coach_feedback: Optional coaching (if turn 15 or scene end)
                - current_phase: Partner phase (1 or 2)
                - timestamp: Turn completion time
        """
        logger.info(
            "Executing turn",
            session_id=session.session_id,
            turn_number=turn_number,
            # NOTE: turn_number is 1-indexed (user-facing), but determine_partner_phase expects
            # 0-indexed turn_count. User turns 1-4 map to Phase 1, turns 5+ map to Phase 2.
            phase=determine_partner_phase(turn_number - 1),
        )

        try:
            runner = get_singleton_runner()
            logger.debug("Using singleton Runner", turn_number=turn_number)

            # Ensure ADK session exists before running agent.
            # This handles the case where the request is routed to a different
            # Cloud Run instance that doesn't have the session in its local SQLite DB.
            # get_adk_session() will create the session if it doesn't exist.
            adk_session = await self.session_manager.get_adk_session(session.session_id)
            if not adk_session:
                logger.error(
                    "Failed to ensure ADK session exists",
                    session_id=session.session_id,
                    user_id=session.user_id,
                )
                raise ValueError(
                    f"Could not create ADK session for {session.session_id}"
                )

            logger.debug(
                "ADK session ready for turn execution",
                session_id=session.session_id,
                events_count=len(adk_session.events),
            )

            scene_prompt = await self._construct_scene_prompt(
                session=session, user_input=user_input, turn_number=turn_number
            )

            response = await self._run_agent_async(
                runner=runner,
                prompt=scene_prompt,
                user_id=session.user_id,
                session_id=session.session_id,
            )

            turn_response = self._parse_agent_response(
                response=response, turn_number=turn_number
            )

            # Update session state
            await self._update_session_after_turn(
                session=session,
                user_input=user_input,
                turn_response=turn_response,
                turn_number=turn_number,
            )

            logger.info(
                "Turn executed successfully",
                session_id=session.session_id,
                turn_number=turn_number,
                phase=turn_response["current_phase"],
            )

            return turn_response

        except Exception as e:
            logger.error(
                "Turn execution failed",
                session_id=session.session_id,
                turn_number=turn_number,
                error=str(e),
            )
            raise

    def _build_context(
        self, session: Session, user_input: str, turn_number: int
    ) -> str:
        """Build conversation context for agent"""
        context_parts = []

        # Include game and suggestion context
        if session.selected_game_name:
            context_parts.append(f"Game: {session.selected_game_name}")
        if session.audience_suggestion:
            context_parts.append(f"Suggestion: {session.audience_suggestion}")

        context_parts.append(f"Turn {turn_number}")

        # Add recent conversation history (last 3 turns for context)
        if session.conversation_history:
            recent_history = session.conversation_history[-3:]
            context_parts.append("Recent conversation:")
            for turn in recent_history:
                context_parts.append(
                    f"Turn {turn['turn_number']}: User: {turn['user_input']}"
                )
                context_parts.append(f"Partner: {turn['partner_response']}")

        return "\n".join(context_parts)

    async def _construct_scene_prompt(
        self, session: Session, user_input: str, turn_number: int
    ) -> str:
        """Construct prompt for Stage Manager with optional memory context"""
        phase = determine_partner_phase(turn_number - 1)
        phase_name = "Phase 1 (Supportive)" if phase == 1 else "Phase 2 (Fallible)"

        memory_context = ""
        if turn_number == 1 and settings.memory_service_enabled:
            game_context = session.selected_game_name or "improv"
            memories = await search_user_memories(
                user_id=session.user_id,
                query=f"improv techniques preferences performance {game_context}",
                limit=3,
            )
            if memories:
                memory_context = "\nPast session insights about this user:\n"
                for memory in memories:
                    content = (
                        memory.get("content", str(memory))
                        if isinstance(memory, dict)
                        else str(memory)
                    )
                    memory_context += f"- {content[:200]}\n"

        # Determine if coach feedback should be included
        # Coach provides feedback at:
        # - Turn 5 (phase transition point)
        # - Every 5 turns after that (turns 10, 15, etc.)
        # - Scene end (turn >= 15)
        include_coach = turn_number == 5 or turn_number % 5 == 0 or turn_number >= 15

        # Build coach instruction based on context
        if turn_number == 5:
            coach_instruction = "3. Coach Agent: Provide mid-scene feedback celebrating their Phase 1 progress and preparing them for the more challenging Phase 2"
        elif turn_number >= 15:
            coach_instruction = "3. Coach Agent: Provide comprehensive end-of-scene feedback summarizing their performance and growth"
        elif include_coach:
            coach_instruction = "3. Coach Agent: Provide brief encouraging feedback on their recent turns"
        else:
            coach_instruction = ""

        # Build scene context from game and suggestion
        game_name = session.selected_game_name or "improv scene"
        suggestion = session.audience_suggestion or "the suggestion"

        prompt = f"""Scene Turn {turn_number} - {phase_name}

Game: {game_name}
Suggestion: {suggestion}
User's contribution: {user_input}
{memory_context}
Coordinate the following:
1. Partner Agent: Respond to user's scene contribution with appropriate phase behavior
2. Room Agent: Analyze scene energy and provide audience vibe
{coach_instruction}

Provide responses in structured format:
PARTNER: [Partner's scene response]
ROOM: [Audience vibe analysis]
{"COACH: [Coaching feedback]" if include_coach else ""}
"""

        return prompt

    async def _run_agent_async(
        self,
        runner: Runner,
        prompt: str,
        user_id: str,
        session_id: str,
        timeout: int = 30,
    ) -> str:
        """Run agent asynchronously with ADK Runner with timeout protection.

        The Runner's session service handles session creation/retrieval automatically
        based on user_id and session_id. No manual session management needed.

        Args:
            runner: ADK Runner instance (singleton)
            prompt: Prompt to send to agent
            user_id: User identifier for the session
            session_id: Session identifier
            timeout: Maximum execution time in seconds (default: 30)

        Returns:
            Agent response string

        Raises:
            asyncio.TimeoutError: If agent execution exceeds timeout
        """
        try:
            new_message = types.Content(
                role="user", parts=[types.Part.from_text(text=prompt)]
            )

            response_parts = []

            async def run_with_timeout():
                async for event in runner.run_async(
                    user_id=user_id, session_id=session_id, new_message=new_message
                ):
                    # Skip events that contain tool/function calls (internal orchestration)
                    # These include transfer_to_agent calls that shouldn't be shown to users
                    if hasattr(event, "get_function_calls") and event.get_function_calls():
                        continue

                    if hasattr(event, "content") and event.content:
                        if hasattr(event.content, "parts"):
                            for part in event.content.parts:
                                # Skip function call parts
                                if hasattr(part, "function_call") and part.function_call:
                                    continue
                                if hasattr(part, "text") and part.text:
                                    # Filter out any leaked tool call text patterns
                                    text = part.text
                                    if "called tool" in text and "transfer_to_agent" in text:
                                        continue
                                    response_parts.append(text)

            await asyncio.wait_for(run_with_timeout(), timeout=timeout)

            return "".join(response_parts)

        except asyncio.TimeoutError:
            logger.error(
                "Agent execution timed out", timeout=timeout, prompt_length=len(prompt)
            )
            raise

    def _extract_mood_metrics(self, room_analysis: str) -> Dict[str, Any]:
        """Extract mood metrics from room analysis text for visual mood indication.

        Analyzes room analysis text to extract:
        - sentiment_score: -1.0 to 1.0 (negative to positive)
        - engagement_score: 0.0 to 1.0 (disengaged to highly engaged)
        - laughter_detected: boolean for laughter keywords

        Args:
            room_analysis: Text from ROOM section describing audience reaction

        Returns:
            Dict with sentiment_score, engagement_score, laughter_detected
        """
        # Default neutral metrics for invalid input
        neutral_metrics = {
            "sentiment_score": 0.0,
            "engagement_score": 0.5,
            "laughter_detected": False,
        }

        # Validate input type and content
        if not isinstance(room_analysis, str):
            logger.warning(
                "room_analysis is not a string, returning neutral metrics",
                input_type=type(room_analysis).__name__,
            )
            return neutral_metrics

        if not room_analysis or not room_analysis.strip():
            logger.debug("Empty room_analysis, returning neutral metrics")
            return neutral_metrics

        # Prevent excessively long strings from causing performance issues
        MAX_ANALYSIS_LENGTH = 5000
        if len(room_analysis) > MAX_ANALYSIS_LENGTH:
            logger.warning(
                "room_analysis exceeds max length, truncating",
                length=len(room_analysis),
                max_length=MAX_ANALYSIS_LENGTH,
            )
            room_analysis = room_analysis[:MAX_ANALYSIS_LENGTH]

        analysis_lower = room_analysis.strip().lower()

        # Laughter detection keywords
        laughter_keywords = [
            "laugh", "laughing", "hilarious", "cracking up", "roar",
            "hysterical", "chuckle", "giggle", "guffaw"
        ]
        laughter_detected = any(keyword in analysis_lower for keyword in laughter_keywords)

        # Engagement score calculation - check negative first to avoid substring issues
        # ("disengaged" contains "engaged", so check disengaged first)
        engagement_score = 0.5  # Default neutral
        engagement_map = [
            (["disengaged", "checking their phones", "not paying attention"], 0.1),
            (["bored", "distracted", "low energy", "low engagement"], 0.2),
            (["moderate", "watching"], 0.5),
            (["highly engaged", "leaning forward", "on the edge"], 0.9),
            (["engaged", "attentive", "following", "interested"], 0.7),
        ]
        for keywords, score in engagement_map:
            if any(keyword in analysis_lower for keyword in keywords):
                engagement_score = score
                break

        # Sentiment score calculation
        sentiment_score = 0.0  # Default neutral

        # Positive sentiment keywords (higher weight)
        positive_high = [
            "loving", "enthusiastic", "excited", "thrilled", "ecstatic",
            "uproarious", "wild", "erupting", "explosive",
        ]
        positive_mid = [
            "positive", "enjoying", "happy", "pleased", "delighted",
            "jovial", "lighthearted", "playful", "amused", "fun",
            "warmth", "warm", "cheerful", "joyful", "gleeful",
        ]

        # Negative sentiment keywords
        negative_high = ["hostile", "angry", "furious", "heckling"]
        negative_mid = ["negative", "bored", "disengaged", "disappointed", "frustrated", "confused", "lost"]

        # Calculate sentiment based on keyword presence
        if any(word in analysis_lower for word in positive_high):
            sentiment_score = 0.8
        elif any(word in analysis_lower for word in positive_mid):
            sentiment_score = 0.5
        elif any(word in analysis_lower for word in negative_high):
            sentiment_score = -0.8
        elif any(word in analysis_lower for word in negative_mid):
            sentiment_score = -0.5

        # Boost scores if laughter detected (laughter indicates high positive engagement)
        if laughter_detected:
            if sentiment_score >= 0:
                sentiment_score = max(sentiment_score, 0.7)  # Laughter is strongly positive
            engagement_score = max(engagement_score, 0.8)  # Laughter shows high engagement

        # Ensure bounds
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        engagement_score = max(0.0, min(1.0, engagement_score))

        return {
            "sentiment_score": sentiment_score,
            "engagement_score": engagement_score,
            "laughter_detected": laughter_detected,
        }

    def _parse_agent_response(self, response: str, turn_number: int) -> Dict[str, Any]:
        """Parse structured response from Stage Manager using robust regex patterns.

        Args:
            response: Raw response from ADK Runner
            turn_number: Current turn number

        Returns:
            Dict with parsed partner_response, room_vibe, coach_feedback, etc.

        Raises:
            ValueError: If partner response is empty after parsing
        """
        import re

        # Initialize response dict
        turn_response = {
            "turn_number": turn_number,
            "partner_response": "",
            "room_vibe": {},
            "coach_feedback": None,
            "current_phase": determine_partner_phase(turn_number - 1),
            "timestamp": datetime.now(timezone.utc),
        }

        # Define section patterns with flexible whitespace and case-insensitive matching
        # Use word boundaries (\b) and non-greedy matching (.*?) to prevent false matches
        partner_pattern = r"\bPARTNER\s*:\s*(.*?)(?=\n\s*\b(?:ROOM|COACH)\s*:|$)"
        room_pattern = r"\bROOM\s*:\s*(.*?)(?=\n\s*\bCOACH\s*:|$)"
        coach_pattern = r"\bCOACH\s*:\s*(.*?)$"

        # Parse PARTNER section (required)
        partner_match = re.search(partner_pattern, response, re.IGNORECASE | re.DOTALL)
        if partner_match:
            turn_response["partner_response"] = partner_match.group(1).strip()
        else:
            # Fallback: treat entire response as partner response
            logger.warning(
                "Failed to parse PARTNER section, using full response",
                response_preview=response[:200],
                turn_number=turn_number,
            )
            turn_response["partner_response"] = response.strip()

        # Validate partner response is not empty
        if not turn_response["partner_response"]:
            logger.error(
                "Empty partner response after parsing",
                raw_response=response,
                turn_number=turn_number,
            )
            raise ValueError("Partner response cannot be empty")

        # Parse ROOM section (optional, with default)
        room_match = re.search(room_pattern, response, re.IGNORECASE | re.DOTALL)
        if room_match:
            room_analysis = room_match.group(1).strip()
            mood_metrics = self._extract_mood_metrics(room_analysis)
            turn_response["room_vibe"] = {
                "analysis": room_analysis,
                "energy": "engaged",  # Default for now
                "mood_metrics": mood_metrics,
            }
        else:
            logger.debug(
                "No ROOM section found, using default", turn_number=turn_number
            )
            turn_response["room_vibe"] = {
                "analysis": "Audience is engaged and enjoying the scene",
                "energy": "positive",
                "mood_metrics": {
                    "sentiment_score": 0.0,
                    "engagement_score": 0.5,
                    "laughter_detected": False,
                },
            }

        # Parse COACH section (optional, only expected at turn >= 15)
        if turn_number >= 15:
            coach_match = re.search(coach_pattern, response, re.IGNORECASE | re.DOTALL)
            if coach_match:
                turn_response["coach_feedback"] = coach_match.group(1).strip()
            else:
                logger.debug(
                    "No COACH section found at turn >= 15", turn_number=turn_number
                )

        return turn_response

    async def _update_session_after_turn(
        self,
        session: Session,
        user_input: str,
        turn_response: Dict[str, Any],
        turn_number: int,
    ) -> None:
        """Update session state in Firestore atomically after turn execution"""
        # Prepare turn data for history
        turn_data = {
            "turn_number": turn_number,
            "user_input": user_input,
            "partner_response": turn_response["partner_response"],
            "room_vibe": turn_response["room_vibe"],
            "phase": f"Phase {turn_response['current_phase']}",
            "timestamp": turn_response["timestamp"].isoformat(),
        }

        if turn_response.get("coach_feedback"):
            turn_data["coach_feedback"] = turn_response["coach_feedback"]

        # Determine phase and status updates
        new_phase = f"PHASE_{turn_response['current_phase']}"
        phase_updated = session.current_phase != new_phase

        new_status = None
        if turn_number == 1:
            new_status = SessionStatus.ACTIVE
        elif turn_number >= 15:
            new_status = SessionStatus.SCENE_COMPLETE

        # Single atomic update for consistency
        await self.session_manager.update_session_atomic(
            session_id=session.session_id,
            turn_data=turn_data,
            new_phase=new_phase if phase_updated else None,
            new_status=new_status,
        )

        if phase_updated:
            logger.info(
                "Phase transition recorded",
                session_id=session.session_id,
                old_phase=session.current_phase,
                new_phase=new_phase,
                turn_number=turn_number,
            )

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        if not self.use_cache or not self.agent_cache:
            return None
        return self.agent_cache.get_cache_stats()

    def invalidate_cache(self, agent_type: Optional[str] = None):
        if self.use_cache and self.agent_cache:
            self.agent_cache.invalidate_cache(agent_type=agent_type)
            logger.info("Agent cache invalidated", agent_type=agent_type or "all")


def get_turn_orchestrator(
    session_manager: SessionManager, use_cache: bool = True, use_parallel: bool = True
) -> TurnOrchestrator:
    """Factory function for TurnOrchestrator"""
    return TurnOrchestrator(
        session_manager=session_manager, use_cache=use_cache, use_parallel=use_parallel
    )
