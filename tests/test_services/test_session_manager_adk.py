"""Tests for SessionManager with ADK Integration - IQS-75

Note: This module tests SessionManager integration with ADK sessions.
The old adk_session_bridge has been replaced with adk_session_service
which uses DatabaseSessionService instead of InMemorySessionService.

IQS-75 Test Coverage:
- TC-MGR-01: Session creation stores interaction_mode in Firestore
- TC-MGR-02: Session retrieval returns correct interaction_mode
- TC-MGR-03: Default mode is TEXT when not specified
- TC-MGR-04: AUDIO mode is correctly stored and retrieved
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.session_manager import SessionManager, get_session_manager
from app.models.session import SessionCreate, InteractionMode


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
    with patch(
        "app.services.session_manager.get_adk_session_service"
    ) as mock_service_getter:
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
async def test_create_session_with_adk(
    session_manager_with_adk, mock_firestore_client, mock_adk_session_service
):
    """Test session creation with ADK integration"""
    session_data = SessionCreate(location="Mars Colony", user_name="Test User")

    mock_doc_ref = MagicMock()
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_with_adk.create_session(
        user_id="user_123", user_email="test@example.com", session_data=session_data
    )

    assert session is not None
    assert session.location == "Mars Colony"
    assert session.user_name == "Test User"
    assert session.user_id == "user_123"

    mock_doc_ref.set.assert_called_once()

    # Verify DatabaseSessionService.create_session was called
    session_manager_with_adk.adk_session_service.create_session.assert_called_once()


@pytest.mark.asyncio
async def test_create_session_without_adk(
    session_manager_no_adk, mock_firestore_client
):
    """Test session creation without ADK integration"""
    session_data = SessionCreate(location="Mars Colony", user_name="Test User")

    mock_doc_ref = MagicMock()
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_no_adk.create_session(
        user_id="user_123", user_email="test@example.com", session_data=session_data
    )

    assert session is not None
    assert session_manager_no_adk.adk_session_service is None


@pytest.mark.asyncio
async def test_get_adk_session(
    session_manager_with_adk, mock_firestore_client, mock_adk_session_service
):
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
        "turn_count": 0,
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
        last_update_time=0.0,
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
async def test_sync_adk_session_to_firestore(
    session_manager_with_adk, mock_firestore_client
):
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
        last_update_time=0.0,
    )

    mock_doc_ref = MagicMock()
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    await session_manager_with_adk.sync_adk_session_to_firestore(
        adk_session=adk_session, session_id="sess_test"
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
        last_update_time=0.0,
    )

    await session_manager_no_adk.sync_adk_session_to_firestore(
        adk_session=adk_session, session_id="sess_test"
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
        with patch(
            "app.services.session_manager.get_adk_session_service"
        ) as mock_service:
            mock_service.return_value = None
            manager = get_session_manager(use_adk_sessions=False)
            assert manager.use_adk_sessions is False


# ============================================================================
# IQS-75: InteractionMode Tests
# ============================================================================


@pytest.mark.asyncio
async def test_tc_mgr_01_create_session_stores_text_mode(
    session_manager_with_adk, mock_firestore_client, mock_adk_session_service
):
    """TC-MGR-01: Session creation stores interaction_mode in Firestore (TEXT mode)"""
    session_data = SessionCreate(
        user_name="Test User",
        interaction_mode=InteractionMode.TEXT
    )

    mock_doc_ref = MagicMock()
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_with_adk.create_session(
        user_id="user_123",
        user_email="test@example.com",
        session_data=session_data
    )

    # Verify session has TEXT mode
    assert session.interaction_mode == InteractionMode.TEXT

    # Verify Firestore document was created with interaction_mode
    mock_doc_ref.set.assert_called_once()
    firestore_data = mock_doc_ref.set.call_args[0][0]
    assert "interaction_mode" in firestore_data
    assert firestore_data["interaction_mode"] == "text"


@pytest.mark.asyncio
async def test_tc_mgr_01_create_session_stores_audio_mode(
    session_manager_with_adk, mock_firestore_client, mock_adk_session_service
):
    """TC-MGR-01: Session creation stores interaction_mode in Firestore (AUDIO mode)"""
    session_data = SessionCreate(
        user_name="Premium User",
        interaction_mode=InteractionMode.AUDIO
    )

    mock_doc_ref = MagicMock()
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_with_adk.create_session(
        user_id="user_456",
        user_email="premium@example.com",
        session_data=session_data
    )

    # Verify session has AUDIO mode
    assert session.interaction_mode == InteractionMode.AUDIO

    # Verify Firestore document was created with interaction_mode
    mock_doc_ref.set.assert_called_once()
    firestore_data = mock_doc_ref.set.call_args[0][0]
    assert "interaction_mode" in firestore_data
    assert firestore_data["interaction_mode"] == "audio"


@pytest.mark.asyncio
async def test_tc_mgr_03_default_mode_is_text(
    session_manager_with_adk, mock_firestore_client, mock_adk_session_service
):
    """TC-MGR-03: Default mode is TEXT when not specified"""
    # Create session without specifying interaction_mode
    session_data = SessionCreate(user_name="Test User")

    mock_doc_ref = MagicMock()
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_with_adk.create_session(
        user_id="user_789",
        user_email="test@example.com",
        session_data=session_data
    )

    # Should default to TEXT mode
    assert session.interaction_mode == InteractionMode.TEXT

    # Verify Firestore has TEXT mode
    firestore_data = mock_doc_ref.set.call_args[0][0]
    assert firestore_data["interaction_mode"] == "text"


@pytest.mark.asyncio
async def test_tc_mgr_02_get_session_returns_text_mode(
    session_manager_with_adk, mock_firestore_client
):
    """TC-MGR-02: Session retrieval returns correct interaction_mode (TEXT)"""
    session_id = "sess_text_mode"

    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {
        "session_id": session_id,
        "user_id": "user_123",
        "user_email": "test@example.com",
        "user_name": "Test User",
        "status": "initialized",
        "interaction_mode": "text",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "conversation_history": [],
        "metadata": {},
        "turn_count": 0,
    }

    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_snapshot
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_with_adk.get_session(session_id)

    assert session is not None
    assert session.interaction_mode == InteractionMode.TEXT


@pytest.mark.asyncio
async def test_tc_mgr_04_audio_mode_stored_and_retrieved(
    session_manager_with_adk, mock_firestore_client
):
    """TC-MGR-04: AUDIO mode is correctly stored and retrieved"""
    session_id = "sess_audio_mode"

    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {
        "session_id": session_id,
        "user_id": "user_premium",
        "user_email": "premium@example.com",
        "user_name": "Premium User",
        "status": "active",
        "interaction_mode": "audio",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "conversation_history": [],
        "metadata": {},
        "turn_count": 0,
    }

    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_snapshot
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_with_adk.get_session(session_id)

    assert session is not None
    assert session.interaction_mode == InteractionMode.AUDIO
    assert session.user_email == "premium@example.com"


@pytest.mark.asyncio
async def test_session_with_text_mode_has_mc_welcome_fields(
    session_manager_with_adk, mock_firestore_client
):
    """Test that TEXT mode sessions can have MC welcome fields"""
    session_id = "sess_text_with_game"

    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {
        "session_id": session_id,
        "user_id": "user_123",
        "user_email": "test@example.com",
        "user_name": "Test User",
        "status": "game_select",
        "interaction_mode": "text",
        "selected_game_id": "game_456",
        "selected_game_name": "Freeze Tag",
        "audience_suggestion": "astronauts",
        "mc_welcome_complete": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "conversation_history": [],
        "metadata": {},
        "turn_count": 0,
    }

    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_snapshot
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_with_adk.get_session(session_id)

    assert session is not None
    assert session.interaction_mode == InteractionMode.TEXT
    assert session.selected_game_id == "game_456"
    assert session.selected_game_name == "Freeze Tag"
    assert session.audience_suggestion == "astronauts"
    assert session.mc_welcome_complete is False


@pytest.mark.asyncio
async def test_session_with_audio_mode_direct_to_active(
    session_manager_with_adk, mock_firestore_client
):
    """Test that AUDIO mode sessions can go directly to ACTIVE status"""
    session_id = "sess_audio_active"

    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {
        "session_id": session_id,
        "user_id": "user_premium",
        "user_email": "premium@example.com",
        "user_name": "Premium User",
        "status": "active",
        "interaction_mode": "audio",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "conversation_history": [],
        "metadata": {},
        "turn_count": 5,
    }

    mock_doc_ref = MagicMock()
    mock_doc_ref.get.return_value = mock_snapshot
    mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref

    session = await session_manager_with_adk.get_session(session_id)

    assert session is not None
    assert session.interaction_mode == InteractionMode.AUDIO
    assert session.status.value == "active"
    assert session.turn_count == 5
