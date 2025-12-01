"""Unit tests for Room Agent TTS module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_room_tts_get_reaction_text_positive():
    """Test that positive sentiment returns appropriate reaction text."""
    from app.audio.room_tts import RoomAgentTTS

    tts = RoomAgentTTS()

    # Positive sentiment should return positive reactions
    text = tts.get_reaction_text("positive", energy_level=0.5)
    assert text in ["Ooh!", "Ha!", "Nice!", "Yes!", "Love it!", "Mmm!", "Ah!"]


@pytest.mark.asyncio
async def test_room_tts_get_reaction_text_very_positive():
    """Test that very positive sentiment returns enthusiastic reactions."""
    from app.audio.room_tts import RoomAgentTTS

    tts = RoomAgentTTS()

    # Very positive or high energy should return enthusiastic reactions
    text = tts.get_reaction_text("positive", energy_level=0.8)
    assert text in ["Ha ha ha!", "Whoo!", "That's great!", "Amazing!", "Brilliant!", "Oh wow!"]


@pytest.mark.asyncio
async def test_room_tts_get_reaction_text_negative():
    """Test that negative sentiment returns concerned reactions."""
    from app.audio.room_tts import RoomAgentTTS

    tts = RoomAgentTTS()

    text = tts.get_reaction_text("negative", energy_level=0.5)
    assert text in ["Ohh...", "Hmm...", "Uh oh...", "Oops..."]


@pytest.mark.asyncio
async def test_room_tts_get_reaction_text_high_energy_neutral():
    """Test that high energy with neutral sentiment returns laughter."""
    from app.audio.room_tts import RoomAgentTTS

    tts = RoomAgentTTS()

    # High energy neutral = laughter
    text = tts.get_reaction_text("neutral", energy_level=0.9)
    assert text in ["Ha!", "Ha ha!", "Ha ha ha!", "Heh heh!"]


@pytest.mark.asyncio
async def test_room_tts_singleton():
    """Test that get_room_tts returns singleton instance."""
    from app.audio.room_tts import get_room_tts

    tts1 = get_room_tts()
    tts2 = get_room_tts()

    assert tts1 is tts2


@pytest.mark.asyncio
async def test_room_tts_uses_charon_voice():
    """Test that Room Agent TTS uses Charon voice."""
    from app.audio.room_tts import RoomAgentTTS
    from app.audio.voice_config import get_voice_config

    tts = RoomAgentTTS()

    # Should use Room agent voice config
    room_voice = get_voice_config("room")
    assert tts._voice_config.voice_name == room_voice.voice_name
    assert tts._voice_config.voice_name == "Charon"


@pytest.mark.asyncio
async def test_room_tts_ambient_reactions_variety():
    """Test that ambient reactions have variety."""
    from app.audio.room_tts import AMBIENT_REACTIONS

    # Check that we have reactions for all categories
    assert "positive" in AMBIENT_REACTIONS
    assert "very_positive" in AMBIENT_REACTIONS
    assert "negative" in AMBIENT_REACTIONS
    assert "very_negative" in AMBIENT_REACTIONS
    assert "neutral" in AMBIENT_REACTIONS
    assert "laughter" in AMBIENT_REACTIONS

    # Each category should have multiple options
    for category, reactions in AMBIENT_REACTIONS.items():
        assert len(reactions) >= 3, f"Category {category} needs more variety"
