"""
Unit Tests for Turn Orchestrator Service - Week 7 Implementation

Test Coverage:
- TC-TURN-01: Context building from conversation history
- TC-TURN-02: Prompt construction for different turn numbers
- TC-TURN-03: ADK Runner execution and async handling
- TC-TURN-04: Response parsing (PARTNER/ROOM/COACH sections)
- TC-TURN-05: Session state updates
- TC-TURN-06: Error handling for agent failures
- TC-TURN-07: Phase transition logic integration
- TC-TURN-08: Turn count tracking
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.turn_orchestrator import TurnOrchestrator
from app.models.session import Session, SessionStatus


class TestTurnOrchestratorContextBuilding:
    """TC-TURN-01: Context Building from Conversation History"""

    @pytest.fixture
    def session_manager(self):
        """Mock session manager"""
        manager = Mock()
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager):
        """Create TurnOrchestrator instance"""
        return TurnOrchestrator(session_manager)

    @pytest.fixture
    def base_session(self):
        """Create base session for testing"""
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Mars Colony",
            status=SessionStatus.INITIALIZED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0
        )

    def test_tc_turn_01a_empty_history_context(self, orchestrator, base_session):
        """
        TC-TURN-01a: Context Building with Empty History

        When conversation_history is empty, context should only include
        location and current turn number.
        """
        context = orchestrator._build_context(
            session=base_session,
            user_input="Hello, I'm ready to start!",
            turn_number=1
        )

        assert "Location: Mars Colony" in context
        assert "Turn 1" in context
        assert "Recent conversation:" not in context

    def test_tc_turn_01b_populated_history_context(self, orchestrator, base_session):
        """
        TC-TURN-01b: Context Building with Populated History

        When conversation_history has turns, context should include
        last 3 turns for continuity.
        """
        base_session.conversation_history = [
            {
                "turn_number": 1,
                "user_input": "Welcome to Mars!",
                "partner_response": "Thanks! The red rocks are beautiful."
            },
            {
                "turn_number": 2,
                "user_input": "Let's check the oxygen levels.",
                "partner_response": "Good idea, I'll grab the scanner."
            },
            {
                "turn_number": 3,
                "user_input": "The readings look low!",
                "partner_response": "We need to act fast."
            }
        ]

        context = orchestrator._build_context(
            session=base_session,
            user_input="I'll contact mission control",
            turn_number=4
        )

        assert "Location: Mars Colony" in context
        assert "Turn 4" in context
        assert "Recent conversation:" in context
        assert "Welcome to Mars!" in context
        assert "Thanks! The red rocks are beautiful." in context
        assert "Let's check the oxygen levels." in context
        assert "The readings look low!" in context

    def test_tc_turn_01c_context_limits_to_three_turns(self, orchestrator, base_session):
        """
        TC-TURN-01c: Context Only Includes Last 3 Turns

        When history has more than 3 turns, only the most recent 3
        should be included to avoid context bloat.
        """
        base_session.conversation_history = [
            {"turn_number": i, "user_input": f"Input {i}", "partner_response": f"Response {i}"}
            for i in range(1, 8)
        ]

        context = orchestrator._build_context(
            session=base_session,
            user_input="Current input",
            turn_number=8
        )

        # Should include turns 5, 6, 7 (last 3)
        assert "Input 5" in context
        assert "Input 6" in context
        assert "Input 7" in context

        # Should NOT include turns 1-4
        assert "Input 1" not in context
        assert "Input 2" not in context
        assert "Input 3" not in context
        assert "Input 4" not in context


class TestTurnOrchestratorPromptConstruction:
    """TC-TURN-02: Prompt Construction for Different Turn Numbers"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    @pytest.fixture
    def base_session(self):
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Underwater Research Station",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0
        )

    @pytest.mark.asyncio
    async def test_tc_turn_02a_phase1_prompt_construction(self, orchestrator, base_session):
        """
        TC-TURN-02a: Phase 1 Prompt Construction (Turns 1-3)

        Prompt should indicate Phase 1 (Supportive) and NOT include
        Coach agent instruction.
        """
        prompt = await orchestrator._construct_scene_prompt(
            session=base_session,
            user_input="Let's explore this coral reef!",
            turn_number=2
        )

        assert "Scene Turn 2" in prompt
        assert "Phase 1 (Supportive)" in prompt
        assert "Underwater Research Station" in prompt
        assert "Let's explore this coral reef!" in prompt
        assert "Partner Agent: Respond to user's scene contribution" in prompt
        assert "Room Agent: Analyze scene energy" in prompt

        # Should NOT include coach in Phase 1 early turns
        assert "Coach Agent" not in prompt

    @pytest.mark.asyncio
    async def test_tc_turn_02b_phase2_prompt_construction(self, orchestrator, base_session):
        """
        TC-TURN-02b: Phase 2 Prompt Construction (Turns 4+)

        Prompt should indicate Phase 2 (Fallible) at turn 4 and beyond.
        """
        prompt = await orchestrator._construct_scene_prompt(
            session=base_session,
            user_input="We need to repair the hull breach!",
            turn_number=5
        )

        assert "Scene Turn 5" in prompt
        assert "Phase 2 (Fallible)" in prompt
        assert "Underwater Research Station" in prompt
        assert "We need to repair the hull breach!" in prompt

    @pytest.mark.asyncio
    async def test_tc_turn_02c_coach_inclusion_at_turn_15(self, orchestrator, base_session):
        """
        TC-TURN-02c: Coach Agent Included at Turn 15+

        Coach feedback should be requested starting at turn 15.
        """
        prompt = await orchestrator._construct_scene_prompt(
            session=base_session,
            user_input="Final scene action",
            turn_number=15
        )

        assert "Coach Agent: Provide constructive feedback" in prompt
        assert "COACH:" in prompt

    @pytest.mark.asyncio
    async def test_tc_turn_02d_coach_not_included_before_turn_15(self, orchestrator, base_session):
        """
        TC-TURN-02d: No Coach Before Turn 15

        Coach should NOT be mentioned in turns 1-14.
        """
        for turn in [1, 5, 10, 14]:
            prompt = await orchestrator._construct_scene_prompt(
                session=base_session,
                user_input="Scene input",
                turn_number=turn
            )

            assert "Coach Agent" not in prompt, f"Coach should not appear in turn {turn}"


