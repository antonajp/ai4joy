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
from app.services.firestore_tool_data_service import get_all_games, get_game_by_id
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

After suggesting, turn to THE AUDIENCE and ask for a suggestion appropriate for that game.
For example: "Audience, give me a location!" or "Who's got a relationship for us?" or "Shout out an occupation!"

Remember: You're asking THE AUDIENCE (the crowd), not the player directly.
Be brief but enthusiastic! 2-3 sentences max."""
        else:
            prompt = """The user hasn't specified what they want.

Suggest a fun beginner-friendly game to get them started!
Pick something like Freeze Tag or 185 that's high energy and easy to learn.

After suggesting, turn to THE AUDIENCE and ask for a suggestion appropriate for that game.
For example: "Audience, give me a location!" or "Who's got a relationship for us?"

Remember: You're asking THE AUDIENCE (the crowd), not the player directly.
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
        """Handle audience suggestion collection.

        Note: user_input here is actually the audience's suggestion coming from the Room Agent.
        """
        game_name = session.selected_game_name or "the game"
        game_id = session.selected_game_id

        logger.info(
            "Handling audience suggestion",
            session_id=session.session_id,
            game_name=game_name,
            has_suggestion=bool(user_input),
        )

        # Fetch actual game rules from database
        game_rules = []
        if game_id:
            game_data = await get_game_by_id(game_id)
            if game_data and "rules" in game_data:
                game_rules = game_data["rules"]

        rules_text = ""
        if game_rules:
            rules_text = "\n".join(f"• {rule}" for rule in game_rules[:3])
            rules_text = f"\n\nHere are the rules to explain:\n{rules_text}"

        if user_input:
            prompt = f"""The AUDIENCE shouted out a suggestion: "{user_input}"

Accept the audience's suggestion with enthusiasm!
Repeat what you heard: "I heard '{user_input}' from the audience - great choice!"

Then explain the rules of {game_name} clearly.{rules_text}

End by building excitement for the scene that's about to start.

Keep it high-energy but concise! About 3-4 sentences."""

            logger.info(
                "Accepting audience suggestion",
                session_id=session.session_id,
                suggestion=user_input,
            )

            # Save the audience suggestion
            await self.session_manager.update_session_suggestion(
                session_id=session.session_id,
                audience_suggestion=user_input,
            )
        else:
            prompt = f"""The audience hasn't given a suggestion yet.

Turn to THE AUDIENCE and ask for a suggestion for {game_name}!
Be playful about it - "Come on audience, don't be shy! Who's got a [location/relationship/etc] for us?"

Remember: You're asking THE AUDIENCE (the crowd), not the player.
Keep it brief and fun."""

            logger.info(
                "Awaiting audience suggestion",
                session_id=session.session_id,
                game_name=game_name,
            )

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
        game_id = session.selected_game_id

        # Fetch game-specific details for context
        game_description = ""
        if game_id:
            game_data = await get_game_by_id(game_id)
            if game_data and "description" in game_data:
                game_description = f"\nGame format: {game_data['description']}"

        prompt = f"""Time to start the scene!

The game is {game_name} and the audience suggestion is "{suggestion}".{game_description}

Give a final pump-up message:
1. Remind them of the key rule (Yes, And!)
2. Tell them their scene partner is ready and waiting to support them
3. Set the scene briefly using the suggestion
4. Tell them to deliver their first line - their partner will respond right after

IMPORTANT: Do NOT use placeholder text like [player's name] or [wait for partner]. Speak directly to the user.
Do NOT include stage directions or system text. Just speak as the MC.

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

        # Ensure MC session exists before running agent
        # ADK's run_async requires the session to already exist
        session_service = get_adk_session_service()
        mc_app_name = f"{settings.app_name}_mc"
        existing_session = await session_service.get_session(
            app_name=mc_app_name, user_id=user_id, session_id=session_id
        )
        if not existing_session:
            logger.info(
                "Creating MC session",
                session_id=session_id,
                user_id=user_id,
                app_name=mc_app_name,
            )
            await session_service.create_session(
                app_name=mc_app_name,
                user_id=user_id,
                session_id=session_id,
                state={},
            )

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
