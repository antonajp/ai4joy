"""ADK Session Bridge - Syncs ADK Sessions with Firestore for Persistence

DEPRECATED: This module is deprecated as of IQS-49.
Use app.services.adk_session_service instead.

The ADK DatabaseSessionService now handles session persistence directly using
SQLite with async support, eliminating the need for this bridge pattern.

This file is retained for reference during the migration period and will be
removed in a future release once all dependent code has been updated.

Migration Guide:
- Old: get_adk_session_bridge().create_session(session)
- New: get_adk_session_service().create_session(app_name, user_id, session_id, state)

- Old: get_adk_session_bridge().get_or_create_adk_session(session)
- New: get_adk_session_service().get_session(app_name, user_id, session_id)

See: app/services/adk_session_service.py for the new implementation.
"""
import warnings
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from google.adk.sessions import InMemorySessionService
from google.adk.sessions.session import Session as ADKSession
from google.cloud import firestore

warnings.warn(
    "adk_session_bridge is deprecated. Use adk_session_service instead. "
    "See app/services/adk_session_service.py for the new implementation.",
    DeprecationWarning,
    stacklevel=2
)

from app.models.session import Session, SessionStatus
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class ADKSessionBridge:
    """
    Bridges ADK InMemorySessionService with Firestore persistence.

    ADK provides automatic context management and event tracking.
    Firestore provides persistence, rate limiting, and session metadata.

    Responsibilities:
    - Create ADK sessions for runtime performance
    - Sync session state to Firestore for persistence
    - Convert between ADK Session and our Session model
    - Track session lifecycle for rate limiting
    """

    def __init__(self):
        self.adk_session_service = InMemorySessionService()
        self.db = firestore.Client(
            project=settings.gcp_project_id,
            database=settings.firestore_database
        )
        self.collection = self.db.collection(settings.firestore_sessions_collection)

    async def create_session(
        self,
        session: Session
    ) -> ADKSession:
        """
        Create ADK session from our Session model.

        Args:
            session: Our session model (from Firestore)

        Returns:
            ADK Session instance
        """
        status_value = session.status if isinstance(session.status, str) else session.status.value

        adk_session = await self.adk_session_service.create_session(
            app_name=settings.app_name,
            user_id=session.user_id,
            session_id=session.session_id,
            state={
                "location": session.location,
                "user_email": session.user_email,
                "user_name": session.user_name,
                "current_phase": session.current_phase or "PHASE_1",
                "turn_count": session.turn_count,
                "status": status_value
            }
        )

        logger.info(
            "ADK session created",
            session_id=session.session_id,
            user_id=session.user_id,
            adk_session_id=adk_session.id
        )

        return adk_session

    async def get_or_create_adk_session(
        self,
        session: Session
    ) -> ADKSession:
        """
        Get existing ADK session or create new one.

        Args:
            session: Our session model

        Returns:
            ADK Session instance
        """
        adk_session = await self.adk_session_service.get_session(
            app_name=settings.app_name,
            user_id=session.user_id,
            session_id=session.session_id
        )

        if adk_session:
            logger.debug(
                "ADK session retrieved from cache",
                session_id=session.session_id,
                events_count=len(adk_session.events)
            )
            return adk_session

        return await self.create_session(session)

    async def sync_adk_session_to_firestore(
        self,
        adk_session: ADKSession,
        session_id: str
    ) -> None:
        """
        Sync ADK session state back to Firestore.

        Only syncs essential state for persistence and rate limiting.
        Full event history remains in ADK session (in-memory).

        Args:
            adk_session: ADK session with updated state
            session_id: Firestore session ID
        """
        try:
            doc_ref = self.collection.document(session_id)

            updates = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "turn_count": adk_session.state.get("turn_count", 0)
            }

            if "current_phase" in adk_session.state:
                updates["current_phase"] = adk_session.state["current_phase"]

            if "status" in adk_session.state:
                updates["status"] = adk_session.state["status"]

            doc_ref.update(updates)

            logger.debug(
                "ADK session synced to Firestore",
                session_id=session_id,
                turn_count=updates["turn_count"],
                events_count=len(adk_session.events)
            )

        except Exception as e:
            logger.error(
                "Failed to sync ADK session to Firestore",
                session_id=session_id,
                error=str(e)
            )
            raise

    def convert_adk_to_session_model(
        self,
        adk_session: ADKSession,
        firestore_session: Session
    ) -> Session:
        """
        Merge ADK session state into our Session model.

        Args:
            adk_session: ADK session with runtime state
            firestore_session: Our session model from Firestore

        Returns:
            Updated Session model
        """
        firestore_session.turn_count = adk_session.state.get(
            "turn_count",
            firestore_session.turn_count
        )

        if "current_phase" in adk_session.state:
            firestore_session.current_phase = adk_session.state["current_phase"]

        if "status" in adk_session.state:
            try:
                firestore_session.status = SessionStatus(adk_session.state["status"])
            except ValueError:
                logger.warning(
                    "Invalid status in ADK session",
                    status=adk_session.state["status"]
                )

        return firestore_session

    async def update_adk_session_state(
        self,
        session_id: str,
        user_id: str,
        state_updates: Dict[str, Any]
    ) -> None:
        """
        Update ADK session state (in-memory).

        Args:
            session_id: Session identifier
            user_id: User identifier
            state_updates: State changes to apply
        """
        adk_session = await self.adk_session_service.get_session(
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

    async def delete_adk_session(
        self,
        session_id: str,
        user_id: str
    ) -> None:
        """
        Delete ADK session from memory.

        Args:
            session_id: Session identifier
            user_id: User identifier
        """
        await self.adk_session_service.delete_session(
            app_name=settings.app_name,
            user_id=user_id,
            session_id=session_id
        )

        logger.info(
            "ADK session deleted",
            session_id=session_id
        )

    def get_adk_event_count(self, adk_session: ADKSession) -> int:
        """
        Get count of events in ADK session.

        Args:
            adk_session: ADK session

        Returns:
            Event count
        """
        return len(adk_session.events)

    async def list_adk_sessions_for_user(self, user_id: str) -> int:
        """
        Count active ADK sessions for user.

        Args:
            user_id: User identifier

        Returns:
            Count of active ADK sessions
        """
        response = await self.adk_session_service.list_sessions(
            app_name=settings.app_name,
            user_id=user_id
        )
        return len(response.sessions)


_adk_bridge_instance: Optional[ADKSessionBridge] = None


def get_adk_session_bridge() -> ADKSessionBridge:
    """Get singleton ADK session bridge instance"""
    global _adk_bridge_instance

    if _adk_bridge_instance is None:
        _adk_bridge_instance = ADKSessionBridge()

    return _adk_bridge_instance
