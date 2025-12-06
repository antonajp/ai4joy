"""User Models for Firestore-based Tier System

This module defines the user profile models for the tier-based access control system.
Supports free, regular, and premium tiers with audio usage tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class UserTier(str, Enum):
    """User tier levels for feature access control."""

    FREE = "free"
    REGULAR = "regular"
    FREEMIUM = "freemium"  # Limited audio access (2 sessions lifetime)
    PREMIUM = "premium"


# Audio usage limits by tier (in seconds)
AUDIO_USAGE_LIMITS = {
    UserTier.FREE: 0,  # No audio access
    UserTier.REGULAR: 0,  # No audio access
    UserTier.FREEMIUM: 0,  # Session-based limit (not time-based)
    UserTier.PREMIUM: 3600,  # 1 hour per reset period
}


@dataclass
class UserProfile:
    """User profile stored in Firestore.

    Attributes:
        user_id: Google OAuth user ID
        email: User email address (required, indexed)
        tier: User tier level (free, regular, premium)
        display_name: Optional display name
        tier_assigned_at: When the tier was assigned
        tier_expires_at: Optional tier expiration date
        audio_usage_seconds: Current audio usage in seconds
        audio_usage_reset_at: When audio usage was last reset
        created_at: Account creation timestamp
        last_login_at: Last login timestamp
        created_by: Admin who provisioned the account
        mfa_enabled: Whether MFA is enabled for this user (Phase 2 - IQS-65)
        mfa_secret: TOTP secret for MFA (base32 encoded)
        mfa_enrolled_at: When MFA was enrolled
        recovery_codes_hash: Hashed recovery codes for MFA bypass
    """

    user_id: str
    email: str
    tier: UserTier
    display_name: Optional[str] = None
    tier_assigned_at: Optional[datetime] = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    tier_expires_at: Optional[datetime] = None
    audio_usage_seconds: int = 0
    audio_usage_reset_at: Optional[datetime] = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    created_at: Optional[datetime] = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Optional[datetime] = None
    created_by: Optional[str] = None

    # MFA fields (Phase 2 - IQS-65)
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None  # TOTP secret (base32 encoded)
    mfa_enrolled_at: Optional[datetime] = None
    recovery_codes_hash: Optional[List[str]] = field(
        default_factory=list
    )  # Hashed recovery codes

    # Freemium session tracking (Phase 3 - IQS-65)
    premium_sessions_used: int = 0  # Number of audio sessions completed
    premium_sessions_limit: int = 2  # Default limit for freemium users

    @property
    def is_premium(self) -> bool:
        """Check if user has premium tier."""
        return self.tier == UserTier.PREMIUM

    @property
    def is_freemium(self) -> bool:
        """Check if user has freemium tier."""
        return self.tier == UserTier.FREEMIUM

    @property
    def has_audio_access(self) -> bool:
        """Check if user has any audio access (freemium or premium)."""
        return self.tier in (UserTier.FREEMIUM, UserTier.PREMIUM)

    @property
    def remaining_premium_sessions(self) -> int:
        """Get remaining audio sessions for freemium users."""
        if self.tier != UserTier.FREEMIUM:
            return 0  # Not applicable for non-freemium
        return max(0, self.premium_sessions_limit - self.premium_sessions_used)

    @property
    def audio_usage_limit(self) -> int:
        """Get audio usage limit in seconds based on tier."""
        return AUDIO_USAGE_LIMITS.get(self.tier, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore storage."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name or "",
            "tier": self.tier.value,
            "tier_assigned_at": self.tier_assigned_at,
            "tier_expires_at": self.tier_expires_at,
            "audio_usage_seconds": self.audio_usage_seconds,
            "audio_usage_reset_at": self.audio_usage_reset_at,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at,
            "created_by": self.created_by,
            "mfa_enabled": self.mfa_enabled,
            "mfa_secret": self.mfa_secret or "",
            "mfa_enrolled_at": self.mfa_enrolled_at,
            "recovery_codes_hash": self.recovery_codes_hash or [],
            "premium_sessions_used": self.premium_sessions_used,
            "premium_sessions_limit": self.premium_sessions_limit,
        }

    @classmethod
    def from_firestore(cls, doc: Dict[str, Any]) -> "UserProfile":
        """Create UserProfile from Firestore document.

        Args:
            doc: Firestore document dictionary

        Returns:
            UserProfile instance
        """
        tier_value = doc.get("tier", "free")
        if isinstance(tier_value, str):
            # Handle case-insensitive tier values from Firestore
            tier = UserTier(tier_value.lower())
        else:
            tier = tier_value

        return cls(
            user_id=doc.get("user_id", ""),
            email=doc.get("email", ""),
            display_name=doc.get("display_name"),
            tier=tier,
            tier_assigned_at=doc.get("tier_assigned_at"),
            tier_expires_at=doc.get("tier_expires_at"),
            audio_usage_seconds=doc.get("audio_usage_seconds", 0),
            audio_usage_reset_at=doc.get("audio_usage_reset_at"),
            created_at=doc.get("created_at"),
            last_login_at=doc.get("last_login_at"),
            created_by=doc.get("created_by"),
            mfa_enabled=doc.get("mfa_enabled", False),
            mfa_secret=doc.get("mfa_secret"),
            mfa_enrolled_at=doc.get("mfa_enrolled_at"),
            recovery_codes_hash=doc.get("recovery_codes_hash", []),
            premium_sessions_used=doc.get("premium_sessions_used", 0),
            premium_sessions_limit=doc.get("premium_sessions_limit", 2),
        )


class UserProfileResponse(BaseModel):
    """API response model for user profile.

    This is the response format for GET /api/v1/user/me endpoint.
    """

    user_id: str = Field(..., description="Google OAuth user ID")
    email: str = Field(..., description="User email address")
    display_name: Optional[str] = Field(None, description="User display name")
    tier: str = Field(..., description="User tier: free, regular, or premium")
    audio_usage_seconds: int = Field(0, description="Current audio usage in seconds")
    audio_usage_limit: int = Field(0, description="Audio usage limit in seconds")

    @classmethod
    def from_user_profile(cls, profile: UserProfile) -> "UserProfileResponse":
        """Create API response from UserProfile.

        Args:
            profile: UserProfile instance

        Returns:
            UserProfileResponse for API
        """
        return cls(
            user_id=profile.user_id,
            email=profile.email,
            display_name=profile.display_name,
            tier=profile.tier.value,
            audio_usage_seconds=profile.audio_usage_seconds,
            audio_usage_limit=profile.audio_usage_limit,
        )
