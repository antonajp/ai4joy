"""
Real ADK Integration Tests - Week 8 Production Readiness

These tests validate the turn orchestrator with actual ADK execution.
They require real GCP credentials and VertexAI access.

Test Coverage:
- TC-REAL-ADK-01: Basic Turn Execution
- TC-REAL-ADK-02: Phase Transition at Turn 5
- TC-REAL-ADK-03: Coach Feedback at Turn 15
- TC-REAL-ADK-04: Response Parsing with Real Output
- TC-REAL-ADK-05: Timeout Handling
"""

import pytest
import asyncio
from datetime import datetime

from app.services.turn_orchestrator import TurnOrchestrator, create_stage_manager
from app.services.session_manager import SessionManager
from app.models.session import SessionCreate
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService


@pytest.mark.integration
@pytest.mark.skip(reason="Requires real ADK credentials and VertexAI quota")
class TestRealADKExecution:
    """Integration tests for real ADK agent execution"""

    @pytest.fixture
    def session_manager(self):
        """Real session manager with Firestore"""
        return SessionManager()

    @pytest.fixture
    def orchestrator(self, session_manager):
        """Real turn orchestrator"""
        return TurnOrchestrator(session_manager)

    @pytest.fixture
    async def test_session(self, session_manager):
        """Create and cleanup test session"""
        session_data = SessionCreate(
            location="Mars Colony Research Station", user_name="Integration Test User"
        )

        session = await session_manager.create_session(
            user_id="integration_test_user",
            user_email="integration-test@example.com",
            session_data=session_data,
        )

        yield session

        await session_manager.close_session(session.session_id)

    @pytest.mark.asyncio
    async def test_tc_real_adk_01_basic_turn_execution(
        self, orchestrator, test_session
    ):
        """
        TC-REAL-ADK-01: Basic Turn Execution

        Execute a single turn with real ADK agents and verify response structure.
        """
        response = await orchestrator.execute_turn(
            session=test_session,
            user_input="Hello! I'm an astronaut checking the oxygen levels.",
            turn_number=1,
        )

        assert response["partner_response"], "Partner response should not be empty"
        assert len(response["partner_response"]) > 20, "Response should be substantial"
        assert response["room_vibe"]["analysis"], "Room analysis should be present"
        assert response["current_phase"] == 1, "Turn 1 should be Phase 1"
        assert response["coach_feedback"] is None, "No coach before turn 15"
        assert response["turn_number"] == 1
        assert "timestamp" in response

    @pytest.mark.asyncio
    async def test_tc_real_adk_02_phase_transition(self, orchestrator, test_session):
        """
        TC-REAL-ADK-02: Phase Transition at Turn 5

        Verify partner behavior changes between Phase 1 and Phase 2.
        Internal turn 4 = user turn 5 (0-indexed vs 1-indexed).
        """
        responses = []

        user_inputs = [
            "Welcome to the station! I'm Captain Rodriguez.",
            "Let me show you the main control room.",
            "These displays monitor our oxygen production.",
            "We've been running smoothly for 6 months now.",
            "Let's check the water recycling system next.",
            "Have you noticed any unusual readings?",
        ]

        for turn_num, user_input in enumerate(user_inputs, start=1):
            response = await orchestrator.execute_turn(
                session=test_session, user_input=user_input, turn_number=turn_num
            )
            responses.append(response)

            test_session.turn_count = turn_num
            test_session.conversation_history.append(
                {
                    "turn_number": turn_num,
                    "user_input": user_input,
                    "partner_response": response["partner_response"],
                }
            )

            if turn_num == 4:
                test_session.current_phase = "PHASE_2"

        assert all(r["current_phase"] == 1 for r in responses[:4]), (
            "Turns 1-4 should be Phase 1"
        )
        assert all(r["current_phase"] == 2 for r in responses[4:]), (
            "Turns 5-6 should be Phase 2"
        )

        phase2_responses = [r["partner_response"].lower() for r in responses[4:]]
        fallibility_indicators = [
            "wait",
            "but",
            "error",
            "problem",
            "confused",
            "uncertain",
            "not sure",
            "maybe",
            "help",
        ]

        fallibility_found = any(
            indicator in response
            for response in phase2_responses
            for indicator in fallibility_indicators
        )

        assert fallibility_found or len(responses[4]) < len(responses[0]), (
            "Phase 2 should show some fallibility or change in behavior"
        )

    @pytest.mark.asyncio
    async def test_tc_real_adk_03_coach_feedback_at_turn_15(
        self, orchestrator, test_session
    ):
        """
        TC-REAL-ADK-03: Coach Feedback at Turn 15

        Verify coach agent provides feedback starting at turn 15.
        """
        user_inputs = [
            f"This is improv line {i} to build up our scene." for i in range(1, 16)
        ]

        for turn_num, user_input in enumerate(user_inputs, start=1):
            response = await orchestrator.execute_turn(
                session=test_session, user_input=user_input, turn_number=turn_num
            )

            test_session.turn_count = turn_num
            test_session.conversation_history.append(
                {
                    "turn_number": turn_num,
                    "user_input": user_input,
                    "partner_response": response["partner_response"],
                }
            )

            if turn_num == 4:
                test_session.current_phase = "PHASE_2"

            if turn_num < 15:
                assert response["coach_feedback"] is None, (
                    f"No coach feedback before turn 15 (turn {turn_num})"
                )
            else:
                assert response["coach_feedback"] is not None, (
                    "Coach feedback should be present at turn 15+"
                )
                assert len(response["coach_feedback"]) > 50, (
                    "Coach feedback should be substantial"
                )

                feedback_lower = response["coach_feedback"].lower()
                coaching_keywords = [
                    "good",
                    "great",
                    "try",
                    "principle",
                    "improve",
                    "yes-and",
                    "listening",
                    "support",
                    "offer",
                ]
                assert any(word in feedback_lower for word in coaching_keywords), (
                    "Coach feedback should contain coaching language"
                )

    @pytest.mark.asyncio
    async def test_tc_real_adk_04_response_parsing(self, orchestrator, test_session):
        """
        TC-REAL-ADK-04: Response Parsing with Real Output

        Validate parsing logic works with actual ADK agent responses.
        """
        response = await orchestrator.execute_turn(
            session=test_session,
            user_input="Let's start an exciting improv scene together!",
            turn_number=1,
        )

        assert response["partner_response"], "Partner section should be parsed"
        assert isinstance(response["partner_response"], str)

        assert "analysis" in response["room_vibe"], "Room vibe should have analysis"
        assert "energy" in response["room_vibe"], "Room vibe should have energy"

        assert "timestamp" in response
        assert isinstance(response["timestamp"], datetime)

        assert "turn_number" in response
        assert response["turn_number"] == 1

        assert "current_phase" in response
        assert response["current_phase"] in [1, 2]

    @pytest.mark.asyncio
    async def test_tc_real_adk_05_timeout_handling(self, orchestrator):
        """
        TC-REAL-ADK-05: Timeout Handling

        Verify timeout mechanism prevents indefinite hangs.
        """
        from app.config import get_settings

        settings = get_settings()

        stage_manager = create_stage_manager()
        session_service = InMemorySessionService()
        runner = Runner(
            agent=stage_manager,
            app_name=settings.app_name,
            artifact_service=None,
            session_service=session_service,
        )

        with pytest.raises(asyncio.TimeoutError):
            await orchestrator._run_agent_async(
                runner=runner,
                prompt="Test prompt",
                user_id="test_user",
                session_id="test_session",
                timeout=0.001,
            )


