"""Freemium Session Limiter Service

This service tracks and enforces session limits for freemium users.
Freemium users get 2 audio sessions (lifetime) before needing to upgrade.

Phase 3 - IQS-65: Freemium Tier Implementation
"""

from typing import Optional
from dataclasses import dataclass

from app.models.user import UserProfile, UserTier
from app.services import user_service
from app.services.firestore_tool_data_service import get_firestore_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SessionLimitStatus:
    """Status of session limit for a user.

    Attributes:
        has_access: Whether user can start a new audio session
        sessions_used: Number of audio sessions used
        sessions_limit: Total session limit
        sessions_remaining: Remaining sessions available
        is_at_limit: Whether user has reached their limit
        upgrade_required: Whether upgrade is needed for access
        message: User-facing message about limit status
    """

    has_access: bool
    sessions_used: int
    sessions_limit: int
    sessions_remaining: int
    is_at_limit: bool
    upgrade_required: bool
    message: str


async def check_session_limit(user_profile: UserProfile) -> SessionLimitStatus:
    """Check if freemium user can start a new audio session.

    Args:
        user_profile: User's profile from Firestore

    Returns:
        SessionLimitStatus with access decision and metadata
    """
    # Premium users have unlimited access
    if user_profile.is_premium:
        logger.debug(
            "Premium user has unlimited audio access",
            email=user_profile.email,
        )
        return SessionLimitStatus(
            has_access=True,
            sessions_used=0,
            sessions_limit=0,  # Unlimited
            sessions_remaining=999,  # Effectively unlimited
            is_at_limit=False,
            upgrade_required=False,
            message="Unlimited audio sessions available",
        )

    # Non-freemium, non-premium users have no audio access
    if not user_profile.is_freemium:
        logger.debug(
            "Non-freemium user has no audio access",
            email=user_profile.email,
            tier=user_profile.tier.value,
        )
        return SessionLimitStatus(
            has_access=False,
            sessions_used=0,
            sessions_limit=0,
            sessions_remaining=0,
            is_at_limit=True,
            upgrade_required=True,
            message="Upgrade to Freemium or Premium to access audio features",
        )

    # Freemium user - check session count
    sessions_used = user_profile.premium_sessions_used
    sessions_limit = user_profile.premium_sessions_limit
    sessions_remaining = max(0, sessions_limit - sessions_used)

    if sessions_used >= sessions_limit:
        logger.info(
            "Freemium session limit reached",
            email=user_profile.email,
            sessions_used=sessions_used,
            sessions_limit=sessions_limit,
        )
        return SessionLimitStatus(
            has_access=False,
            sessions_used=sessions_used,
            sessions_limit=sessions_limit,
            sessions_remaining=0,
            is_at_limit=True,
            upgrade_required=True,
            message=f"You've used all {sessions_limit} free audio sessions. Upgrade to Premium for unlimited access!",
        )

    # User has sessions remaining
    logger.debug(
        "Freemium user has sessions remaining",
        email=user_profile.email,
        sessions_used=sessions_used,
        sessions_remaining=sessions_remaining,
    )

    # Generate appropriate message based on remaining sessions
    if sessions_remaining == 1:
        message = "🎤 This is your last free audio session! Upgrade to Premium for unlimited access."
    elif sessions_remaining == 2:
        message = f"🎤 You have {sessions_remaining} free audio sessions remaining."
    else:
        message = f"You have {sessions_remaining} audio sessions remaining."

    return SessionLimitStatus(
        has_access=True,
        sessions_used=sessions_used,
        sessions_limit=sessions_limit,
        sessions_remaining=sessions_remaining,
        is_at_limit=False,
        upgrade_required=False,
        message=message,
    )


async def increment_session_count(email: str) -> bool:
    """Increment the session count for a freemium user using atomic increment.

    This should be called when an audio session is COMPLETED successfully.
    Not called for text-only sessions or abandoned sessions.

    SECURITY: Uses Firestore's atomic Increment operation to prevent race conditions
    when concurrent sessions complete simultaneously. This ensures the session limit
    cannot be bypassed by opening multiple browser tabs.

    Args:
        email: User's email address

    Returns:
        True if increment succeeded, False otherwise
    """
    from google.cloud.firestore_v1 import Increment

    try:
        user = await user_service.get_user_by_email(email)
        if not user:
            logger.error("Cannot increment session count: User not found", email=email)
            return False

        # Only increment for freemium users
        if user.tier != UserTier.FREEMIUM:
            logger.debug(
                "Skipping session increment for non-freemium user",
                email=email,
                tier=user.tier.value,
            )
            return True  # Not an error, just not applicable

        # Atomic increment in Firestore to prevent race conditions
        # This is critical for ensuring session limits cannot be bypassed
        client = get_firestore_client()
        collection = client.collection("users")
        query = collection.where("email", "==", email)

        async for doc in query.stream():
            doc_data = doc.to_dict()
            current_count = doc_data.get("premium_sessions_used", 0) if doc_data else 0

            # Use Firestore's atomic Increment to prevent race conditions
            # This ensures concurrent session completions don't bypass the limit
            await collection.document(doc.id).update(
                {
                    "premium_sessions_used": Increment(1),
                }
            )

            logger.info(
                "Freemium session count incremented atomically",
                email=email,
                previous_count=current_count,
                new_count=current_count + 1,
                limit=doc_data.get("premium_sessions_limit", 2) if doc_data else 2,
            )

            return True

        logger.error("Failed to find user document for session increment", email=email)
        return False

    except Exception as e:
        logger.error(
            "Failed to increment session count",
            email=email,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False


async def get_session_counter_display(
    user_profile: Optional[UserProfile],
) -> Optional[str]:
    """Get session counter display string for UI header.

    Format: "🎤 1/2 [Upgrade]" for freemium users with sessions remaining.
    Returns None for users who shouldn't see the counter.

    Args:
        user_profile: User's profile (may be None for unauthenticated)

    Returns:
        Display string or None if counter not applicable
    """
    if not user_profile or user_profile.tier != UserTier.FREEMIUM:
        return None

    sessions_used = user_profile.premium_sessions_used
    sessions_limit = user_profile.premium_sessions_limit

    return f"🎤 {sessions_used}/{sessions_limit}"


async def should_show_upgrade_modal(user_profile: UserProfile) -> bool:
    """Check if upgrade modal should be shown.

    Modal appears when freemium user attempts to start 3rd session (after limit reached).

    Args:
        user_profile: User's profile

    Returns:
        True if modal should be shown
    """
    if user_profile.tier != UserTier.FREEMIUM:
        return False

    return user_profile.premium_sessions_used >= user_profile.premium_sessions_limit


async def should_show_toast_notification(user_profile: UserProfile) -> bool:
    """Check if toast notification should be shown.

    Toast appears after 2nd session is used to warn about limit.

    Args:
        user_profile: User's profile

    Returns:
        True if toast should be shown
    """
    if user_profile.tier != UserTier.FREEMIUM:
        return False

    # Show toast after 2nd session (when they've used all their sessions)
    sessions_used = user_profile.premium_sessions_used
    sessions_limit = user_profile.premium_sessions_limit

    return sessions_used == sessions_limit and sessions_limit == 2
