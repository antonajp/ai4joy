"""Integration tests for ADK session persistence

These tests use a real SQLite database to verify that sessions actually
persist across simulated Cloud Run instance restarts.
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone

from app.models.session import Session, SessionStatus


@pytest.fixture
def temp_db_path():
    """Create temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield f"sqlite+aiosqlite:///{db_path}"

    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_session():
    """Sample session for testing."""
    return Session(
        session_id="sess_integration_test",
        user_id="user_integration_123",
        user_email="integration@example.com",
        user_name="Integration Test User",
        location="Integration Test Location",
        status=SessionStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
        conversation_history=[
            {
                "turn_number": 1,
                "user_input": "Test input",
                "partner_response": "Test response",
            }
        ],
        metadata={"test_key": "test_value"},
        current_phase="PHASE_1",
        turn_count=1,
    )


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before and after each test for isolation."""
    from app.services import adk_session_service

    adk_session_service._session_service = None
    yield
    adk_session_service._session_service = None


class TestSessionPersistence:
    """Test session persistence across simulated restarts"""

    @pytest.mark.asyncio
    async def test_session_survives_service_restart(self, temp_db_path, sample_session):
        """
        Simulate Cloud Run instance restart:
        1. Create session with state
        2. Close session service (simulating restart)
        3. Get new session service instance
        4. Verify session state is preserved
        """
        from unittest.mock import patch

        with patch("app.services.adk_session_service.settings") as mock_settings:
            mock_settings.adk_database_url = temp_db_path
            mock_settings.app_name = "Improv Olympics"

            from app.services.adk_session_service import (
                create_adk_session,
                get_adk_session,
                close_adk_session_service,
                reset_adk_session_service,
            )

            created_session = await create_adk_session(sample_session)

            assert created_session is not None
            assert created_session.id == "sess_integration_test"

            await close_adk_session_service()
            reset_adk_session_service()

            retrieved_session = await get_adk_session(
                session_id="sess_integration_test", user_id="user_integration_123"
            )

            assert retrieved_session is not None
            assert retrieved_session.id == "sess_integration_test"
            assert retrieved_session.user_id == "user_integration_123"
            assert retrieved_session.state["location"] == "Integration Test Location"
            assert retrieved_session.state["current_phase"] == "PHASE_1"

            await close_adk_session_service()

    @pytest.mark.asyncio
    async def test_session_not_found_returns_none(self, temp_db_path):
        """Test that retrieving non-existent session returns None."""
        from unittest.mock import patch

        with patch("app.services.adk_session_service.settings") as mock_settings:
            mock_settings.adk_database_url = temp_db_path
            mock_settings.app_name = "Improv Olympics"

            from app.services.adk_session_service import (
                get_adk_session,
                close_adk_session_service,
            )

            retrieved_session = await get_adk_session(
                session_id="nonexistent_session", user_id="nonexistent_user"
            )

            assert retrieved_session is None

            await close_adk_session_service()

    @pytest.mark.asyncio
    async def test_multiple_sessions_for_same_user(self, temp_db_path):
        """Test multiple concurrent sessions for the same user."""
        from unittest.mock import patch

        with patch("app.services.adk_session_service.settings") as mock_settings:
            mock_settings.adk_database_url = temp_db_path
            mock_settings.app_name = "Improv Olympics"

            from app.services.adk_session_service import (
                create_adk_session,
                get_adk_session,
                close_adk_session_service,
            )

            session1 = Session(
                session_id="sess_multi_1",
                user_id="user_multi_test",
                user_email="multi@example.com",
                user_name="Multi Test",
                location="Location 1",
                status=SessionStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc),
                conversation_history=[],
                metadata={},
                current_phase="PHASE_1",
                turn_count=2,
            )

            session2 = Session(
                session_id="sess_multi_2",
                user_id="user_multi_test",
                user_email="multi@example.com",
                user_name="Multi Test",
                location="Location 2",
                status=SessionStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc),
                conversation_history=[],
                metadata={},
                current_phase="PHASE_2",
                turn_count=7,
            )

            await create_adk_session(session1)
            await create_adk_session(session2)

            retrieved1 = await get_adk_session(
                session_id="sess_multi_1", user_id="user_multi_test"
            )
            retrieved2 = await get_adk_session(
                session_id="sess_multi_2", user_id="user_multi_test"
            )

            assert retrieved1.state["location"] == "Location 1"
            assert retrieved1.state["turn_count"] == 2
            assert retrieved1.state["current_phase"] == "PHASE_1"

            assert retrieved2.state["location"] == "Location 2"
            assert retrieved2.state["turn_count"] == 7
            assert retrieved2.state["current_phase"] == "PHASE_2"

            await close_adk_session_service()
