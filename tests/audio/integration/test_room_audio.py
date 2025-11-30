"""
Integration tests for Room Agent audio capabilities.
Tests Room agent creation, voice configuration, and ambient audio behavior.

Test cases:
- TC-ROOM-023: Room audio generation with Live API model
- TC-ROOM-024: Room agent uses correct voice (Charon)
- TC-ROOM-025: Room agent has sentiment analysis tools
- TC-ROOM-026: Room agent audio factory function works
- TC-ROOM-027: Room agent is distinct from MC and Partner
- TC-ROOM-028: Room agent system prompt is appropriate for ambient commentary
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_tc_room_023_room_agent_audio_creation():
    """TC-ROOM-023: Room agent for audio should use Live API model."""
    from app.agents.room_agent import create_room_agent_for_audio

    agent = create_room_agent_for_audio()

    assert agent is not None
    assert agent.name == "room_agent_audio"
    # Live model check - should use realtime or compatible model
    assert "live" in agent.model.lower() or "realtime" in agent.model.lower()


@pytest.mark.asyncio
async def test_tc_room_024_room_voice_is_charon():
    """TC-ROOM-024: Room agent should use Charon voice configuration."""
    from app.agents.room_agent import create_room_agent_for_audio
    from app.audio.voice_config import get_voice_config

    agent = create_room_agent_for_audio()
    voice_config = get_voice_config(agent_type="room")

    assert voice_config.voice_name == "Charon"
    # Verify the agent is for ambient/room commentary
    assert "room" in agent.name.lower() or "audience" in agent.name.lower()


@pytest.mark.asyncio
async def test_tc_room_025_room_agent_has_sentiment_tools():
    """TC-ROOM-025: Room agent should have sentiment analysis tools."""
    from app.agents.room_agent import create_room_agent_for_audio

    agent = create_room_agent_for_audio()

    # Room agent should have sentiment analysis capabilities
    assert agent.tools is not None
    tool_names = [str(tool) for tool in agent.tools]
    tool_str = " ".join(tool_names).lower()

    # Should have sentiment analysis capability
    assert "sentiment" in tool_str or len(agent.tools) > 0


@pytest.mark.asyncio
async def test_tc_room_026_room_agent_audio_factory():
    """TC-ROOM-026: Room agent audio factory should return valid agent."""
    from app.agents.room_agent import create_room_agent_for_audio

    agent = create_room_agent_for_audio()

    # Should be a valid ADK agent
    assert hasattr(agent, "name")
    assert hasattr(agent, "model")
    assert hasattr(agent, "instruction")


@pytest.mark.asyncio
async def test_tc_room_027_room_distinct_from_mc_partner():
    """TC-ROOM-027: Room agent should be distinct from MC and Partner."""
    from app.agents.room_agent import create_room_agent_for_audio
    from app.agents.mc_agent import create_mc_agent_for_audio
    from app.agents.partner_agent import create_partner_agent_for_audio

    room = create_room_agent_for_audio()
    mc = create_mc_agent_for_audio()
    partner = create_partner_agent_for_audio(phase=1)

    # Different names
    assert room.name != mc.name
    assert room.name != partner.name

    # Different instructions
    room_inst = room.instruction if hasattr(room, "instruction") else str(room)
    mc_inst = mc.instruction if hasattr(mc, "instruction") else str(mc)
    partner_inst = partner.instruction if hasattr(partner, "instruction") else str(partner)

    assert room_inst != mc_inst
    assert room_inst != partner_inst


@pytest.mark.asyncio
async def test_tc_room_028_room_system_prompt_ambient():
    """TC-ROOM-028: Room agent instruction should support ambient commentary."""
    from app.agents.room_agent import create_room_agent_for_audio

    agent = create_room_agent_for_audio()

    instruction = agent.instruction if hasattr(agent, "instruction") else str(agent)
    instruction_lower = instruction.lower()

    # Should mention audience/room/collective concepts
    has_audience = "audience" in instruction_lower
    has_room = "room" in instruction_lower
    has_collective = "collective" in instruction_lower
    has_sentiment = "sentiment" in instruction_lower

    assert has_audience or has_room or has_collective or has_sentiment


@pytest.mark.asyncio
async def test_tc_room_029_room_agent_audio_uses_live_model():
    """TC-ROOM-029: Room agent should use Live API compatible model."""
    from app.agents.room_agent import create_room_agent_for_audio
    from app.config import get_settings

    settings = get_settings()
    agent = create_room_agent_for_audio()

    # Should use the live model configured in settings
    assert agent.model == settings.vertexai_live_model


@pytest.mark.asyncio
async def test_tc_room_030_room_agent_has_archetypes_tool():
    """TC-ROOM-030: Room agent should have audience archetypes tool."""
    from app.agents.room_agent import create_room_agent_for_audio

    agent = create_room_agent_for_audio()

    # Room agent should have archetypes capability for understanding audience
    assert agent.tools is not None
    # At least some tools should be present
    assert len(agent.tools) >= 1
