"""Tests for ADK Session Service - DatabaseSessionService Singleton

This module tests the new adk_session_service module that replaces the
deprecated adk_session_bridge with ADK's native DatabaseSessionService.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.models.session import Session, SessionStatus


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before and after each test for isolation."""
    from app.services import adk_session_service
    adk_session_service._session_service = None
    yield
    adk_session_service._session_service = None


class TestADKSessionServiceSingleton:
    """Test singleton pattern for ADK session service"""

    def test_get_adk_session_service_returns_same_instance(self):
        """Verify singleton returns same instance on multiple calls."""
        with patch('app.services.adk_session_service.DatabaseSessionService') as mock_db_service:
            mock_db_service.return_value = MagicMock()

            from app.services.adk_session_service import get_adk_session_service

            service1 = get_adk_session_service()
            service2 = get_adk_session_service()

            assert service1 is service2
            assert mock_db_service.call_count == 1

    def test_get_adk_session_service_initializes_with_config(self):
        """Verify service uses db_url from settings."""
        with patch('app.services.adk_session_service.DatabaseSessionService') as mock_db_service:
            with patch('app.services.adk_session_service.settings') as mock_settings:
                mock_settings.adk_database_url = "postgresql://user:pass@localhost/testdb"
                mock_instance = MagicMock()
                mock_db_service.return_value = mock_instance

                from app.services.adk_session_service import get_adk_session_service

                service = get_adk_session_service()

                mock_db_service.assert_called_once_with(
                    db_url="postgresql://user:pass@localhost/testdb"
                )
                assert service is mock_instance

    def test_singleton_reset_for_testing(self):
        """Verify singleton can be reset for testing purposes."""
        with patch('app.services.adk_session_service.DatabaseSessionService') as mock_db_service:
            mock_instance1 = MagicMock(name="instance1")
            mock_instance2 = MagicMock(name="instance2")
            mock_db_service.side_effect = [mock_instance1, mock_instance2]

            from app.services.adk_session_service import (
                get_adk_session_service,
                reset_adk_session_service
            )

            service1 = get_adk_session_service()
            reset_adk_session_service()
            service2 = get_adk_session_service()

            assert service1 is mock_instance1
            assert service2 is mock_instance2
            assert service1 is not service2
            assert mock_db_service.call_count == 2