class TestTurnOrchestratorResponseParsing:
    """TC-TURN-04: Response Parsing for PARTNER/ROOM/COACH Sections"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    def test_tc_turn_04a_parse_complete_structured_response(self, orchestrator):
        """
        TC-TURN-04a: Parse Complete Structured Response

        When agent returns properly formatted response with all sections,
        parsing should extract each component correctly.
        """
        agent_response = """PARTNER: Great idea! Let's check the oxygen levels together. I'll grab the analyzer from the storage bay.

ROOM: The audience is leaning forward, clearly engaged by the building tension around the oxygen crisis. Energy level: High.

COACH: Nice work establishing clear stakes and collaborative action. Remember to keep building on each other's offers."""

        parsed = orchestrator._parse_agent_response(
            response=agent_response,
            turn_number=15
        )

        assert parsed["partner_response"] == "Great idea! Let's check the oxygen levels together. I'll grab the analyzer from the storage bay."
        assert "leaning forward" in parsed["room_vibe"]["analysis"]
        assert parsed["room_vibe"]["energy"] == "engaged"
        assert parsed["coach_feedback"] is not None
        assert "Nice work" in parsed["coach_feedback"]
        assert parsed["current_phase"] == 2  # Turn 15 is Phase 2

    def test_tc_turn_04b_parse_missing_sections_fallback(self, orchestrator):
        """
        TC-TURN-04b: Fallback When Sections Missing

        If response doesn't include structured markers, system should
        use fallback defaults.
        """
        agent_response = "Just a plain text response without sections"

        parsed = orchestrator._parse_agent_response(
            response=agent_response,
            turn_number=3
        )

        # Should use entire response as partner response
        assert parsed["partner_response"] == "Just a plain text response without sections"

        # Should use default room vibe
        assert "engaged" in parsed["room_vibe"]["analysis"].lower()
        assert parsed["room_vibe"]["energy"] == "positive"

        # No coach feedback before turn 15
        assert parsed["coach_feedback"] is None
        assert parsed["current_phase"] == 1  # Turn 3 is Phase 1

    def test_tc_turn_04c_parse_partial_sections(self, orchestrator):
        """
        TC-TURN-04c: Parse Partial Sections

        If only PARTNER section exists, should extract it and use
        defaults for others.
        """
        agent_response = "PARTNER: Let's do this! I'm ready to start the scene."

        parsed = orchestrator._parse_agent_response(
            response=agent_response,
            turn_number=2
        )

        assert parsed["partner_response"] == "Let's do this! I'm ready to start the scene."
        assert parsed["room_vibe"]["analysis"]  # Should have default
        assert parsed["coach_feedback"] is None

    def test_tc_turn_04d_parse_coach_only_after_turn_15(self, orchestrator):
        """
        TC-TURN-04d: Coach Parsing Only After Turn 15

        Coach section should only be parsed if turn >= 15, even if
        present in response.
        """
        agent_response = """PARTNER: Scene response.
ROOM: Good energy.
COACH: Great work!"""

        # Turn 10: Coach should be ignored
        parsed_10 = orchestrator._parse_agent_response(
            response=agent_response,
            turn_number=10
        )
        assert parsed_10["coach_feedback"] is None

        # Turn 15: Coach should be parsed
        parsed_15 = orchestrator._parse_agent_response(
            response=agent_response,
            turn_number=15
        )
        assert parsed_15["coach_feedback"] == "Great work!"

    def test_tc_turn_04e_timestamp_and_turn_number_included(self, orchestrator):
        """
        TC-TURN-04e: Timestamp and Turn Number in Response

        Parsed response should include turn number and timestamp.
        """
        parsed = orchestrator._parse_agent_response(
            response="PARTNER: Test response",
            turn_number=7
        )

        assert parsed["turn_number"] == 7
        assert "timestamp" in parsed
        assert isinstance(parsed["timestamp"], datetime)


