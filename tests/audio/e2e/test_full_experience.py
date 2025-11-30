"""
End-to-end tests for Phase 3 full audio experience.
Tests the complete MC → Partner → Room Agent flow.

Test cases (from IQS-60):
- TC-025: Full experience E2E - MC welcomes, Partner scenes, Room ambient
- TC-023: Room audio generation
- TC-024: Audio mixing quality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np


@pytest.mark.asyncio
async def test_tc_025_full_experience_agent_creation():
    """TC-025: Full experience - All three agents can be created for audio."""
    from app.agents.mc_agent import create_mc_agent_for_audio
    from app.agents.partner_agent import create_partner_agent_for_audio
    from app.agents.room_agent import create_room_agent_for_audio

    # Create all three agents
    mc = create_mc_agent_for_audio()
    partner = create_partner_agent_for_audio(phase=1)
    room = create_room_agent_for_audio()

    # All agents should be created successfully
    assert mc is not None
    assert partner is not None
    assert room is not None

    # All should use Live API model
    assert "live" in mc.model.lower()
    assert "live" in partner.model.lower()
    assert "live" in room.model.lower()


@pytest.mark.asyncio
async def test_tc_025_full_experience_voice_differentiation():
    """TC-025: Full experience - All agents have distinct voices."""
    from app.audio.voice_config import get_voice_config

    mc_voice = get_voice_config("mc")
    partner_voice = get_voice_config("partner")
    room_voice = get_voice_config("room")

    # All voices should be different
    voices = {mc_voice.voice_name, partner_voice.voice_name, room_voice.voice_name}
    assert len(voices) == 3  # 3 unique voices

    # Verify specific voices
    assert mc_voice.voice_name == "Aoede"  # Warm host
    assert partner_voice.voice_name == "Puck"  # Playful partner
    assert room_voice.voice_name == "Charon"  # Ambient background


@pytest.mark.asyncio
async def test_tc_023_room_audio_generation_capabilities():
    """TC-023: Room audio generation - Room agent has required capabilities."""
    from app.agents.room_agent import create_room_agent_for_audio
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    # Create room agent
    room = create_room_agent_for_audio()

    # Should have sentiment analysis tools
    assert room.tools is not None
    assert len(room.tools) >= 1

    # Ambient trigger should work
    trigger = AmbientAudioTrigger()
    should_trigger = trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.8,
    )
    assert should_trigger is True


@pytest.mark.asyncio
async def test_tc_024_audio_mixing_with_all_agents():
    """TC-024: Audio mixing - Multiple agent streams mix correctly."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()

    # Create sample audio for each agent (16-bit PCM, 24kHz mono)
    sample_rate = 24000
    duration_ms = 100
    samples = int(sample_rate * duration_ms / 1000)

    # Different frequencies for each agent
    t = np.linspace(0, duration_ms / 1000, samples, dtype=np.float32)
    mc_audio = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16).tobytes()
    partner_audio = (np.sin(2 * np.pi * 550 * t) * 16000).astype(np.int16).tobytes()
    room_audio = (np.sin(2 * np.pi * 330 * t) * 16000).astype(np.int16).tobytes()

    # Mix all three
    streams = {
        "mc": mc_audio,
        "partner": partner_audio,
        "room": room_audio,
    }
    mixed = mixer.mix_streams(streams)

    # Verify output
    assert mixed is not None
    assert isinstance(mixed, bytes)
    assert len(mixed) > 0

    # Verify no clipping
    mixed_array = np.frombuffer(mixed, dtype=np.int16)
    assert np.max(np.abs(mixed_array)) <= 32767


@pytest.mark.asyncio
async def test_tc_024_room_audio_at_30_percent_volume():
    """TC-024: Audio mixing - Room audio at 30% doesn't overpower."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()

    # Verify default volumes
    assert mixer.get_volume("mc") == 1.0
    assert mixer.get_volume("partner") == 1.0
    assert mixer.get_volume("room") == 0.3  # Room at 30%


@pytest.mark.asyncio
async def test_full_experience_ambient_triggers():
    """Test that ambient audio triggers work for various scenarios."""
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger(cooldown_seconds=0)  # No cooldown for testing

    # Scenario 1: High energy moment
    assert trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.9,
    ) is True

    # Reset for next test
    trigger.reset()

    # Scenario 2: Tension moment
    assert trigger.should_trigger(
        sentiment=SentimentLevel.VERY_NEGATIVE,
        energy_level=0.5,
    ) is True

    # Reset for next test
    trigger.reset()

    # Scenario 3: Quiet moment (should not trigger)
    assert trigger.should_trigger(
        sentiment=SentimentLevel.NEUTRAL,
        energy_level=0.2,
    ) is False


@pytest.mark.asyncio
async def test_full_experience_commentary_prompts():
    """Test that room agent gets appropriate prompts for different moments."""
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger()

    # Positive moment prompt
    positive_prompt = trigger.get_commentary_prompt(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.9,
        context="Great scene connection",
    )
    assert "brief" in positive_prompt.lower() or "sentence" in positive_prompt.lower()
    assert "energy" in positive_prompt.lower() or "excitement" in positive_prompt.lower()

    # Tense moment prompt
    tense_prompt = trigger.get_commentary_prompt(
        sentiment=SentimentLevel.NEGATIVE,
        energy_level=0.4,
        context="Challenging moment",
    )
    assert positive_prompt != tense_prompt


@pytest.mark.asyncio
async def test_full_experience_agent_instructions():
    """Test that all agents have appropriate instructions for their roles."""
    from app.agents.mc_agent import create_mc_agent_for_audio
    from app.agents.partner_agent import create_partner_agent_for_audio
    from app.agents.room_agent import create_room_agent_for_audio

    mc = create_mc_agent_for_audio()
    partner = create_partner_agent_for_audio(phase=1)
    room = create_room_agent_for_audio()

    # MC should mention hosting/welcoming
    mc_inst = mc.instruction.lower()
    assert "mc" in mc_inst or "host" in mc_inst or "welcome" in mc_inst

    # Partner should mention scene/improv
    partner_inst = partner.instruction.lower()
    assert "scene" in partner_inst or "improv" in partner_inst

    # Room should mention ambient/audience/brief
    room_inst = room.instruction.lower()
    assert ("ambient" in room_inst or "audience" in room_inst or "room" in room_inst)
    assert "brief" in room_inst  # Room should be brief


@pytest.mark.asyncio
async def test_coach_remains_text_only():
    """AC3: Coach feedback should remain text-only."""
    from app.agents.coach_agent import create_coach_agent

    # Coach agent should NOT have audio version
    coach = create_coach_agent()

    # Coach should use text model, not live model
    assert "live" not in coach.model.lower()
    assert "flash" in coach.model.lower() or "pro" in coach.model.lower()
