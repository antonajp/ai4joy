"""Turn Orchestration Service - Coordinates ADK Agents for Session Turns"""
from datetime import datetime, timezone
from typing import Dict, Any
import asyncio

from google.adk import Runner

from app.agents import create_stage_manager, determine_partner_phase
from app.models.session import Session, SessionStatus
from app.services.session_manager import SessionManager
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


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

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    async def execute_turn(
        self,
        session: Session,
        user_input: str,
        turn_number: int
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
            phase=determine_partner_phase(turn_number - 1)
        )

        try:
            # Create Stage Manager with current turn count (0-indexed)
            stage_manager = create_stage_manager(turn_count=turn_number - 1)

            # Build context from conversation history
            context = self._build_context(session, user_input, turn_number)

            # Execute agent with ADK Runner
            runner = Runner(stage_manager)

            # Construct scene prompt for Stage Manager
            scene_prompt = self._construct_scene_prompt(
                session=session,
                user_input=user_input,
                turn_number=turn_number
            )

            # Run the agent
            response = await self._run_agent_async(runner, scene_prompt)

            # Parse agent response
            turn_response = self._parse_agent_response(
                response=response,
                turn_number=turn_number
            )

            # Update session state
            await self._update_session_after_turn(
                session=session,
                user_input=user_input,
                turn_response=turn_response,
                turn_number=turn_number
            )

            logger.info(
                "Turn executed successfully",
                session_id=session.session_id,
                turn_number=turn_number,
                phase=turn_response["current_phase"]
            )

            return turn_response

        except Exception as e:
            logger.error(
                "Turn execution failed",
                session_id=session.session_id,
                turn_number=turn_number,
                error=str(e)
            )
            raise

    def _build_context(
        self,
        session: Session,
        user_input: str,
        turn_number: int
    ) -> str:
        """Build conversation context for agent"""
        context_parts = [
            f"Location: {session.location}",
            f"Turn {turn_number}"
        ]

        # Add recent conversation history (last 3 turns for context)
        if session.conversation_history:
            recent_history = session.conversation_history[-3:]
            context_parts.append("Recent conversation:")
            for turn in recent_history:
                context_parts.append(
                    f"Turn {turn['turn_number']}: User: {turn['user_input']}"
                )
                context_parts.append(
                    f"Partner: {turn['partner_response']}"
                )

        return "\n".join(context_parts)

    def _construct_scene_prompt(
        self,
        session: Session,
        user_input: str,
        turn_number: int
    ) -> str:
        """Construct prompt for Stage Manager"""
        phase = determine_partner_phase(turn_number - 1)
        phase_name = "Phase 1 (Supportive)" if phase == 1 else "Phase 2 (Fallible)"

        prompt = f"""Scene Turn {turn_number} - {phase_name}

Location: {session.location}
User's contribution: {user_input}

Coordinate the following:
1. Partner Agent: Respond to user's scene contribution with appropriate phase behavior
2. Room Agent: Analyze scene energy and provide audience vibe
{"3. Coach Agent: Provide constructive feedback on this turn" if turn_number >= 15 else ""}

Provide responses in structured format:
PARTNER: [Partner's scene response]
ROOM: [Audience vibe analysis]
{"COACH: [Coaching feedback]" if turn_number >= 15 else ""}
"""

        return prompt

    async def _run_agent_async(self, runner: Runner, prompt: str, timeout: int = 30) -> str:
        """Run agent asynchronously with ADK Runner with timeout protection.

        Args:
            runner: ADK Runner instance
            prompt: Prompt to send to agent
            timeout: Maximum execution time in seconds (default: 30)

        Returns:
            Agent response string

        Raises:
            asyncio.TimeoutError: If agent execution exceeds timeout
        """
        loop = asyncio.get_event_loop()

        try:
            # ADK Runner.run() is synchronous, so run in executor with timeout
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: runner.run(prompt)
                ),
                timeout=timeout
            )

            return response

        except asyncio.TimeoutError:
            logger.error(
                "Agent execution timed out",
                timeout=timeout,
                prompt_length=len(prompt)
            )
            raise

    def _parse_agent_response(
        self,
        response: str,
        turn_number: int
    ) -> Dict[str, Any]:
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
            "timestamp": datetime.now(timezone.utc)
        }

        # Define section patterns with flexible whitespace and case-insensitive matching
        # Use word boundaries (\b) and non-greedy matching (.*?) to prevent false matches
        partner_pattern = r'\bPARTNER\s*:\s*(.*?)(?=\n\s*\b(?:ROOM|COACH)\s*:|$)'
        room_pattern = r'\bROOM\s*:\s*(.*?)(?=\n\s*\bCOACH\s*:|$)'
        coach_pattern = r'\bCOACH\s*:\s*(.*?)$'

        # Parse PARTNER section (required)
        partner_match = re.search(partner_pattern, response, re.IGNORECASE | re.DOTALL)
        if partner_match:
            turn_response["partner_response"] = partner_match.group(1).strip()
        else:
            # Fallback: treat entire response as partner response
            logger.warning(
                "Failed to parse PARTNER section, using full response",
                response_preview=response[:200],
                turn_number=turn_number
            )
            turn_response["partner_response"] = response.strip()

        # Validate partner response is not empty
        if not turn_response["partner_response"]:
            logger.error(
                "Empty partner response after parsing",
                raw_response=response,
                turn_number=turn_number
            )
            raise ValueError("Partner response cannot be empty")

        # Parse ROOM section (optional, with default)
        room_match = re.search(room_pattern, response, re.IGNORECASE | re.DOTALL)
        if room_match:
            room_analysis = room_match.group(1).strip()
            turn_response["room_vibe"] = {
                "analysis": room_analysis,
                "energy": "engaged"  # Default for now
            }
        else:
            logger.debug(
                "No ROOM section found, using default",
                turn_number=turn_number
            )
            turn_response["room_vibe"] = {
                "analysis": "Audience is engaged and enjoying the scene",
                "energy": "positive"
            }

        # Parse COACH section (optional, only expected at turn >= 15)
        if turn_number >= 15:
            coach_match = re.search(coach_pattern, response, re.IGNORECASE | re.DOTALL)
            if coach_match:
                turn_response["coach_feedback"] = coach_match.group(1).strip()
            else:
                logger.debug(
                    "No COACH section found at turn >= 15",
                    turn_number=turn_number
                )

        return turn_response

    async def _update_session_after_turn(
        self,
        session: Session,
        user_input: str,
        turn_response: Dict[str, Any],
        turn_number: int
    ) -> None:
        """Update session state in Firestore atomically after turn execution"""
        # Prepare turn data for history
        turn_data = {
            "turn_number": turn_number,
            "user_input": user_input,
            "partner_response": turn_response["partner_response"],
            "room_vibe": turn_response["room_vibe"],
            "phase": f"Phase {turn_response['current_phase']}",
            "timestamp": turn_response["timestamp"].isoformat()
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
            new_status=new_status
        )

        if phase_updated:
            logger.info(
                "Phase transition recorded",
                session_id=session.session_id,
                old_phase=session.current_phase,
                new_phase=new_phase,
                turn_number=turn_number
            )


def get_turn_orchestrator(session_manager: SessionManager) -> TurnOrchestrator:
    """Factory function for TurnOrchestrator"""
    return TurnOrchestrator(session_manager)
