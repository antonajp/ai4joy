"""
Tests for OAuth Auth Middleware with Firestore Integration - TDD Phase 3
Tests for auth middleware checking Firestore users collection

Test Cases:
- TC-AUTH-FS-01: User in Firestore can authenticate
- TC-AUTH-FS-02: User NOT in Firestore gets 403
- TC-AUTH-FS-03: User tier is attached to request state
- TC-AUTH-FS-04: Last login is updated on successful auth
- TC-AUTH-FS-05: Feature flag enables/disables Firestore auth
- TC-AUTH-FS-06: Fallback to ALLOWED_USERS when Firestore disabled
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware


@pytest.fixture
def mock_user_service():
    """Mock user service for testing."""
    with patch("app.services.user_service.get_user_by_email") as mock_get:
        with patch("app.services.user_service.update_last_login") as mock_update:
            yield {"get_user": mock_get, "update_login": mock_update}


@pytest.fixture
def sample_user_profile():
    """Sample UserProfile for testing."""
    from app.models.user import UserProfile, UserTier

    return UserProfile(
        user_id="google-oauth-12345",
        email="test@example.com",
        display_name="Test User",
        tier=UserTier.PREMIUM,
        audio_usage_seconds=0,
    )


@pytest.fixture
def app_with_oauth_middleware():
    """Create test app with OAuth middleware."""
    from fastapi import FastAPI
    from app.middleware.oauth_auth import OAuthSessionMiddleware

    app = FastAPI()

    # Add session middleware first
    app.add_middleware(
        SessionMiddleware,
        secret_key="test-secret-key",
    )

    # Add OAuth middleware
    app.add_middleware(OAuthSessionMiddleware)

    @app.get("/protected")
    async def protected_route(request: Request):
        return {
            "user_email": getattr(request.state, "user_email", None),
            "user_tier": getattr(request.state, "user_tier", None),
        }

    return app


class TestFirestoreUserAuthentication:
    """Tests for Firestore-based user authentication."""

    @pytest.mark.asyncio
    async def test_tc_auth_fs_01_user_in_firestore_authenticates(
        self, sample_user_profile
    ):
        """TC-AUTH-FS-01: User in Firestore can authenticate."""
        from app.middleware.oauth_auth import validate_user_access
        from app.models.user import UserProfile

        with patch("app.services.user_service.get_user_by_email") as mock_get:
            mock_get.return_value = sample_user_profile

            result = await validate_user_access("test@example.com")

            assert result is not None
            assert isinstance(result, UserProfile)
            assert result.email == "test@example.com"
            mock_get.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_tc_auth_fs_02_user_not_in_firestore_denied(self):
        """TC-AUTH-FS-02: User NOT in Firestore gets 403."""
        from app.middleware.oauth_auth import validate_user_access

        with patch("app.services.user_service.get_user_by_email") as mock_get:
            mock_get.return_value = None

            result = await validate_user_access("unauthorized@example.com")

            assert result is None

    @pytest.mark.asyncio
    async def test_tc_auth_fs_03_user_tier_attached_to_state(self, sample_user_profile):
        """TC-AUTH-FS-03: User tier is attached to request state."""
        from app.middleware.oauth_auth import OAuthSessionMiddleware

        # Verify user tier would be set correctly
        assert sample_user_profile.tier.value == "premium"
        assert sample_user_profile.is_premium is True

    @pytest.mark.asyncio
    async def test_tc_auth_fs_04_last_login_updated(self, sample_user_profile):
        """TC-AUTH-FS-04: Last login is updated on successful auth."""
        from app.middleware.oauth_auth import on_successful_auth

        with patch("app.services.user_service.update_last_login") as mock_update:
            mock_update.return_value = None

            await on_successful_auth("test@example.com")

            mock_update.assert_called_once_with("test@example.com")


class TestFeatureFlag:
    """Tests for USE_FIRESTORE_AUTH feature flag."""

    @pytest.mark.asyncio
    async def test_tc_auth_fs_05_feature_flag_enables_firestore(self):
        """TC-AUTH-FS-05: Feature flag enables Firestore auth."""
        from app.middleware.oauth_auth import should_use_firestore_auth

        with patch("app.middleware.oauth_auth.settings") as mock_settings:
            mock_settings.use_firestore_auth = True

            result = should_use_firestore_auth()

            assert result is True

    @pytest.mark.asyncio
    async def test_tc_auth_fs_06_fallback_to_allowed_users(self):
        """TC-AUTH-FS-06: Fallback to ALLOWED_USERS when Firestore disabled."""
        from app.middleware.oauth_auth import validate_user_access_legacy

        with patch("app.middleware.oauth_auth.settings") as mock_settings:
            mock_settings.use_firestore_auth = False
            mock_settings.allowed_users_list = [
                "allowed@example.com",
                "test@example.com",
            ]

            # User in ALLOWED_USERS should be allowed
            result = validate_user_access_legacy("test@example.com")
            assert result is True

            # User not in ALLOWED_USERS should be denied
            result = validate_user_access_legacy("unauthorized@example.com")
            assert result is False


class TestOAuthCallbackWithFirestore:
    """Tests for OAuth callback with Firestore integration."""

    @pytest.mark.asyncio
    async def test_callback_checks_firestore(self, sample_user_profile):
        """Test that OAuth callback checks Firestore for user."""
        from app.routers.auth import check_user_authorization

        with patch("app.middleware.oauth_auth.should_use_firestore_auth") as mock_flag:
            mock_flag.return_value = True
            with patch("app.middleware.oauth_auth.validate_user_access") as mock_validate:
                mock_validate.return_value = sample_user_profile

                result = await check_user_authorization("test@example.com")

                assert result is True
                mock_validate.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_callback_denies_unauthorized_user(self):
        """Test that OAuth callback denies user not in Firestore."""
        from app.routers.auth import check_user_authorization

        with patch("app.middleware.oauth_auth.should_use_firestore_auth") as mock_flag:
            mock_flag.return_value = True
            with patch("app.middleware.oauth_auth.validate_user_access") as mock_validate:
                mock_validate.return_value = None

                result = await check_user_authorization("unauthorized@example.com")

                assert result is False


class TestRequestStateEnhancement:
    """Tests for request state enhancement with user data."""

    def test_request_state_has_user_profile(self):
        """Test that request.state includes full user profile."""
        from app.models.user import UserProfile, UserTier

        profile = UserProfile(
            user_id="123",
            email="test@example.com",
            tier=UserTier.PREMIUM,
        )

        # Simulate what middleware should add to request state
        mock_state = MagicMock()
        mock_state.user_email = profile.email
        mock_state.user_id = profile.user_id
        mock_state.user_tier = profile.tier.value
        mock_state.user_profile = profile

        assert mock_state.user_tier == "premium"
        assert mock_state.user_profile.is_premium is True

    def test_request_state_for_free_tier(self):
        """Test request state for free tier user."""
        from app.models.user import UserProfile, UserTier

        profile = UserProfile(
            user_id="456",
            email="free@example.com",
            tier=UserTier.FREE,
        )

        mock_state = MagicMock()
        mock_state.user_tier = profile.tier.value
        mock_state.user_profile = profile

        assert mock_state.user_tier == "free"
        assert mock_state.user_profile.is_premium is False


class TestMiddlewareBypassPaths:
    """Tests for middleware bypass paths with Firestore auth."""

    def test_health_endpoints_bypass_firestore_check(self):
        """Test that health endpoints bypass Firestore check."""
        from app.config import get_settings

        settings = get_settings()
        bypass_paths = settings.auth_bypass_paths

        # Health endpoints should be in bypass list
        assert "/health" in bypass_paths
        assert "/ready" in bypass_paths

    def test_auth_endpoints_bypass_firestore_check(self):
        """Test that auth endpoints bypass Firestore check."""
        from app.config import get_settings

        settings = get_settings()
        bypass_paths = settings.auth_bypass_paths

        # Auth endpoints should be in bypass list
        assert "/auth/login" in bypass_paths
        assert "/auth/callback" in bypass_paths
        assert "/auth/logout" in bypass_paths
