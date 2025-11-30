"""Session Management Service with Firestore Persistence and ADK Integration"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import uuid
from google.cloud import firestore  # type: ignore[attr-defined]
from google.adk.sessions.session import Session as ADKSession

from app.config import get_settings
from app.utils.logger import get_logger
from app.models.session import Session, SessionStatus, SessionCreate
from app.services.adk_session_service import get_adk_session_service

logger = get_logger(__name__)
settings = get_settings()


class SessionManager:
    """
    Manages user sessions with Firestore persistence and ADK session integration.

    Architecture:
    - ADK DatabaseSessionService: SQLite-backed session persistence across restarts
    - Firestore: Rate limiting, session metadata, conversation history
    - Shared session service: Single DatabaseSessionService singleton for all requests

    All sessions are associated with authenticated user IDs from IAP.

    Firestore Schema (sessions collection):
    {
        "session_id": "sess_abc123",
        "user_id": "1234567890",
        "user_email": "user@example.com",
        "user_name": "Test User",
        "status": "active",
        "created_at": "2025-11-23T15:00:00Z",
        "updated_at": "2025-11-23T15:30:00Z",
        "expires_at": "2025-11-23T16:00:00Z",
        "conversation_history": [],
        "metadata": {},
        "current_phase": "PHASE_1",
        "turn_count": 5,
        "selected_game_id": "185",
        "selected_game_name": "185",
        "audience_suggestion": "lawyers"
    }
    """

    def __init__(self, use_adk_sessions: bool = True):
        self.db = firestore.Client(
            project=settings.gcp_project_id, database=settings.firestore_database
        )
        self.collection = self.db.collection(settings.firestore_sessions_collection)
        self.use_adk_sessions = use_adk_sessions
        # Use shared DatabaseSessionService singleton
        self.adk_session_service = (
            get_adk_session_service() if use_adk_sessions else None
        )

    async def create_session(
        self, user_id: str, user_email: str, session_data: SessionCreate
    ) -> Session:
        """
        Create new session associated with authenticated user.

        Args:
            user_id: User ID from IAP header
            user_email: User email from IAP header
            session_data: Session creation parameters

        Returns:
            Created Session object
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.session_timeout_minutes)

        session_id = f"sess_{uuid.uuid4().hex[:16]}"

        # Determine initial status based on whether game is pre-selected
        # If game is pre-selected, skip game selection phases
        initial_status = SessionStatus.INITIALIZED
        if session_data.selected_game_id and session_data.selected_game_name:
            # Game pre-selected: start at suggestion phase (skip MC welcome & game select)
            initial_status = SessionStatus.GAME_SELECT

        session = Session(
            session_id=session_id,
            user_id=user_id,
            user_email=user_email,
            user_name=session_data.user_name,
            status=initial_status,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            conversation_history=[],
            metadata={},
            turn_count=0,
            selected_game_id=session_data.selected_game_id,
            selected_game_name=session_data.selected_game_name,
        )

        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.set(session.model_dump(mode="json"))

            logger.info(
                "Session created successfully",
                session_id=session_id,
                user_id=user_id,
                user_email=user_email,
            )

            # Create ADK session with DatabaseSessionService
            if self.use_adk_sessions and self.adk_session_service:
                status_value = (
                    session.status
                    if isinstance(session.status, str)
                    else session.status.value
                )
                await self.adk_session_service.create_session(
                    app_name=settings.app_name,
                    user_id=session.user_id,
                    session_id=session.session_id,
                    state={
                        "user_email": session.user_email,
                        "user_name": session.user_name,
                        "current_phase": session.current_phase or "PHASE_1",
                        "turn_count": session.turn_count,
                        "status": status_value,
                    },
                )
                logger.info(
                    "ADK session created in DatabaseSessionService",
                    session_id=session_id,
                )

            return session

        except Exception as e:
            logger.error("Failed to create session", user_id=user_id, error=str(e))
            raise

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve session by ID.

        Returns:
            Session object or None if not found
        """
        try:
            doc_ref = self.collection.document(session_id)
            snapshot = doc_ref.get()

            if not snapshot.exists:
                logger.warning("Session not found", session_id=session_id)
                return None

            data = snapshot.to_dict()

            for date_field in ["created_at", "updated_at", "expires_at"]:
                if date_field in data and isinstance(data[date_field], str):
                    data[date_field] = datetime.fromisoformat(
                        data[date_field].replace("Z", "+00:00")
                    )

            session = Session(**data)

            if datetime.now(timezone.utc) > session.expires_at:
                logger.warning(
                    "Session expired",
                    session_id=session_id,
                    expired_at=session.expires_at.isoformat(),
                )
                await self.update_session_status(session_id, SessionStatus.TIMEOUT)
                return None

            return session

        except Exception as e:
            logger.error(
                "Failed to retrieve session", session_id=session_id, error=str(e)
            )
            raise

    async def update_session_status(
        self, session_id: str, status: SessionStatus
    ) -> None:
        """Update session status"""
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update(
                {
                    "status": status.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info(
                "Session status updated", session_id=session_id, new_status=status.value
            )

        except Exception as e:
            logger.error(
                "Failed to update session status", session_id=session_id, error=str(e)
            )
            raise

    async def add_conversation_turn(
        self, session_id: str, turn_data: Dict[str, Any]
    ) -> None:
        """
        Add conversation turn to session history.

        Args:
            session_id: Session identifier
            turn_data: Turn information (user input, responses, etc.)
        """
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update(
                {
                    "conversation_history": firestore.ArrayUnion([turn_data]),
                    "turn_count": firestore.Increment(1),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info(
                "Conversation turn added",
                session_id=session_id,
                turn_number=turn_data.get("turn_number"),
            )

        except Exception as e:
            logger.error(
                "Failed to add conversation turn", session_id=session_id, error=str(e)
            )
            raise

    async def update_session_phase(self, session_id: str, phase: str) -> None:
        """Update current phase of session"""
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update(
                {
                    "current_phase": phase,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info("Session phase updated", session_id=session_id, phase=phase)

        except Exception as e:
            logger.error(
                "Failed to update session phase", session_id=session_id, error=str(e)
            )
            raise

    async def update_session_atomic(
        self,
        session_id: str,
        turn_data: Dict[str, Any],
        new_phase: Optional[str] = None,
        new_status: Optional[SessionStatus] = None,
    ) -> None:
        """
        Atomically update session with turn data, phase, and status using Firestore transaction.

        This ensures consistency when multiple fields need to be updated together.

        Args:
            session_id: Session identifier
            turn_data: Turn information to append to history
            new_phase: Optional new phase value
            new_status: Optional new status value
        """
        try:

            @firestore.transactional
            def update_in_transaction(transaction, doc_ref):
                # Build update dict
                updates = {
                    "conversation_history": firestore.ArrayUnion([turn_data]),
                    "turn_count": firestore.Increment(1),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                if new_phase is not None:
                    updates["current_phase"] = new_phase

                if new_status is not None:
                    updates["status"] = new_status.value

                # Atomic update
                transaction.update(doc_ref, updates)

            # Execute transaction
            doc_ref = self.collection.document(session_id)
            transaction = self.db.transaction()
            update_in_transaction(transaction, doc_ref)

            logger.info(
                "Session updated atomically",
                session_id=session_id,
                turn_number=turn_data.get("turn_number"),
                phase_updated=new_phase is not None,
                status_updated=new_status is not None,
            )

        except Exception as e:
            logger.error(
                "Failed to update session atomically",
                session_id=session_id,
                error=str(e),
            )
            raise

    async def close_session(self, session_id: str) -> None:
        """
        Close session and mark as complete.
        This should also decrement the concurrent session counter.
        """
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update(
                {
                    "status": SessionStatus.CLOSED.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info("Session closed", session_id=session_id)

        except Exception as e:
            logger.error("Failed to close session", session_id=session_id, error=str(e))
            raise

    async def update_session_game(
        self, session_id: str, game_id: str, game_name: str
    ) -> None:
        """Update session with selected game information."""
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update(
                {
                    "selected_game_id": game_id,
                    "selected_game_name": game_name,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info(
                "Session game updated",
                session_id=session_id,
                game_id=game_id,
                game_name=game_name,
            )

        except Exception as e:
            logger.error(
                "Failed to update session game", session_id=session_id, error=str(e)
            )
            raise

    async def update_session_suggestion(
        self, session_id: str, audience_suggestion: str
    ) -> None:
        """Update session with audience suggestion."""
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update(
                {
                    "audience_suggestion": audience_suggestion,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info(
                "Session suggestion updated",
                session_id=session_id,
                suggestion=audience_suggestion[:50],
            )

        except Exception as e:
            logger.error(
                "Failed to update session suggestion",
                session_id=session_id,
                error=str(e),
            )
            raise

    async def complete_mc_welcome(self, session_id: str) -> None:
        """Mark MC welcome phase as complete and transition to ACTIVE status."""
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update(
                {
                    "mc_welcome_complete": True,
                    "status": SessionStatus.ACTIVE.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info("MC welcome phase completed", session_id=session_id)

        except Exception as e:
            logger.error(
                "Failed to complete MC welcome", session_id=session_id, error=str(e)
            )
            raise

    async def update_session_turn_count(
        self, session_id: str, turn_count: int
    ) -> None:
        """Update session turn count (used by audio mode).

        Args:
            session_id: Session identifier
            turn_count: New turn count value
        """
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update(
                {
                    "turn_count": turn_count,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.debug(
                "Session turn count updated",
                session_id=session_id,
                turn_count=turn_count,
            )

        except Exception as e:
            logger.error(
                "Failed to update session turn count",
                session_id=session_id,
                turn_count=turn_count,
                error=str(e),
            )
            raise

    async def get_user_active_sessions(self, user_id: str) -> int:
        """Get count of active sessions for user"""
        try:
            query = self.collection.where("user_id", "==", user_id).where(
                "status",
                "in",
                [
                    SessionStatus.INITIALIZED.value,
                    SessionStatus.MC_WELCOME.value,
                    SessionStatus.GAME_SELECT.value,
                    SessionStatus.SUGGESTION_PHASE.value,
                    SessionStatus.MC_PHASE.value,
                    SessionStatus.ACTIVE.value,
                    SessionStatus.SCENE_COMPLETE.value,
                    SessionStatus.COACH_PHASE.value,
                ],
            )

            results = query.stream()
            count = sum(1 for _ in results)

            logger.debug("Active sessions counted", user_id=user_id, count=count)
            return count

        except Exception as e:
            logger.error(
                "Failed to count active sessions", user_id=user_id, error=str(e)
            )
            return 0

    async def get_adk_session(self, session_id: str) -> Optional[ADKSession]:
        """
        Get ADK session for runtime agent execution.

        Args:
            session_id: Session identifier

        Returns:
            ADK Session if found and ADK sessions enabled, None otherwise
        """
        if not self.use_adk_sessions or not self.adk_session_service:
            return None

        firestore_session = await self.get_session(session_id)
        if not firestore_session:
            return None

        # Get or create ADK session using DatabaseSessionService
        adk_session = await self.adk_session_service.get_session(
            app_name=settings.app_name,
            user_id=firestore_session.user_id,
            session_id=firestore_session.session_id,
        )

        if adk_session:
            logger.debug(
                "ADK session retrieved from DatabaseSessionService",
                session_id=session_id,
                events_count=len(adk_session.events),
            )
            return adk_session

        # Create new ADK session if not found
        status_value = (
            firestore_session.status
            if isinstance(firestore_session.status, str)
            else firestore_session.status.value
        )
        adk_session = await self.adk_session_service.create_session(
            app_name=settings.app_name,
            user_id=firestore_session.user_id,
            session_id=firestore_session.session_id,
            state={
                "user_email": firestore_session.user_email,
                "user_name": firestore_session.user_name,
                "current_phase": firestore_session.current_phase or "PHASE_1",
                "turn_count": firestore_session.turn_count,
                "status": status_value,
            },
        )

        logger.info(
            "ADK session created in DatabaseSessionService", session_id=session_id
        )

        return adk_session

    async def sync_adk_session_to_firestore(
        self, adk_session: ADKSession, session_id: str
    ) -> None:
        """
        Sync ADK session state to Firestore for audit and metadata.

        Note: With DatabaseSessionService, ADK session state is automatically
        persisted to SQLite. This method syncs essential state to Firestore
        for rate limiting and session metadata purposes.

        Args:
            adk_session: ADK session with updated state
            session_id: Firestore session ID
        """
        if not self.use_adk_sessions or not self.adk_session_service:
            return

        try:
            doc_ref = self.collection.document(session_id)

            updates = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "turn_count": adk_session.state.get("turn_count", 0),
            }

            if "current_phase" in adk_session.state:
                updates["current_phase"] = adk_session.state["current_phase"]

            if "status" in adk_session.state:
                updates["status"] = adk_session.state["status"]

            doc_ref.update(updates)

            logger.debug(
                "ADK session state synced to Firestore",
                session_id=session_id,
                turn_count=updates["turn_count"],
                events_count=len(adk_session.events),
            )

        except Exception as e:
            logger.error(
                "Failed to sync ADK session to Firestore",
                session_id=session_id,
                error=str(e),
            )
            raise


def get_session_manager(use_adk_sessions: bool = True) -> SessionManager:
    """Get session manager instance with optional ADK session integration"""
    return SessionManager(use_adk_sessions=use_adk_sessions)
