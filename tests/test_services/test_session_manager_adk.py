"""Tests for SessionManager with ADK Integration

Note: This module tests SessionManager integration with ADK sessions.
The old adk_session_bridge has been replaced with adk_session_service
which uses DatabaseSessionService instead of InMemorySessionService.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.services.session_manager import SessionManager, get_session_manager
from app.models.session import SessionCreate, SessionStatus


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client"""
    with patch("app.services.session_manager.firestore.Client") as mock_client:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_client.return_value = mock_db
        yield mock_db


@pytest.fixture
def mock_adk_session_service():
    """Mock ADK session service (replacing adk_bridge)"""
    with patch("app.services.session_manager.get_adk_session_service") as mock_service_getter:
        mock_service = AsyncMock()
        mock_service.create_session = AsyncMock()
        mock_service.get_session = AsyncMock()
        mock_service.update_session = AsyncMock()
        mock_service_getter.return_value = mock_service
        yield mock_service


@pytest.fixture
def session_manager_with_adk(mock_firestore_client, mock_adk_session_service):
    """Session manager with ADK enabled"""
    return SessionManager(use_adk_sessions=True)


@pytest.fixture
def session_manager_no_adk(mock_firestore_client):
    """Session manager with ADK disabled"""
    with patch("app.services.session_manager.get_adk_session_service") as mock_service:
        mock_service.return_value = None
        return SessionManager(use_adk_sessions=False)


@pytest.mark.asyncio
async def test_create_session_with_adk(session_manager_with_adk, mock_firestore_client, mock_adk_session_service):
    """Test session creation with ADK integration"""
    session_data = SessionCreate(
        location="Mars Colony",
        user_name="Test User"
    )

    mock_doc_ref = MagicMock()
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_with_adk.create_session(
        user_id="user_123",
        user_email="test@example.com",
        session_data=session_data
    )

    assert session is not None
    assert session.location == "Mars Colony"
    assert session.user_name == "Test User"
    assert session.user_id == "user_123"

    mock_doc_ref.set.assert_called_once()

    # Verify DatabaseSessionService.create_session was called
    session_manager_with_adk.adk_session_service.create_session.assert_called_once()


@pytest.mark.asyncio
async def test_create_session_without_adk(session_manager_no_adk, mock_firestore_client):
    """Test session creation without ADK integration"""
    session_data = SessionCreate(
        location="Mars Colony",
        user_name="Test User"
    )

    mock_doc_ref = MagicMock()
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_no_adk.create_session(
        user_id="user_123",
        user_email="test@example.com",
        session_data=session_data
    )

    assert session is not None
    assert session_manager_no_adk.adk_session_service is None


@pytest.mark.asyncio
async def test_get_adk_session(session_manager_with_adk, mock_firestore_client, mock_adk_session_service):
    """Test getting ADK session"""
    session_id = "sess_test123"

    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {
        "session_id": session_id,
        "user_id": "user_123",
        "user_email": "test@example.com",
        "user_name": "Test User",
        "location": "Mars",
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "conversation_history": [],
        "metadata": {},
        "current_phase": "PHASE_1",
        "turn_count": 0
    }

    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_snapshot
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    from google.adk.sessions.session import Session as ADKSession
    mock_adk_session = ADKSession(
        id=session_id,
        app_name="test_app",
        user_id="user_123",
        state={},
        events=[],
        last_update_time=0.0
    )
    mock_adk_session_service.get_session.return_value = mock_adk_session

    adk_session = await session_manager_with_adk.get_adk_session(session_id)

    assert adk_session is not None
    assert adk_session.id == session_id
    # Verify DatabaseSessionService.get_session was called
    mock_adk_session_service.get_session.assert_called()


@pytest.mark.asyncio
async def test_get_adk_session_returns_none_when_disabled(session_manager_no_adk):
    """Test get_adk_session returns None when ADK disabled"""
    adk_session = await session_manager_no_adk.get_adk_session("sess_test")

    assert adk_session is None


@pytest.mark.asyncio
async def test_sync_adk_session_to_firestore(session_manager_with_adk, mock_firestore_client):
    """Test syncing ADK session to Firestore

    Note: With DatabaseSessionService, state updates are automatically persisted
    to the database. This test verifies that the SessionManager can still sync
    ADK state back to Firestore for any metadata that needs to be stored there.
    """
    from google.adk.sessions.session import Session as ADKSession

    adk_session = ADKSession(
        id="sess_test",
        app_name="test_app",
        user_id="user_123",
        state={"turn_count": 5, "current_phase": "PHASE_2"},
        events=[],
        last_update_time=0.0
    )

    mock_doc_ref = MagicMock()
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    await session_manager_with_adk.sync_adk_session_to_firestore(
        adk_session=adk_session,
        session_id="sess_test"
    )

    # Verify Firestore was updated with state from ADK session
    mock_doc_ref.update.assert_called_once()
    update_data = mock_doc_ref.update.call_args[0][0]
    assert update_data["turn_count"] == 5
    assert update_data["current_phase"] == "PHASE_2"


@pytest.mark.asyncio
async def test_sync_does_nothing_when_adk_disabled(session_manager_no_adk):
    """Test sync does nothing when ADK disabled"""
    from google.adk.sessions.session import Session as ADKSession

    adk_session = ADKSession(
        id="sess_test",
        app_name="test_app",
        user_id="user_123",
        state={},
        events=[],
        last_update_time=0.0
    )

    await session_manager_no_adk.sync_adk_session_to_firestore(
        adk_session=adk_session,
        session_id="sess_test"
    )


def test_session_manager_factory_with_adk():
    """Test factory function creates manager with ADK enabled"""
    with patch("app.services.session_manager.firestore.Client"):
        with patch("app.services.session_manager.get_adk_session_service"):
            manager = get_session_manager(use_adk_sessions=True)
            assert manager.use_adk_sessions is True


def test_session_manager_factory_without_adk():
    """Test factory function creates manager with ADK disabled"""
    with patch("app.services.session_manager.firestore.Client"):
        with patch("app.services.session_manager.get_adk_session_service") as mock_service:
            mock_service.return_value = None
            manager = get_session_manager(use_adk_sessions=False)
            assert manager.use_adk_sessions is False
