"""Per-User Rate Limiting Service with Firestore Backend"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from google.cloud import firestore
from fastapi import HTTPException, status

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit violations"""

    def __init__(self, limit_type: str, reset_time: Optional[datetime] = None):
        detail = f"Rate limit exceeded: {limit_type}"
        if reset_time:
            detail += f". Resets at {reset_time.isoformat()}"

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "3600"}
        )


class RateLimiter:
    """
    Per-user rate limiting with Firestore persistence.

    Limits:
    - Daily sessions: 10 sessions per user per day (resets at midnight UTC)
    - Concurrent sessions: 3 active sessions per user at any time

    Firestore Schema (user_limits collection):
    {
        "user_id": "1234567890",
        "daily_sessions": {
            "count": 5,
            "reset_at": "2025-11-24T00:00:00Z"
        },
        "concurrent_sessions": {
            "count": 2,
            "active_session_ids": ["sess_1", "sess_2"]
        },
        "last_updated": "2025-11-23T15:30:00Z"
    }
    """

    def __init__(self):
        self.db = firestore.Client(
            project=settings.gcp_project_id,
            database=settings.firestore_database
        )
        self.collection = self.db.collection(settings.firestore_user_limits_collection)

    async def check_and_increment_daily_limit(self, user_id: str) -> None:
        """
        Check daily session limit and increment counter.

        Raises:
            RateLimitExceeded: If daily limit exceeded
        """
        doc_ref = self.collection.document(user_id)
        now = datetime.now(timezone.utc)
        midnight_utc = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        try:
            transaction = self.db.transaction()

            @firestore.transactional
            def update_in_transaction(transaction, doc_ref):
                snapshot = doc_ref.get(transaction=transaction)

                if snapshot.exists:
                    data = snapshot.to_dict()
                    daily = data.get("daily_sessions", {})

                    reset_at_str = daily.get("reset_at")
                    if reset_at_str:
                        reset_at = datetime.fromisoformat(reset_at_str.replace("Z", "+00:00"))
                        if now >= reset_at:
                            daily = {"count": 0, "reset_at": midnight_utc.isoformat()}
                    else:
                        daily = {"count": 0, "reset_at": midnight_utc.isoformat()}

                    current_count = daily.get("count", 0)

                    if current_count >= settings.rate_limit_daily_sessions:
                        raise RateLimitExceeded(
                            f"Daily limit ({settings.rate_limit_daily_sessions} sessions)",
                            reset_time=datetime.fromisoformat(daily["reset_at"].replace("Z", "+00:00"))
                        )

                    daily["count"] = current_count + 1
                    transaction.update(doc_ref, {
                        "daily_sessions": daily,
                        "last_updated": now.isoformat()
                    })

                    logger.info(
                        "Daily limit check passed",
                        user_id=user_id,
                        current_count=daily["count"],
                        limit=settings.rate_limit_daily_sessions
                    )
                else:
                    daily = {"count": 1, "reset_at": midnight_utc.isoformat()}
                    transaction.set(doc_ref, {
                        "user_id": user_id,
                        "daily_sessions": daily,
                        "concurrent_sessions": {"count": 0, "active_session_ids": []},
                        "last_updated": now.isoformat()
                    })

                    logger.info(
                        "Created new rate limit record",
                        user_id=user_id
                    )

            update_in_transaction(transaction, doc_ref)

        except RateLimitExceeded:
            logger.warning(
                "Daily rate limit exceeded",
                user_id=user_id,
                limit=settings.rate_limit_daily_sessions
            )
            raise
        except Exception as e:
            logger.error("Rate limit check failed", user_id=user_id, error=str(e))
            raise

    async def check_and_increment_concurrent_limit(
        self, user_id: str, session_id: str
    ) -> None:
        """
        Check concurrent session limit and add session to active list.

        Raises:
            RateLimitExceeded: If concurrent limit exceeded
        """
        doc_ref = self.collection.document(user_id)
        now = datetime.now(timezone.utc)

        try:
            transaction = self.db.transaction()

            @firestore.transactional
            def update_in_transaction(transaction, doc_ref):
                snapshot = doc_ref.get(transaction=transaction)

                if snapshot.exists:
                    data = snapshot.to_dict()
                    concurrent = data.get("concurrent_sessions", {})
                    active_sessions = concurrent.get("active_session_ids", [])

                    if session_id in active_sessions:
                        logger.debug(
                            "Session already counted in concurrent limit",
                            user_id=user_id,
                            session_id=session_id
                        )
                        return

                    if len(active_sessions) >= settings.rate_limit_concurrent_sessions:
                        raise RateLimitExceeded(
                            f"Concurrent session limit ({settings.rate_limit_concurrent_sessions} sessions)"
                        )

                    active_sessions.append(session_id)
                    concurrent["count"] = len(active_sessions)
                    concurrent["active_session_ids"] = active_sessions

                    transaction.update(doc_ref, {
                        "concurrent_sessions": concurrent,
                        "last_updated": now.isoformat()
                    })

                    logger.info(
                        "Concurrent limit check passed",
                        user_id=user_id,
                        session_id=session_id,
                        current_count=concurrent["count"],
                        limit=settings.rate_limit_concurrent_sessions
                    )
                else:
                    logger.warning(
                        "User limit doc not found for concurrent check",
                        user_id=user_id
                    )

            update_in_transaction(transaction, doc_ref)

        except RateLimitExceeded:
            logger.warning(
                "Concurrent rate limit exceeded",
                user_id=user_id,
                limit=settings.rate_limit_concurrent_sessions
            )
            raise
        except Exception as e:
            logger.error(
                "Concurrent limit check failed",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def decrement_concurrent_sessions(self, user_id: str, session_id: str) -> None:
        """
        Remove session from concurrent active list.
        Called when session is closed or times out.
        """
        doc_ref = self.collection.document(user_id)
        now = datetime.now(timezone.utc)

        try:
            transaction = self.db.transaction()

            @firestore.transactional
            def update_in_transaction(transaction, doc_ref):
                snapshot = doc_ref.get(transaction=transaction)

                if snapshot.exists:
                    data = snapshot.to_dict()
                    concurrent = data.get("concurrent_sessions", {})
                    active_sessions = concurrent.get("active_session_ids", [])

                    if session_id in active_sessions:
                        active_sessions.remove(session_id)
                        concurrent["count"] = len(active_sessions)
                        concurrent["active_session_ids"] = active_sessions

                        transaction.update(doc_ref, {
                            "concurrent_sessions": concurrent,
                            "last_updated": now.isoformat()
                        })

                        logger.info(
                            "Decremented concurrent sessions",
                            user_id=user_id,
                            session_id=session_id,
                            remaining_count=concurrent["count"]
                        )

            update_in_transaction(transaction, doc_ref)

        except Exception as e:
            logger.error(
                "Failed to decrement concurrent sessions",
                user_id=user_id,
                session_id=session_id,
                error=str(e)
            )

    async def get_user_limits_status(self, user_id: str) -> Dict:
        """
        Get current rate limit status for user.

        Returns:
            dict with daily and concurrent session info
        """
        try:
            doc_ref = self.collection.document(user_id)
            snapshot = doc_ref.get()

            if not snapshot.exists:
                return {
                    "daily_sessions": {
                        "used": 0,
                        "limit": settings.rate_limit_daily_sessions,
                        "reset_at": None
                    },
                    "concurrent_sessions": {
                        "active": 0,
                        "limit": settings.rate_limit_concurrent_sessions
                    }
                }

            data = snapshot.to_dict()
            daily = data.get("daily_sessions", {})
            concurrent = data.get("concurrent_sessions", {})

            return {
                "daily_sessions": {
                    "used": daily.get("count", 0),
                    "limit": settings.rate_limit_daily_sessions,
                    "reset_at": daily.get("reset_at")
                },
                "concurrent_sessions": {
                    "active": concurrent.get("count", 0),
                    "limit": settings.rate_limit_concurrent_sessions,
                    "active_session_ids": concurrent.get("active_session_ids", [])
                }
            }

        except Exception as e:
            logger.error("Failed to get user limits status", user_id=user_id, error=str(e))
            return {}


def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance"""
    return RateLimiter()
