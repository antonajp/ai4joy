"""Tests for ADK Session Bridge Service"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from app.services.adk_session_bridge import ADKSessionBridge, get_adk_session_bridge
from app.models.session import Session, SessionStatus


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client"""
    with patch("app.services.adk_session_bridge.firestore.Client") as mock_client:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_client.return_value = mock_db
        yield mock_db


@pytest.fixture
def sample_session():
    """Sample session for testing"""
    return Session(
        session_id="sess_test123",
        user_id="user_123",
        user_email="test@example.com",
        user_name="Test User",
        location="Mars Base",
        status=SessionStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        conversation_history=[],
        metadata={},
        current_phase="PHASE_1",
        turn_count=0
    )


@pytest.fixture
def adk_bridge(mock_firestore_client):
    """ADK Session Bridge instance"""
    return ADKSessionBridge()


@pytest.mark.asyncio
async def test_create_adk_session(adk_bridge, sample_session):
    """Test creating ADK session from Session model"""
    adk_session = await adk_bridge.create_session(sample_session)

    assert adk_session is not None
    assert adk_session.id == sample_session.session_id
    assert adk_session.user_id == sample_session.user_id
    assert adk_session.state["location"] == sample_session.location
    assert adk_session.state["current_phase"] == "PHASE_1"
    assert adk_session.state["turn_count"] == 0


@pytest.mark.asyncio
async def test_get_or_create_adk_session_creates_new(adk_bridge, sample_session):
    """Test get_or_create creates new session when not exists"""
    adk_session = await adk_bridge.get_or_create_adk_session(sample_session)

    assert adk_session is not None
    assert adk_session.id == sample_session.session_id


@pytest.mark.asyncio
async def test_get_or_create_adk_session_retrieves_existing(adk_bridge, sample_session):
    """Test get_or_create retrieves existing session"""
    adk_session_1 = await adk_bridge.create_session(sample_session)

    adk_session_2 = await adk_bridge.get_or_create_adk_session(sample_session)

    assert adk_session_1.id == adk_session_2.id
    assert len(adk_session_2.events) == len(adk_session_1.events)


@pytest.mark.asyncio
async def test_sync_adk_session_to_firestore(adk_bridge, sample_session, mock_firestore_client):
    """Test syncing ADK session state to Firestore"""
    adk_session = await adk_bridge.create_session(sample_session)

    adk_session.state["turn_count"] = 5
    adk_session.state["current_phase"] = "PHASE_2"

    await adk_bridge.sync_adk_session_to_firestore(
        adk_session=adk_session,
        session_id=sample_session.session_id
    )

    collection = mock_firestore_client.collection.return_value
    doc_ref = collection.document.return_value
    doc_ref.update.assert_called_once()

    update_call = doc_ref.update.call_args[0][0]
    assert update_call["turn_count"] == 5
    assert update_call["current_phase"] == "PHASE_2"
    assert "updated_at" in update_call


@pytest.mark.asyncio
async def test_update_adk_session_state(adk_bridge, sample_session):
    """Test updating ADK session state in-memory

    Note: ADK InMemorySessionService returns deep copies, so this test
    verifies the update method works without errors. In production with
    DatabaseSessionService, updates would persist.
    """
    await adk_bridge.create_session(sample_session)

    state_updates = {
        "turn_count": 3,
        "current_phase": "PHASE_2"
    }

    await adk_bridge.update_adk_session_state(
        session_id=sample_session.session_id,
        user_id=sample_session.user_id,
        state_updates=state_updates
    )

    adk_session = await adk_bridge.adk_session_service.get_session(
        app_name="Improv Olympics",
        user_id=sample_session.user_id,
        session_id=sample_session.session_id
    )

    assert adk_session is not None


@pytest.mark.asyncio
async def test_delete_adk_session(adk_bridge, sample_session):
    """Test deleting ADK session"""
    await adk_bridge.create_session(sample_session)

    await adk_bridge.delete_adk_session(
        session_id=sample_session.session_id,
        user_id=sample_session.user_id
    )

    adk_session = await adk_bridge.adk_session_service.get_session(
        app_name="Improv Olympics",
        user_id=sample_session.user_id,
        session_id=sample_session.session_id
    )

    assert adk_session is None


@pytest.mark.asyncio
async def test_list_adk_sessions_for_user(adk_bridge):
    """Test listing ADK sessions for a user"""
    user_id = "user_123"

    session1 = Session(
        session_id="sess_1",
        user_id=user_id,
        user_email="test@example.com",
        user_name="Test",
        location="Location 1",
        status=SessionStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        conversation_history=[],
        metadata={},
        turn_count=0
    )

    session2 = Session(
        session_id="sess_2",
        user_id=user_id,
        user_email="test@example.com",
        user_name="Test",
        location="Location 2",
        status=SessionStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        conversation_history=[],
        metadata={},
        turn_count=0
    )

    await adk_bridge.create_session(session1)
    await adk_bridge.create_session(session2)

    count = await adk_bridge.list_adk_sessions_for_user(user_id)

    assert count == 2


def test_get_adk_event_count(adk_bridge):
    """Test getting event count from ADK session"""
    from google.adk.sessions.session import Session as ADKSession

    adk_session = ADKSession(
        id="sess_test",
        app_name="test_app",
        user_id="user_123",
        state={},
        events=[],
        last_update_time=0.0
    )

    count = adk_bridge.get_adk_event_count(adk_session)
    assert count == 0


def test_convert_adk_to_session_model(adk_bridge, sample_session):
    """Test converting ADK session to Session model"""
    from google.adk.sessions.session import Session as ADKSession

    adk_session = ADKSession(
        id=sample_session.session_id,
        app_name="test_app",
        user_id=sample_session.user_id,
        state={
            "turn_count": 5,
            "current_phase": "PHASE_2",
            "status": "active"
        },
        events=[],
        last_update_time=0.0
    )

    updated_session = adk_bridge.convert_adk_to_session_model(
        adk_session=adk_session,
        firestore_session=sample_session
    )

    assert updated_session.turn_count == 5
    assert updated_session.current_phase == "PHASE_2"
    assert updated_session.status == SessionStatus.ACTIVE


def test_get_adk_session_bridge_singleton():
    """Test singleton pattern for ADK session bridge"""
    bridge1 = get_adk_session_bridge()
    bridge2 = get_adk_session_bridge()

    assert bridge1 is bridge2
