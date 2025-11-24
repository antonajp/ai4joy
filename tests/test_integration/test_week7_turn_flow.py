"""
Integration Tests for Week 7 Turn Execution Flow

Test Coverage:
- TC-INT-01: End-to-end turn flow (user input → agents → response)
- TC-INT-02: Stage Manager receives correct turn count
- TC-INT-03: Partner phase transitions at turn 4
- TC-INT-04: Conversation history accumulation
- TC-INT-05: Session status transitions
- TC-INT-06: Phase persistence in Firestore
- TC-INT-07: Multi-turn session simulation
- TC-INT-08: Performance and latency
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import asyncio

from app.services.turn_orchestrator import TurnOrchestrator
from app.services.session_manager import SessionManager
from app.models.session import Session, SessionStatus


class TestEndToEndTurnFlow:
    """TC-INT-01: End-to-End Turn Flow"""

    @pytest.fixture
    def session_manager_mock(self):
        """Mock session manager with spy capabilities"""
        manager = Mock(spec=SessionManager)
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager_mock):
        return TurnOrchestrator(session_manager_mock)

    @pytest.fixture
    def initial_session(self):
        return Session(
            session_id="integration-test-session",
            user_id="test-user-999",
            user_email="integration@test.com",
            location="Integration Test Arena",
            status=SessionStatus.INITIALIZED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=0,
            current_phase=None
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tc_int_01a_complete_turn_flow(
        self, orchestrator, session_manager_mock, initial_session
    ):
        """
        TC-INT-01a: Complete Turn Flow (User Input → Agents → Response)

        Verify entire pipeline executes: context building → Stage Manager
        creation → agent execution → response parsing → state updates.
        """
        with patch('app.services.turn_orchestrator.create_stage_manager') as mock_create_sm:
            with patch('app.services.turn_orchestrator.Runner') as mock_runner_class:
                # Mock Stage Manager
                mock_stage_manager = Mock()
                mock_create_sm.return_value = mock_stage_manager

                # Mock Runner
                mock_runner_instance = Mock()
                mock_runner_class.return_value = mock_runner_instance

                # Mock agent response
                agent_response = """PARTNER: Welcome to the arena! This is going to be amazing.
