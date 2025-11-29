"""
Unit Tests for WebSocket Audio Handler - TDD Phase 3
Tests for the production WebSocket handler with ADK Live API integration

Test Cases per IQS-58 Acceptance Criteria:
- TC-WS-01: WebSocket endpoint accepts authenticated connections (AC1)
- TC-WS-02: OAuth session token authentication works
- TC-WS-03: Bidirectional audio streaming (PCM16 @ 16kHz input)
- TC-WS-04: Handle connection lifecycle (open, message, close, error) (AC6)
- TC-WS-05: Audio output is 24kHz PCM (per ADK research)
- TC-WS-06: Graceful error handling (network drops, codec errors) (AC6)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import base64


class TestWebSocketHandler:
    """Tests for AudioWebSocketHandler production implementation."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.receive_bytes = AsyncMock()
        ws.send_bytes = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.fixture
    def mock_user_profile(self):
        """Create mock premium user profile."""
        from app.models.user import UserProfile, UserTier

        return UserProfile(
            user_id="test-user-123",
            email="test@example.com",
            tier=UserTier.PREMIUM,
            audio_usage_seconds=0,
        )

    @pytest.mark.asyncio
    async def test_tc_ws_01_accepts_authenticated_connections(
        self, mock_websocket, mock_user_profile
    ):
        """TC-WS-01: WebSocket endpoint accepts authenticated connections (AC1)."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()
        session_id = "authenticated-session-123"

        with patch.object(handler, "validate_authentication") as mock_auth:
            mock_auth.return_value = mock_user_profile

            result = await handler.connect(
                mock_websocket, session_id, auth_token="valid-token"
            )

            assert result is True
            mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_tc_ws_02_oauth_session_authentication(self, mock_websocket):
        """TC-WS-02: OAuth session token authentication works."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()

        with patch("app.middleware.oauth_auth.validate_session_token") as mock_validate:
            mock_validate.return_value = {"email": "test@example.com", "user_id": "123"}

            with patch("app.services.user_service.get_user_by_email") as mock_get:
                from app.models.user import UserProfile, UserTier

                mock_get.return_value = UserProfile(
                    user_id="123",
                    email="test@example.com",
                    tier=UserTier.PREMIUM,
                )

                result = await handler.validate_authentication("valid-oauth-token")

                assert result is not None
                assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_tc_ws_03_bidirectional_audio_streaming(
        self, mock_websocket, mock_user_profile
    ):
        """TC-WS-03: Bidirectional audio streaming (PCM16 @ 16kHz input)."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()
        session_id = "streaming-session-123"

        # Simulate PCM16 audio at 16kHz (320 bytes = 10ms of audio)
        input_audio = b"\x00\x01" * 160  # 320 bytes PCM16

        # Mock orchestrator to return audio response
        with patch.object(handler, "orchestrator") as mock_orch:
            mock_orch.send_audio_chunk = AsyncMock(return_value={"status": "ok"})

            async def mock_stream():
                yield {"type": "audio", "data": b"\x00" * 480}  # 24kHz response

            mock_orch.stream_responses = MagicMock(return_value=mock_stream())

            # Process incoming audio
            await handler.process_audio_message(session_id, input_audio)

            # Should forward to orchestrator
            mock_orch.send_audio_chunk.assert_called_once()
            call_args = mock_orch.send_audio_chunk.call_args
            assert call_args[0][1] == input_audio

    @pytest.mark.asyncio
    async def test_tc_ws_04_connection_lifecycle(self, mock_websocket, mock_user_profile):
        """TC-WS-04: Handle connection lifecycle (open, message, close, error)."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()
        session_id = "lifecycle-session-123"

        # 1. Open
        with patch.object(handler, "validate_authentication") as mock_auth:
            mock_auth.return_value = mock_user_profile

            connected = await handler.connect(mock_websocket, session_id, "token")
            assert connected is True
            assert session_id in handler.active_connections

        # 2. Message handling is tested in other tests

        # 3. Close
        await handler.disconnect(session_id)
        assert session_id not in handler.active_connections

    @pytest.mark.asyncio
    async def test_tc_ws_05_audio_output_24khz(self, mock_websocket):
        """TC-WS-05: Audio output is 24kHz PCM (per ADK research)."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()

        # ADK Live API outputs 24kHz
        output_sample_rate = handler.get_output_sample_rate()

        assert output_sample_rate == 24000

    @pytest.mark.asyncio
    async def test_tc_ws_06_graceful_error_handling_network_drop(
        self, mock_websocket, mock_user_profile
    ):
        """TC-WS-06: Graceful error handling - network drops (AC6)."""
        from app.audio.websocket_handler import AudioWebSocketHandler
        from starlette.websockets import WebSocketDisconnect

        handler = AudioWebSocketHandler()
        session_id = "network-error-session"

        with patch.object(handler, "validate_authentication") as mock_auth:
            mock_auth.return_value = mock_user_profile
            await handler.connect(mock_websocket, session_id, "token")

        # Simulate network drop
        mock_websocket.receive_bytes.side_effect = WebSocketDisconnect()

        with patch.object(handler, "orchestrator") as mock_orch:
            mock_orch.handle_disconnect = AsyncMock()

            # Should handle gracefully without raising
            await handler.handle_connection_error(session_id, "WebSocket disconnected")

            # Should clean up orchestrator
            mock_orch.handle_disconnect.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_tc_ws_06_graceful_error_handling_codec_error(self, mock_websocket):
        """TC-WS-06: Graceful error handling - codec errors (AC6)."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()
        session_id = "codec-error-session"

        # Invalid audio data
        invalid_audio = b"not-valid-pcm-data"

        with patch.object(handler, "orchestrator") as mock_orch:
            mock_orch.send_audio_chunk = AsyncMock(
                return_value={"error": True, "message": "Invalid audio format"}
            )

            result = await handler.process_audio_message(session_id, invalid_audio)

            # Should return error, not raise
            assert result.get("error") is True or "error" in str(result).lower()


