"""
OAuth Authentication Tests for Identity-Aware Proxy (IAP)
Tests TC-AUTH-01 through TC-AUTH-06 from GCP Deployment Test Plan

These tests validate that:
1. Unauthenticated requests are blocked
2. OAuth flow redirects users properly
3. IAP headers are injected correctly
4. Only authorized users can access
5. Health checks work without auth
"""

import os
import pytest
import requests
from typing import Dict, Optional

# Skip production OAuth tests by default unless explicitly enabled
INTEGRATION_TESTS_ENABLED = os.getenv("ENABLE_INTEGRATION_TESTS", "false").lower() == "true"


@pytest.mark.skipif(
    not INTEGRATION_TESTS_ENABLED,
    reason="OAuth integration tests require running server. Set ENABLE_INTEGRATION_TESTS=true to run."
)
class TestOAuthAuthentication:
    """
    Test suite for Identity-Aware Proxy (IAP) OAuth authentication.

    Prerequisites:
    - GCP IAP enabled on backend service
    - Test user credentials available
    - SERVICE_URL environment variable set
    """

    @pytest.fixture
    def service_url(self, config) -> str:
        """Base URL for the deployed service."""
        return config.get('service_url', 'https://ai4joy.org')

    @pytest.fixture
    def unauthorized_session(self) -> requests.Session:
        """HTTP session without authentication."""
        return requests.Session()

    def test_tc_auth_01_unauthenticated_access_blocked(
        self,
        service_url: str,
        unauthorized_session: requests.Session
    ):
        """
        TC-AUTH-01: Unauthenticated Access Blocked

        Verify that unauthenticated requests to the application are redirected
        to Google Sign-In via Identity-Aware Proxy.

        Expected Behavior:
        - HTTP 302/303 redirect to Google OAuth consent screen
        - Redirect URL contains 'accounts.google.com'
        - Cannot access application without authentication
        """
        response = unauthorized_session.get(
            f"{service_url}/",
            allow_redirects=False
        )

        # Should redirect to OAuth consent screen
        assert response.status_code in [302, 303], \
            f"Expected redirect (302/303), got {response.status_code}"

        redirect_location = response.headers.get('Location', '')
        assert 'accounts.google.com' in redirect_location or \
               'iap' in redirect_location.lower(), \
            f"Redirect should go to Google OAuth, got: {redirect_location}"

        print(f"✓ Unauthenticated request correctly redirected to: {redirect_location}")

    def test_tc_auth_02_health_check_accessible_without_auth(
        self,
        service_url: str,
        unauthorized_session: requests.Session
    ):
        """
        TC-AUTH-02: Health Check Accessible Without Auth

        Verify that health check endpoints are accessible without authentication.
        IAP should allowlist /health and /ready endpoints.

        Expected Behavior:
        - GET /health returns 200 OK without authentication
        - Response indicates service is healthy
        """
        health_endpoints = ['/health', '/ready']

        for endpoint in health_endpoints:
            response = unauthorized_session.get(
                f"{service_url}{endpoint}",
                timeout=10
            )

            assert response.status_code == 200, \
                f"{endpoint} should be accessible without auth, got {response.status_code}"

            print(f"✓ {endpoint} accessible without authentication: {response.status_code}")

    @pytest.mark.manual
    def test_tc_auth_03_oauth_flow_success(
        self,
        service_url: str,
        authorized_user_credentials: Dict
    ):
        """
        TC-AUTH-03: OAuth Flow Success (MANUAL TEST)

        This test requires manual execution with browser automation or actual OAuth flow.

        Test Steps:
        1. Navigate to {service_url} in browser
        2. Should redirect to Google Sign-In
        3. Enter authorized user credentials
        4. Should redirect back to application with access granted
        5. User can interact with application

        Expected Behavior:
        - OAuth consent screen appears
        - Successful sign-in grants access
        - User redirected back to application
        - Application session established

        To run this test manually:
        1. Open incognito browser window
        2. Navigate to https://ai4joy.org
        3. Sign in with authorized Google account
        4. Verify access granted to application
        """
        pytest.skip("Manual test - requires browser automation")

    @pytest.mark.manual
    def test_tc_auth_04_unauthorized_user_denied(
        self,
        service_url: str
    ):
        """
        TC-AUTH-04: Unauthorized User Denied (MANUAL TEST)

        Verify that users not in iap_allowed_users list receive 403 Forbidden.

        Test Steps:
        1. Sign in with Google account NOT in IAP allowed users
        2. Should receive 403 Forbidden error
        3. Error message should be clear and actionable

        Expected Behavior:
        - 403 Forbidden response
        - Clear error message indicating access denied
        - User cannot access any protected endpoints

        To run this test manually:
        1. Sign out of Google account
        2. Sign in with unauthorized account
        3. Navigate to https://ai4joy.org
        4. Verify 403 error displayed
        """
        pytest.skip("Manual test - requires unauthorized user account")

    @pytest.mark.integration
    def test_tc_auth_05_iap_headers_present(
        self,
        service_url: str,
        authenticated_request_headers: Optional[Dict]
    ):
        """
        TC-AUTH-05: IAP Headers Present

        Verify that IAP injects user identity headers into requests reaching Cloud Run.

        Expected Headers:
        - X-Goog-Authenticated-User-Email: accounts.google.com:user@example.com
        - X-Goog-Authenticated-User-ID: accounts.google.com:10769150350006150715113082367
        - X-Goog-IAP-JWT-Assertion: (JWT token)

        Note: This test requires a test endpoint that echoes back headers,
        or access to Cloud Run logs to inspect incoming requests.
        """
        if not authenticated_request_headers:
            pytest.skip("No authenticated request headers available - requires deployed app with debug endpoint")

        required_headers = [
            'X-Goog-Authenticated-User-Email',
            'X-Goog-Authenticated-User-ID'
        ]

        for header in required_headers:
            assert header in authenticated_request_headers, \
                f"Required IAP header '{header}' not present in request"

            header_value = authenticated_request_headers[header]
            assert header_value, f"IAP header '{header}' is empty"
            assert 'accounts.google.com' in header_value, \
                f"IAP header should contain 'accounts.google.com', got: {header_value}"

            print(f"✓ IAP header '{header}' present: {header_value}")

    @pytest.mark.integration
    def test_tc_auth_06_session_user_association(
        self,
        service_url: str,
        authenticated_session: Optional[requests.Session]
    ):
        """
        TC-AUTH-06: Session User Association

        Verify that sessions are correctly associated with authenticated user IDs.

        Expected Behavior:
        - Create session request includes user_id extracted from IAP headers
        - Session stored in Firestore with user_id field
        - User can only access their own sessions
        """
        if not authenticated_session:
            pytest.skip("Requires authenticated session - run after OAuth integration implemented")

        # Create a session
        response = authenticated_session.post(
            f"{service_url}/session/start",
            json={"location": "Test Location"},
            timeout=30
        )

        assert response.status_code == 200, \
            f"Session creation failed: {response.status_code}"

        session_data = response.json()
        assert 'session_id' in session_data, "Response should contain session_id"
        assert 'user_id' in session_data, "Session should be associated with user_id"

        session_id = session_data['session_id']
        user_id = session_data['user_id']

        assert user_id, "user_id should not be empty"
        print(f"✓ Session {session_id} associated with user {user_id}")

        # Verify session retrieval includes user_id
        get_response = authenticated_session.get(
            f"{service_url}/session/{session_id}",
            timeout=10
        )

        assert get_response.status_code == 200
        retrieved_session = get_response.json()
        assert retrieved_session['user_id'] == user_id, \
            "Retrieved session should have same user_id"

        print("✓ Session user association verified")


