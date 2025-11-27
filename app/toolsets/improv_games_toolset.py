"""Improv Games Toolset - ADK BaseToolset for Game Database Access

This toolset provides access to the improv games database stored in Firestore.
Used by the MC Agent for game selection and information retrieval.

Follows ADK patterns:
- Extends BaseToolset for proper ADK integration
- Uses FunctionTool to wrap async functions
- Supports tool filtering and prefixing
"""

from typing import Optional, List, Dict, Any, Union
from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.base_toolset import BaseToolset, ToolPredicate
from google.adk.agents.readonly_context import ReadonlyContext

from app.services import firestore_tool_data_service as data_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImprovGamesToolset(BaseToolset):
    """ADK Toolset for accessing improv game database from Firestore.

    Provides tools for:
    - get_all_games: List all available improv games
    - get_game_by_id: Get details for a specific game
    - search_games: Search games by criteria (energy, difficulty, duration)

    Example usage with ADK Agent:
        ```python
        from app.toolsets import ImprovGamesToolset

        toolset = ImprovGamesToolset()
        agent = Agent(
            name="mc_agent",
            model="gemini-2.0-flash",
            instruction="...",
            tools=[toolset],  # ADK automatically calls get_tools()
        )
        ```
    """

    def __init__(
        self,
        *,
        tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
        tool_name_prefix: Optional[str] = None,
    ):
        """Initialize the ImprovGamesToolset.

        Args:
            tool_filter: Optional filter to include specific tools by name or predicate
            tool_name_prefix: Optional prefix to prepend to all tool names
        """
        super().__init__(tool_filter=tool_filter, tool_name_prefix=tool_name_prefix)
        self._tools: Optional[List[BaseTool]] = None
        logger.info("ImprovGamesToolset initialized")

    async def get_tools(
        self,
        readonly_context: Optional[ReadonlyContext] = None,
    ) -> List[BaseTool]:
        """Return all game database tools.

        Args:
            readonly_context: Optional context for filtering tools

        Returns:
            List of FunctionTool instances wrapping game database functions
        """
        if self._tools is None:
            self._tools = [
                FunctionTool(self._get_all_games),
                FunctionTool(self._get_game_by_id),
                FunctionTool(self._search_games),
            ]
            logger.debug("Game tools created", tool_count=len(self._tools))

        # Apply tool filter if provided
        if self.tool_filter and readonly_context:
            return [
                tool
                for tool in self._tools
                if self._is_tool_selected(tool, readonly_context)
            ]

        return self._tools

    async def _get_all_games(self) -> List[Dict[str, Any]]:
        """Get complete list of all available improv games.

        Returns:
            List of all game dictionaries with details, rules, and requirements.
        """
        return await data_service.get_all_games()

    async def _get_game_by_id(self, game_id: str) -> Dict[str, Any]:
        """Get specific improv game by its unique ID.

        Args:
            game_id: Unique game identifier (e.g., 'long_form', 'questions_only')

        Returns:
            Game dictionary with all details, or empty dict if not found.
        """
        result = await data_service.get_game_by_id(game_id)
        return result if result else {}

    async def _search_games(
        self,
        energy_level: Optional[str] = None,
        player_count: Optional[int] = None,
        difficulty: Optional[str] = None,
        max_duration: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search improv games by multiple criteria.

        Args:
            energy_level: Filter by energy (high, medium, low)
            player_count: Number of players available (filters by min/max range)
            difficulty: Filter by difficulty (beginner, intermediate, advanced)
            max_duration: Maximum duration in minutes

        Returns:
            List of matching game dictionaries.
        """
        return await data_service.search_games(
            energy_level=energy_level,
            player_count=player_count,
            difficulty=difficulty,
            max_duration=max_duration,
        )

    async def close(self) -> None:
        """Cleanup resources when toolset is no longer needed."""
        self._tools = None
        logger.debug("ImprovGamesToolset closed")