class TestADKSessionServiceOperations:
    """Test session CRUD operations"""

    @pytest.fixture
    def sample_session(self):
        """Sample Session model for testing"""
        return Session(
            session_id="sess_test123",
            user_id="user_456",
            user_email="test@example.com",
            user_name="Test User",
            location="Mars Colony",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            metadata={},
            current_phase="PHASE_1",
            turn_count=0
        )

    @pytest.mark.asyncio
    async def test_create_session_stores_state(self, sample_session):
        """Test creating session stores state data."""
        with patch('app.services.adk_session_service.DatabaseSessionService') as mock_db_service:
            with patch('app.services.adk_session_service.settings') as mock_settings:
                mock_settings.app_name = "Improv Olympics"
                mock_settings.adk_database_url = "sqlite:///test.db"

                mock_instance = MagicMock()
                mock_adk_session = MagicMock()
                mock_adk_session.id = sample_session.session_id
                mock_adk_session.user_id = sample_session.user_id
                mock_instance.create_session = AsyncMock(return_value=mock_adk_session)
                mock_db_service.return_value = mock_instance

                from app.services.adk_session_service import create_adk_session

                adk_session = await create_adk_session(sample_session)

                mock_instance.create_session.assert_called_once()
                call_kwargs = mock_instance.create_session.call_args[1]

                assert call_kwargs["app_name"] == "Improv Olympics"
                assert call_kwargs["user_id"] == "user_456"
                assert call_kwargs["session_id"] == "sess_test123"
                assert call_kwargs["state"]["location"] == "Mars Colony"
                assert call_kwargs["state"]["status"] == "active"
                assert adk_session.id == "sess_test123"

    @pytest.mark.asyncio
    async def test_get_session_retrieves_state(self):
        """Test retrieving session returns stored state."""
        with patch('app.services.adk_session_service.DatabaseSessionService') as mock_db_service:
            with patch('app.services.adk_session_service.settings') as mock_settings:
                mock_settings.app_name = "Improv Olympics"
                mock_settings.adk_database_url = "sqlite:///test.db"

                mock_instance = MagicMock()
                mock_adk_session = MagicMock()
                mock_adk_session.id = "sess_test123"
                mock_adk_session.state = {
                    "location": "Mars Colony",
                    "turn_count": 3
                }
                mock_adk_session.events = []
                mock_instance.get_session = AsyncMock(return_value=mock_adk_session)
                mock_db_service.return_value = mock_instance

                from app.services.adk_session_service import get_adk_session

                adk_session = await get_adk_session(
                    session_id="sess_test123",
                    user_id="user_456"
                )

                mock_instance.get_session.assert_called_once_with(
                    app_name="Improv Olympics",
                    user_id="user_456",
                    session_id="sess_test123"
                )
                assert adk_session.id == "sess_test123"
                assert adk_session.state["location"] == "Mars Colony"

    @pytest.mark.asyncio
    async def test_get_session_returns_none_if_not_found(self):
        """Test get_session returns None for non-existent session."""
        with patch('app.services.adk_session_service.DatabaseSessionService') as mock_db_service:
            with patch('app.services.adk_session_service.settings') as mock_settings:
                mock_settings.app_name = "Improv Olympics"
                mock_settings.adk_database_url = "sqlite:///test.db"

                mock_instance = MagicMock()
                mock_instance.get_session = AsyncMock(return_value=None)
                mock_db_service.return_value = mock_instance

                from app.services.adk_session_service import get_adk_session

                adk_session = await get_adk_session(
                    session_id="nonexistent",
                    user_id="user_456"
                )

                assert adk_session is None

    @pytest.mark.asyncio
    async def test_update_session_state(self):
        """Test updating session state."""
        with patch('app.services.adk_session_service.DatabaseSessionService') as mock_db_service:
            with patch('app.services.adk_session_service.settings') as mock_settings:
                mock_settings.app_name = "Improv Olympics"
                mock_settings.adk_database_url = "sqlite:///test.db"

                mock_instance = MagicMock()
                mock_adk_session = MagicMock()
                mock_adk_session.state = {"location": "Mars Colony", "turn_count": 3}
                mock_instance.get_session = AsyncMock(return_value=mock_adk_session)
                mock_db_service.return_value = mock_instance

                from app.services.adk_session_service import update_adk_session_state

                await update_adk_session_state(
                    session_id="sess_test123",
                    user_id="user_456",
                    state_updates={"turn_count": 4, "current_phase": "PHASE_2"}
                )

                assert mock_adk_session.state["turn_count"] == 4
                assert mock_adk_session.state["current_phase"] == "PHASE_2"
                assert mock_adk_session.state["location"] == "Mars Colony"


class TestADKSessionServiceCleanup:
    """Test cleanup and disposal"""

    @pytest.mark.asyncio
    async def test_close_adk_session_service_disposes_engine(self):
        """Test cleanup properly disposes database engine."""
        with patch('app.services.adk_session_service.DatabaseSessionService') as mock_db_service:
            mock_instance = MagicMock()
            mock_engine = MagicMock()
            mock_engine.dispose = AsyncMock()
            mock_instance.db_engine = mock_engine
            mock_db_service.return_value = mock_instance

            from app.services.adk_session_service import (
                get_adk_session_service,
                close_adk_session_service
            )

            get_adk_session_service()
            await close_adk_session_service()

            mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_handles_no_service_gracefully(self):
        """Test close handles case where service was never initialized."""
        from app.services.adk_session_service import close_adk_session_service

        await close_adk_session_service()


class TestADKSessionServiceErrorHandling:
    """Test error handling in session operations"""

    @pytest.mark.asyncio
    async def test_create_session_propagates_db_errors(self):
        """Test that database errors are properly propagated."""
        with patch('app.services.adk_session_service.DatabaseSessionService') as mock_db_service:
            with patch('app.services.adk_session_service.settings') as mock_settings:
                mock_settings.app_name = "Improv Olympics"
                mock_settings.adk_database_url = "sqlite:///test.db"

                mock_instance = MagicMock()
                mock_instance.create_session = AsyncMock(
                    side_effect=Exception("Database connection failed")
                )
                mock_db_service.return_value = mock_instance

                from app.services.adk_session_service import create_adk_session

                sample_session = Session(
                    session_id="sess_error",
                    user_id="user_456",
                    user_email="test@example.com",
                    user_name="Test User",
                    location="Error Zone",
                    status=SessionStatus.ACTIVE,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc),
                    conversation_history=[],
                    metadata={},
                    current_phase="PHASE_1",
                    turn_count=0
                )

                with pytest.raises(Exception, match="Database connection failed"):
                    await create_adk_session(sample_session)
