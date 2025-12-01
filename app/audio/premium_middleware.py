"""Premium Tier Middleware for Audio Features

This module provides access control for premium-only audio features.
Implements tier gating, usage tracking, and graceful fallbacks.
"""

from dataclasses import dataclass
from typing import Optional

from app.models.user import UserProfile, UserTier, AUDIO_USAGE_LIMITS
from app.services import user_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AudioAccessResponse:
    """Response from audio access check.

    Attributes:
        allowed: Whether audio access is allowed
        error: Error message if denied
        status_code: HTTP status code if denied
        remaining_seconds: Remaining audio seconds (for premium users)
        warning: Warning message (e.g., approaching limit)
    """

    allowed: bool
    error: Optional[str] = None
    status_code: Optional[int] = None
    remaining_seconds: Optional[int] = None
    warning: Optional[str] = None


@dataclass
class FallbackMode:
    """Fallback mode for non-premium users.

    Attributes:
        mode: The fallback mode ("text")
        message: Message to display to user
    """

    mode: str
    message: str


async def check_audio_access(
    user_profile: Optional[UserProfile],
) -> AudioAccessResponse:
    """Check if user has access to audio features.

    Implements tier gating:
    - Premium users: Full access (up to usage limit)
    - Regular users: 403 Forbidden
    - Free users: 403 Forbidden

    Args:
        user_profile: User's profile from Firestore

    Returns:
        AudioAccessResponse with access decision
    """
    # No profile = not authenticated
    if user_profile is None:
        logger.warning("Audio access denied: No user profile")
        return AudioAccessResponse(
            allowed=False,
            error="Authentication required for audio features",
            status_code=401,
        )

    # Check tier
    if not user_profile.is_premium:
        logger.info(
            "Audio access denied: Non-premium tier",
            email=user_profile.email,
            tier=user_profile.tier.value,
        )
        return AudioAccessResponse(
            allowed=False,
            error="Premium subscription required for audio features. Upgrade to unlock voice interactions.",
            status_code=403,
        )

    # Check usage limits for premium users
    usage_limit = AUDIO_USAGE_LIMITS.get(user_profile.tier, 0)
    current_usage = user_profile.audio_usage_seconds
    remaining = usage_limit - current_usage

    if remaining <= 0:
        logger.info(
            "Audio access denied: Usage limit exceeded",
            email=user_profile.email,
            usage=current_usage,
            limit=usage_limit,
        )
        return AudioAccessResponse(
            allowed=False,
            error="Audio usage limit exceeded for this period. Limit resets at the start of next period.",
            status_code=429,
            remaining_seconds=0,
        )

    # Access granted
    logger.debug(
        "Audio access granted",
        email=user_profile.email,
        remaining_seconds=remaining,
    )

    # Add warning if approaching limit (< 5 minutes remaining)
    warning = None
    if remaining < 300:
        warning = (
            f"You have {remaining // 60} minutes of audio remaining in this period."
        )

    return AudioAccessResponse(
        allowed=True,
        remaining_seconds=remaining,
        warning=warning,
    )


async def track_audio_usage(email: str, seconds: int) -> None:
    """Track audio usage for a user.

    Args:
        email: User's email address
        seconds: Number of seconds to add to usage
    """
    try:
        await user_service.increment_audio_usage(email, seconds)
        logger.debug(
            "Audio usage tracked",
            email=email,
            seconds=seconds,
        )
    except Exception as e:
        logger.error(
            "Failed to track audio usage",
            email=email,
            seconds=seconds,
            error=str(e),
        )


def get_fallback_mode(user_profile: Optional[UserProfile]) -> FallbackMode:
    """Get fallback mode for users who cannot access audio.

    Args:
        user_profile: User's profile (may be None for unauthenticated)

    Returns:
        FallbackMode with text mode configuration
    """
    if user_profile is None:
        return FallbackMode(
            mode="text",
            message="Sign in to access all features. Text mode is available for everyone.",
        )

    if user_profile.tier == UserTier.FREE:
        return FallbackMode(
            mode="text",
            message="Upgrade to Premium to unlock voice interactions with the MC! "
            "For now, enjoy text-based improv games.",
        )

    if user_profile.tier == UserTier.REGULAR:
        return FallbackMode(
            mode="text",
            message="Voice features are available for Premium subscribers. "
            "Upgrade to hear the MC welcome you live!",
        )

    # Premium user over limit
    return FallbackMode(
        mode="text",
        message="You've reached your audio limit for this period. "
        "Continue with text mode - your limit resets soon!",
    )