class TestTurnOrchestratorSessionStateUpdates:
    """TC-TURN-05: Session State Updates"""

    @pytest.fixture
    def session_manager(self):
        manager = Mock()
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        manager.update_session_atomic = AsyncMock()
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager):
        return TurnOrchestrator(session_manager)

    @pytest.fixture
    def base_session(self):
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Space Station",
            status=SessionStatus.INITIALIZED,
            current_phase="PHASE_1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0
        )

    @pytest.mark.asyncio
    async def test_tc_turn_05a_conversation_history_updated(
        self, orchestrator, session_manager, base_session
    ):
        """
        TC-TURN-05a: Conversation Turn Added to History

        After turn execution, turn data should be added to conversation history.
        """
        turn_response = {
            "turn_number": 3,
            "partner_response": "Great scene work!",
            "room_vibe": {"analysis": "High energy", "energy": "engaged"},
            "current_phase": 1,
            "timestamp": datetime.now(timezone.utc),
            "coach_feedback": None
        }

        await orchestrator._update_session_after_turn(
            session=base_session,
            user_input="Let's continue the scene",
            turn_response=turn_response,
            turn_number=3
        )

        session_manager.update_session_atomic.assert_called_once()
        call_args = session_manager.update_session_atomic.call_args

        assert call_args[1]["session_id"] == "test-session-123"
        turn_data = call_args[1]["turn_data"]
        assert turn_data["turn_number"] == 3
        assert turn_data["user_input"] == "Let's continue the scene"
        assert turn_data["partner_response"] == "Great scene work!"
        assert turn_data["phase"] == "Phase 1"

    @pytest.mark.asyncio
    async def test_tc_turn_05b_phase_transition_persisted(
        self, orchestrator, session_manager, base_session
    ):
        """
        TC-TURN-05b: Phase Transition Persisted to Firestore

        When phase changes (turn 4), new phase should be persisted.
        """
        base_session.current_phase = "PHASE_1"

        turn_response = {
            "turn_number": 4,
            "partner_response": "Scene continues",
            "room_vibe": {"analysis": "Good", "energy": "engaged"},
            "current_phase": 2,  # Phase transition!
            "timestamp": datetime.now(timezone.utc)
        }

        await orchestrator._update_session_after_turn(
            session=base_session,
            user_input="Turn 4 input",
            turn_response=turn_response,
            turn_number=4
        )

        session_manager.update_session_atomic.assert_called_once()
        call_args = session_manager.update_session_atomic.call_args
        assert call_args[1]["new_phase"] == "PHASE_2"

    @pytest.mark.asyncio
    async def test_tc_turn_05c_status_transitions_turn_1(
        self, orchestrator, session_manager, base_session
    ):
        """
        TC-TURN-05c: Status Transition on Turn 1 (INITIALIZED → ACTIVE)

        First turn should transition session from INITIALIZED to ACTIVE.
        """
        base_session.status = SessionStatus.INITIALIZED

        turn_response = {
            "turn_number": 1,
            "partner_response": "Welcome!",
            "room_vibe": {"analysis": "Good", "energy": "engaged"},
            "current_phase": 1,
            "timestamp": datetime.now(timezone.utc)
        }

        await orchestrator._update_session_after_turn(
            session=base_session,
            user_input="First input",
            turn_response=turn_response,
            turn_number=1
        )

        session_manager.update_session_atomic.assert_called_once()
        call_args = session_manager.update_session_atomic.call_args
        assert call_args[1]["new_status"] == SessionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_tc_turn_05d_status_transitions_turn_15(
        self, orchestrator, session_manager, base_session
    ):
        """
        TC-TURN-05d: Status Transition on Turn 15 (ACTIVE → SCENE_COMPLETE)

        Turn 15 or later should transition to SCENE_COMPLETE.
        """
        base_session.status = SessionStatus.ACTIVE

        turn_response = {
            "turn_number": 15,
            "partner_response": "Scene ending",
            "room_vibe": {"analysis": "Complete", "energy": "satisfied"},
            "current_phase": 2,
            "timestamp": datetime.now(timezone.utc),
            "coach_feedback": "Great work!"
        }

        await orchestrator._update_session_after_turn(
            session=base_session,
            user_input="Final input",
            turn_response=turn_response,
            turn_number=15
        )

        session_manager.update_session_atomic.assert_called_once()
        call_args = session_manager.update_session_atomic.call_args
        assert call_args[1]["new_status"] == SessionStatus.SCENE_COMPLETE

    @pytest.mark.asyncio
    async def test_tc_turn_05e_coach_feedback_included_when_present(
        self, orchestrator, session_manager, base_session
    ):
        """
        TC-TURN-05e: Coach Feedback Included in Turn Data

        When coach feedback exists, it should be included in turn data.
        """
        turn_response = {
            "turn_number": 15,
            "partner_response": "Scene work",
            "room_vibe": {"analysis": "Good", "energy": "engaged"},
            "current_phase": 2,
            "timestamp": datetime.now(timezone.utc),
            "coach_feedback": "Excellent use of Yes-And principle!"
        }

        await orchestrator._update_session_after_turn(
            session=base_session,
            user_input="Input",
            turn_response=turn_response,
            turn_number=15
        )

        session_manager.update_session_atomic.assert_called_once()
        call_args = session_manager.update_session_atomic.call_args
        turn_data = call_args[1]["turn_data"]

        assert "coach_feedback" in turn_data
        assert turn_data["coach_feedback"] == "Excellent use of Yes-And principle!"


