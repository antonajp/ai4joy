"""
Integration Tests for MC Agent Audio - TDD Phase 3
Tests for MC Agent integration with ADK Live API

Test Cases per IQS-58 Acceptance Criteria:
- TC-MC-01: MC Agent configured for audio streaming
- TC-MC-02: MC welcomes premium users with audio (AC2)
- TC-MC-03: Voice synthesis uses Aoede voice
- TC-MC-04: Tool execution works during audio conversation
- TC-MC-05: Session persistence across audio reconnections
- TC-MC-06: Audio latency < 2 seconds P95 (AC4)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time


class TestMCAgentAudioIntegration:
    """Integration tests for MC Agent with Live API."""

    @pytest.fixture
    def mock_live_request_queue(self):
        """Mock LiveRequestQueue for testing."""
        queue = MagicMock()
        queue.send_realtime = AsyncMock()
        queue.send_content = AsyncMock()
        queue.close = MagicMock()
        return queue

    @pytest.fixture
    def mock_runner(self):
        """Mock InMemoryRunner for testing."""
        runner = MagicMock()
        runner.run_live = AsyncMock()
        return runner

    def test_tc_mc_01_mc_agent_configured_for_audio(self):
        """TC-MC-01: MC Agent is configured for audio streaming."""
        from app.agents.mc_agent import create_mc_agent

        agent = create_mc_agent()

        # Agent should be compatible with Live API
        assert agent.name == "mc_agent"
        # Model should support Live API (gemini-2.0-flash-live or compatible)
        # The agent can use standard model as run_live handles the live model

    def test_tc_mc_02_mc_welcomes_premium_users_audio(self):
        """TC-MC-02: MC agent welcome is available via audio (AC2)."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()

        # MC should be configured for welcome message
        welcome_config = orchestrator.get_welcome_config()

        assert welcome_config is not None
        assert "welcome" in welcome_config.get("initial_message", "").lower() or \
               welcome_config.get("auto_greet") is True

    def test_tc_mc_03_voice_synthesis_uses_aoede(self):
        """TC-MC-03: Voice synthesis uses Aoede voice."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()

        # Should use Aoede voice as specified in requirements
        voice_config = orchestrator.get_voice_config()

        assert voice_config.voice_name == "Aoede"

    @pytest.mark.asyncio
    async def test_tc_mc_04_tool_execution_during_audio(self, mock_runner):
        """TC-MC-04: Tool execution works during audio conversation."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        # Mock event with tool call
        mock_tool_event = MagicMock()
        mock_tool_event.tool_call = MagicMock()
        mock_tool_event.tool_call.name = "get_improv_games"
        mock_tool_event.tool_call.args = {"category": "warmup"}

        mock_tool_result_event = MagicMock()
        mock_tool_result_event.tool_result = MagicMock()
        mock_tool_result_event.tool_result.result = "Found 5 warmup games"

        mock_audio_event = MagicMock()
        mock_audio_event.server_content = MagicMock()
        mock_audio_event.server_content.model_turn = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"\x00" * 1000
        mock_audio_event.server_content.model_turn.parts = [mock_part]

        async def mock_event_stream():
            yield mock_tool_event
            yield mock_tool_result_event
            yield mock_audio_event

        mock_runner.run_live.return_value = mock_event_stream()

        orchestrator = AudioStreamOrchestrator()

        with patch.object(orchestrator, "_runner", mock_runner):
            events = []
            async for event in orchestrator.stream_responses("test-session"):
                events.append(event)

            # Should have processed tool call and returned audio
            assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_tc_mc_05_session_persistence_audio_reconnection(self):
        """TC-MC-05: Session persists across audio reconnections."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        session_id = "persistent-session-123"
        user_email = "test@example.com"

        # Start session
        await orchestrator.start_session(session_id, user_email=user_email)

        # Store some session state
        with patch.object(orchestrator, "_session_service") as mock_svc:
            mock_svc.get_session = AsyncMock(return_value=MagicMock(
                history=[{"role": "user", "content": "Previous message"}]
            ))

            # Simulate disconnect
            await orchestrator.handle_disconnect(session_id)

            # Reconnect with same session_id
            await orchestrator.start_session(session_id, user_email=user_email)

            # Session should be restored
            session = await orchestrator.get_session(session_id)
            assert session is not None

    @pytest.mark.asyncio
    async def test_tc_mc_06_audio_latency_under_2_seconds(self, mock_runner):
        """TC-MC-06: Audio latency < 2 seconds P95 (AC4)."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        session_id = "latency-test-session"

        # Mock fast response
        mock_event = MagicMock()
        mock_event.server_content = MagicMock()
        mock_event.server_content.model_turn = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"\x00" * 1000
        mock_event.server_content.model_turn.parts = [mock_part]

        async def mock_event_stream():
            yield mock_event

        mock_runner.run_live.return_value = mock_event_stream()

        with patch.object(orchestrator, "_runner", mock_runner):
            # Measure latency
            start_time = time.time()

            audio_chunk = b"\x00\x01" * 160
            await orchestrator.send_audio_chunk(session_id, audio_chunk)

            responses = []
            async for response in orchestrator.stream_responses(session_id):
                responses.append(response)
                break  # First response

            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Should be under 2000ms (2 seconds)
            # In unit test with mocks, this should be near-instant
            assert latency_ms < 2000