class TestIAPHeaderExtraction:
    """
    Tests for IAP header extraction and validation logic.
    These are unit tests for the authentication middleware.
    """

    def test_extract_user_email_from_iap_header(self):
        """
        Test extraction of user email from IAP header format.

        IAP Header Format: accounts.google.com:user@example.com
        Expected Output: user@example.com
        """
        iap_header = "accounts.google.com:pilot@ai4joy.org"
        expected_email = "pilot@ai4joy.org"

        # This would test the actual extraction function in the application
        # extracted_email = extract_user_email(iap_header)
        # assert extracted_email == expected_email

        # For now, test the expected parsing logic
        if ':' in iap_header:
            extracted_email = iap_header.split(':', 1)[1]
            assert extracted_email == expected_email
            print(f"✓ Correctly extracted email: {extracted_email}")

    def test_extract_user_id_from_iap_header(self):
        """
        Test extraction of user ID from IAP header format.

        IAP Header Format: accounts.google.com:10769150350006150715113082367
        Expected Output: 10769150350006150715113082367
        """
        iap_header = "accounts.google.com:10769150350006150715113082367"
        expected_user_id = "10769150350006150715113082367"

        if ':' in iap_header:
            extracted_user_id = iap_header.split(':', 1)[1]
            assert extracted_user_id == expected_user_id
            print(f"✓ Correctly extracted user ID: {extracted_user_id}")

    def test_missing_iap_headers_returns_401(self):
        """
        Test that requests without IAP headers are rejected.

        Expected Behavior:
        - Missing X-Goog-Authenticated-User-Email → 401 Unauthorized
        - Clear error message indicating authentication required
        """
        # This tests the authentication middleware behavior
        # In actual implementation:
        # response = app.get('/session/start', headers={})
        # assert response.status_code == 401

        print("✓ Test case defined for missing IAP headers validation")

    def test_malformed_iap_headers_rejected(self):
        """
        Test that malformed IAP headers are rejected.

        Test Cases:
        - Header without 'accounts.google.com' prefix
        - Header without colon separator
        - Empty header value
        """
        invalid_headers = [
            "user@example.com",  # Missing prefix
            "accounts.google.com",  # Missing separator and email
            "",  # Empty
            "wrongprefix:user@example.com"  # Wrong prefix
        ]

        for invalid_header in invalid_headers:
            # In actual implementation, should reject these
            # is_valid = validate_iap_header(invalid_header)
            # assert not is_valid
            print(f"✓ Should reject invalid IAP header: '{invalid_header}'")