class TestTurnOrchestratorErrorHandling:
    """TC-TURN-06: Error Handling for Agent Failures"""

    @pytest.fixture
    def session_manager(self):
        manager = Mock()
        manager.add_conversation_turn = AsyncMock()
        manager.update_session_phase = AsyncMock()
        manager.update_session_status = AsyncMock()
        manager.update_session_atomic = AsyncMock()
        # Mock get_adk_session to return a mock ADK session
        mock_adk_session = Mock()
        mock_adk_session.events = []
        manager.get_adk_session = AsyncMock(return_value=mock_adk_session)
        return manager

    @pytest.fixture
    def orchestrator(self, session_manager):
        return TurnOrchestrator(session_manager)

    @pytest.fixture
    def base_session(self):
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Mars",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=3
        )

    @pytest.mark.asyncio
    async def test_tc_turn_06a_agent_execution_failure(
        self, orchestrator, base_session
    ):
        """
        TC-TURN-06a: Agent Execution Failure Raises Exception

        When ADK Runner fails, error should be logged and re-raised.
        """
        with patch('app.services.turn_orchestrator.create_stage_manager'):
            with patch('app.services.turn_orchestrator.Runner') as mock_runner:
                # Simulate runner failure
                mock_runner_instance = Mock()
                mock_runner.return_value = mock_runner_instance

                async def failing_run(*args, **kwargs):
                    raise RuntimeError("ADK execution failed")

                # Patch the async run method
                with patch.object(orchestrator, '_run_agent_async', side_effect=failing_run):
                    with pytest.raises(RuntimeError, match="ADK execution failed"):
                        await orchestrator.execute_turn(
                            session=base_session,
                            user_input="Test input",
                            turn_number=4
                        )

    @pytest.mark.asyncio
    async def test_tc_turn_06b_malformed_response_handling(
        self, orchestrator
    ):
        """
        TC-TURN-06b: Malformed Response Handled Gracefully

        If agent returns unexpected format, parser should use fallbacks
        without crashing. Empty responses raise ValueError.
        """
        with pytest.raises(ValueError, match="Partner response cannot be empty"):
            orchestrator._parse_agent_response(
                response="",
                turn_number=5
            )

        parsed = orchestrator._parse_agent_response(
            response="###INVALID_FORMAT###",
            turn_number=5
        )
        assert parsed["partner_response"] == "###INVALID_FORMAT###"
        assert "room_vibe" in parsed

    @pytest.mark.asyncio
    async def test_tc_turn_06c_firestore_update_failure(
        self, orchestrator, session_manager, base_session
    ):
        """
        TC-TURN-06c: Firestore Update Failure Raises Exception

        If session update fails, error should be propagated.
        """
        session_manager.update_session_atomic.side_effect = Exception("Firestore error")

        turn_response = {
            "turn_number": 5,
            "partner_response": "Response",
            "room_vibe": {"analysis": "Good", "energy": "engaged"},
            "current_phase": 2,
            "timestamp": datetime.now(timezone.utc)
        }

        with pytest.raises(Exception, match="Firestore error"):
            await orchestrator._update_session_after_turn(
                session=base_session,
                user_input="Input",
                turn_response=turn_response,
                turn_number=5
            )


