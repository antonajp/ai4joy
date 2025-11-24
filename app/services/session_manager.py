"""Session Management Service with Firestore Persistence"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import uuid
from google.cloud import firestore

from app.config import get_settings
from app.utils.logger import get_logger
from app.models.session import Session, SessionStatus, SessionCreate

logger = get_logger(__name__)
settings = get_settings()


class SessionManager:
    """
    Manages user sessions with Firestore persistence.

    All sessions are associated with authenticated user IDs from IAP.

    Firestore Schema (sessions collection):
    {
        "session_id": "sess_abc123",
        "user_id": "1234567890",
        "user_email": "user@example.com",
        "user_name": "Test User",
        "location": "Mars Colony",
        "status": "active",
        "created_at": "2025-11-23T15:00:00Z",
        "updated_at": "2025-11-23T15:30:00Z",
        "expires_at": "2025-11-23T16:00:00Z",
        "conversation_history": [],
        "metadata": {},
        "current_phase": "PHASE_1",
        "turn_count": 5
    }
    """

    def __init__(self):
        self.db = firestore.Client(
            project=settings.gcp_project_id,
            database=settings.firestore_database
        )
        self.collection = self.db.collection(settings.firestore_sessions_collection)

    async def create_session(
        self,
        user_id: str,
        user_email: str,
        session_data: SessionCreate
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

        session = Session(
            session_id=session_id,
            user_id=user_id,
            user_email=user_email,
            user_name=session_data.user_name,
            location=session_data.location,
            status=SessionStatus.INITIALIZED,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            conversation_history=[],
            metadata={},
            turn_count=0
        )

        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.set(session.model_dump(mode='json'))

            logger.info(
                "Session created successfully",
                session_id=session_id,
                user_id=user_id,
                user_email=user_email,
                location=session_data.location
            )

            return session

        except Exception as e:
            logger.error(
                "Failed to create session",
                user_id=user_id,
                error=str(e)
            )
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

            for date_field in ['created_at', 'updated_at', 'expires_at']:
                if date_field in data and isinstance(data[date_field], str):
                    data[date_field] = datetime.fromisoformat(
                        data[date_field].replace('Z', '+00:00')
                    )

            session = Session(**data)

            if datetime.now(timezone.utc) > session.expires_at:
                logger.warning(
                    "Session expired",
                    session_id=session_id,
                    expired_at=session.expires_at.isoformat()
                )
                await self.update_session_status(session_id, SessionStatus.TIMEOUT)
                return None

            return session

        except Exception as e:
            logger.error("Failed to retrieve session", session_id=session_id, error=str(e))
            raise

    async def update_session_status(
        self,
        session_id: str,
        status: SessionStatus
    ) -> None:
        """Update session status"""
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update({
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })

            logger.info(
                "Session status updated",
                session_id=session_id,
                new_status=status.value
            )

        except Exception as e:
            logger.error(
                "Failed to update session status",
                session_id=session_id,
                error=str(e)
            )
            raise

    async def add_conversation_turn(
        self,
        session_id: str,
        turn_data: Dict[str, Any]
    ) -> None:
        """
        Add conversation turn to session history.

        Args:
            session_id: Session identifier
            turn_data: Turn information (user input, responses, etc.)
        """
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update({
                "conversation_history": firestore.ArrayUnion([turn_data]),
                "turn_count": firestore.Increment(1),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })

            logger.info(
                "Conversation turn added",
                session_id=session_id,
                turn_number=turn_data.get("turn_number")
            )

        except Exception as e:
            logger.error(
                "Failed to add conversation turn",
                session_id=session_id,
                error=str(e)
            )
            raise

    async def update_session_phase(
        self,
        session_id: str,
        phase: str
    ) -> None:
        """Update current phase of session"""
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update({
                "current_phase": phase,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })

            logger.info(
                "Session phase updated",
                session_id=session_id,
                phase=phase
            )

        except Exception as e:
            logger.error(
                "Failed to update session phase",
                session_id=session_id,
                error=str(e)
            )
            raise

    async def update_session_atomic(
        self,
        session_id: str,
        turn_data: Dict[str, Any],
        new_phase: Optional[str] = None,
        new_status: Optional[SessionStatus] = None
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
                    "updated_at": datetime.now(timezone.utc).isoformat()
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
                status_updated=new_status is not None
            )

        except Exception as e:
            logger.error(
                "Failed to update session atomically",
                session_id=session_id,
                error=str(e)
            )
            raise

    async def close_session(self, session_id: str) -> None:
        """
        Close session and mark as complete.
        This should also decrement the concurrent session counter.
        """
        try:
            doc_ref = self.collection.document(session_id)
            doc_ref.update({
                "status": SessionStatus.CLOSED.value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })

            logger.info("Session closed", session_id=session_id)

        except Exception as e:
            logger.error("Failed to close session", session_id=session_id, error=str(e))
            raise

    async def get_user_active_sessions(self, user_id: str) -> int:
        """Get count of active sessions for user"""
        try:
            query = self.collection.where("user_id", "==", user_id).where(
                "status", "in", [
                    SessionStatus.INITIALIZED.value,
                    SessionStatus.MC_PHASE.value,
                    SessionStatus.ACTIVE.value,
                    SessionStatus.SCENE_COMPLETE.value,
                    SessionStatus.COACH_PHASE.value
                ]
            )

            results = query.stream()
            count = sum(1 for _ in results)

            logger.debug("Active sessions counted", user_id=user_id, count=count)
            return count

        except Exception as e:
            logger.error("Failed to count active sessions", user_id=user_id, error=str(e))
            return 0


def get_session_manager() -> SessionManager:
    """Get session manager instance"""
    return SessionManager()
