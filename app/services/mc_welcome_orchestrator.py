"""MC Welcome Orchestrator - Handles the MC Welcome Phase using ADK Agents"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import asyncio

from google.adk.runners import Runner
from google.genai import types

from app.agents.mc_agent import create_mc_agent
from app.models.session import Session, SessionStatus
from app.services.session_manager import SessionManager
from app.services.adk_session_service import get_adk_session_service
from app.services.adk_memory_service import get_adk_memory_service
from app.tools.game_database_tools import get_all_games, get_game_by_id
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class MCWelcomeOrchestrator:
    """
    Orchestrates the MC Welcome Phase before scene work begins.

    The MC Welcome Phase consists of:
    1. Welcome message from MC introducing Improv Olympics
    2. Game selection (MC suggests based on mood or user chooses)
    3. Audience suggestion collection (e.g., "Give me a location!")
    4. Brief rules explanation for the chosen game
    5. Transition to scene work with Partner
    """

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self._runner: Optional[Runner] = None

    def _get_mc_runner(self) -> Runner:
        """Get or create the MC Agent Runner."""
        if self._runner is None:
            mc_agent = create_mc_agent()
            self._runner = Runner(
                agent=mc_agent,
                app_name=f"{settings.app_name}_mc",
                artifact_service=None,
                session_service=get_adk_session_service(),
                memory_service=get_adk_memory_service(),
            )
        return self._runner

    async def execute_welcome(
        self, session: Session, user_input: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute MC welcome phase based on current session status.

        Args:
            session: Current session state
            user_input: Optional user input (for game selection or suggestions)

        Returns:
            Dict containing:
                - mc_response: MC Agent's response
                - available_games: List of games (if in game selection phase)
                - next_status: Next session status
                - timestamp: Response timestamp
        """
        status = SessionStatus(session.status)
        logger.info(
            "Executing MC welcome phase",
            session_id=session.session_id,
            current_status=status.value,
            user_input=user_input[:50] if user_input else None,
        )

        if status == SessionStatus.INITIALIZED:
            return await self._handle_initial_welcome(session)
        elif status == SessionStatus.MC_WELCOME:
            return await self._handle_game_selection(session, user_input)
        elif status == SessionStatus.GAME_SELECT:
            return await self._handle_audience_suggestion(session, user_input)
        elif status == SessionStatus.SUGGESTION_PHASE:
            return await self._handle_rules_and_start(session, user_input)
        else:
            logger.warning(
                "Invalid status for MC welcome phase",
                session_id=session.session_id,
                status=status.value,
            )
            raise ValueError(f"Invalid status for MC welcome phase: {status.value}")

    async def _handle_initial_welcome(self, session: Session) -> Dict[str, Any]:
        """Handle initial MC welcome message."""
        prompt = """Welcome a new user to Improv Olympics!

Be enthusiastic and energetic! This is their first time here.

1. Introduce yourself as the MC
2. Briefly explain what Improv Olympics is about
3. Ask about their mood/energy level today
4. Tease that you'll help them pick the perfect game

Keep it concise but exciting - about 3-4 sentences max.
End with a question about how they're feeling or what kind of experience they want."""

        mc_response = await self._run_mc_agent(
            prompt=prompt,
            user_id=session.user_id,
            session_id=f"{session.session_id}_mc",
        )

        # Get available games for the next phase
        games = await get_all_games()
        game_options = [
            {"id": g["id"], "name": g["name"], "difficulty": g["difficulty"]}
            for g in games
        ]

        # Update session status
        await self.session_manager.update_session_status(
            session_id=session.session_id,
            status=SessionStatus.MC_WELCOME,
        )

        return {
            "mc_response": mc_response,
            "available_games": game_options,
            "next_status": SessionStatus.MC_WELCOME.value,
            "phase": "welcome",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _handle_game_selection(
        self, session: Session, user_input: Optional[str]
    ) -> Dict[str, Any]:
        """Handle game selection phase."""
        games = await get_all_games()

        # Check if user specified a game or mood
        if user_input:
            prompt = f"""The user responded: "{user_input}"

Based on their response, suggest a perfect improv game for them!
Use your game database tools to find the best match.

If they mentioned:
- Wanting something fun/silly: suggest a high-energy beginner game
- Feeling nervous/new: suggest an easy, supportive game
- Wanting a challenge: suggest an intermediate or advanced game
- A specific game name: acknowledge their choice and get excited about it

After suggesting, ask them for an audience suggestion appropriate for that game.
For example: "Give me a location!" or "Give me a relationship!" or "Give me an occupation!"

Be brief but enthusiastic! 2-3 sentences max."""
        else:
            prompt = """The user hasn't specified what they want.

Suggest a fun beginner-friendly game to get them started!
Pick something like Freeze Tag or 185 that's high energy and easy to learn.

After suggesting, ask them for an audience suggestion appropriate for that game.
For example: "Give me a location!" or "Give me a relationship!"

Be brief but enthusiastic! 2-3 sentences max."""

        mc_response = await self._run_mc_agent(
            prompt=prompt,
            user_id=session.user_id,
            session_id=f"{session.session_id}_mc",
        )

        # Try to detect which game was suggested
        suggested_game = self._detect_game_from_response(mc_response, games)

        # Update session with game selection
        if suggested_game:
            await self.session_manager.update_session_game(
                session_id=session.session_id,
                game_id=suggested_game["id"],
                game_name=suggested_game["name"],
            )

        # Update session status
        await self.session_manager.update_session_status(
            session_id=session.session_id,
            status=SessionStatus.GAME_SELECT,
        )

        return {
            "mc_response": mc_response,
            "selected_game": suggested_game,
            "next_status": SessionStatus.GAME_SELECT.value,
            "phase": "game_selection",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _handle_audience_suggestion(
        self, session: Session, user_input: Optional[str]
    ) -> Dict[str, Any]:
        """Handle audience suggestion collection."""
        game_name = session.selected_game_name or "the game"

        if user_input:
            prompt = f"""The user gave an audience suggestion: "{user_input}"

Accept their suggestion with enthusiasm!
Then briefly explain the rules of {game_name} in 2-3 simple bullet points.
End by saying you're about to start the scene and introduce their scene partner.

Keep it high-energy but concise! About 3-4 sentences."""

            # Save the audience suggestion
            await self.session_manager.update_session_suggestion(
                session_id=session.session_id,
                audience_suggestion=user_input,
            )
        else:
            prompt = f"""The user didn't provide a suggestion yet.

Ask them again for an audience suggestion for {game_name}!
Be playful about it - "Come on, don't be shy! Give me a [location/relationship/etc]!"

Keep it brief and fun."""

            # Don't advance status if no suggestion
            return {
                "mc_response": await self._run_mc_agent(
                    prompt=prompt,
                    user_id=session.user_id,
                    session_id=f"{session.session_id}_mc",
                ),
                "next_status": SessionStatus.GAME_SELECT.value,
                "phase": "awaiting_suggestion",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        mc_response = await self._run_mc_agent(
            prompt=prompt,
            user_id=session.user_id,
            session_id=f"{session.session_id}_mc",
        )

        # Update session status
        await self.session_manager.update_session_status(
            session_id=session.session_id,
            status=SessionStatus.SUGGESTION_PHASE,
        )

        return {
            "mc_response": mc_response,
            "audience_suggestion": user_input,
            "next_status": SessionStatus.SUGGESTION_PHASE.value,
            "phase": "suggestion_received",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _handle_rules_and_start(
        self, session: Session, user_input: Optional[str]
    ) -> Dict[str, Any]:
        """Handle rules explanation and transition to scene work."""
        game_name = session.selected_game_name or "improv"
        suggestion = session.audience_suggestion or "a fun location"

        prompt = f"""Time to start the scene!

The game is {game_name} and the audience suggestion is "{suggestion}".

Give a final pump-up message:
1. Remind them of the key rule (Yes, And!)
2. Introduce their scene partner (they'll be supportive in Phase 1)
3. Set the scene briefly using the suggestion
4. Invite them to start with their first line

Be exciting and encouraging! About 3-4 sentences.
End with something like "Take it away!" or "You're on!"

This is the transition to scene work, so make it feel like a big moment!"""

        mc_response = await self._run_mc_agent(
            prompt=prompt,
            user_id=session.user_id,
            session_id=f"{session.session_id}_mc",
        )

        # Mark MC welcome as complete and transition to ACTIVE
        await self.session_manager.complete_mc_welcome(
            session_id=session.session_id,
        )

        return {
            "mc_response": mc_response,
            "mc_welcome_complete": True,
            "next_status": SessionStatus.ACTIVE.value,
            "phase": "scene_start",
            "game_name": game_name,
            "audience_suggestion": suggestion,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _run_mc_agent(
        self, prompt: str, user_id: str, session_id: str, timeout: int = 30
    ) -> str:
        """Run the MC Agent with the given prompt."""
        runner = self._get_mc_runner()

        try:
            new_message = types.Content(
                role="user", parts=[types.Part.from_text(text=prompt)]
            )

            response_parts = []

            async def run_with_timeout():
                async for event in runner.run_async(
                    user_id=user_id, session_id=session_id, new_message=new_message
                ):
                    if hasattr(event, "content") and event.content:
                        if hasattr(event.content, "parts"):
                            for part in event.content.parts:
                                if hasattr(part, "text") and part.text:
                                    response_parts.append(part.text)

            await asyncio.wait_for(run_with_timeout(), timeout=timeout)

            return "".join(response_parts)

        except asyncio.TimeoutError:
            logger.error(
                "MC Agent execution timed out",
                timeout=timeout,
                prompt_length=len(prompt),
            )
            raise

    def _detect_game_from_response(
        self, response: str, games: List[Dict]
    ) -> Optional[Dict]:
        """Attempt to detect which game was mentioned in the MC response."""
        response_lower = response.lower()

        for game in games:
            if game["name"].lower() in response_lower:
                return game

        # Default to Freeze Tag if no match found
        for game in games:
            if game["id"] == "freeze_tag":
                return game

        return games[0] if games else None


def get_mc_welcome_orchestrator(
    session_manager: SessionManager,
) -> MCWelcomeOrchestrator:
    """Factory function for MCWelcomeOrchestrator."""
    return MCWelcomeOrchestrator(session_manager=session_manager)
