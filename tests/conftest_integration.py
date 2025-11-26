"""
Integration Test Fixtures - Week 8 Production Readiness

Shared fixtures for integration tests that require real infrastructure.

Usage:
    pytest -m integration --run-integration

Configuration:
    Set environment variables for real infrastructure:
    - GCP_PROJECT_ID
    - FIRESTORE_DATABASE
    - GOOGLE_APPLICATION_CREDENTIALS
"""

import pytest
import asyncio
import os
from typing import List, AsyncGenerator
from datetime import datetime, timezone

from app.services.session_manager import SessionManager
from app.models.session import SessionCreate


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring real infrastructure"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take significant time to execute"
    )


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires real infrastructure)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is specified"""
    if config.getoption("--run-integration"):
        return

    skip_integration = pytest.mark.skip(
        reason="Integration tests skipped (use --run-integration to run)"
    )

    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def integration_session_manager():
    """Real session manager for integration tests"""
    return SessionManager()


@pytest.fixture
async def integration_test_session(integration_session_manager) -> AsyncGenerator:
    """
    Create test session and cleanup after test.

    Usage:
        async def test_something(integration_test_session):
            session = integration_test_session
            # Use session for testing
    """
    session_data = SessionCreate(
        location="Integration Test Location", user_name="Integration Test User"
    )

    session = await integration_session_manager.create_session(
        user_id=f"integration_test_{datetime.now(timezone.utc).timestamp()}",
        user_email="integration-test@example.com",
        session_data=session_data,
    )

    yield session

    try:
        await integration_session_manager.close_session(session.session_id)
    except Exception:
        pass


@pytest.fixture
async def integration_session_cleanup():
    """
    Cleanup fixture for tracking multiple sessions.

    Usage:
        async def test_multiple_sessions(integration_session_cleanup):
            session_ids = integration_session_cleanup
            # Create sessions and append IDs
            session_ids.append(session1.session_id)
            session_ids.append(session2.session_id)
            # Cleanup happens automatically
    """
    session_ids: List[str] = []

    yield session_ids

    manager = SessionManager()
    for session_id in session_ids:
        try:
            await manager.close_session(session_id)
        except Exception:
            pass


@pytest.fixture
def integration_auth_headers():
    """
    Mock IAP authentication headers for integration tests.

    Returns headers dict suitable for HTTP requests.
    """
    return {
        "X-Goog-Authenticated-User-Id": "integration-test-user",
        "X-Goog-Authenticated-User-Email": "integration-test@example.com",
    }


@pytest.fixture
def integration_test_inputs():
    """Standard test user inputs for integration tests"""
    return [
        "Welcome to the scene! I'm excited to start.",
        "Let me show you around this location.",
        "Have you noticed anything unusual?",
        "I think we should investigate further.",
        "There's something strange happening here.",
        "We need to work together on this.",
        "Let me try a different approach.",
        "I'm not sure this is working.",
        "Maybe we should reconsider our strategy.",
        "I'm starting to see a pattern.",
        "This is more complex than I thought.",
        "We're making progress though.",
        "Let's keep pushing forward.",
        "I think we're almost there.",
        "This is it, the final moment!",
    ]


@pytest.fixture(scope="session")
def check_integration_requirements():
    """
    Verify integration test requirements are met.

    Checks for:
    - GCP credentials
    - Project ID
    - Firestore access
    """
    required_env_vars = ["GCP_PROJECT_ID", "GOOGLE_APPLICATION_CREDENTIALS"]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        pytest.skip(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path and not os.path.exists(credentials_path):
        pytest.skip(f"Credentials file not found: {credentials_path}")


@pytest.fixture
def integration_timeout():
    """Default timeout for integration tests (seconds)"""
    return 30.0


@pytest.fixture
def integration_test_config():
    """Configuration for integration tests"""
    return {
        "max_turns": 15,
        "phase_1_turns": 4,
        "phase_2_start": 5,
        "coach_start_turn": 15,
        "session_timeout_minutes": 60,
        "turn_timeout_seconds": 30,
    }


class IntegrationTestSession:
    """Helper class for managing integration test sessions"""

    def __init__(self):
        self.manager = SessionManager()
        self.session_ids: List[str] = []

    async def create_session(
        self, location: str = "Test Location", user_id: str = "integration_test_user"
    ):
        """Create test session and track for cleanup"""
        session_data = SessionCreate(location=location)

        session = await self.manager.create_session(
            user_id=user_id,
            user_email=f"{user_id}@example.com",
            session_data=session_data,
        )

        self.session_ids.append(session.session_id)
        return session

    async def cleanup(self):
        """Cleanup all tracked sessions"""
        for session_id in self.session_ids:
            try:
                await self.manager.close_session(session_id)
            except Exception:
                pass

        self.session_ids.clear()


@pytest.fixture
async def integration_test_helper():
    """Helper for managing multiple test sessions"""
    helper = IntegrationTestSession()

    yield helper

    await helper.cleanup()


@pytest.fixture
def skip_if_no_credentials():
    """Skip test if GCP credentials not available"""
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        pytest.skip("GCP credentials not configured")


@pytest.fixture
def skip_if_no_adk():
    """Skip test if ADK not available"""
    try:
        from google.adk.runners import Runner  # noqa: F401
    except ImportError:
        pytest.skip("ADK not installed")


@pytest.fixture(autouse=True)
def integration_test_logging(caplog):
    """Enable detailed logging for integration tests"""
    import logging

    caplog.set_level(logging.DEBUG)


@pytest.fixture
def assert_turn_response_valid():
    """Helper to validate turn response structure"""

    def validate(response: dict, turn_number: int):
        """Validate turn response has required fields"""
        assert "partner_response" in response
        assert response["partner_response"], "Partner response should not be empty"

        assert "room_vibe" in response
        assert "analysis" in response["room_vibe"]
        assert "energy" in response["room_vibe"]

        assert "current_phase" in response
        assert response["current_phase"] in [1, 2]

        assert "turn_number" in response
        assert response["turn_number"] == turn_number

        assert "timestamp" in response

        if turn_number >= 15:
            assert response.get("coach_feedback") is not None, (
                f"Coach feedback missing at turn {turn_number}"
            )
        else:
            assert response.get("coach_feedback") is None, (
                f"Coach feedback should not appear before turn 15 (turn {turn_number})"
            )

    return validate