class TestTurnOrchestratorPhaseIntegration:
    """TC-TURN-07: Phase Transition Logic Integration"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    @pytest.fixture
    def base_session(self):
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Laboratory",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0
        )

    @pytest.mark.asyncio
    async def test_tc_turn_07a_phase_1_for_turns_1_to_4(self, orchestrator, base_session):
        """
        TC-TURN-07a: Phase 1 for Turns 1-4

        User turns 1, 2, 3, 4 should use Phase 1 (Supportive).
        Internal turn_count is turn_number - 1, so turns 0-3 are Phase 1.
        """
        for turn in [1, 2, 3, 4]:
            prompt = await orchestrator._construct_scene_prompt(
                session=base_session,
                user_input="Test",
                turn_number=turn
            )
            assert "Phase 1 (Supportive)" in prompt

            parsed = orchestrator._parse_agent_response(
                response="PARTNER: Test",
                turn_number=turn
            )
            assert parsed["current_phase"] == 1

    @pytest.mark.asyncio
    async def test_tc_turn_07b_phase_2_from_turn_5_onwards(self, orchestrator, base_session):
        """
        TC-TURN-07b: Phase 2 from Turn 5 Onwards

        User turn 5 and beyond should use Phase 2 (Fallible).
        Internal turn_count is turn_number - 1, so turn_count 4+ is Phase 2.
        """
        for turn in [5, 6, 10, 15]:
            prompt = await orchestrator._construct_scene_prompt(
                session=base_session,
                user_input="Test",
                turn_number=turn
            )
            assert "Phase 2 (Fallible)" in prompt

            parsed = orchestrator._parse_agent_response(
                response="PARTNER: Test",
                turn_number=turn
            )
            assert parsed["current_phase"] == 2


class TestTurnOrchestratorAsyncExecution:
    """TC-TURN-03: ADK Runner Execution and Async Handling"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    @pytest.mark.asyncio
    async def test_tc_turn_03a_uses_singleton_runner(self, orchestrator):
        """
        TC-TURN-03a: Turn Orchestrator Uses Singleton Runner

        The orchestrator should use the singleton Runner via get_singleton_runner(),
        not create a new Runner per request.

        This ensures:
        - Better performance (no Runner recreation overhead)
        - Sessions persist across Cloud Run instance restarts via shared session service
        """
        from app.services.turn_orchestrator import get_singleton_runner, reset_runner

        with patch('app.services.turn_orchestrator.get_adk_session_service') as mock_get_service:
            with patch('app.services.turn_orchestrator.Runner') as mock_runner_class:
                with patch('app.services.turn_orchestrator.create_stage_manager') as mock_create_stage:
                    reset_runner()

                    mock_session_service = Mock()
                    mock_get_service.return_value = mock_session_service

                    mock_stage_manager = Mock()
                    mock_create_stage.return_value = mock_stage_manager

                    mock_runner_instance = Mock()
                    mock_runner_class.return_value = mock_runner_instance

                    async def mock_run_async(*args, **kwargs):
                        yield {
                            "type": "final",
                            "content": "PARTNER: Test response"
                        }

                    mock_runner_instance.run_async = mock_run_async

                    runner1 = get_singleton_runner()
                    runner2 = get_singleton_runner()

                    assert runner1 is runner2, "Singleton Runner should return same instance"

                    mock_runner_class.assert_called_once()
                    call_args = mock_runner_class.call_args
                    assert call_args[1]['session_service'] is mock_session_service

                    reset_runner()

    @pytest.mark.asyncio
    async def test_tc_turn_03b_execute_turn_uses_singleton_runner(self):
        """
        TC-TURN-03b: execute_turn Uses Singleton Runner

        The execute_turn method should get the singleton Runner via
        get_singleton_runner(), not create a new Runner each call.
        """

        session_manager = Mock()
        session_manager.update_session_atomic = AsyncMock()
        # Mock get_adk_session to return a mock ADK session
        mock_adk_session = Mock()
        mock_adk_session.events = []
        session_manager.get_adk_session = AsyncMock(return_value=mock_adk_session)

        orchestrator = TurnOrchestrator(session_manager)

        with patch('app.services.turn_orchestrator.get_singleton_runner') as mock_get_runner:
            mock_runner = Mock()

            async def mock_run_async(*args, **kwargs):
                mock_event = Mock()
                mock_event.content = Mock()
                mock_event.content.parts = [Mock(text="PARTNER: Test response\nROOM: Good energy")]
                yield mock_event

            mock_runner.run_async = mock_run_async
            mock_get_runner.return_value = mock_runner

            session = Session(
                session_id="test-session",
                user_id="user-123",
                user_email="test@example.com",
                location="Test Location",
                status=SessionStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc),
                conversation_history=[],
                turn_count=0,
                current_phase="PHASE_1"
            )

            await orchestrator.execute_turn(
                session=session,
                user_input="Test input",
                turn_number=1
            )

            mock_get_runner.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Test needs to be rewritten for new ADK run_async API")
    async def test_tc_turn_03c_runner_timeout_handling(self, orchestrator):
        """
        TC-TURN-03c: Long-Running Agent Execution

        Note: The ADK Runner API has changed to use async run_async().
        Timeout handling is now done by wrapping the async generator iteration.
        """
        pass