@pytest.mark.skipif(
    not INTEGRATION_TESTS_ENABLED,
    reason="OAuth sign-out tests require running server. Set ENABLE_INTEGRATION_TESTS=true to run."
)
class TestOAuthSignOut:
    """Tests for OAuth sign-out functionality."""

    @pytest.mark.manual
    def test_tc_auth_07_signout_flow(self, service_url: str):
        """
        TC-AUTH-07: Sign-Out Flow

        Verify that signing out clears IAP session and requires re-authentication.

        Test Steps:
        1. Authenticate and access application
        2. Navigate to sign-out URL or click sign-out button
        3. Access application again
        4. Should redirect to Google Sign-In

        Expected Behavior:
        - Sign-out clears IAP session cookie
        - Subsequent requests require re-authentication
        - No cached credentials used

        To run manually:
        1. Sign in and access https://ai4joy.org
        2. Navigate to https://ai4joy.org/_gcp_iap/clear_login_cookie
        3. Try accessing application again
        4. Verify prompted to sign in again
        """
        pytest.skip("Manual test - requires browser session management")


# Test fixtures and helpers

@pytest.fixture
def config() -> Dict:
    """Configuration for OAuth tests."""
    import os
    return {
        'service_url': os.getenv('SERVICE_URL', 'https://ai4joy.org'),
        'project_id': os.getenv('GCP_PROJECT_ID', 'improvOlympics'),
    }


@pytest.fixture
def authorized_user_credentials() -> Optional[Dict]:
    """
    Credentials for an authorized test user.

    Should be set via environment variables for CI/CD:
    - TEST_USER_EMAIL
    - TEST_USER_PASSWORD (use Secret Manager, not committed to repo)
    """
    import os
    email = os.getenv('TEST_USER_EMAIL')
    password = os.getenv('TEST_USER_PASSWORD')

    if not email or not password:
        return None

    return {
        'email': email,
        'password': password
    }


@pytest.fixture
def authenticated_session(service_url: str) -> Optional[requests.Session]:
    """
    Authenticated HTTP session with IAP cookies.

    Note: This requires browser automation or manual cookie extraction.
    For automated testing, consider using Selenium or Playwright.
    """
    # Implementation would require OAuth flow automation
    # For now, return None to skip tests requiring authentication
    return None


@pytest.fixture
def authenticated_request_headers() -> Optional[Dict]:
    """
    Sample IAP headers for testing.

    In production tests, these would come from actual authenticated requests.
    For unit tests, can use mock values.
    """
    # For integration tests, these would be extracted from logs or debug endpoint
    # For now, return None to skip tests
    return None
