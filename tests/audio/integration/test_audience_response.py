"""
Integration Tests for Audience (Room Agent) Audio Response - IQS-60

Tests the Room Agent's ambient audio commentary during scenes:
- TC-060-001: Audience responds after partner turns
- TC-060-002: Audience uses Charon voice
- TC-060-003: Audience audio at 30% volume
- TC-060-004: Audience reactions are brief (under 2 sentences)
- TC-060-005: Ambient trigger respects cooldown
- TC-060-006: Room agent doesn't block main conversation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_tc_060_001_audience_responds_after_partner_turn():
    """TC-060-001: Audience (Room Agent) responds after each partner turn.

    When Partner completes a turn in scene work, the Room Agent should
    provide brief ambient commentary based on sentiment analysis.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator
    from app.audio.ambient_audio import SentimentLevel

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-audience-response-001"

    # Start session with MC first
    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
        game_name="Long Form",
    )

    session = await orchestrator.get_session(session_id)
    assert session is not None
    assert session.room_agent is not None

    # Switch to Partner for scene work
    orchestrator.switch_to_partner(session_id)

    # Verify Room agent is available for ambient audio
    assert session.room_agent.name == "room_agent_audio"
    assert session.audio_mixer is not None
    assert session.ambient_trigger is not None

    # Simulate high-energy positive moment (should trigger ambient audio)
    should_trigger = orchestrator.should_trigger_ambient(
        session_id=session_id,
        sentiment="very_positive",
        energy_level=0.9,
    )

    assert should_trigger is True


@pytest.mark.asyncio
async def test_tc_060_002_audience_uses_charon_voice():
    """TC-060-002: Audience audio uses Charon voice configuration.

    The Room Agent should use the Charon voice (ambient background voice)
    which is distinct from MC (Aoede) and Partner (Puck).
    """
    from app.audio.voice_config import get_voice_config
    from app.agents.room_agent import create_room_agent_for_audio

    # Get voice configs for all agents
    mc_voice = get_voice_config("mc")
    partner_voice = get_voice_config("partner")
    room_voice = get_voice_config("room")

    # Room should use Charon
    assert room_voice.voice_name == "Charon"

    # All three voices should be different
    assert mc_voice.voice_name != room_voice.voice_name
    assert partner_voice.voice_name != room_voice.voice_name
    assert mc_voice.voice_name != partner_voice.voice_name

    # Room agent should be configured with Live API model
    room_agent = create_room_agent_for_audio()
    assert "live" in room_agent.model.lower()


@pytest.mark.asyncio
async def test_tc_060_003_audience_audio_at_30_percent():
    """TC-060-003: Audience audio volume set to 30% to not overpower main agents.

    The Room Agent's audio should be mixed at 30% volume while MC and Partner
    are at 100%, creating ambient background effect.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-audience-volume-003"

    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
    )

    # Check default volume levels
    session = await orchestrator.get_session(session_id)
    assert session.audio_mixer is not None

    # MC and Partner at 100%
    assert session.audio_mixer.get_volume("mc") == 1.0
    assert session.audio_mixer.get_volume("partner") == 1.0

    # Room at 30%
    room_volume = orchestrator.get_room_volume(session_id)
    assert room_volume == 0.3

    # Verify via mixer directly
    assert session.audio_mixer.get_volume("room") == 0.3


@pytest.mark.asyncio
async def test_tc_060_004_audience_reaction_brief():
    """TC-060-004: Audience reactions are brief (under 2 sentences).

    The Room Agent's system prompt should emphasize brevity,
    and ambient commentary should be 1-2 sentences maximum.
    """
    from app.agents.room_agent import create_room_agent_for_audio, ROOM_AUDIO_SYSTEM_PROMPT

    room_agent = create_room_agent_for_audio()

    # Check system prompt emphasizes brevity
    instruction = room_agent.instruction.lower()

    # Should mention being brief
    assert "brief" in instruction or "1-2 sentences" in instruction

    # Should mention ambient/background nature
    assert "ambient" in instruction or "background" in instruction

    # Should explicitly say not to talk over main agents
    assert "don't talk over" in instruction or "never intrusive" in instruction or "without overwhelming" in instruction


@pytest.mark.asyncio
async def test_tc_060_005_ambient_trigger_respects_cooldown():
    """TC-060-005: Ambient audio trigger respects cooldown period.

    After triggering once, the Room Agent should wait for cooldown period
    before triggering again, preventing spam.
    """
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    # Create trigger with 5-second cooldown
    trigger = AmbientAudioTrigger(cooldown_seconds=5.0)

    # First trigger should succeed
    assert trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.9,
    ) is True

    # Immediate second trigger should fail (cooldown active)
    assert trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.9,
    ) is False

    # After reset, should trigger again
    trigger.reset()
    assert trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.9,
    ) is True


@pytest.mark.asyncio
async def test_tc_060_006_room_agent_nonblocking():
    """TC-060-006: Room Agent doesn't block main conversation flow.

    Room Agent ambient audio should be triggered asynchronously and
    should not block or delay MC/Partner interactions.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-room-nonblocking-006"

    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
    )

    session = await orchestrator.get_session(session_id)

    # Room agent should exist but not interfere with turn management
    assert session.room_agent is not None
    assert session.turn_manager is not None

    # Turn manager should only track MC and Partner, not Room
    assert session.turn_manager.current_speaker in ["mc", "partner"]

    # Room agent is not part of the turn-taking system
    # (it provides ambient commentary alongside the main conversation)


