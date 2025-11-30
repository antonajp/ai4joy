"""Scene Transition Toolset - ADK Tools for MC to Partner Agent Handoff

This toolset provides tools for the MC Agent to signal when the scene should
begin, triggering a handoff to the Partner Agent for scene work.

In audio mode, the MC hosts and introduces games, then uses _start_scene to
hand off to the Partner Agent who will do the actual scene work.
"""

from typing import Optional, List, Dict, Any
from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.agents.readonly_context import ReadonlyContext

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SceneTransitionToolset(BaseToolset):
    """ADK Toolset for MC to Partner agent handoff.

    Provides tools for:
    - start_scene: Signal that scene work should begin with Partner Agent
    - end_scene: Signal that scene is complete and MC should resume

    The audio orchestrator monitors for these tool calls and handles
    the actual agent switching.
    """

    def __init__(self):
        """Initialize the SceneTransitionToolset."""
        super().__init__()
        self._tools: Optional[List[BaseTool]] = None
        logger.info("SceneTransitionToolset initialized")

    async def get_tools(
        self,
        readonly_context: Optional[ReadonlyContext] = None,
    ) -> List[BaseTool]:
        """Return scene transition tools.

        Args:
            readonly_context: Optional context for filtering tools

        Returns:
            List of FunctionTool instances for scene transitions
        """
        if self._tools is None:
            self._tools = [
                FunctionTool(self._start_scene),
                FunctionTool(self._end_scene),
            ]
            logger.debug("Scene transition tools created", tool_count=len(self._tools))

        return self._tools

    async def _start_scene(
        self,
        game_name: str,
        scene_premise: Optional[str] = None,
        warm_up_complete: bool = True,
    ) -> Dict[str, Any]:
        """Signal that scene work should begin with the Partner Agent.

        Call this tool when:
        - The user has selected a game (or you've helped them choose)
        - You've explained the rules and warmed them up
        - They're ready to start the improv scene

        The system will automatically transition to the Partner Agent who
        will be their scene partner for the actual improv work.

        Args:
            game_name: Name of the selected improv game
            scene_premise: Optional starting premise or suggestion for the scene
            warm_up_complete: Whether warm-up/preparation is complete (default True)

        Returns:
            Dict with transition status and instructions for the handoff
        """
        logger.info(
            "MC signaled scene start",
            game_name=game_name,
            scene_premise=scene_premise,
            warm_up_complete=warm_up_complete,
        )

        # This return value signals to the audio orchestrator to switch agents
        # The orchestrator monitors tool_call events and switches when it sees this
        return {
            "status": "scene_starting",
            "action": "transfer_to_partner",
            "game_name": game_name,
            "scene_premise": scene_premise,
            "message": (
                f"Great! Starting '{game_name}' scene. "
                "Handing off to your scene partner now. Have fun!"
            ),
        }

    async def _end_scene(
        self,
        reason: str = "scene_complete",
        turn_count: int = 0,
    ) -> Dict[str, Any]:
        """Signal that scene work is complete and MC should resume.

        Call this tool when:
        - The scene has reached a natural conclusion
        - The user wants to end the scene early
        - There's been enough turns for coaching feedback

        The system will transition back to the MC for wrap-up and
        optionally trigger Coach feedback.

        Args:
            reason: Why the scene is ending (scene_complete, user_request, etc.)
            turn_count: Number of turns completed in the scene

        Returns:
            Dict with transition status
        """
        logger.info(
            "Partner signaled scene end",
            reason=reason,
            turn_count=turn_count,
        )

        return {
            "status": "scene_ending",
            "action": "transfer_to_mc",
            "reason": reason,
            "turn_count": turn_count,
            "message": "Scene complete! Let me hand you back to the MC for feedback.",
        }

    async def close(self) -> None:
        """Cleanup resources when toolset is no longer needed."""
        self._tools = None
        logger.debug("SceneTransitionToolset closed")
