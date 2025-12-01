"""
Integration Tests for Audience (Room Agent) Audio Response - IQS-60

NOTE: Room Agent audio functionality has been deprecated for AUDIO mode as of IQS-63.

The simplified audio architecture now uses a single unified MC agent that handles
both hosting AND scene partner work. The Room Agent is NO LONGER USED in audio mode.

Room Agent audio features that were removed:
- TC-060-001: Audience responds after partner turns
- TC-060-003: Audience audio at 30% volume
- TC-060-006: Room agent nonblocking
- TC-060-007: Ambient prompt generation
- TC-060-008: Audio mixing three streams
- TC-060-009: Room volume adjustable
- TC-060-010: Reset ambient trigger

Tests that still pass (testing Room Agent factory functions):
- TC-060-002: Audience uses Charon voice (tests room agent creation)
- TC-060-004: Audience reaction brief (tests system prompt)
- TC-060-005: Ambient trigger respects cooldown (tests AmbientAudioTrigger class)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Tests that depend on Room Agent being used in audio orchestrator
# are skipped because this functionality was removed in IQS-63


@pytest.mark.skip(reason="Room Agent removed from audio orchestration in IQS-63")
@pytest.mark.asyncio
async def test_tc_060_001_audience_responds_after_partner_turn():
    """[DEPRECATED] TC-060-001: Audience (Room Agent) responds after each partner turn."""
    pass


@pytest.mark.asyncio
async def test_tc_060_002_audience_uses_charon_voice():
    """TC-060-002: Audience audio uses Charon voice configuration.

    The Room Agent should use the Charon voice (ambient background voice)
    which is distinct from MC (Aoede) and Partner (Puck).

    Note: While Room Agent is not used in audio orchestration (IQS-63),
    the voice configuration and agent factory still exist for potential
    future use or text mode.
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


@pytest.mark.skip(reason="Room Agent audio mixing removed from orchestration in IQS-63")
@pytest.mark.asyncio
async def test_tc_060_003_audience_audio_at_30_percent():
    """[DEPRECATED] TC-060-003: Audience audio volume set to 30%."""
    pass


@pytest.mark.asyncio
async def test_tc_060_004_audience_reaction_brief():
    """TC-060-004: Audience reactions are brief (under 2 sentences).

    The Room Agent's system prompt should emphasize brevity,
    and ambient commentary should be 1-2 sentences maximum.

    Note: While Room Agent is not used in audio orchestration (IQS-63),
    the system prompt requirements are still validated.
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

    Note: While not used in current audio orchestration (IQS-63),
    the AmbientAudioTrigger class is still tested for potential future use.
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


@pytest.mark.skip(reason="Room Agent removed from audio orchestration in IQS-63")
@pytest.mark.asyncio
async def test_tc_060_006_room_agent_nonblocking():
    """[DEPRECATED] TC-060-006: Room Agent doesn't block main conversation flow."""
    pass


@pytest.mark.skip(reason="Room Agent ambient prompts removed from orchestration in IQS-63")
@pytest.mark.asyncio
async def test_tc_060_007_ambient_prompt_generation():
    """[DEPRECATED] TC-060-007: Ambient prompts are generated based on sentiment."""
    pass


@pytest.mark.skip(reason="Room Agent audio mixing removed from orchestration in IQS-63")
@pytest.mark.asyncio
async def test_tc_060_008_audio_mixing_three_streams():
    """[DEPRECATED] TC-060-008: Audio mixer can combine MC, Partner, and Room streams."""
    pass


@pytest.mark.skip(reason="Room Agent volume controls removed from orchestration in IQS-63")
@pytest.mark.asyncio
async def test_tc_060_009_room_volume_adjustable():
    """[DEPRECATED] TC-060-009: Room Agent volume can be adjusted dynamically."""
    pass


@pytest.mark.skip(reason="Room Agent ambient trigger removed from orchestration in IQS-63")
@pytest.mark.asyncio
async def test_tc_060_010_reset_ambient_trigger():
    """[DEPRECATED] TC-060-010: Ambient trigger can be manually reset."""
    pass
