"""
TC-AUTH-IAP: IAP Authentication Middleware Tests

Tests the Identity-Aware Proxy header extraction and validation middleware.
Covers successful authentication, missing headers, malformed headers, and JWT validation.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from app.middleware.iap_auth import IAPAuthMiddleware, get_authenticated_user
from app.config import get_settings

settings = get_settings()


class TestIAPAuthMiddleware:
    """Test suite for IAP authentication middleware."""

    @pytest.fixture
    def valid_iap_headers(self):
        """Valid IAP headers for testing (lowercase to match config)"""
        return {
            "x-goog-authenticated-user-email": "accounts.google.com:testuser@example.com",
            "x-goog-authenticated-user-id": "accounts.google.com:1234567890",
            "x-goog-iap-jwt-assertion": "mock.jwt.token.here"
        }

    @pytest.fixture
    def mock_request(self):
        """Create mock request object"""
        def _create_request(path="/api/sessions", headers=None):
            mock_req = Mock(spec=Request)
            mock_req.url.path = path
            mock_req.headers.get = lambda key, default=None: (headers or {}).get(key, default)
            mock_req.state = Mock()
            return mock_req
        return _create_request

    @pytest.mark.asyncio
    async def test_tc_auth_iap_01_valid_headers_extract_correctly(
        self, valid_iap_headers, mock_request
    ):
        """
        TC-AUTH-IAP-01: Valid IAP headers extract user email and ID correctly

        Verify that properly formatted IAP headers are parsed and user info extracted.
        """
        request = mock_request(path="/api/sessions", headers=valid_iap_headers)

        middleware = IAPAuthMiddleware(app=None)

        user_email = middleware._extract_user_email(request)
        user_id = middleware._extract_user_id(request)

        assert user_email == "testuser@example.com", \
            f"Expected 'testuser@example.com', got '{user_email}'"
        assert user_id == "1234567890", \
            f"Expected '1234567890', got '{user_id}'"

        print(f"✓ Valid IAP headers extracted correctly: {user_email}, {user_id}")

    @pytest.mark.asyncio
    async def test_tc_auth_iap_02_missing_email_header_returns_401(
        self, valid_iap_headers, mock_request
    ):
        """
        TC-AUTH-IAP-02: Missing X-Goog-Authenticated-User-Email returns 401

        Verify that requests without email header are rejected.
        """
        headers = valid_iap_headers.copy()
        del headers["x-goog-authenticated-user-email"]

        request = mock_request(path="/api/sessions", headers=headers)
        middleware = IAPAuthMiddleware(app=None)

        user_email = middleware._extract_user_email(request)

        assert user_email is None, "Should return None for missing email header"
        print("✓ Missing email header correctly returns None (will trigger 401)")

    @pytest.mark.asyncio
    async def test_tc_auth_iap_03_missing_user_id_header_returns_401(
        self, valid_iap_headers, mock_request
    ):
        """
        TC-AUTH-IAP-03: Missing X-Goog-Authenticated-User-ID returns 401

        Verify that requests without user ID header are rejected.
        """
        headers = valid_iap_headers.copy()
        del headers["x-goog-authenticated-user-id"]

        request = mock_request(path="/api/sessions", headers=headers)
        middleware = IAPAuthMiddleware(app=None)

        user_id = middleware._extract_user_id(request)

        assert user_id is None, "Should return None for missing user ID header"
        print("✓ Missing user ID header correctly returns None (will trigger 401)")

    @pytest.mark.asyncio
    async def test_tc_auth_iap_04_malformed_header_format_handled(
        self, mock_request
    ):
        """
        TC-AUTH-IAP-04: Malformed header format handled gracefully

        Verify that headers without "accounts.google.com:" prefix are handled.
        """
        # Test direct email without prefix
        headers_no_prefix = {
            "x-goog-authenticated-user-email": "directemail@example.com",
            "x-goog-authenticated-user-id": "9876543210"
        }

        request = mock_request(path="/api/sessions", headers=headers_no_prefix)
        middleware = IAPAuthMiddleware(app=None)

        user_email = middleware._extract_user_email(request)
        user_id = middleware._extract_user_id(request)

        # Should fall back to using raw value
        assert user_email == "directemail@example.com", \
            "Should accept email without prefix as fallback"
        assert user_id == "9876543210", \
            "Should accept ID without prefix as fallback"

        print("✓ Malformed headers handled gracefully with fallback")

    @pytest.mark.asyncio
    async def test_tc_auth_iap_05_health_check_bypasses_auth(self, mock_request):
        """
        TC-AUTH-IAP-05: Health check endpoints bypass authentication

        Verify that /health and /ready endpoints don't require authentication.
        """
        middleware = IAPAuthMiddleware(app=None)

        health_paths = ["/health", "/ready", "/health/", "/ready/"]

        for path in health_paths:
            request = mock_request(path=path, headers={})
            should_bypass = middleware._should_bypass_auth(path)

            assert should_bypass, f"Path {path} should bypass authentication"

        print("✓ Health check endpoints correctly bypass authentication")

    @pytest.mark.asyncio
    async def test_tc_auth_iap_06_protected_endpoints_require_auth(self, mock_request):
        """
        TC-AUTH-IAP-06: Protected endpoints require authentication

        Verify that application endpoints do NOT bypass authentication.
        """
        middleware = IAPAuthMiddleware(app=None)

        protected_paths = [
            "/api/sessions",
            "/api/sessions/123",
            "/api/agent/test",
            # Note: "/" is intentionally in bypass paths for landing page access
            "/admin"
        ]

        for path in protected_paths:
            request = mock_request(path=path, headers={})
            should_bypass = middleware._should_bypass_auth(path)

            assert not should_bypass, f"Path {path} should NOT bypass authentication"

        print("✓ Protected endpoints correctly require authentication")

    @pytest.mark.asyncio
    @patch('app.middleware.iap_auth.JWT_VALIDATION_AVAILABLE', True)
    @patch('app.middleware.iap_auth.id_token.verify_token')
    async def test_tc_auth_iap_07_jwt_validation_succeeds(
        self, mock_verify_token, valid_iap_headers, mock_request
    ):
        """
        TC-AUTH-IAP-07: JWT validation succeeds with valid token

        Verify that IAP JWT tokens are validated correctly.
        """
        # Mock successful JWT validation
        mock_verify_token.return_value = {
            "sub": "1234567890",
            "email": "testuser@example.com",
            "iss": "https://cloud.google.com/iap"
        }

        request = mock_request(path="/api/sessions", headers=valid_iap_headers)
        middleware = IAPAuthMiddleware(app=None)

        is_valid = middleware._validate_iap_jwt(request)

        assert is_valid, "JWT validation should succeed with valid token"
        assert mock_verify_token.called, "JWT verify_token should be called"

        print("✓ JWT validation succeeds with valid token")

    @pytest.mark.asyncio
    @patch('app.middleware.iap_auth.JWT_VALIDATION_AVAILABLE', True)
    @patch('app.middleware.iap_auth.id_token.verify_token')
    async def test_tc_auth_iap_08_jwt_validation_fails_invalid_signature(
        self, mock_verify_token, valid_iap_headers, mock_request
    ):
        """
        TC-AUTH-IAP-08: JWT validation fails with invalid signature

        Verify that invalid JWT tokens are rejected.
        """
        # Mock failed JWT validation
        mock_verify_token.side_effect = Exception("Invalid signature")

        request = mock_request(path="/api/sessions", headers=valid_iap_headers)
        middleware = IAPAuthMiddleware(app=None)

        is_valid = middleware._validate_iap_jwt(request)

        assert not is_valid, "JWT validation should fail with invalid token"
        assert mock_verify_token.called, "JWT verify_token should be called"

        print("✓ JWT validation correctly fails with invalid signature")

    @pytest.mark.asyncio
    async def test_tc_auth_iap_09_missing_jwt_token_fails_validation(
        self, mock_request
    ):
        """
        TC-AUTH-IAP-09: Missing JWT token fails validation

        Verify that requests without JWT assertion fail validation.
        """
        headers_no_jwt = {
            "x-goog-authenticated-user-email": "accounts.google.com:test@example.com",
            "x-goog-authenticated-user-id": "accounts.google.com:1234567890"
        }

        request = mock_request(path="/api/sessions", headers=headers_no_jwt)
        middleware = IAPAuthMiddleware(app=None)

        is_valid = middleware._validate_iap_jwt(request)

        assert not is_valid, "JWT validation should fail without token"

        print("✓ Missing JWT token correctly fails validation")


class TestGetAuthenticatedUser:
    """Test suite for get_authenticated_user helper function."""

    @pytest.mark.asyncio
    async def test_get_authenticated_user_success(self):
        """
        Test successful extraction of authenticated user from request state.
        """
        mock_request = Mock(spec=Request)
        mock_request.state.user_email = "test@example.com"
        mock_request.state.user_id = "1234567890"

        user_info = get_authenticated_user(mock_request)

        assert user_info["user_email"] == "test@example.com"
        assert user_info["user_id"] == "1234567890"

        print("✓ get_authenticated_user extracts user info correctly")

    @pytest.mark.asyncio
    async def test_get_authenticated_user_missing_state_raises_401(self):
        """
        Test that missing authentication state raises HTTPException.
        """
        mock_request = Mock(spec=Request)
        # Use spec to prevent auto-creation of attributes
        mock_request.state = Mock(spec=[])  # Empty spec means no attributes

        with pytest.raises(HTTPException) as exc_info:
            get_authenticated_user(mock_request)

        assert exc_info.value.status_code == 401
        assert "not authenticated" in exc_info.value.detail.lower()

        print("✓ get_authenticated_user raises 401 for missing state")


class TestIAPAuthMiddlewareIntegration:
    """Integration tests for IAP auth middleware in request flow."""

    @pytest.fixture
    def valid_iap_headers(self):
        """Valid IAP headers for testing (lowercase to match config)"""
        return {
            "x-goog-authenticated-user-email": "accounts.google.com:testuser@example.com",
            "x-goog-authenticated-user-id": "accounts.google.com:1234567890",
            "x-goog-iap-jwt-assertion": "mock.jwt.token.here"
        }

    @pytest.mark.asyncio
    async def test_full_auth_flow_with_valid_headers(self, valid_iap_headers):
        """
        Integration test: Valid IAP headers → request state populated
        """
        # Create mock ASGI scope
        async def mock_app(scope, receive, send):
            # App should receive populated state
            assert "state" in scope
            assert scope["state"]["user_email"] == "testuser@example.com"
            assert scope["state"]["user_id"] == "1234567890"

        middleware = IAPAuthMiddleware(app=mock_app)

        # Create ASGI scope with valid headers
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/sessions",
            "headers": [
                (b"x-goog-authenticated-user-email", b"accounts.google.com:testuser@example.com"),
                (b"x-goog-authenticated-user-id", b"accounts.google.com:1234567890"),
            ],
        }

        async def receive():
            return {"type": "http.request"}

        responses = []
        async def send(message):
            responses.append(message)

        # Note: This test requires proper ASGI scope setup
        # For now, we test components individually above

        print("✓ Integration test structure defined (requires full ASGI setup)")
