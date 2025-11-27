"""Improv Principles Toolset - ADK BaseToolset for Core Improv Principles Access

This toolset provides access to improv coaching principles stored in Firestore.
Used by the Coach Agent for providing principle-based feedback.

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


class ImprovPrinciplesToolset(BaseToolset):
    """ADK Toolset for accessing improv principles from Firestore.

    Provides tools for:
    - get_all_principles: List all core improv principles
    - get_principle_by_id: Get details for a specific principle
    - get_beginner_essentials: Get foundational principles for beginners
    - get_principles_by_importance: Filter by importance level
    - search_principles_by_keyword: Search principles by text

    Example usage with ADK Agent:
        ```python
        from app.toolsets import ImprovPrinciplesToolset

        toolset = ImprovPrinciplesToolset()
        agent = Agent(
            name="coach_agent",
            model="gemini-2.0-flash",
            instruction="...",
            tools=[toolset],
        )
        ```
    """

    def __init__(
        self,
        *,
        tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
        tool_name_prefix: Optional[str] = None,
    ):
        """Initialize the ImprovPrinciplesToolset.

        Args:
            tool_filter: Optional filter to include specific tools by name or predicate
            tool_name_prefix: Optional prefix to prepend to all tool names
        """
        super().__init__(tool_filter=tool_filter, tool_name_prefix=tool_name_prefix)
        self._tools: Optional[List[BaseTool]] = None
        logger.info("ImprovPrinciplesToolset initialized")

    async def get_tools(
        self,
        readonly_context: Optional[ReadonlyContext] = None,
    ) -> List[BaseTool]:
        """Return all improv principles tools.

        Args:
            readonly_context: Optional context for filtering tools

        Returns:
            List of FunctionTool instances wrapping principles functions
        """
        if self._tools is None:
            self._tools = [
                FunctionTool(self._get_all_principles),
                FunctionTool(self._get_principle_by_id),
                FunctionTool(self._get_beginner_essentials),
                FunctionTool(self._get_principles_by_importance),
                FunctionTool(self._search_principles_by_keyword),
            ]
            logger.debug("Principles tools created", tool_count=len(self._tools))

        # Apply tool filter if provided
        if self.tool_filter and readonly_context:
            return [
                tool
                for tool in self._tools
                if self._is_tool_selected(tool, readonly_context)
            ]

        return self._tools

    async def _get_all_principles(self) -> List[Dict[str, Any]]:
        """Get complete list of all core improv principles.

        Returns:
            List of all principle dictionaries with examples and coaching tips.
        """
        return await data_service.get_all_principles()

    async def _get_principle_by_id(self, principle_id: str) -> Dict[str, Any]:
        """Get specific improv principle by its unique ID.

        Args:
            principle_id: Unique principle identifier (e.g., 'yes_and', 'listening')

        Returns:
            Principle dictionary with all details, or empty dict if not found.
        """
        result = await data_service.get_principle_by_id(principle_id)
        return result if result else {}

    async def _get_beginner_essentials(self) -> List[Dict[str, Any]]:
        """Get essential principles for beginners to focus on first.

        Returns:
            List of foundational and essential principles.
        """
        return await data_service.get_beginner_essentials()

    async def _get_principles_by_importance(
        self, importance: str
    ) -> List[Dict[str, Any]]:
        """Get principles filtered by importance level.

        Args:
            importance: Level (foundational, essential, technical, intermediate, advanced)

        Returns:
            List of matching principles.
        """
        return await data_service.get_principles_by_importance(importance)

    async def _search_principles_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """Search principles by keyword in name or description.

        Args:
            keyword: Search term to match

        Returns:
            List of matching principles.
        """
        return await data_service.search_principles_by_keyword(keyword)

    async def close(self) -> None:
        """Cleanup resources when toolset is no longer needed."""
        self._tools = None
        logger.debug("ImprovPrinciplesToolset closed")