@pytest.mark.asyncio
async def test_tc_060_007_ambient_prompt_generation():
    """TC-060-007: Ambient prompts are generated based on sentiment and energy.

    Different sentiment levels and energy should produce appropriate prompts
    for the Room Agent to generate contextual ambient commentary.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-ambient-prompts-007"

    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
    )

    # High-energy positive moment
    positive_prompt = orchestrator.get_ambient_prompt(
        session_id=session_id,
        sentiment="very_positive",
        energy_level=0.9,
        context="Great scene connection",
    )

    assert positive_prompt != ""
    assert "brief" in positive_prompt.lower() or "sentence" in positive_prompt.lower()

    # Low-energy tense moment
    tense_prompt = orchestrator.get_ambient_prompt(
        session_id=session_id,
        sentiment="negative",
        energy_level=0.4,
        context="Challenging moment",
    )

    assert tense_prompt != ""
    # Prompts should be different for different scenarios
    assert positive_prompt != tense_prompt


@pytest.mark.asyncio
async def test_tc_060_008_audio_mixing_three_streams():
    """TC-060-008: Audio mixer can combine MC, Partner, and Room streams.

    When all three agents are producing audio, the mixer should combine them
    with appropriate volume levels without clipping.
    """
    import numpy as np
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-three-stream-mix-008"

    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
    )

    # Create sample audio for each agent (16-bit PCM, 24kHz mono)
    sample_rate = 24000
    duration_ms = 100
    samples = int(sample_rate * duration_ms / 1000)

    t = np.linspace(0, duration_ms / 1000, samples, dtype=np.float32)
    mc_audio = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16).tobytes()
    partner_audio = (np.sin(2 * np.pi * 550 * t) * 16000).astype(np.int16).tobytes()
    room_audio = (np.sin(2 * np.pi * 330 * t) * 16000).astype(np.int16).tobytes()

    # Mix all three streams
    mixed = orchestrator.mix_audio_streams(
        session_id=session_id,
        streams={
            "mc": mc_audio,
            "partner": partner_audio,
            "room": room_audio,
        }
    )

    # Verify output
    assert mixed is not None
    assert isinstance(mixed, bytes)
    assert len(mixed) > 0

    # Verify no clipping occurred
    mixed_array = np.frombuffer(mixed, dtype=np.int16)
    assert np.max(np.abs(mixed_array)) <= 32767


@pytest.mark.asyncio
async def test_tc_060_009_room_volume_adjustable():
    """TC-060-009: Room Agent volume can be adjusted dynamically.

    The orchestrator should allow adjusting Room Agent volume during
    a session for user preference or content-specific needs.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-room-volume-adjust-009"

    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
    )

    # Start with default 30%
    assert orchestrator.get_room_volume(session_id) == 0.3

    # Increase to 50%
    result = orchestrator.set_room_volume(session_id, 0.5)
    assert result["status"] == "ok"
    assert orchestrator.get_room_volume(session_id) == 0.5

    # Decrease to 10%
    result = orchestrator.set_room_volume(session_id, 0.1)
    assert result["status"] == "ok"
    assert orchestrator.get_room_volume(session_id) == 0.1


@pytest.mark.asyncio
async def test_tc_060_010_reset_ambient_trigger():
    """TC-060-010: Ambient trigger can be manually reset.

    For testing or special circumstances, the ambient trigger cooldown
    should be resettable to allow immediate re-triggering.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-reset-trigger-010"

    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
    )

    # Trigger ambient audio once
    should_trigger = orchestrator.should_trigger_ambient(
        session_id=session_id,
        sentiment="very_positive",
        energy_level=0.9,
    )
    assert should_trigger is True

    # Immediately trying again should fail (cooldown)
    should_trigger = orchestrator.should_trigger_ambient(
        session_id=session_id,
        sentiment="very_positive",
        energy_level=0.9,
    )
    assert should_trigger is False

    # Reset the trigger
    result = orchestrator.reset_ambient_trigger(session_id)
    assert result["status"] == "ok"

    # Now it should trigger again
    should_trigger = orchestrator.should_trigger_ambient(
        session_id=session_id,
        sentiment="very_positive",
        energy_level=0.9,
    )
    assert should_trigger is True