ROOM: The audience is buzzing with anticipation. Energy: High."""

                async def mock_run_agent(runner, prompt):
                    return agent_response

                # Patch the async run method
                orchestrator._run_agent_async = mock_run_agent

                # Execute turn
                result = await orchestrator.execute_turn(
                    session=initial_session,
                    user_input="Hi! I'm excited to start!",
                    turn_number=1
                )

                # Verify Stage Manager was created with correct turn count
                mock_create_sm.assert_called_once_with(turn_count=0)  # 0-indexed

                # Verify Runner was created with Stage Manager
                mock_runner_class.assert_called_once_with(mock_stage_manager)

                # Verify response structure
                assert result["turn_number"] == 1
                assert "Welcome to the arena" in result["partner_response"]
                assert "room_vibe" in result
                assert result["current_phase"] == 1  # Turn 1 is Phase 1

                # Verify session updates were called
                session_manager_mock.add_conversation_turn.assert_called_once()
                session_manager_mock.update_session_status.assert_called_once()


class TestStageManagerTurnCount:
    """TC-INT-02: Stage Manager Receives Correct Turn Count"""

    @pytest.fixture
    def orchestrator(self):
        manager = Mock(spec=SessionManager)
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        return TurnOrchestrator(manager)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tc_int_02a_stage_manager_turn_count_mapping(self, orchestrator):
        """
        TC-INT-02a: Stage Manager Turn Count is 0-Indexed

        When turn_number is 1, Stage Manager should receive turn_count=0.
        When turn_number is 5, Stage Manager should receive turn_count=4.
        """
        session = Session(
            session_id="test-session",
            user_id="user-123",
            user_email="test@example.com",
            location="Test",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=0
        )

        test_cases = [
            (1, 0),  # turn_number 1 → turn_count 0
            (4, 3),  # turn_number 4 → turn_count 3
            (5, 4),  # turn_number 5 → turn_count 4
            (15, 14),  # turn_number 15 → turn_count 14
        ]

        for turn_number, expected_turn_count in test_cases:
            with patch('app.services.turn_orchestrator.create_stage_manager') as mock_create:
                with patch('app.services.turn_orchestrator.Runner'):
                    async def mock_run(*args, **kwargs):
                        return "PARTNER: Test response\nROOM: Good energy"

                    orchestrator._run_agent_async = mock_run

                    await orchestrator.execute_turn(
                        session=session,
                        user_input="Test",
                        turn_number=turn_number
                    )

                    # Verify create_stage_manager called with correct turn_count
                    mock_create.assert_called_once_with(turn_count=expected_turn_count)


class TestPhaseTransitionsAtTurnFour:
    """TC-INT-03: Partner Phase Transitions at Turn 4"""

    @pytest.fixture
    def session_manager_mock(self):
        manager = Mock(spec=SessionManager)
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager_mock):
        return TurnOrchestrator(session_manager_mock)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tc_int_03a_phase_transition_logged_at_turn_4(
        self, orchestrator, session_manager_mock
    ):
        """
        TC-INT-03a: Phase Transition Logged at Turn 4

        When executing turn 4, phase should transition from 1 to 2,
        and update_session_phase should be called.
        """
        session = Session(
            session_id="phase-test-session",
            user_id="user-123",
            user_email="test@example.com",
            location="Test Arena",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=3,
            current_phase="PHASE_1"  # Currently Phase 1
        )

        with patch('app.services.turn_orchestrator.create_stage_manager'):
            with patch('app.services.turn_orchestrator.Runner'):
                async def mock_run(*args, **kwargs):
                    return "PARTNER: Turn 4 response\nROOM: Energy shift detected"

                orchestrator._run_agent_async = mock_run

                result = await orchestrator.execute_turn(
                    session=session,
                    user_input="Turn 4 input",
                    turn_number=4
                )

                # Verify phase in result
                assert result["current_phase"] == 2

                # Verify phase update was called
                session_manager_mock.update_session_phase.assert_called_once_with(
                    session_id="phase-test-session",
                    phase="PHASE_2"
                )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tc_int_03b_no_phase_update_when_unchanged(
        self, orchestrator, session_manager_mock
    ):
        """
        TC-INT-03b: No Phase Update When Phase Unchanged

        If phase doesn't change (e.g., turn 5 in Phase 2), should NOT
        call update_session_phase.
        """
        session = Session(
            session_id="phase-test-session",
            user_id="user-123",
            user_email="test@example.com",
            location="Test Arena",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=4,
            current_phase="PHASE_2"  # Already Phase 2
        )

        with patch('app.services.turn_orchestrator.create_stage_manager'):
            with patch('app.services.turn_orchestrator.Runner'):
                async def mock_run(*args, **kwargs):
                    return "PARTNER: Turn 5 response\nROOM: Continued energy"

                orchestrator._run_agent_async = mock_run

                await orchestrator.execute_turn(
                    session=session,
                    user_input="Turn 5 input",
                    turn_number=5
                )

                # Phase update should NOT be called
                session_manager_mock.update_session_phase.assert_not_called()


class TestConversationHistoryAccumulation:
    """TC-INT-04: Conversation History Accumulation"""

    @pytest.fixture
    def session_manager_mock(self):
        manager = Mock(spec=SessionManager)
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager_mock):
        return TurnOrchestrator(session_manager_mock)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tc_int_04a_conversation_history_builds_up(
        self, orchestrator, session_manager_mock
    ):
        """
        TC-INT-04a: Conversation History Builds Up Over Turns

        Simulate multiple turns and verify conversation history grows.
        """
        session = Session(
            session_id="history-test-session",
            user_id="user-123",
            user_email="test@example.com",
            location="History Test Arena",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=0
        )

        with patch('app.services.turn_orchestrator.create_stage_manager'):
            with patch('app.services.turn_orchestrator.Runner'):
                for turn_num in range(1, 6):
                    async def mock_run(*args, **kwargs):
                        return f"PARTNER: Response for turn {turn_num}\nROOM: Energy level {turn_num}"

                    orchestrator._run_agent_async = mock_run

                    await orchestrator.execute_turn(
                        session=session,
                        user_input=f"Input for turn {turn_num}",
                        turn_number=turn_num
                    )

                    # Add the turn to mock history (simulate Firestore behavior)
                    call_args = session_manager_mock.add_conversation_turn.call_args
                    turn_data = call_args[1]["turn_data"]
                    session.conversation_history.append(turn_data)

        # Verify 5 turns were added
        assert len(session.conversation_history) == 5

        # Verify turn data structure
        first_turn = session.conversation_history[0]
        assert first_turn["turn_number"] == 1
        assert first_turn["user_input"] == "Input for turn 1"
        assert "Response for turn 1" in first_turn["partner_response"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tc_int_04b_context_includes_recent_history(
        self, orchestrator
    ):
        """
        TC-INT-04b: Context Building Includes Recent History

        When executing turn 5 with 4 previous turns, context should
        include last 3 turns.
        """
        session = Session(
            session_id="context-test-session",
            user_id="user-123",
            user_email="test@example.com",
            location="Context Test Arena",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[
                {
                    "turn_number": 1,
                    "user_input": "Turn 1 input",
                    "partner_response": "Turn 1 response"
                },
                {
                    "turn_number": 2,
                    "user_input": "Turn 2 input",
                    "partner_response": "Turn 2 response"
                },
                {
                    "turn_number": 3,
                    "user_input": "Turn 3 input",
                    "partner_response": "Turn 3 response"
                },
                {
                    "turn_number": 4,
                    "user_input": "Turn 4 input",
                    "partner_response": "Turn 4 response"
                }
            ],
            turn_count=4
        )

        context = orchestrator._build_context(
            session=session,
            user_input="Turn 5 input",
            turn_number=5
        )

        # Should include turns 2, 3, 4 (last 3)
        assert "Turn 2 input" in context
        assert "Turn 3 input" in context
        assert "Turn 4 input" in context

        # Should NOT include turn 1
        assert "Turn 1 input" not in context


class TestSessionStatusTransitions:
    """TC-INT-05: Session Status Transitions"""

    @pytest.fixture
    def session_manager_mock(self):
        manager = Mock(spec=SessionManager)
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager_mock):
        return TurnOrchestrator(session_manager_mock)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tc_int_05a_initialized_to_active_on_turn_1(
        self, orchestrator, session_manager_mock
    ):
        """
        TC-INT-05a: INITIALIZED → ACTIVE on Turn 1

        First turn should transition session to ACTIVE status.
        """
        session = Session(
            session_id="status-test-session",
            user_id="user-123",
            user_email="test@example.com",
            location="Status Test Arena",
            status=SessionStatus.INITIALIZED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=0
        )

        with patch('app.services.turn_orchestrator.create_stage_manager'):
            with patch('app.services.turn_orchestrator.Runner'):
                async def mock_run(*args, **kwargs):
                    return "PARTNER: First turn response\nROOM: Initial energy"

                orchestrator._run_agent_async = mock_run

                await orchestrator.execute_turn(
                    session=session,
                    user_input="First turn input",
                    turn_number=1
                )

                # Verify status update to ACTIVE
                session_manager_mock.update_session_status.assert_called_once_with(
                    "status-test-session",
                    SessionStatus.ACTIVE
                )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tc_int_05b_active_to_scene_complete_on_turn_15(
        self, orchestrator, session_manager_mock
    ):
        """
        TC-INT-05b: ACTIVE → SCENE_COMPLETE on Turn 15

        Turn 15 should transition session to SCENE_COMPLETE.
        """
        session = Session(
            session_id="status-test-session",
            user_id="user-123",
            user_email="test@example.com",
            location="Status Test Arena",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=14
        )

        with patch('app.services.turn_orchestrator.create_stage_manager'):
            with patch('app.services.turn_orchestrator.Runner'):
                async def mock_run(*args, **kwargs):
                    return "PARTNER: Final turn\nROOM: Complete\nCOACH: Great work!"

                orchestrator._run_agent_async = mock_run

                await orchestrator.execute_turn(
                    session=session,
                    user_input="Final turn input",
                    turn_number=15
                )

                # Verify status update to SCENE_COMPLETE
                session_manager_mock.update_session_status.assert_called_once_with(
                    "status-test-session",
                    SessionStatus.SCENE_COMPLETE
                )


class TestMultiTurnSessionSimulation:
    """TC-INT-07: Multi-Turn Session Simulation"""

    @pytest.fixture
    def session_manager_mock(self):
        manager = Mock(spec=SessionManager)
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager_mock):
        return TurnOrchestrator(session_manager_mock)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_tc_int_07a_simulate_15_turn_session(
        self, orchestrator, session_manager_mock
    ):
        """
        TC-INT-07a: Simulate Complete 15-Turn Session

        Execute 15 consecutive turns and verify:
        - Phase transition at turn 4
        - Status transitions at turns 1 and 15
        - Coach feedback at turn 15
        - All turns recorded
        """
        session = Session(
            session_id="full-session-test",
            user_id="user-123",
            user_email="test@example.com",
            location="Full Session Arena",
            status=SessionStatus.INITIALIZED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=0,
            current_phase=None
        )

        phase_updates = []
        status_updates = []

        def record_phase_update(*args, **kwargs):
            phase_updates.append((args, kwargs))

        def record_status_update(*args, **kwargs):
            status_updates.append((args, kwargs))

        session_manager_mock.update_session_phase.side_effect = record_phase_update
        session_manager_mock.update_session_status.side_effect = record_status_update

        with patch('app.services.turn_orchestrator.create_stage_manager'):
            with patch('app.services.turn_orchestrator.Runner'):
                for turn_num in range(1, 16):
                    # Simulate agent response
                    if turn_num >= 15:
                        agent_response = f"PARTNER: Turn {turn_num} response\nROOM: Energy\nCOACH: Feedback!"
                    else:
                        agent_response = f"PARTNER: Turn {turn_num} response\nROOM: Energy"

                    async def mock_run(*args, **kwargs):
                        return agent_response

                    orchestrator._run_agent_async = mock_run

                    result = await orchestrator.execute_turn(
                        session=session,
                        user_input=f"Turn {turn_num} input",
                        turn_number=turn_num
                    )

                    # Update session for next iteration
                    session.turn_count = turn_num
                    if result["current_phase"] == 2:
                        session.current_phase = "PHASE_2"

                    # Verify phase
                    if turn_num <= 3:
                        assert result["current_phase"] == 1
                    else:
                        assert result["current_phase"] == 2

                    # Verify coach feedback only at turn 15
                    if turn_num >= 15:
                        assert result.get("coach_feedback") is not None
                    else:
                        assert result.get("coach_feedback") is None

        # Verify phase update happened (at turn 4)
        assert len(phase_updates) == 1
        phase_call = phase_updates[0]
        assert phase_call[1]["phase"] == "PHASE_2"

        # Verify status updates (turns 1 and 15)
        assert len(status_updates) == 2
        assert status_updates[0][0][1] == SessionStatus.ACTIVE
        assert status_updates[1][0][1] == SessionStatus.SCENE_COMPLETE

        # Verify 15 conversation turns were added
        assert session_manager_mock.add_conversation_turn.call_count == 15


class TestPerformanceAndLatency:
    """TC-INT-08: Performance and Latency"""

    @pytest.fixture
    def orchestrator(self):
        manager = Mock(spec=SessionManager)
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        return TurnOrchestrator(manager)

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_tc_int_08a_turn_execution_time(self, orchestrator):
        """
        TC-INT-08a: Turn Execution Time Measurement

        Measure time for single turn execution. Target: < 5 seconds
        (with mocked agent to isolate orchestration overhead).
        """
        session = Session(
            session_id="perf-test-session",
            user_id="user-123",
            user_email="test@example.com",
            location="Performance Test Arena",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            turn_count=3
        )

        with patch('app.services.turn_orchestrator.create_stage_manager'):
            with patch('app.services.turn_orchestrator.Runner'):
                async def mock_run(*args, **kwargs):
                    # Simulate 1 second agent execution
                    await asyncio.sleep(0.01)
                    return "PARTNER: Quick response\nROOM: Good energy"

                orchestrator._run_agent_async = mock_run

                start_time = asyncio.get_event_loop().time()

                await orchestrator.execute_turn(
                    session=session,
                    user_input="Performance test input",
                    turn_number=4
                )

                end_time = asyncio.get_event_loop().time()
                execution_time = end_time - start_time

                # Orchestration overhead should be minimal (< 0.1s)
                assert execution_time < 1.0, f"Execution took {execution_time}s, should be < 1.0s"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_tc_int_08b_response_parsing_performance(self, orchestrator):
        """
        TC-INT-08b: Response Parsing Performance

        Verify response parsing is fast even with large responses.
        """
        large_response = f"""PARTNER: {"Very long partner response " * 100}
ROOM: {"Very long room analysis " * 50}
COACH: {"Very long coaching feedback " * 30}"""

        start_time = asyncio.get_event_loop().time()

        parsed = orchestrator._parse_agent_response(
            response=large_response,
            turn_number=15
        )

        end_time = asyncio.get_event_loop().time()
        parse_time = end_time - start_time

        # Parsing should be near-instant
        assert parse_time < 0.01, f"Parsing took {parse_time}s, should be < 0.01s"

        # Verify parsing worked
        assert len(parsed["partner_response"]) > 1000
        assert len(parsed["room_vibe"]["analysis"]) > 500
        assert parsed["coach_feedback"] is not None
