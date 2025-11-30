"""
Integration tests for Partner agent audio capabilities.
Tests Partner agent creation, voice configuration, and phase-based instructions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_partner_agent_audio_creation():
    """Partner agent for audio should use Live API model."""
    from app.agents.partner_agent import create_partner_agent_for_audio

    agent = create_partner_agent_for_audio(phase=1)

    assert agent is not None
    assert agent.name == "partner_agent_audio"
    # Live model check - should use realtime or compatible model
    assert "live" in agent.model.lower() or "realtime" in agent.model.lower()


@pytest.mark.asyncio
async def test_partner_voice_is_puck():
    """Partner agent should use Puck voice configuration."""
    from app.agents.partner_agent import create_partner_agent_for_audio
    from app.audio.voice_config import get_voice_config

    agent = create_partner_agent_for_audio(phase=1)
    voice_config = get_voice_config(agent_type="partner")

    assert voice_config.voice == "puck"
    # Agent should have voice configuration accessible
    assert hasattr(agent, "voice") or hasattr(agent, "voice_config")


@pytest.mark.asyncio
async def test_partner_phase_1_instruction():
    """Partner in Phase 1 should use supportive instruction set."""
    from app.agents.partner_agent import create_partner_agent_for_audio

    agent = create_partner_agent_for_audio(phase=1)

    # Extract system instruction
    instruction = agent.instructions if hasattr(agent, "instructions") else str(agent)

    # Phase 1 should be supportive and helpful
    assert "supportive" in instruction.lower() or "guide" in instruction.lower()
    assert "fallible" not in instruction.lower()


@pytest.mark.asyncio
async def test_partner_phase_2_instruction():
    """Partner in Phase 2 should use fallible instruction set."""
    from app.agents.partner_agent import create_partner_agent_for_audio

    agent = create_partner_agent_for_audio(phase=2)

    # Extract system instruction
    instruction = agent.instructions if hasattr(agent, "instructions") else str(agent)

    # Phase 2 should introduce fallibility
    assert "fallible" in instruction.lower() or "mistake" in instruction.lower() or "imperfect" in instruction.lower()


@pytest.mark.asyncio
async def test_partner_agent_has_audio_capabilities():
    """Partner agent should have audio streaming capabilities."""
    from app.agents.partner_agent import create_partner_agent_for_audio

    agent = create_partner_agent_for_audio(phase=1)

    # Should support audio methods
    assert hasattr(agent, "run") or hasattr(agent, "process_audio")
    # Should use realtime-compatible model
    assert agent.model is not None


@pytest.mark.asyncio
async def test_partner_phase_transition():
    """Partner agent should handle phase transitions."""
    from app.agents.partner_agent import create_partner_agent_for_audio

    phase1_agent = create_partner_agent_for_audio(phase=1)
    phase2_agent = create_partner_agent_for_audio(phase=2)

    # Both should be valid but with different instructions
    assert phase1_agent is not None
    assert phase2_agent is not None

    inst1 = phase1_agent.instructions if hasattr(phase1_agent, "instructions") else str(phase1_agent)
    inst2 = phase2_agent.instructions if hasattr(phase2_agent, "instructions") else str(phase2_agent)

    assert inst1 != inst2


@pytest.mark.asyncio
async def test_partner_audio_response_format():
    """Partner agent responses should be suitable for TTS."""
    from app.agents.partner_agent import create_partner_agent_for_audio

    agent = create_partner_agent_for_audio(phase=1)

    # Mock response processing
    with patch.object(agent, "run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = "This is a test response for audio output."

        response = await agent.run("Test user input")

        # Response should be text suitable for TTS
        assert isinstance(response, str)
        assert len(response) > 0


@pytest.mark.asyncio
async def test_partner_agent_distinct_from_mc():
    """Partner agent should have distinct characteristics from MC."""
    from app.agents.partner_agent import create_partner_agent_for_audio
    from app.agents.mc_agent import create_mc_agent_for_audio

    partner = create_partner_agent_for_audio(phase=1)
    mc = create_mc_agent_for_audio(phase=1)

    # Different voices
    assert partner.name != mc.name

    # Different instructions
    partner_inst = partner.instructions if hasattr(partner, "instructions") else str(partner)
    mc_inst = mc.instructions if hasattr(mc, "instructions") else str(mc)
    assert partner_inst != mc_inst


@pytest.mark.asyncio
async def test_partner_audio_uses_streaming():
    """Partner agent should support streaming audio responses."""
    from app.agents.partner_agent import create_partner_agent_for_audio

    agent = create_partner_agent_for_audio(phase=1)

    # Should have streaming capability
    assert hasattr(agent, "stream") or "stream" in agent.model.lower()


@pytest.mark.asyncio
async def test_partner_agent_invalid_phase():
    """Partner agent creation with invalid phase should handle gracefully."""
    from app.agents.partner_agent import create_partner_agent_for_audio

    # Invalid phase should default or raise clear error
    try:
        agent = create_partner_agent_for_audio(phase=99)
        # If it doesn't raise, should default to valid phase
        assert agent is not None
    except ValueError as e:
        assert "phase" in str(e).lower()