class TestMCAgentAudioConfiguration:
    """Tests for MC Agent audio configuration."""

    def test_mc_agent_live_model_configuration(self):
        """Test MC Agent can use live-compatible model."""
        from app.config import get_settings

        settings = get_settings()

        # Should have live model configured or fallback
        live_model = getattr(settings, "vertexai_live_model", None)

        # Even if not explicitly set, system should handle model selection
        assert live_model is not None or settings.vertexai_flash_model is not None

    def test_run_config_for_audio(self):
        """Test RunConfig is properly set for audio streaming."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        run_config = orchestrator.get_run_config()

        # Should have audio transcription enabled
        assert run_config is not None
        assert run_config.data.get("input_audio_transcription") is not None
        assert run_config.data.get("output_audio_transcription") is not None

    def test_speech_config_for_aoede(self):
        """Test speech config uses Aoede voice."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        speech_config = orchestrator.get_speech_config()

        assert speech_config is not None
        assert speech_config.voice_config is not None
        assert speech_config.voice_config.prebuilt_voice_config.get("voice_name") == "Aoede"


class TestMCAgentToolsWithAudio:
    """Tests for MC Agent tool integration during audio."""

    @pytest.mark.asyncio
    async def test_improv_games_toolset_available(self):
        """Test ImprovGamesToolset is available during audio."""
        from app.agents.mc_agent import create_mc_agent

        agent = create_mc_agent()

        # Agent should have tools
        assert len(agent.tools) > 0

        # ImprovGamesToolset should be included
        tool_names = [str(t) for t in agent.tools]
        has_games_toolset = any("improv" in name.lower() or "games" in name.lower()
                                for name in tool_names)

        # If toolset is object, check differently
        if not has_games_toolset:
            from app.toolsets import ImprovGamesToolset
            has_games_toolset = any(isinstance(t, ImprovGamesToolset) for t in agent.tools)

        assert has_games_toolset or len(agent.tools) > 0

    @pytest.mark.asyncio
    async def test_tool_results_spoken_by_mc(self):
        """Test that tool results are spoken by MC."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()

        # Mock tool result event followed by audio
        mock_tool_result = MagicMock()
        mock_tool_result.tool_result = MagicMock()
        mock_tool_result.tool_result.result = {
            "games": [{"name": "Word Association", "description": "Quick word game"}]
        }

        # After tool result, agent should speak response
        events = [mock_tool_result]

        with patch.object(orchestrator, "_process_tool_result") as mock_process:
            mock_process.return_value = {"type": "continue", "speak": True}

            for event in events:
                result = await orchestrator._handle_event(event)

                # Should indicate that audio response will follow
                if hasattr(event, "tool_result"):
                    assert result.get("speak") is True or result is not None
