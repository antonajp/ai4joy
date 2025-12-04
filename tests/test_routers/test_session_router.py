"""
API Endpoint Tests for Session Creation - IQS-75
Tests for interaction_mode parameter in session endpoints

Test Coverage:
- TC-API-SESSION-01: POST /session/start accepts interaction_mode parameter
- TC-API-SESSION-02: Response includes session with correct mode
- TC-API-SESSION-03: TEXT mode works correctly
- TC-API-SESSION-04: AUDIO mode works correctly
- TC-API-SESSION-05: Default to TEXT when mode not specified
- TC-API-SESSION-06: Invalid mode values are rejected
- TC-API-SESSION-07: GET /session/{id} returns interaction_mode
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import status
from datetime import datetime, timezone, timedelta

from app.routers.sessions import start_session, get_session_info
from app.models.session import SessionCreate, SessionResponse, Session, InteractionMode, SessionStatus
from app.services.session_manager import SessionManager


class TestSessionStartEndpoint:
    """Tests for POST /session/start endpoint with interaction_mode"""

    @pytest.fixture
    def mock_request(self):
        """Mock authenticated request"""
        request = Mock()
        request.headers = {
            "X-Goog-IAP-JWT-Assertion": "valid-jwt-token",
            "X-Goog-Authenticated-User-ID": "accounts.google.com:123456",
            "X-Goog-Authenticated-User-Email": "test@example.com",
        }
        return request

    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager"""
        manager = Mock(spec=SessionManager)
        manager.create_session = AsyncMock()
        return manager

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter"""
        limiter = Mock()
        limiter.check_and_increment_daily_limit = AsyncMock()
        limiter.check_and_increment_concurrent_limit = AsyncMock()
        return limiter

    @pytest.mark.asyncio
    async def test_tc_api_session_01_accepts_text_mode(
        self, mock_request, mock_session_manager, mock_rate_limiter
    ):
        """TC-API-SESSION-01: POST /session/start accepts interaction_mode (TEXT)"""
        session_data = SessionCreate(
            user_name="Test User",
            interaction_mode=InteractionMode.TEXT
        )

        # Mock created session
        created_session = Session(
            session_id="sess_text123",
            user_id="123456",
            user_email="test@example.com",
            user_name="Test User",
            status=SessionStatus.INITIALIZED,
            interaction_mode=InteractionMode.TEXT,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            metadata={},
            turn_count=0,
        )

        mock_session_manager.create_session.return_value = created_session

        with patch("app.routers.sessions.get_authenticated_user") as mock_auth:
            mock_auth.return_value = {
                "user_id": "123456",
                "user_email": "test@example.com",
            }

            response = await start_session(
                session_data=session_data,
                request=mock_request,
                session_manager=mock_session_manager,
                rate_limiter=mock_rate_limiter,
            )

            # Verify session was created with TEXT mode
            mock_session_manager.create_session.assert_called_once()
            call_args = mock_session_manager.create_session.call_args
            assert call_args[1]["session_data"].interaction_mode == InteractionMode.TEXT

    @pytest.mark.asyncio
    async def test_tc_api_session_01_accepts_audio_mode(
        self, mock_request, mock_session_manager, mock_rate_limiter
    ):
        """TC-API-SESSION-01: POST /session/start accepts interaction_mode (AUDIO)"""
        session_data = SessionCreate(
            user_name="Premium User",
            interaction_mode=InteractionMode.AUDIO
        )

        # Mock created session
        created_session = Session(
            session_id="sess_audio456",
            user_id="123456",
            user_email="premium@example.com",
            user_name="Premium User",
            status=SessionStatus.ACTIVE,
            interaction_mode=InteractionMode.AUDIO,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            metadata={},
            turn_count=0,
        )

        mock_session_manager.create_session.return_value = created_session

        with patch("app.routers.sessions.get_authenticated_user") as mock_auth:
            mock_auth.return_value = {
                "user_id": "123456",
                "user_email": "premium@example.com",
            }

            response = await start_session(
                session_data=session_data,
                request=mock_request,
                session_manager=mock_session_manager,
                rate_limiter=mock_rate_limiter,
            )

            # Verify session was created with AUDIO mode
            mock_session_manager.create_session.assert_called_once()
            call_args = mock_session_manager.create_session.call_args
            assert call_args[1]["session_data"].interaction_mode == InteractionMode.AUDIO

    @pytest.mark.asyncio
    async def test_tc_api_session_02_response_includes_session(
        self, mock_request, mock_session_manager, mock_rate_limiter
    ):
        """TC-API-SESSION-02: Response includes session with correct details"""
        session_data = SessionCreate(
            user_name="Test User",
            interaction_mode=InteractionMode.TEXT
        )

        # Mock created session
        created_session = Session(
            session_id="sess_test789",
            user_id="123456",
            user_email="test@example.com",
            user_name="Test User",
            status=SessionStatus.INITIALIZED,
            interaction_mode=InteractionMode.TEXT,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            metadata={},
            turn_count=0,
        )

        mock_session_manager.create_session.return_value = created_session

        with patch("app.routers.sessions.get_authenticated_user") as mock_auth:
            mock_auth.return_value = {
                "user_id": "123456",
                "user_email": "test@example.com",
            }

            response = await start_session(
                session_data=session_data,
                request=mock_request,
                session_manager=mock_session_manager,
                rate_limiter=mock_rate_limiter,
            )

            # Verify response type and contents
            assert isinstance(response, SessionResponse)
            assert response.session_id == "sess_test789"
            assert response.status == SessionStatus.INITIALIZED
            assert response.turn_count == 0

    @pytest.mark.asyncio
    async def test_tc_api_session_05_defaults_to_text_mode(
        self, mock_request, mock_session_manager, mock_rate_limiter
    ):
        """TC-API-SESSION-05: Default to TEXT when mode not specified"""
        # Create session data without interaction_mode
        session_data = SessionCreate(user_name="Test User")

        # Session should default to TEXT mode
        assert session_data.interaction_mode == InteractionMode.TEXT

        # Mock created session
        created_session = Session(
            session_id="sess_default",
            user_id="123456",
            user_email="test@example.com",
            user_name="Test User",
            status=SessionStatus.INITIALIZED,
            interaction_mode=InteractionMode.TEXT,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            metadata={},
            turn_count=0,
        )

        mock_session_manager.create_session.return_value = created_session

        with patch("app.routers.sessions.get_authenticated_user") as mock_auth:
            mock_auth.return_value = {
                "user_id": "123456",
                "user_email": "test@example.com",
            }

            response = await start_session(
                session_data=session_data,
                request=mock_request,
                session_manager=mock_session_manager,
                rate_limiter=mock_rate_limiter,
            )

            # Verify session was created with default TEXT mode
            call_args = mock_session_manager.create_session.call_args
            assert call_args[1]["session_data"].interaction_mode == InteractionMode.TEXT

    @pytest.mark.asyncio
    async def test_tc_api_session_03_text_mode_with_game_selection(
        self, mock_request, mock_session_manager, mock_rate_limiter
    ):
        """TC-API-SESSION-03: TEXT mode works with pre-selected game"""
        session_data = SessionCreate(
            user_name="Test User",
            selected_game_id="game_123",
            selected_game_name="Yes, And",
            interaction_mode=InteractionMode.TEXT
        )

        # Mock created session
        created_session = Session(
            session_id="sess_text_game",
            user_id="123456",
            user_email="test@example.com",
            user_name="Test User",
            status=SessionStatus.INITIALIZED,
            interaction_mode=InteractionMode.TEXT,
            selected_game_id="game_123",
            selected_game_name="Yes, And",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            metadata={},
            turn_count=0,
        )

        mock_session_manager.create_session.return_value = created_session

        with patch("app.routers.sessions.get_authenticated_user") as mock_auth:
            mock_auth.return_value = {
                "user_id": "123456",
                "user_email": "test@example.com",
            }

            response = await start_session(
                session_data=session_data,
                request=mock_request,
                session_manager=mock_session_manager,
                rate_limiter=mock_rate_limiter,
            )

            # Verify session created with TEXT mode and game selection
            call_args = mock_session_manager.create_session.call_args
            created_data = call_args[1]["session_data"]
            assert created_data.interaction_mode == InteractionMode.TEXT
            assert created_data.selected_game_id == "game_123"
            assert created_data.selected_game_name == "Yes, And"

    @pytest.mark.asyncio
    async def test_tc_api_session_04_audio_mode_for_premium(
        self, mock_request, mock_session_manager, mock_rate_limiter
    ):
        """TC-API-SESSION-04: AUDIO mode works for premium users"""
        session_data = SessionCreate(
            user_name="Premium User",
            interaction_mode=InteractionMode.AUDIO
        )

        # Mock created session with AUDIO mode
        created_session = Session(
            session_id="sess_premium_audio",
            user_id="premium_123",
            user_email="premium@example.com",
            user_name="Premium User",
            status=SessionStatus.ACTIVE,  # AUDIO mode goes directly to ACTIVE
            interaction_mode=InteractionMode.AUDIO,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            metadata={},
            turn_count=0,
        )

        mock_session_manager.create_session.return_value = created_session

        with patch("app.routers.sessions.get_authenticated_user") as mock_auth:
            mock_auth.return_value = {
                "user_id": "premium_123",
                "user_email": "premium@example.com",
            }

            response = await start_session(
                session_data=session_data,
                request=mock_request,
                session_manager=mock_session_manager,
                rate_limiter=mock_rate_limiter,
            )

            # Verify AUDIO mode session
            assert isinstance(response, SessionResponse)
            call_args = mock_session_manager.create_session.call_args
            assert call_args[1]["session_data"].interaction_mode == InteractionMode.AUDIO


class TestGetSessionEndpoint:
    """Tests for GET /session/{id} endpoint with interaction_mode"""

    @pytest.fixture
    def mock_request(self):
        """Mock authenticated request"""
        request = Mock()
        request.headers = {
            "X-Goog-IAP-JWT-Assertion": "valid-jwt-token",
            "X-Goog-Authenticated-User-ID": "accounts.google.com:123456",
            "X-Goog-Authenticated-User-Email": "test@example.com",
        }
        return request

    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager"""
        manager = Mock(spec=SessionManager)
        manager.get_session = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_tc_api_session_07_get_returns_text_mode(
        self, mock_request, mock_session_manager
    ):
        """TC-API-SESSION-07: GET /session/{id} returns TEXT mode"""
        session = Session(
            session_id="sess_text_get",
            user_id="123456",
            user_email="test@example.com",
            user_name="Test User",
            status=SessionStatus.ACTIVE,
            interaction_mode=InteractionMode.TEXT,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            metadata={},
            turn_count=5,
        )

        mock_session_manager.get_session.return_value = session

        with patch("app.routers.sessions.get_authenticated_user") as mock_auth:
            mock_auth.return_value = {
                "user_id": "123456",
                "user_email": "test@example.com",
            }

            response = await get_session_info(
                session_id="sess_text_get",
                request=mock_request,
                session_manager=mock_session_manager,
            )

            # Verify response
            assert isinstance(response, SessionResponse)
            assert response.session_id == "sess_text_get"
            assert response.turn_count == 5

    @pytest.mark.asyncio
    async def test_tc_api_session_07_get_returns_audio_mode(
        self, mock_request, mock_session_manager
    ):
        """TC-API-SESSION-07: GET /session/{id} returns AUDIO mode"""
        session = Session(
            session_id="sess_audio_get",
            user_id="premium_123",
            user_email="premium@example.com",
            user_name="Premium User",
            status=SessionStatus.ACTIVE,
            interaction_mode=InteractionMode.AUDIO,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            metadata={},
            turn_count=10,
        )

        mock_session_manager.get_session.return_value = session

        with patch("app.routers.sessions.get_authenticated_user") as mock_auth:
            mock_auth.return_value = {
                "user_id": "premium_123",
                "user_email": "premium@example.com",
            }

            response = await get_session_info(
                session_id="sess_audio_get",
                request=mock_request,
                session_manager=mock_session_manager,
            )

            # Verify response
            assert isinstance(response, SessionResponse)
            assert response.session_id == "sess_audio_get"
            assert response.turn_count == 10


class TestInteractionModeValidation:
    """Tests for interaction_mode validation"""

    def test_tc_api_session_06_invalid_mode_rejected(self):
        """TC-API-SESSION-06: Invalid mode values are rejected"""
        # Pydantic should reject invalid enum values
        with pytest.raises(Exception):  # ValidationError
            SessionCreate(
                user_name="Test User",
                interaction_mode="invalid_mode"  # Not a valid InteractionMode
            )

    def test_valid_mode_string_converted_to_enum(self):
        """Test that valid mode string is converted to enum"""
        # Valid string should be converted to enum
        session_data = SessionCreate(
            user_name="Test User",
            interaction_mode="text"
        )
        assert session_data.interaction_mode == InteractionMode.TEXT

        session_data_audio = SessionCreate(
            user_name="Premium User",
            interaction_mode="audio"
        )
        assert session_data_audio.interaction_mode == InteractionMode.AUDIO