class TestWebSocketMessageTypes:
    """Tests for different WebSocket message types."""

    @pytest.mark.asyncio
    async def test_audio_message_type(self):
        """Test handling of audio/pcm message type."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()

        message = {
            "type": "audio/pcm",
            "audio": base64.b64encode(b"\x00\x01" * 160).decode("utf-8"),
        }

        msg_type = handler.get_message_type(message)
        assert msg_type == "audio/pcm"

    @pytest.mark.asyncio
    async def test_text_message_type(self):
        """Test handling of text message type."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()

        message = {"type": "text", "text": "Hello"}

        msg_type = handler.get_message_type(message)
        assert msg_type == "text"

    @pytest.mark.asyncio
    async def test_control_message_type(self):
        """Test handling of control messages (start/stop)."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()

        start_msg = {"type": "control", "action": "start_listening"}
        stop_msg = {"type": "control", "action": "stop_listening"}

        assert handler.get_message_type(start_msg) == "control"
        assert handler.get_message_type(stop_msg) == "control"


class TestWebSocketAuthentication:
    """Tests for WebSocket authentication."""

    @pytest.mark.asyncio
    async def test_missing_auth_token_rejected(self):
        """Test that missing auth token is rejected."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()
        mock_ws = AsyncMock()

        result = await handler.connect(mock_ws, "session-123", auth_token=None)

        assert result is False
        mock_ws.close.assert_called()

    @pytest.mark.asyncio
    async def test_invalid_auth_token_rejected(self):
        """Test that invalid auth token is rejected."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()
        mock_ws = AsyncMock()

        with patch.object(handler, "validate_authentication") as mock_auth:
            mock_auth.return_value = None

            result = await handler.connect(mock_ws, "session-123", auth_token="invalid")

            assert result is False

    @pytest.mark.asyncio
    async def test_expired_session_rejected(self):
        """Test that expired session is rejected."""
        from app.audio.websocket_handler import AudioWebSocketHandler

        handler = AudioWebSocketHandler()

        with patch("app.middleware.oauth_auth.validate_session_token") as mock_validate:
            mock_validate.return_value = None  # Expired/invalid session

            result = await handler.validate_authentication("expired-token")

            assert result is None