@pytest.mark.integration
@pytest.mark.skip(reason="Requires real ADK credentials")
class TestADKResponseStructure:
    """Test ADK response format compliance"""

    @pytest.mark.asyncio
    async def test_adk_response_has_sections(self):
        """Verify ADK responses contain expected section markers"""
        from app.config import get_settings

        settings = get_settings()

        stage_manager = create_stage_manager()
        session_service = InMemorySessionService()
        runner = Runner(
            agent=stage_manager,
            app_name=settings.app_name,
            artifact_service=None,
            session_service=session_service,
        )

        prompt = """Location: Test Arena
Turn 1
User: Hello!

Provide response with PARTNER:, ROOM:, and COACH: sections."""

        orchestrator = TurnOrchestrator(SessionManager())

        response = await orchestrator._run_agent_async(
            runner=runner,
            prompt=prompt,
            user_id="test_user",
            session_id="test_session",
            timeout=30.0,
        )

        assert isinstance(response, str)
        assert len(response) > 0

        assert "PARTNER:" in response or "partner" in response.lower(), (
            "Response should contain partner section marker"
        )

    @pytest.mark.asyncio
    async def test_adk_runner_basic_functionality(self):
        """Basic smoke test for ADK runner setup"""
        from app.config import get_settings
        from google.genai import types

        settings = get_settings()

        stage_manager = create_stage_manager()
        session_service = InMemorySessionService()
        runner = Runner(
            agent=stage_manager,
            app_name=settings.app_name,
            artifact_service=None,
            session_service=session_service,
        )

        assert runner is not None
        assert hasattr(runner, "run_async")

        # Create session for the runner
        await session_service.create_session(
            app_name=settings.app_name,
            user_id="test_user",
            session_id="test_session",
            state={},
        )

        # New API uses run_async with Content object
        new_message = types.Content(
            role="user", parts=[types.Part.from_text(text="Say hello")]
        )

        response_parts = []
        async for event in runner.run_async(
            user_id="test_user", session_id="test_session", new_message=new_message
        ):
            if hasattr(event, "content") and event.content:
                if hasattr(event.content, "parts"):
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_parts.append(part.text)

        result = "".join(response_parts)
        assert isinstance(result, str)
        assert len(result) > 0
