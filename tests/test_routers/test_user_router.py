"""
Tests for User Router - TDD Phase 3
Tests for /api/v1/user/* endpoints

Test Cases:
- TC-ROUTER-01: GET /api/v1/user/me returns user profile for authenticated user
- TC-ROUTER-02: GET /api/v1/user/me returns 401 for unauthenticated user
- TC-ROUTER-03: GET /api/v1/user/me returns 403 for user not in Firestore
- TC-ROUTER-04: User profile response includes tier information
- TC-ROUTER-05: User profile response includes audio usage
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI


@pytest.fixture
def mock_user_service():
    """Mock user service for testing."""
    with patch("app.routers.user.get_user_by_email") as mock:
        yield mock


@pytest.fixture
def mock_oauth_middleware():
    """Mock OAuth middleware to inject user info."""
    with patch("app.middleware.oauth_auth.OAuthSessionMiddleware") as mock:
        yield mock


@pytest.fixture
def sample_user_profile():
    """Sample UserProfile for testing."""
    from app.models.user import UserProfile, UserTier

    return UserProfile(
        user_id="google-oauth-12345",
        email="test@example.com",
        display_name="Test User",
        tier=UserTier.PREMIUM,
        audio_usage_seconds=1234,
    )


@pytest.fixture
def app_with_user_router():
    """Create test app with user router."""
    from fastapi import FastAPI
    from app.routers.user import router

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def authenticated_client(app_with_user_router):
    """Test client with authenticated user."""
    from starlette.testclient import TestClient

    client = TestClient(app_with_user_router)
    return client


class TestGetCurrentUser:
    """Tests for GET /api/v1/user/me endpoint."""

    @pytest.mark.asyncio
    async def test_tc_router_01_get_me_authenticated(
        self, mock_user_service, sample_user_profile
    ):
        """TC-ROUTER-01: GET /api/v1/user/me returns user profile for authenticated user."""
        from app.routers.user import get_current_user
        from app.models.user import UserProfileResponse
        from fastapi import Request

        mock_user_service.return_value = sample_user_profile

        # Create mock request with user state
        mock_request = MagicMock(spec=Request)
        mock_request.state.user_email = "test@example.com"
        mock_request.state.user_id = "google-oauth-12345"

        result = await get_current_user(mock_request)

        assert isinstance(result, UserProfileResponse)
        assert result.user_id == "google-oauth-12345"
        assert result.email == "test@example.com"
        assert result.tier == "premium"

    @pytest.mark.asyncio
    async def test_tc_router_02_get_me_unauthenticated(self):
        """TC-ROUTER-02: GET /api/v1/user/me returns 401 for unauthenticated user."""
        from app.routers.user import get_current_user
        from fastapi import Request, HTTPException

        # Create mock request without user state
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        del mock_request.state.user_email  # Remove user_email attribute

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_tc_router_03_get_me_user_not_in_firestore(self, mock_user_service):
        """TC-ROUTER-03: GET /api/v1/user/me returns 403 for user not in Firestore."""
        from app.routers.user import get_current_user
        from fastapi import Request, HTTPException

        mock_user_service.return_value = None  # User not found in Firestore

        mock_request = MagicMock(spec=Request)
        mock_request.state.user_email = "notregistered@example.com"
        mock_request.state.user_id = "google-oauth-99999"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 403
        assert "not authorized" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_tc_router_04_response_includes_tier(
        self, mock_user_service, sample_user_profile
    ):
        """TC-ROUTER-04: User profile response includes tier information."""
        from app.routers.user import get_current_user
        from fastapi import Request

        mock_user_service.return_value = sample_user_profile

        mock_request = MagicMock(spec=Request)
        mock_request.state.user_email = "test@example.com"
        mock_request.state.user_id = "google-oauth-12345"

        result = await get_current_user(mock_request)

        assert hasattr(result, "tier")
        assert result.tier in ["free", "regular", "premium"]

    @pytest.mark.asyncio
    async def test_tc_router_05_response_includes_audio_usage(
        self, mock_user_service, sample_user_profile
    ):
        """TC-ROUTER-05: User profile response includes audio usage."""
        from app.routers.user import get_current_user
        from fastapi import Request

        mock_user_service.return_value = sample_user_profile

        mock_request = MagicMock(spec=Request)
        mock_request.state.user_email = "test@example.com"
        mock_request.state.user_id = "google-oauth-12345"

        result = await get_current_user(mock_request)

        assert hasattr(result, "audio_usage_seconds")
        assert hasattr(result, "audio_usage_limit")
        assert isinstance(result.audio_usage_seconds, int)
        assert isinstance(result.audio_usage_limit, int)


class TestUserRouterIntegration:
    """Integration tests for user router."""

    def test_router_prefix(self):
        """Test that router has correct prefix."""
        from app.routers.user import router

        assert router.prefix == "/api/v1/user"

    def test_router_tags(self):
        """Test that router has correct tags."""
        from app.routers.user import router

        assert "user" in router.tags

    def test_get_me_endpoint_exists(self):
        """Test that /me endpoint exists."""
        from app.routers.user import router

        routes = [route.path for route in router.routes]
        assert "/me" in routes or any("/me" in route for route in routes)


class TestUserProfileResponseFormat:
    """Tests for the API response format."""

    def test_response_schema(self):
        """Test that response matches expected schema."""
        from app.models.user import UserProfileResponse

        # Verify required fields exist in the model
        response = UserProfileResponse(
            user_id="123",
            email="test@example.com",
            display_name="Test",
            tier="premium",
            audio_usage_seconds=0,
            audio_usage_limit=3600,
        )

        # Check all required fields
        assert response.user_id is not None
        assert response.email is not None
        assert response.tier is not None
        assert response.audio_usage_seconds is not None
        assert response.audio_usage_limit is not None

    def test_response_json_serialization(self):
        """Test that response can be serialized to JSON."""
        from app.models.user import UserProfileResponse

        response = UserProfileResponse(
            user_id="123",
            email="test@example.com",
            display_name="Test",
            tier="premium",
            audio_usage_seconds=1234,
            audio_usage_limit=3600,
        )

        json_data = response.model_dump()

        assert json_data["user_id"] == "123"
        assert json_data["email"] == "test@example.com"
        assert json_data["tier"] == "premium"
        assert json_data["audio_usage_seconds"] == 1234
        assert json_data["audio_usage_limit"] == 3600
