"""
Tests for User Models - TDD Phase 3
Tests for UserTier enum and UserProfile model

Test Cases:
- TC-MODEL-01: UserTier enum has correct values
- TC-MODEL-02: UserProfile model validates required fields
- TC-MODEL-03: UserProfile model has correct defaults
- TC-MODEL-04: UserProfile serialization to dict
- TC-MODEL-05: UserProfile creation from Firestore document
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any


class TestUserTier:
    """Tests for UserTier enum."""

    def test_tc_model_01_user_tier_values(self):
        """TC-MODEL-01: UserTier enum has correct tier values."""
        from app.models.user import UserTier

        assert hasattr(UserTier, "FREE")
        assert hasattr(UserTier, "REGULAR")
        assert hasattr(UserTier, "PREMIUM")

        assert UserTier.FREE.value == "free"
        assert UserTier.REGULAR.value == "regular"
        assert UserTier.PREMIUM.value == "premium"

    def test_user_tier_from_string(self):
        """Test creating UserTier from string value."""
        from app.models.user import UserTier

        assert UserTier("free") == UserTier.FREE
        assert UserTier("regular") == UserTier.REGULAR
        assert UserTier("premium") == UserTier.PREMIUM

    def test_user_tier_invalid_value(self):
        """Test that invalid tier value raises ValueError."""
        from app.models.user import UserTier

        with pytest.raises(ValueError):
            UserTier("invalid_tier")


class TestUserProfile:
    """Tests for UserProfile model."""

    @pytest.fixture
    def sample_user_data(self) -> Dict[str, Any]:
        """Sample user data for testing."""
        return {
            "user_id": "google-oauth-12345",
            "email": "test@example.com",
            "display_name": "Test User",
            "tier": "premium",
            "tier_assigned_at": datetime.now(timezone.utc),
            "tier_expires_at": None,
            "audio_usage_seconds": 1234,
            "audio_usage_reset_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "last_login_at": datetime.now(timezone.utc),
            "created_by": "admin@example.com",
        }

    def test_tc_model_02_user_profile_required_fields(self):
        """TC-MODEL-02: UserProfile model validates required fields."""
        from app.models.user import UserProfile, UserTier

        # Should raise validation error if email is missing
        with pytest.raises((ValueError, TypeError)):
            UserProfile(user_id="123", tier=UserTier.FREE)  # Missing email

        # Should raise validation error if user_id is missing
        with pytest.raises((ValueError, TypeError)):
            UserProfile(email="test@example.com", tier=UserTier.FREE)  # Missing user_id

    def test_tc_model_03_user_profile_defaults(self):
        """TC-MODEL-03: UserProfile model has correct defaults."""
        from app.models.user import UserProfile, UserTier

        profile = UserProfile(
            user_id="google-oauth-12345",
            email="test@example.com",
            tier=UserTier.FREE,
        )

        # Check defaults
        assert profile.display_name is None or profile.display_name == ""
        assert profile.audio_usage_seconds == 0
        assert profile.tier_expires_at is None
        assert profile.created_at is not None
        assert profile.tier_assigned_at is not None

    def test_tc_model_04_user_profile_to_dict(self, sample_user_data):
        """TC-MODEL-04: UserProfile serialization to dict."""
        from app.models.user import UserProfile, UserTier

        profile = UserProfile(
            user_id=sample_user_data["user_id"],
            email=sample_user_data["email"],
            display_name=sample_user_data["display_name"],
            tier=UserTier.PREMIUM,
            audio_usage_seconds=sample_user_data["audio_usage_seconds"],
        )

        profile_dict = profile.to_dict()

        assert isinstance(profile_dict, dict)
        assert profile_dict["user_id"] == sample_user_data["user_id"]
        assert profile_dict["email"] == sample_user_data["email"]
        assert profile_dict["display_name"] == sample_user_data["display_name"]
        assert profile_dict["tier"] == "premium"
        assert profile_dict["audio_usage_seconds"] == sample_user_data["audio_usage_seconds"]

    def test_tc_model_05_user_profile_from_firestore(self, sample_user_data):
        """TC-MODEL-05: UserProfile creation from Firestore document."""
        from app.models.user import UserProfile

        # Firestore documents use string tier values
        firestore_doc = {
            "user_id": sample_user_data["user_id"],
            "email": sample_user_data["email"],
            "display_name": sample_user_data["display_name"],
            "tier": "premium",
            "audio_usage_seconds": 1234,
            "created_at": datetime.now(timezone.utc),
        }

        profile = UserProfile.from_firestore(firestore_doc)

        assert profile.user_id == sample_user_data["user_id"]
        assert profile.email == sample_user_data["email"]
        assert profile.tier.value == "premium"
        assert profile.audio_usage_seconds == 1234

    def test_user_profile_is_premium(self):
        """Test is_premium property."""
        from app.models.user import UserProfile, UserTier

        premium_user = UserProfile(
            user_id="123",
            email="test@example.com",
            tier=UserTier.PREMIUM,
        )
        regular_user = UserProfile(
            user_id="456",
            email="regular@example.com",
            tier=UserTier.REGULAR,
        )
        free_user = UserProfile(
            user_id="789",
            email="free@example.com",
            tier=UserTier.FREE,
        )

        assert premium_user.is_premium is True
        assert regular_user.is_premium is False
        assert free_user.is_premium is False

    def test_user_profile_audio_usage_limit(self):
        """Test audio_usage_limit property based on tier."""
        from app.models.user import UserProfile, UserTier

        premium_user = UserProfile(
            user_id="123",
            email="test@example.com",
            tier=UserTier.PREMIUM,
        )
        regular_user = UserProfile(
            user_id="456",
            email="regular@example.com",
            tier=UserTier.REGULAR,
        )
        free_user = UserProfile(
            user_id="789",
            email="free@example.com",
            tier=UserTier.FREE,
        )

        # Premium: 3600 seconds (1 hour)
        assert premium_user.audio_usage_limit == 3600
        # Regular: 0 (no audio)
        assert regular_user.audio_usage_limit == 0
        # Free: 0 (no audio)
        assert free_user.audio_usage_limit == 0


class TestUserProfileResponse:
    """Tests for UserProfileResponse model (API response)."""

    def test_user_profile_response_from_profile(self):
        """Test creating API response from UserProfile."""
        from app.models.user import UserProfile, UserProfileResponse, UserTier

        profile = UserProfile(
            user_id="google-oauth-12345",
            email="test@example.com",
            display_name="Test User",
            tier=UserTier.PREMIUM,
            audio_usage_seconds=1234,
        )

        response = UserProfileResponse.from_user_profile(profile)

        assert response.user_id == "google-oauth-12345"
        assert response.email == "test@example.com"
        assert response.display_name == "Test User"
        assert response.tier == "premium"
        assert response.audio_usage_seconds == 1234
        assert response.audio_usage_limit == 3600  # Premium limit
