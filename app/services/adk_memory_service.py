"""ADK Memory Service - Singleton Memory Service for Cross-Session Learning

This module provides a singleton memory service that enables cross-session learning
by storing and retrieving session insights using ADK's MemoryService capabilities.

Key Features:
- Singleton pattern for shared memory service across all requests
- Support for both VertexAiMemoryBankService (production) and InMemoryMemoryService (dev/test)
- Async operations for session memory storage and retrieval
- Graceful degradation when memory service is disabled
- Configuration-driven initialization

Usage:
    from app.services.adk_memory_service import get_adk_memory_service

    memory_service = get_adk_memory_service()
    if memory_service:
        await save_session_to_memory(session)
        results = await search_user_memories(user_id, "improv techniques")
"""

import threading
from typing import Optional, List, Dict, Any, Union

from google.adk.memory import VertexAiMemoryBankService, InMemoryMemoryService
from google.adk.sessions.session import Session as ADKSession

from app.config import get_settings
from app.utils.logger import get_logger

MemoryServiceType = Union[VertexAiMemoryBankService, InMemoryMemoryService]

logger = get_logger(__name__)
settings = get_settings()

_memory_service: Optional[MemoryServiceType] = None
_init_lock = threading.Lock()


def get_adk_memory_service() -> Optional[MemoryServiceType]:
    """Get singleton ADK Memory Service instance.

    Returns VertexAiMemoryBankService for production (requires agent_engine_id)
    or InMemoryMemoryService for development/testing.

    Returns:
        Memory service instance if enabled, None otherwise

    Note:
        This function is thread-safe using double-checked locking pattern.
        It returns the same instance across all calls within a process.
        Returns None if memory_service_enabled is False in settings.
    """
    global _memory_service

    if not settings.memory_service_enabled:
        return None

    if _memory_service is not None:
        return _memory_service

    with _init_lock:
        if _memory_service is None:
            try:
                if settings.use_in_memory_memory_service:
                    logger.info("Initializing ADK InMemoryMemoryService")
                    _memory_service = InMemoryMemoryService()
                    logger.info("ADK InMemoryMemoryService initialized successfully")
                else:
                    if not settings.agent_engine_id:
                        logger.error(
                            "Agent Engine ID required for VertexAiMemoryBankService",
                            use_in_memory=settings.use_in_memory_memory_service,
                        )
                        raise ValueError(
                            "AGENT_ENGINE_ID must be set for production memory service"
                        )

                    logger.info(
                        "Initializing ADK VertexAiMemoryBankService",
                        project=settings.gcp_project_id,
                        location=settings.gcp_location,
                        agent_engine_id=settings.agent_engine_id,
                    )
                    _memory_service = VertexAiMemoryBankService(
                        project=settings.gcp_project_id,
                        location=settings.gcp_location,
                        agent_engine_id=settings.agent_engine_id,
                    )
                    logger.info(
                        "ADK VertexAiMemoryBankService initialized successfully"
                    )
            except Exception as e:
                logger.error(
                    "Failed to initialize ADK Memory Service",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

    return _memory_service


async def close_adk_memory_service() -> None:
    """Cleanup function to close the memory service.

    This should be called during application shutdown to properly
    dispose of any resources held by the memory service.

    Usage:
        # In FastAPI shutdown event
        await close_adk_memory_service()
    """
    global _memory_service
    if _memory_service is not None:
        logger.info("Closing ADK Memory Service")
        _memory_service = None
        logger.info("ADK Memory Service closed")


def reset_adk_memory_service() -> None:
    """Reset the singleton for testing purposes.

    This allows tests to reset the service between test cases
    for proper isolation. Should NOT be used in production.
    """
    global _memory_service
    _memory_service = None


async def save_session_to_memory(adk_session: ADKSession) -> bool:
    """Save completed session to memory for cross-session learning.

    Extracts insights from the session and stores them in the memory service
    for future retrieval. Fails gracefully if memory service is disabled.

    Args:
        adk_session: ADK Session instance to save

    Returns:
        True if successfully saved, False otherwise
    """
    memory_service = get_adk_memory_service()

    if not memory_service:
        logger.debug("Memory service disabled, skipping session memory save")
        return False

    try:
        logger.info(
            "Saving session to memory",
            session_id=adk_session.id,
            user_id=adk_session.user_id,
            events_count=len(adk_session.events),
        )

        await memory_service.add_session_to_memory(adk_session)

        logger.info(
            "Session saved to memory successfully",
            session_id=adk_session.id,
            user_id=adk_session.user_id,
        )

        return True

    except Exception as e:
        logger.error(
            "Failed to save session to memory",
            session_id=adk_session.id,
            user_id=adk_session.user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False


async def search_user_memories(
    user_id: str, query: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """Search user's past session memories.

    Retrieves relevant memories from past sessions based on the query.
    Useful for providing personalized coaching based on user history.

    Args:
        user_id: User identifier
        query: Search query text
        limit: Maximum number of results to return

    Returns:
        List of memory results, empty list if memory service disabled or error
    """
    memory_service = get_adk_memory_service()

    if not memory_service:
        logger.debug("Memory service disabled, returning empty memories")
        return []

    try:
        logger.info(
            "Searching user memories", user_id=user_id, query=query[:100], limit=limit
        )

        results = await memory_service.search_memory(
            app_name=settings.app_name, user_id=user_id, query=query
        )

        results_list = list(results)[:limit] if results else []

        logger.info(
            "Memory search completed", user_id=user_id, results_count=len(results_list)
        )

        return results_list

    except Exception as e:
        logger.error(
            "Failed to search user memories",
            user_id=user_id,
            query=query[:100],
            error=str(e),
            error_type=type(e).__name__,
        )
        return []
