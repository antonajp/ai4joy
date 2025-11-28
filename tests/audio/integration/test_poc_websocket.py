"""Integration tests for audio PoC WebSocket endpoint."""

import json
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestWebSocketPoC:
    """Integration tests for the audio PoC WebSocket endpoint."""

    def test_websocket_connection_success(self, client: TestClient):
        """Test that WebSocket connection can be established."""
        session_id = "test_session_123"

        with client.websocket_connect(f"/api/audio/poc/ws/{session_id}") as websocket:
            assert websocket is not None

    def test_websocket_text_echo(self, client: TestClient):
        """Test text message echo with latency measurement."""
        session_id = "test_session_456"

        with client.websocket_connect(f"/api/audio/poc/ws/{session_id}") as websocket:
            websocket.send_json({
                "type": "text/plain",
                "text": "Hello WebSocket"
            })
            response = websocket.receive_json()

            assert response["type"] == "text/plain"
            assert "Echo: Hello WebSocket" in response["text"]
            assert "latency_ms" in response
            assert response["latency_ms"] < 50

    def test_websocket_audio_roundtrip(self, client: TestClient):
        """Test audio message encode/decode roundtrip."""
        session_id = "test_session_audio"
        # Small PCM16 audio sample (8 bytes = 4 samples at 16-bit)
        import base64
        test_audio = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        encoded_audio = base64.b64encode(test_audio).decode("utf-8")

        with client.websocket_connect(f"/api/audio/poc/ws/{session_id}") as websocket:
            websocket.send_json({
                "type": "audio/pcm",
                "audio": encoded_audio
            })
            response = websocket.receive_json()

            assert response["type"] == "audio/pcm"
            assert "audio" in response
            assert response["audio_bytes"] == len(test_audio)
            assert "latency_ms" in response
            assert "decode_ms" in response
            assert "encode_ms" in response
            assert response["latency_ms"] < 50

    def test_websocket_invalid_message_type(self, client: TestClient):
        """Test error handling for unsupported message type."""
        session_id = "test_session_error"

        with client.websocket_connect(f"/api/audio/poc/ws/{session_id}") as websocket:
            websocket.send_json({
                "type": "invalid/type",
                "data": "test"
            })
            response = websocket.receive_json()

            assert response["type"] == "error"
            assert "Unsupported message type" in response["error"]

    def test_websocket_connection_close(self, client: TestClient):
        """Test that WebSocket connection closes gracefully."""
        session_id = "test_session_789"

        # Connection should close without raising an exception
        with client.websocket_connect(f"/api/audio/poc/ws/{session_id}") as websocket:
            websocket.close()
        # If we reach here, the connection closed gracefully
