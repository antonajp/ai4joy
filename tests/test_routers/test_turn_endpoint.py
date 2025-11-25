"""
API Endpoint Tests for Turn Execution - Week 7 Implementation

Test Coverage:
- TC-API-01: POST /session/{id}/turn with valid inputs
- TC-API-02: Authentication and authorization checks
- TC-API-03: Turn number validation (sequence enforcement)
- TC-API-04: Session not found scenarios
- TC-API-05: Expired session handling
- TC-API-06: Unauthorized access attempts
- TC-API-07: HTTP status codes correctness
- TC-API-08: Request/response validation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException, status
from datetime import datetime, timezone, timedelta

from app.routers.sessions import execute_turn
from app.models.session import Session, SessionStatus, TurnInput, TurnResponse
from app.services.session_manager import SessionManager


class TestTurnEndpointValidInputs:
    """TC-API-01: POST /session/{id}/turn with Valid Inputs"""

    @pytest.fixture
    def mock_request(self):
        """Mock authenticated request"""
        request = Mock()
        request.headers = {
            "X-Goog-IAP-JWT-Assertion": "valid-jwt-token",
            "X-Goog-Authenticated-User-ID": "accounts.google.com:123456",
            "X-Goog-Authenticated-User-Email": "test@example.com"
        }
        return request

    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager"""
        manager = Mock(spec=SessionManager)
        manager.get_session = AsyncMock()
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        return manager

    @pytest.fixture
    def active_session(self):
        """Create active session for testing"""
        return Session(
            session_id="sess-test-123",
            user_id="123456",
            user_email="test@example.com",
            location="Mars Colony",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=3,
            current_phase="PHASE_1"
        )

    @pytest.mark.asyncio
    async def test_tc_api_01a_successful_turn_execution(
        self, mock_request, mock_session_manager, active_session
    ):
        """
        TC-API-01a: Successful Turn Execution

        Valid request with correct turn number should execute successfully
        and return TurnResponse.
        """
        mock_session_manager.get_session.return_value = active_session

        turn_input = TurnInput(
            user_input="Let's check the oxygen levels",
            turn_number=4
        )

        # Mock turn orchestrator
        with patch('app.routers.sessions.get_turn_orchestrator') as mock_orchestrator:
            mock_orch_instance = Mock()
            mock_orch_instance.execute_turn = AsyncMock(return_value={
                "turn_number": 4,
                "partner_response": "Great idea! I'll grab the scanner.",
                "room_vibe": {"analysis": "Engaged", "energy": "high"},
                "current_phase": 2,
                "timestamp": datetime.now(timezone.utc)
            })
            mock_orchestrator.return_value = mock_orch_instance

            # Mock authentication
            with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
                mock_auth.return_value = {
                    "user_id": "123456",
                    "user_email": "test@example.com"
                }

                response = await execute_turn(
                    session_id="sess-test-123",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

                assert isinstance(response, TurnResponse)
                assert response.turn_number == 4
                assert response.partner_response == "Great idea! I'll grab the scanner."
                assert "Phase 2" in response.current_phase
                assert "room_vibe" in response.model_dump()

    @pytest.mark.asyncio
    async def test_tc_api_01b_turn_response_includes_all_fields(
        self, mock_request, mock_session_manager, active_session
    ):
        """
        TC-API-01b: Response Includes All Required Fields

        TurnResponse should include turn_number, partner_response,
        room_vibe, current_phase, and timestamp.
        """
        mock_session_manager.get_session.return_value = active_session

        turn_input = TurnInput(
            user_input="Test input",
            turn_number=4
        )

        with patch('app.routers.sessions.get_turn_orchestrator') as mock_orchestrator:
            mock_orch_instance = Mock()
            mock_orch_instance.execute_turn = AsyncMock(return_value={
                "turn_number": 4,
                "partner_response": "Response text",
                "room_vibe": {"analysis": "Good", "energy": "medium"},
                "current_phase": 2,
                "timestamp": datetime.now(timezone.utc)
            })
            mock_orchestrator.return_value = mock_orch_instance

            with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
                mock_auth.return_value = {
                    "user_id": "123456",
                    "user_email": "test@example.com"
                }

                response = await execute_turn(
                    session_id="sess-test-123",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

                response_dict = response.model_dump()

                # Verify all required fields present
                assert "turn_number" in response_dict
                assert "partner_response" in response_dict
                assert "room_vibe" in response_dict
                assert "current_phase" in response_dict
                assert "timestamp" in response_dict


class TestTurnEndpointAuthentication:
    """TC-API-02: Authentication and Authorization Checks"""

    @pytest.fixture
    def mock_session_manager(self):
        manager = Mock(spec=SessionManager)
        manager.get_session = AsyncMock()
        return manager

    @pytest.fixture
    def valid_session(self):
        return Session(
            session_id="sess-test-123",
            user_id="owner-123",
            user_email="owner@example.com",
            location="Test Location",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=2
        )

    @pytest.mark.asyncio
    async def test_tc_api_02a_unauthorized_user_cannot_execute_turn(
        self, mock_session_manager, valid_session
    ):
        """
        TC-API-02a: Unauthorized User Blocked (403 Forbidden)

        User who doesn't own the session should receive 403.
        """
        mock_session_manager.get_session.return_value = valid_session

        turn_input = TurnInput(
            user_input="Unauthorized input",
            turn_number=3
        )

        mock_request = Mock()
        with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
            # Different user trying to access
            mock_auth.return_value = {
                "user_id": "attacker-999",
                "user_email": "attacker@example.com"
            }

            with pytest.raises(HTTPException) as exc_info:
                await execute_turn(
                    session_id="sess-test-123",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Not authorized" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_tc_api_02b_owner_can_execute_turn(
        self, mock_session_manager, valid_session
    ):
        """
        TC-API-02b: Session Owner Can Execute Turn

        User who owns the session should be authorized.
        """
        mock_session_manager.get_session.return_value = valid_session

        turn_input = TurnInput(
            user_input="Owner input",
            turn_number=3
        )

        mock_request = Mock()

        with patch('app.routers.sessions.get_turn_orchestrator') as mock_orchestrator:
            mock_orch_instance = Mock()
            mock_orch_instance.execute_turn = AsyncMock(return_value={
                "turn_number": 3,
                "partner_response": "Response",
                "room_vibe": {"analysis": "Good", "energy": "medium"},
                "current_phase": 1,
                "timestamp": datetime.now(timezone.utc)
            })
            mock_orchestrator.return_value = mock_orch_instance

            with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
                # Same user as session owner
                mock_auth.return_value = {
                    "user_id": "owner-123",
                    "user_email": "owner@example.com"
                }

                response = await execute_turn(
                    session_id="sess-test-123",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

                # Should succeed
                assert response.turn_number == 3


class TestTurnEndpointTurnNumberValidation:
    """TC-API-03: Turn Number Validation (Sequence Enforcement)"""

    @pytest.fixture
    def mock_session_manager(self):
        manager = Mock(spec=SessionManager)
        manager.get_session = AsyncMock()
        return manager

    @pytest.fixture
    def session_at_turn_5(self):
        return Session(
            session_id="sess-test-123",
            user_id="user-123",
            user_email="user@example.com",
            location="Test Location",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=5  # Currently at turn 5
        )

    @pytest.mark.asyncio
    async def test_tc_api_03a_out_of_sequence_turn_rejected(
        self, mock_session_manager, session_at_turn_5
    ):
        """
        TC-API-03a: Out-of-Sequence Turn Rejected (400 Bad Request)

        If user submits turn 3 when session is at turn 5, reject with 400.
        """
        mock_session_manager.get_session.return_value = session_at_turn_5

        turn_input = TurnInput(
            user_input="Out of order input",
            turn_number=3  # Wrong! Should be 6
        )

        mock_request = Mock()
        with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "user-123",
                "user_email": "user@example.com"
            }

            with pytest.raises(HTTPException) as exc_info:
                await execute_turn(
                    session_id="sess-test-123",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Expected turn 6, got 3" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_tc_api_03b_correct_sequence_accepted(
        self, mock_session_manager, session_at_turn_5
    ):
        """
        TC-API-03b: Correct Turn Sequence Accepted

        If user submits turn 6 when session is at turn 5, accept.
        """
        mock_session_manager.get_session.return_value = session_at_turn_5

        turn_input = TurnInput(
            user_input="Correct sequence input",
            turn_number=6  # Correct!
        )

        mock_request = Mock()

        with patch('app.routers.sessions.get_turn_orchestrator') as mock_orchestrator:
            mock_orch_instance = Mock()
            mock_orch_instance.execute_turn = AsyncMock(return_value={
                "turn_number": 6,
                "partner_response": "Response",
                "room_vibe": {"analysis": "Good", "energy": "medium"},
                "current_phase": 2,
                "timestamp": datetime.now(timezone.utc)
            })
            mock_orchestrator.return_value = mock_orch_instance

            with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
                mock_auth.return_value = {
                    "user_id": "user-123",
                    "user_email": "user@example.com"
                }

                response = await execute_turn(
                    session_id="sess-test-123",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

                assert response.turn_number == 6

    @pytest.mark.asyncio
    async def test_tc_api_03c_skip_turn_rejected(
        self, mock_session_manager, session_at_turn_5
    ):
        """
        TC-API-03c: Skipping Turn Rejected

        If user tries to skip from turn 5 to turn 7, reject.
        """
        mock_session_manager.get_session.return_value = session_at_turn_5

        turn_input = TurnInput(
            user_input="Skipping turn",
            turn_number=7  # Skipping turn 6!
        )

        mock_request = Mock()
        with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "user-123",
                "user_email": "user@example.com"
            }

            with pytest.raises(HTTPException) as exc_info:
                await execute_turn(
                    session_id="sess-test-123",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


class TestTurnEndpointSessionNotFound:
    """TC-API-04: Session Not Found Scenarios"""

    @pytest.fixture
    def mock_session_manager(self):
        manager = Mock(spec=SessionManager)
        manager.get_session = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_tc_api_04a_nonexistent_session_returns_404(
        self, mock_session_manager
    ):
        """
        TC-API-04a: Non-Existent Session Returns 404

        Request to non-existent session should return 404 Not Found.
        """
        mock_session_manager.get_session.return_value = None

        turn_input = TurnInput(
            user_input="Test input",
            turn_number=1
        )

        mock_request = Mock()
        with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "user-123",
                "user_email": "user@example.com"
            }

            with pytest.raises(HTTPException) as exc_info:
                await execute_turn(
                    session_id="nonexistent-session",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in exc_info.value.detail.lower()


class TestTurnEndpointExpiredSession:
    """TC-API-05: Expired Session Handling"""

    @pytest.fixture
    def mock_session_manager(self):
        manager = Mock(spec=SessionManager)
        manager.get_session = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_tc_api_05a_expired_session_returns_404(
        self, mock_session_manager
    ):
        """
        TC-API-05a: Expired Session Returns 404

        SessionManager.get_session() returns None for expired sessions,
        resulting in 404.
        """
        # get_session returns None for expired sessions
        mock_session_manager.get_session.return_value = None

        turn_input = TurnInput(
            user_input="Test input",
            turn_number=1
        )

        mock_request = Mock()
        with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "user-123",
                "user_email": "user@example.com"
            }

            with pytest.raises(HTTPException) as exc_info:
                await execute_turn(
                    session_id="expired-session",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "expired" in exc_info.value.detail.lower() or "not found" in exc_info.value.detail.lower()


class TestTurnEndpointHTTPStatusCodes:
    """TC-API-07: HTTP Status Codes Correctness"""

    @pytest.fixture
    def mock_session_manager(self):
        manager = Mock(spec=SessionManager)
        manager.get_session = AsyncMock()
        return manager

    @pytest.fixture
    def valid_session(self):
        return Session(
            session_id="sess-test-123",
            user_id="user-123",
            user_email="user@example.com",
            location="Test",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=3
        )

    @pytest.mark.asyncio
    async def test_tc_api_07a_successful_turn_returns_200(
        self, mock_session_manager, valid_session
    ):
        """
        TC-API-07a: Successful Turn Returns 200 OK

        Valid turn execution should return 200 OK (default for FastAPI).
        """
        mock_session_manager.get_session.return_value = valid_session

        turn_input = TurnInput(
            user_input="Valid input",
            turn_number=4
        )

        mock_request = Mock()

        with patch('app.routers.sessions.get_turn_orchestrator') as mock_orchestrator:
            mock_orch_instance = Mock()
            mock_orch_instance.execute_turn = AsyncMock(return_value={
                "turn_number": 4,
                "partner_response": "Response",
                "room_vibe": {"analysis": "Good", "energy": "medium"},
                "current_phase": 2,
                "timestamp": datetime.now(timezone.utc)
            })
            mock_orchestrator.return_value = mock_orch_instance

            with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
                mock_auth.return_value = {
                    "user_id": "user-123",
                    "user_email": "user@example.com"
                }

                response = await execute_turn(
                    session_id="sess-test-123",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

                # Should return TurnResponse without exception
                assert isinstance(response, TurnResponse)

    @pytest.mark.asyncio
    async def test_tc_api_07b_agent_failure_returns_500(
        self, mock_session_manager, valid_session
    ):
        """
        TC-API-07b: Agent Failure Returns 500 Internal Server Error

        When turn orchestrator fails, should return 500.
        """
        mock_session_manager.get_session.return_value = valid_session

        turn_input = TurnInput(
            user_input="Input that causes failure",
            turn_number=4
        )

        mock_request = Mock()

        with patch('app.routers.sessions.get_turn_orchestrator') as mock_orchestrator:
            mock_orch_instance = Mock()
            mock_orch_instance.execute_turn = AsyncMock(
                side_effect=Exception("Agent execution failed")
            )
            mock_orchestrator.return_value = mock_orch_instance

            with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
                mock_auth.return_value = {
                    "user_id": "user-123",
                    "user_email": "user@example.com"
                }

                with pytest.raises(HTTPException) as exc_info:
                    await execute_turn(
                        session_id="sess-test-123",
                        turn_input=turn_input,
                        request=mock_request,
                        session_manager=mock_session_manager
                    )

                assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
                assert "error occurred" in exc_info.value.detail.lower()


class TestTurnEndpointRequestValidation:
    """TC-API-08: Request/Response Validation"""

    @pytest.mark.asyncio
    async def test_tc_api_08a_empty_user_input_rejected(self):
        """
        TC-API-08a: Empty User Input Rejected

        TurnInput validation should reject empty user_input.
        """
        with pytest.raises(Exception):  # Pydantic ValidationError
            TurnInput(
                user_input="",  # Empty!
                turn_number=1
            )

    @pytest.mark.asyncio
    async def test_tc_api_08b_turn_number_zero_rejected(self):
        """
        TC-API-08b: Turn Number 0 Rejected

        Turn numbers must be >= 1.
        """
        with pytest.raises(Exception):  # Pydantic ValidationError
            TurnInput(
                user_input="Valid input",
                turn_number=0  # Invalid!
            )

    @pytest.mark.asyncio
    async def test_tc_api_08c_negative_turn_number_rejected(self):
        """
        TC-API-08c: Negative Turn Number Rejected

        Turn numbers must be positive.
        """
        with pytest.raises(Exception):  # Pydantic ValidationError
            TurnInput(
                user_input="Valid input",
                turn_number=-1  # Invalid!
            )

    @pytest.mark.asyncio
    async def test_tc_api_08d_user_input_max_length_enforced(self):
        """
        TC-API-08d: User Input Max Length (1000 chars)

        TurnInput should enforce 1000 character maximum.
        """
        # Exactly 1000 chars should be OK
        valid_input = TurnInput(
            user_input="A" * 1000,
            turn_number=1
        )
        assert len(valid_input.user_input) == 1000

        # 1001 chars should be rejected
        with pytest.raises(Exception):  # Pydantic ValidationError
            TurnInput(
                user_input="A" * 1001,
                turn_number=1
            )

    @pytest.mark.asyncio
    async def test_tc_api_08e_valid_input_accepted(self):
        """
        TC-API-08e: Valid Input Accepted

        Normal valid inputs should pass validation.
        """
        valid_input = TurnInput(
            user_input="This is a valid scene contribution!",
            turn_number=5
        )

        assert valid_input.user_input == "This is a valid scene contribution!"
        assert valid_input.turn_number == 5


class TestTurnEndpointErrorMessages:
    """TC-API-09: Error Message Safety (No Sensitive Data Leaks)"""

    @pytest.fixture
    def mock_session_manager(self):
        manager = Mock(spec=SessionManager)
        manager.get_session = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_tc_api_09a_error_messages_no_pii(
        self, mock_session_manager
    ):
        """
        TC-API-09a: Error Messages Don't Leak PII

        Error messages should not expose user emails, internal IDs, etc.
        """
        mock_session_manager.get_session.return_value = None

        turn_input = TurnInput(
            user_input="Test",
            turn_number=1
        )

        mock_request = Mock()
        with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
            mock_auth.return_value = {
                "user_id": "secret-user-id-12345",
                "user_email": "secret@example.com"
            }

            with pytest.raises(HTTPException) as exc_info:
                await execute_turn(
                    session_id="nonexistent",
                    turn_input=turn_input,
                    request=mock_request,
                    session_manager=mock_session_manager
                )

            # Error message should not contain user email or internal IDs
            error_detail = exc_info.value.detail
            assert "secret-user-id-12345" not in error_detail
            assert "secret@example.com" not in error_detail

    @pytest.mark.asyncio
    async def test_tc_api_09b_generic_error_on_agent_failure(
        self, mock_session_manager
    ):
        """
        TC-API-09b: Generic Error Message on Agent Failure

        Internal agent errors should not expose implementation details.
        """
        valid_session = Session(
            session_id="sess-test-123",
            user_id="user-123",
            user_email="user@example.com",
            location="Test",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=3
        )

        mock_session_manager.get_session.return_value = valid_session

        turn_input = TurnInput(
            user_input="Test",
            turn_number=4
        )

        mock_request = Mock()

        with patch('app.routers.sessions.get_turn_orchestrator') as mock_orchestrator:
            mock_orch_instance = Mock()
            mock_orch_instance.execute_turn = AsyncMock(
                side_effect=Exception("Internal database connection string: postgres://secret:password@host")
            )
            mock_orchestrator.return_value = mock_orch_instance

            with patch('app.routers.sessions.get_authenticated_user') as mock_auth:
                mock_auth.return_value = {
                    "user_id": "user-123",
                    "user_email": "user@example.com"
                }

                with pytest.raises(HTTPException) as exc_info:
                    await execute_turn(
                        session_id="sess-test-123",
                        turn_input=turn_input,
                        request=mock_request,
                        session_manager=mock_session_manager
                    )

                error_detail = exc_info.value.detail.lower()
                assert "error occurred" in error_detail
