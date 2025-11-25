"""ADK Session Service - Singleton DatabaseSessionService for Session Persistence

This module provides a singleton DatabaseSessionService that replaces the previous
per-request InMemorySessionService pattern. This ensures sessions persist across
Cloud Run instance restarts and eliminates the anti-pattern of creating new session
services for each request.

Key Features:
- Singleton pattern for shared session service across all requests
- SQLite persistence with async support (aiosqlite)
- Automatic table creation and management by ADK
- Session state persistence for location, user info, phase, status

Usage:
    from app.services.adk_session_service import get_adk_session_service

    session_service = get_adk_session_service()
    adk_session = await session_service.get_session(
        app_name="Improv Olympics",
        user_id="user_123",
        session_id="sess_abc"
    )
"""
import threading
from typing import Optional, Dict, Any
from google.adk.sessions import DatabaseSessionService
from google.adk.sessions.session import Session as ADKSession
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_session_service: Optional[DatabaseSessionService] = None
_init_lock = threading.Lock()


def get_adk_session_service() -> DatabaseSessionService:
    """Get singleton ADK DatabaseSessionService instance.

    Uses SQLite for persistence. The database file is auto-created
    and tables are auto-managed by ADK's DatabaseSessionService.

    The database URL uses the async SQLite driver (aiosqlite) which is
    required for ADK's async session operations.

    Returns:
        DatabaseSessionService: Shared session service instance

    Note:
        This function is thread-safe using double-checked locking pattern.
        It returns the same instance across all calls within a process.
    """
    global _session_service

    if _session_service is not None:
        return _session_service

    with _init_lock:
        if _session_service is None:
            logger.info(
                "Initializing ADK DatabaseSessionService",
                db_url=settings.adk_database_url
            )
            _session_service = DatabaseSessionService(
                db_url=settings.adk_database_url
            )
            logger.info("ADK DatabaseSessionService initialized successfully")

    return _session_service


async def close_adk_session_service() -> None:
    """Cleanup function to close the session service connection.

    This should be called during application shutdown to properly dispose
    of the SQLAlchemy async engine and close database connections.

    Usage:
        # In FastAPI lifespan or shutdown event
        await close_adk_session_service()
    """
    global _session_service
    if _session_service is not None:
        await _session_service.db_engine.dispose()
        _session_service = None
        logger.info("ADK DatabaseSessionService closed")


def reset_adk_session_service() -> None:
    """Reset the singleton for testing purposes.

    This allows tests to reset the service between test cases
    for proper isolation. Should NOT be used in production.
    """
    global _session_service
    _session_service = None


async def create_adk_session(session) -> ADKSession:
    """Create ADK session from Session model.

    Args:
        session: Session model with user/session info

    Returns:
        ADK Session instance
    """
    service = get_adk_session_service()
    status_value = session.status if isinstance(session.status, str) else session.status.value

    state = {
        "location": session.location,
        "user_email": session.user_email,
        "user_name": session.user_name,
        "current_phase": session.current_phase or "PHASE_1",
        "turn_count": session.turn_count,
        "status": status_value
    }

    if session.conversation_history:
        state["conversation_history"] = session.conversation_history

    adk_session = await service.create_session(
        app_name=settings.app_name,
        user_id=session.user_id,
        session_id=session.session_id,
        state=state
    )

    logger.info(
        "ADK session created",
        session_id=session.session_id,
        user_id=session.user_id
    )

    return adk_session


async def get_adk_session(session_id: str, user_id: str) -> Optional[ADKSession]:
    """Retrieve ADK session by ID.

    Args:
        session_id: Session identifier
        user_id: User identifier

    Returns:
        ADK Session if found, None otherwise
    """
    service = get_adk_session_service()

    adk_session = await service.get_session(
        app_name=settings.app_name,
        user_id=user_id,
        session_id=session_id
    )

    if adk_session:
        logger.debug(
            "ADK session retrieved",
            session_id=session_id,
            events_count=len(adk_session.events)
        )

    return adk_session


async def update_adk_session_state(
    session_id: str,
    user_id: str,
    state_updates: Dict[str, Any]
) -> None:
    """Update ADK session state.

    Note: DatabaseSessionService updates state via append_event.
    This function provides a simplified interface for state updates.

    Args:
        session_id: Session identifier
        user_id: User identifier
        state_updates: State changes to apply
    """
    service = get_adk_session_service()

    adk_session = await service.get_session(
        app_name=settings.app_name,
        user_id=user_id,
        session_id=session_id
    )

    if not adk_session:
        logger.warning(
            "ADK session not found for state update",
            session_id=session_id
        )
        return

    adk_session.state.update(state_updates)

    logger.debug(
        "ADK session state updated",
        session_id=session_id,
        updates=list(state_updates.keys())
    )