class TestTurnOrchestratorEdgeCases:
    """TC-TURN-08: Edge Cases and Boundary Conditions"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    @pytest.fixture
    def base_session(self):
        return Session(
            session_id="test-session-123",
            user_id="user-456",
            user_email="test@example.com",
            location="Edge Case Arena",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc),
            conversation_history=[],
            turn_count=0
        )

    @pytest.mark.asyncio
    async def test_tc_turn_08a_very_long_user_input(self, orchestrator, base_session):
        """
        TC-TURN-08a: Very Long User Input (1000 chars)

        System should handle maximum length user input (1000 chars).
        """
        long_input = "A" * 1000

        prompt = await orchestrator._construct_scene_prompt(
            session=base_session,
            user_input=long_input,
            turn_number=5
        )

        assert long_input in prompt
        assert len(prompt) > 1000

    @pytest.mark.asyncio
    async def test_tc_turn_08b_special_characters_in_input(self, orchestrator, base_session):
        """
        TC-TURN-08b: Special Characters in User Input

        User input with special characters should be handled correctly.
        """
        special_input = 'Test with "quotes" and <tags> and & symbols!'

        prompt = await orchestrator._construct_scene_prompt(
            session=base_session,
            user_input=special_input,
            turn_number=2
        )

        assert special_input in prompt

    def test_tc_turn_08c_empty_location(self, orchestrator, base_session):
        """
        TC-TURN-08c: Empty Location String

        Even with empty location, system should not crash.
        """
        base_session.location = ""

        context = orchestrator._build_context(
            session=base_session,
            user_input="Test",
            turn_number=1
        )

        assert "Location:" in context

    def test_tc_turn_08d_response_with_multiple_colons(self, orchestrator):
        """
        TC-TURN-08d: Response with Multiple Section Markers

        If response has duplicate markers, parser should handle gracefully.
        """
        confusing_response = """PARTNER: First response
PARTNER: Wait, second response
ROOM: Confused energy
ROOM: Actually good energy"""

        parsed = orchestrator._parse_agent_response(
            response=confusing_response,
            turn_number=5
        )

        # Should parse first occurrence
        assert "First response" in parsed["partner_response"]
        assert "room_vibe" in parsed
