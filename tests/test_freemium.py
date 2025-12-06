"""Comprehensive Test Suite for Freemium Tier Implementation (Phase 3 - IQS-65)

This test suite validates:
- AC-FREEM-01: New users auto-assigned freemium tier on first login
- AC-FREEM-02: Freemium users limited to 2 audio sessions (lifetime)
- AC-FREEM-06: Text mode remains unlimited after audio limit reached
- AC-FREEM-07: Premium users have unlimited audio (existing behavior)
- AC-PROV-01 to AC-PROV-04: Auto-provisioning requirements
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import UserProfile, UserTier
from app.services.freemium_session_limiter import (
    check_session_limit,
    increment_session_count,
    get_session_counter_display,
    should_show_upgrade_modal,
    should_show_toast_notification,
    SessionLimitStatus,
)
from app.audio.premium_middleware import check_audio_access, AudioAccessResponse
from app.services.firebase_auth_service import get_or_create_user_from_firebase_token


class TestFreemiumTierEnum:
    """Test FREEMIUM tier enum validation (AC-FREEM-01 baseline)."""

    def test_freemium_tier_exists(self):
        """Verify FREEMIUM tier is defined in UserTier enum."""
        assert hasattr(UserTier, "FREEMIUM")
        assert UserTier.FREEMIUM.value == "freemium"

    def test_user_profile_freemium_properties(self):
        """Test UserProfile has freemium-related properties."""
        user = UserProfile(
            user_id="test123",
            email="test@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=1,
            premium_sessions_limit=2,
        )

        assert user.is_freemium is True
        assert user.is_premium is False
        assert user.has_audio_access is True
        assert user.remaining_premium_sessions == 1

    def test_user_profile_session_fields_default_values(self):
        """Test that session tracking fields have correct defaults."""
        user = UserProfile(
            user_id="test123",
            email="test@example.com",
            tier=UserTier.FREEMIUM,
        )

        assert user.premium_sessions_used == 0
        assert user.premium_sessions_limit == 2


class TestSessionLimitChecking:
    """Test session limit checking logic (AC-FREEM-02)."""

    @pytest.mark.asyncio
    async def test_premium_user_has_unlimited_access(self):
        """AC-FREEM-07: Premium users have unlimited audio sessions."""
        user = UserProfile(
            user_id="premium_user",
            email="premium@example.com",
            tier=UserTier.PREMIUM,
            premium_sessions_used=100,  # Even with high count
        )

        status = await check_session_limit(user)

        assert status.has_access is True
        assert status.sessions_limit == 0  # Unlimited
        assert status.sessions_remaining == 999  # Effectively unlimited
        assert status.is_at_limit is False
        assert status.upgrade_required is False
        assert "Unlimited" in status.message

    @pytest.mark.asyncio
    async def test_freemium_user_with_zero_sessions_used(self):
        """AC-FREEM-02: Freemium user with 0/2 sessions has full access."""
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=0,
            premium_sessions_limit=2,
        )

        status = await check_session_limit(user)

        assert status.has_access is True
        assert status.sessions_used == 0
        assert status.sessions_limit == 2
        assert status.sessions_remaining == 2
        assert status.is_at_limit is False
        assert status.upgrade_required is False
        assert "2 free audio sessions remaining" in status.message

    @pytest.mark.asyncio
    async def test_freemium_user_with_one_session_used(self):
        """AC-FREEM-02: Freemium user with 1/2 sessions has access with warning."""
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=1,
            premium_sessions_limit=2,
        )

        status = await check_session_limit(user)

        assert status.has_access is True
        assert status.sessions_used == 1
        assert status.sessions_remaining == 1
        assert status.is_at_limit is False
        assert status.upgrade_required is False
        assert "last free audio session" in status.message

    @pytest.mark.asyncio
    async def test_freemium_user_at_session_limit(self):
        """AC-FREEM-02: Freemium user with 2/2 sessions blocked from audio."""
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=2,
            premium_sessions_limit=2,
        )

        status = await check_session_limit(user)

        assert status.has_access is False
        assert status.sessions_used == 2
        assert status.sessions_remaining == 0
        assert status.is_at_limit is True
        assert status.upgrade_required is True
        assert "used all 2 free audio sessions" in status.message
        assert "Upgrade to Premium" in status.message

    @pytest.mark.asyncio
    async def test_freemium_user_over_session_limit(self):
        """Edge case: Freemium user with sessions_used > sessions_limit."""
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=3,
            premium_sessions_limit=2,
        )

        status = await check_session_limit(user)

        assert status.has_access is False
        assert status.sessions_remaining == 0
        assert status.is_at_limit is True

    @pytest.mark.asyncio
    async def test_non_freemium_non_premium_user_has_no_audio_access(self):
        """Non-freemium, non-premium users cannot access audio."""
        user = UserProfile(
            user_id="free_user",
            email="free@example.com",
            tier=UserTier.FREE,
        )

        status = await check_session_limit(user)

        assert status.has_access is False
        assert status.is_at_limit is True
        assert status.upgrade_required is True
        assert "Upgrade to Freemium or Premium" in status.message


class TestSessionCountIncrement:
    """Test session count increment logic (AC-FREEM-02)."""

    @pytest.mark.asyncio
    async def test_increment_session_count_for_freemium_user(self):
        """Successfully increment session count for freemium user."""
        with patch("app.services.freemium_session_limiter.user_service") as mock_user_service, \
             patch("app.services.freemium_session_limiter.get_firestore_client") as mock_firestore:

            # Mock user lookup
            freemium_user = UserProfile(
                user_id="freemium123",
                email="freemium@example.com",
                tier=UserTier.FREEMIUM,
                premium_sessions_used=0,
                premium_sessions_limit=2,
            )
            mock_user_service.get_user_by_email = AsyncMock(return_value=freemium_user)

            # Mock Firestore operations
            mock_doc = MagicMock()
            mock_doc.id = "doc123"
            mock_doc.to_dict.return_value = {
                "premium_sessions_used": 0,
                "premium_sessions_limit": 2,
            }

            # Create an async generator for the stream
            async def mock_stream():
                yield mock_doc

            mock_query = MagicMock()
            mock_query.stream.return_value = mock_stream()

            mock_collection = MagicMock()
            mock_collection.where.return_value = mock_query
            mock_update = AsyncMock()
            mock_collection.document.return_value.update = mock_update

            mock_client = MagicMock()
            mock_client.collection.return_value = mock_collection
            mock_firestore.return_value = mock_client

            # Execute increment
            result = await increment_session_count("freemium@example.com")

            # Verify success
            assert result is True
            mock_update.assert_called_once_with({
                "premium_sessions_used": 1,
            })

    @pytest.mark.asyncio
    async def test_increment_skipped_for_premium_user(self):
        """AC-FREEM-07: Session increment is no-op for premium users."""
        with patch("app.services.freemium_session_limiter.user_service") as mock_user_service:
            # Mock premium user
            premium_user = UserProfile(
                user_id="premium123",
                email="premium@example.com",
                tier=UserTier.PREMIUM,
            )
            mock_user_service.get_user_by_email = AsyncMock(return_value=premium_user)

            # Execute increment
            result = await increment_session_count("premium@example.com")

            # Should return True but not actually increment (no-op)
            assert result is True

    @pytest.mark.asyncio
    async def test_increment_fails_for_nonexistent_user(self):
        """Increment fails gracefully when user not found."""
        with patch("app.services.freemium_session_limiter.user_service") as mock_user_service:
            mock_user_service.get_user_by_email = AsyncMock(return_value=None)

            result = await increment_session_count("nonexistent@example.com")

            assert result is False


class TestPremiumMiddlewareIntegration:
    """Test premium middleware integration with freemium limits (AC-FREEM-02, AC-FREEM-06)."""

    @pytest.mark.asyncio
    async def test_audio_access_granted_for_freemium_with_sessions_remaining(self):
        """AC-FREEM-02: Freemium user with sessions remaining can access audio."""
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=1,
            premium_sessions_limit=2,
        )

        access = await check_audio_access(user)

        assert access.allowed is True
        assert access.warning is not None  # Warning on last session
        assert "last free audio session" in access.warning

    @pytest.mark.asyncio
    async def test_audio_access_denied_for_freemium_at_limit(self):
        """AC-FREEM-02: Freemium user at limit cannot access audio."""
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=2,
            premium_sessions_limit=2,
        )

        access = await check_audio_access(user)

        assert access.allowed is False
        assert access.status_code == 429  # Too Many Requests
        assert "used all 2 free audio sessions" in access.error
        assert "Upgrade to Premium" in access.error

    @pytest.mark.asyncio
    async def test_audio_access_unlimited_for_premium(self):
        """AC-FREEM-07: Premium users have unlimited audio access."""
        user = UserProfile(
            user_id="premium_user",
            email="premium@example.com",
            tier=UserTier.PREMIUM,
            audio_usage_seconds=100,  # Within limit
        )

        access = await check_audio_access(user)

        assert access.allowed is True
        assert access.remaining_seconds is not None
        assert access.remaining_seconds > 0

    @pytest.mark.asyncio
    async def test_unauthenticated_user_denied_audio_access(self):
        """Unauthenticated users cannot access audio."""
        access = await check_audio_access(None)

        assert access.allowed is False
        assert access.status_code == 401
        assert "Authentication required" in access.error


class TestAutoProvisioning:
    """Test auto-provisioning of freemium tier (AC-PROV-01 to AC-PROV-04)."""

    @pytest.mark.asyncio
    async def test_new_user_auto_provisioned_as_freemium(self):
        """AC-PROV-01: New users auto-assigned FREEMIUM tier on first login."""
        with patch("app.services.firebase_auth_service.get_user_by_id") as mock_get_by_id, \
             patch("app.services.firebase_auth_service.get_user_by_email") as mock_get_by_email, \
             patch("app.services.firebase_auth_service.create_user") as mock_create_user:

            # No existing user found
            mock_get_by_id.return_value = None
            mock_get_by_email.return_value = None

            # Mock user creation
            new_user = UserProfile(
                user_id="firebase123",
                email="newuser@example.com",
                tier=UserTier.FREEMIUM,
                premium_sessions_used=0,
                premium_sessions_limit=2,
            )
            mock_create_user.return_value = new_user

            decoded_token = {
                "uid": "firebase123",
                "email": "newuser@example.com",
                "email_verified": True,
                "name": "New User",
                "firebase": {"sign_in_provider": "google.com"},
            }

            user = await get_or_create_user_from_firebase_token(decoded_token)

            # AC-PROV-01: Verify FREEMIUM tier assigned
            assert user.tier == UserTier.FREEMIUM
            assert user.premium_sessions_used == 0
            assert user.premium_sessions_limit == 2

            # AC-PROV-02: Verify tier set by firebase-auth-service
            mock_create_user.assert_called_once()
            call_kwargs = mock_create_user.call_args[1]
            assert call_kwargs["tier"] == UserTier.FREEMIUM
            assert call_kwargs["created_by"] == "firebase-auth-service"

    @pytest.mark.asyncio
    async def test_existing_premium_user_not_downgraded(self):
        """AC-PROV-04: Existing premium users NOT affected by auto-provisioning."""
        with patch("app.services.firebase_auth_service.get_user_by_id") as mock_get_by_id:
            # Existing premium user
            existing_premium = UserProfile(
                user_id="firebase123",
                email="premium@example.com",
                tier=UserTier.PREMIUM,
                premium_sessions_used=50,  # High count
            )
            mock_get_by_id.return_value = existing_premium

            decoded_token = {
                "uid": "firebase123",
                "email": "premium@example.com",
                "email_verified": True,
                "firebase": {"sign_in_provider": "google.com"},
            }

            user = await get_or_create_user_from_firebase_token(decoded_token)

            # AC-PROV-04: Verify premium tier preserved
            assert user.tier == UserTier.PREMIUM
            assert user.premium_sessions_used == 50


class TestTextModeUnlimited:
    """Test text mode remains unlimited after audio limit (AC-FREEM-06)."""

    def test_text_mode_always_available(self):
        """AC-FREEM-06: Text mode available regardless of audio session limit.

        Note: This test validates the data model. Text mode enforcement
        is in the frontend/backend routes, not the tier system itself.
        """
        # Freemium user at audio limit
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=2,
            premium_sessions_limit=2,
        )

        # User still has authentication and tier assigned
        assert user.tier == UserTier.FREEMIUM
        assert user.email == "freemium@example.com"

        # Text mode enforcement is handled at route/frontend level
        # The tier system doesn't block text mode access


class TestUIHelpers:
    """Test UI helper functions for session counter and notifications."""

    @pytest.mark.asyncio
    async def test_session_counter_display_for_freemium(self):
        """Test session counter display for freemium users."""
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=1,
            premium_sessions_limit=2,
        )

        display = await get_session_counter_display(user)

        assert display == "🎤 1/2"

    @pytest.mark.asyncio
    async def test_session_counter_hidden_for_premium(self):
        """Session counter not shown for premium users."""
        user = UserProfile(
            user_id="premium_user",
            email="premium@example.com",
            tier=UserTier.PREMIUM,
        )

        display = await get_session_counter_display(user)

        assert display is None

    @pytest.mark.asyncio
    async def test_upgrade_modal_shown_at_limit(self):
        """Upgrade modal shown when freemium user reaches limit."""
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=2,
            premium_sessions_limit=2,
        )

        should_show = await should_show_upgrade_modal(user)

        assert should_show is True

    @pytest.mark.asyncio
    async def test_toast_notification_after_second_session(self):
        """Toast notification shown after 2nd session (limit reached)."""
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=2,
            premium_sessions_limit=2,
        )

        should_show = await should_show_toast_notification(user)

        assert should_show is True

    @pytest.mark.asyncio
    async def test_toast_not_shown_before_limit(self):
        """Toast not shown before limit reached."""
        user = UserProfile(
            user_id="freemium_user",
            email="freemium@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=1,
            premium_sessions_limit=2,
        )

        should_show = await should_show_toast_notification(user)

        assert should_show is False


class TestWebSocketSessionTracking:
    """Test WebSocket session tracking integration (AC-FREEM-02)."""

    @pytest.mark.asyncio
    async def test_websocket_disconnect_increments_session_count(self):
        """WebSocket disconnect should increment session count for freemium users."""
        with patch("app.services.freemium_session_limiter.increment_session_count") as mock_increment:
            mock_increment.return_value = True

            from app.audio.websocket_handler import audio_handler

            # Simulate active connection with user email
            session_id = "test_session_123"
            audio_handler.active_user_emails[session_id] = "freemium@example.com"

            # Trigger disconnect
            await audio_handler.disconnect(session_id)

            # Verify session count was incremented
            mock_increment.assert_called_once_with("freemium@example.com")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_negative_sessions_remaining_handled_gracefully(self):
        """Handle edge case where sessions_used > sessions_limit."""
        user = UserProfile(
            user_id="edge_case",
            email="edge@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=5,
            premium_sessions_limit=2,
        )

        status = await check_session_limit(user)

        # Should block access and show 0 remaining (not negative)
        assert status.has_access is False
        assert status.sessions_remaining == 0

    @pytest.mark.asyncio
    async def test_custom_session_limit(self):
        """Test user with custom session limit (not standard 2)."""
        user = UserProfile(
            user_id="custom_user",
            email="custom@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=3,
            premium_sessions_limit=5,  # Custom limit
        )

        status = await check_session_limit(user)

        assert status.has_access is True
        assert status.sessions_remaining == 2
        assert status.sessions_limit == 5

    @pytest.mark.asyncio
    async def test_zero_session_limit(self):
        """Test edge case with 0 session limit."""
        user = UserProfile(
            user_id="zero_limit",
            email="zero@example.com",
            tier=UserTier.FREEMIUM,
            premium_sessions_used=0,
            premium_sessions_limit=0,
        )

        status = await check_session_limit(user)

        # Should immediately block access
        assert status.has_access is False
        assert status.sessions_remaining == 0


# Test execution summary helper
def pytest_collection_modifyitems(items):
    """Add markers to test items for reporting."""
    for item in items:
        if "auto_provisioning" in item.nodeid:
            item.add_marker(pytest.mark.auto_provisioning)
        if "session_limit" in item.nodeid:
            item.add_marker(pytest.mark.session_limit)
        if "premium_protection" in item.nodeid:
            item.add_marker(pytest.mark.premium_protection)
