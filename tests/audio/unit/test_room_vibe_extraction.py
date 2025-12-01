"""Unit tests for room_vibe extraction from audience tool results.

Tests the _extract_room_vibe_from_tool_result method in AudioStreamOrchestrator
which converts audience tool results to room_vibe events for visual display.
"""

import pytest
from unittest.mock import MagicMock

from app.audio.audio_orchestrator import AudioStreamOrchestrator


class TestRoomVibeExtraction:
    """Tests for extracting room_vibe from audience tool results."""

    @pytest.fixture
    def orchestrator(self):
        """Create an AudioStreamOrchestrator instance."""
        return AudioStreamOrchestrator()

    def test_extracts_room_vibe_from_suggestion_for_game(self, orchestrator):
        """Test extraction from _get_suggestion_for_game tool result."""
        tool_result = MagicMock()
        tool_result.name = "_get_suggestion_for_game"
        tool_result.result = "Someone from the crowd shouts: 'A coffee shop!'"

        room_vibe = orchestrator._extract_room_vibe_from_tool_result(tool_result)

        assert room_vibe is not None
        assert room_vibe["type"] == "room_vibe"
        assert room_vibe["analysis"] == "Someone from the crowd shouts: 'A coffee shop!'"
        assert "mood_metrics" in room_vibe
        assert room_vibe["mood_metrics"]["engagement_score"] == 0.8
        assert "timestamp" in room_vibe

    def test_extracts_room_vibe_from_generate_audience_suggestion(self, orchestrator):
        """Test extraction from _generate_audience_suggestion tool result."""
        tool_result = MagicMock()
        tool_result.name = "_generate_audience_suggestion"
        tool_result.result = "A hospital waiting room"

        room_vibe = orchestrator._extract_room_vibe_from_tool_result(tool_result)

        # This won't match by name because result doesn't contain "shouts"
        # but let's verify the name-based detection works
        assert room_vibe is not None
        assert room_vibe["type"] == "room_vibe"
        assert room_vibe["analysis"] == "A hospital waiting room"

    def test_extracts_room_vibe_from_shout_phrases(self, orchestrator):
        """Test extraction based on shout phrase patterns in result."""
        tool_result = MagicMock()
        tool_result.name = "unknown_tool"  # Name won't match
        tool_result.result = "An audience member yells: 'A haunted library!'"

        room_vibe = orchestrator._extract_room_vibe_from_tool_result(tool_result)

        assert room_vibe is not None
        assert room_vibe["type"] == "room_vibe"
        assert "haunted library" in room_vibe["analysis"]

    def test_returns_none_for_non_audience_tool(self, orchestrator):
        """Test that non-audience tools return None."""
        tool_result = MagicMock()
        tool_result.name = "get_improv_games"
        tool_result.result = {"games": [{"name": "Word Association"}]}

        room_vibe = orchestrator._extract_room_vibe_from_tool_result(tool_result)

        assert room_vibe is None

    def test_returns_none_for_string_without_shout_phrases(self, orchestrator):
        """Test that generic strings don't trigger room_vibe."""
        tool_result = MagicMock()
        tool_result.name = "unknown_tool"
        tool_result.result = "This is just a regular response"

        room_vibe = orchestrator._extract_room_vibe_from_tool_result(tool_result)

        assert room_vibe is None

    def test_handles_dict_result_with_suggestion_key(self, orchestrator):
        """Test extraction from dict result with suggestion key."""
        tool_result = MagicMock()
        tool_result.name = "get_suggestion_for_game"
        tool_result.result = {
            "suggestion": "Someone shouts: 'A coffee shop!'",
            "type": "location"
        }

        room_vibe = orchestrator._extract_room_vibe_from_tool_result(tool_result)

        assert room_vibe is not None
        assert "coffee shop" in room_vibe["analysis"]

    def test_handles_tool_result_without_name(self, orchestrator):
        """Test handling of tool result without name attribute."""
        tool_result = MagicMock(spec=[])  # No name attribute
        tool_result.result = "From the back row, someone calls out: 'A spaceship!'"

        room_vibe = orchestrator._extract_room_vibe_from_tool_result(tool_result)

        assert room_vibe is not None
        assert "spaceship" in room_vibe["analysis"]

    def test_mood_metrics_indicate_engagement(self, orchestrator):
        """Test that mood_metrics indicate audience engagement."""
        tool_result = MagicMock()
        tool_result.name = "_get_suggestion_for_game"
        tool_result.result = "Someone from the crowd shouts: 'A coffee shop!'"

        room_vibe = orchestrator._extract_room_vibe_from_tool_result(tool_result)

        assert room_vibe is not None
        mood = room_vibe["mood_metrics"]
        assert mood["sentiment_score"] > 0  # Positive sentiment
        assert mood["engagement_score"] > 0.5  # High engagement
        assert mood["laughter_detected"] is False  # No laughter for suggestions

    def test_handles_exception_gracefully(self, orchestrator):
        """Test graceful handling of unexpected errors."""
        tool_result = MagicMock()
        tool_result.name = "_get_suggestion_for_game"
        # Make result raise an exception when accessed
        type(tool_result).result = property(lambda self: (_ for _ in ()).throw(RuntimeError("Test error")))

        room_vibe = orchestrator._extract_room_vibe_from_tool_result(tool_result)

        assert room_vibe is None  # Should return None, not raise

    def test_timestamp_is_iso_format(self, orchestrator):
        """Test that timestamp is in ISO format."""
        import re

        tool_result = MagicMock()
        tool_result.name = "_get_suggestion_for_game"
        tool_result.result = "Someone shouts: 'Test!'"

        room_vibe = orchestrator._extract_room_vibe_from_tool_result(tool_result)

        assert room_vibe is not None
        # ISO format: 2025-11-30T12:34:56.123456+00:00
        iso_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(iso_pattern, room_vibe["timestamp"])
