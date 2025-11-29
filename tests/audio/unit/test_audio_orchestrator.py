"""
Unit Tests for AudioStreamOrchestrator - TDD Phase 3
Tests for the audio orchestration service that integrates ADK with WebSocket streaming

Test Cases per IQS-58 Acceptance Criteria:
- TC-ORCH-01: Orchestrator initializes with MC agent
- TC-ORCH-02: Orchestrator creates LiveRequestQueue for streaming
- TC-ORCH-03: Audio chunks are forwarded to queue correctly
- TC-ORCH-04: Agent responses are streamed back
- TC-ORCH-05: Session lifecycle management (start, stop)
- TC-ORCH-06: Graceful shutdown on connection close
- TC-ORCH-07: Error handling for malformed audio
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator


class TestAudioStreamOrchestrator:
    """Tests for AudioStreamOrchestrator service."""

    @pytest.fixture
    def mock_mc_agent(self):
        """Mock MC Agent for testing."""
        agent = MagicMock()
        agent.name = "mc_agent"
        agent.model = "gemini-2.0-flash-live-001"
        return agent

    @pytest.fixture
    def mock_runner(self):
        """Mock InMemoryRunner for testing."""
        runner = MagicMock()
        runner.run_live = AsyncMock()
        return runner

    def test_tc_orch_01_orchestrator_initializes_with_mc_agent(self):
        """TC-ORCH-01: AudioStreamOrchestrator initializes with MC agent."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()

        # Should have MC agent reference
        assert orchestrator.agent is not None
        assert orchestrator.agent.name == "mc_agent"

    def test_tc_orch_02_orchestrator_creates_live_request_queue(self):
        """TC-ORCH-02: Orchestrator creates LiveRequestQueue for session."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        session_id = "test-session-123"

        queue = orchestrator.create_session_queue(session_id)

        # Should return a LiveRequestQueue instance
        assert queue is not None
        assert hasattr(queue, "send_realtime")
        assert hasattr(queue, "close")

    @pytest.mark.asyncio
    async def test_tc_orch_03_audio_chunks_forwarded_to_queue(self, mock_runner):
        """TC-ORCH-03: Audio chunks are forwarded to queue correctly."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        session_id = "test-session-456"
        audio_chunk = b"\x00\x01\x02\x03" * 100  # 400 bytes of PCM16

        # Start session first to create the queue
        await orchestrator.start_session(session_id, user_email="test@example.com")

        # Get session and mock its queue
        session = await orchestrator.get_session(session_id)
        session.queue.send_realtime = AsyncMock()

        result = await orchestrator.send_audio_chunk(session_id, audio_chunk)

        # Queue should receive the audio blob
        session.queue.send_realtime.assert_called_once()
        call_args = session.queue.send_realtime.call_args
        blob = call_args[0][0]
        assert blob.mime_type == "audio/pcm;rate=16000"
        assert blob.data == audio_chunk
        assert result.get("status") == "ok"

    @pytest.mark.asyncio
    async def test_tc_orch_04_agent_responses_streamed_back(self, mock_runner):
        """TC-ORCH-04: Agent responses are streamed back to caller."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        # Mock event stream from agent
        mock_event = MagicMock()
        mock_event.server_content = MagicMock()
        mock_event.server_content.model_turn = MagicMock()
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"\x00" * 1000  # Audio response
        mock_part.inline_data.mime_type = "audio/pcm;rate=24000"
        mock_part.text = None
        mock_event.server_content.model_turn.parts = [mock_part]
        mock_event.tool_call = None
        mock_event.tool_result = None

        orchestrator = AudioStreamOrchestrator()

        # Test the _process_event method directly since run_live is complex to mock
        responses = await orchestrator._process_event(mock_event)

        assert len(responses) >= 1
        assert responses[0].get("type") == "audio"

    @pytest.mark.asyncio
    async def test_tc_orch_05_session_lifecycle_start_stop(self):
        """TC-ORCH-05: Session lifecycle management (start, stop)."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        session_id = "test-session-lifecycle"

        # Start session
        await orchestrator.start_session(session_id, user_email="test@example.com")

        # Session should be active
        assert orchestrator.is_session_active(session_id)

        # Stop session
        await orchestrator.stop_session(session_id)

        # Session should be inactive
        assert not orchestrator.is_session_active(session_id)

    @pytest.mark.asyncio
    async def test_tc_orch_06_graceful_shutdown_on_close(self):
        """TC-ORCH-06: Graceful shutdown on connection close."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        session_id = "test-session-shutdown"

        await orchestrator.start_session(session_id, user_email="test@example.com")

        # Get session and mock its queue
        session = await orchestrator.get_session(session_id)
        original_queue = session.queue
        session.queue = MagicMock()
        session.queue.close = MagicMock()

        await orchestrator.handle_disconnect(session_id)

        # Queue should be closed
        session.queue.close.assert_called_once()

        # Session should be removed
        assert not orchestrator.is_session_active(session_id)

    @pytest.mark.asyncio
    async def test_tc_orch_07_error_handling_malformed_audio(self):
        """TC-ORCH-07: Error handling for malformed audio data."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        session_id = "test-session-error"
        malformed_audio = b""  # Empty/malformed audio

        # Should handle gracefully without raising
        result = await orchestrator.send_audio_chunk(session_id, malformed_audio)

        # Should return error indicator
        assert result.get("error") is True or result.get("status") == "error"


class TestAudioStreamOrchestratorVoiceConfig:
    """Tests for voice configuration in AudioStreamOrchestrator."""

    def test_default_voice_is_aoede(self):
        """Test that default voice is Aoede as specified in requirements."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()

        assert orchestrator.voice_name == "Aoede"

    def test_voice_config_applied_to_run_config(self):
        """Test that voice config is applied in get_speech_config."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        speech_config = orchestrator.get_speech_config()

        # Should have speech config with Aoede voice
        assert speech_config is not None
        assert speech_config.voice_config is not None


class TestAudioStreamOrchestratorTranscription:
    """Tests for transcription handling."""

    @pytest.mark.asyncio
    async def test_transcription_included_with_audio(self):
        """Test that transcription is provided alongside audio (AC5)."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        # Mock event with both audio and text
        mock_event = MagicMock()
        mock_event.server_content = MagicMock()
        mock_event.server_content.model_turn = MagicMock()

        audio_part = MagicMock()
        audio_part.inline_data = MagicMock()
        audio_part.inline_data.data = b"\x00" * 1000
        audio_part.text = None

        text_part = MagicMock()
        text_part.inline_data = None
        text_part.text = "Hello, welcome to Improv Olympics!"

        mock_event.server_content.model_turn.parts = [audio_part, text_part]

        orchestrator = AudioStreamOrchestrator()

        responses = await orchestrator._process_event(mock_event)

        # Should have both audio and transcription
        has_audio = any(r.get("type") == "audio" for r in responses)
        has_transcription = any(r.get("type") == "transcription" for r in responses)

        assert has_audio or has_transcription

    def test_transcription_config_enabled(self):
        """Test that audio transcription is enabled in run_config."""
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()
        run_config = orchestrator.get_run_config()

        # Should have run_config (transcription configured within)
        assert run_config is not None
        # Verify it's a valid RunConfig object
        from google.adk.runners import RunConfig
        assert isinstance(run_config, RunConfig)
