"""
Integration tests for Partner agent audio capabilities.

NOTE: Partner agent audio functionality has been deprecated for AUDIO mode as of IQS-63.

The simplified audio architecture now uses a single unified MC agent that handles
both hosting AND scene partner work. The Partner agent is NO LONGER USED in audio mode.

The Partner agent IS STILL USED in TEXT mode via the StageManager architecture.
For text mode Partner tests, see tests/agents/test_partner_agent.py

The remaining tests in this file are kept for historical reference but marked as skipped.
"""

import pytest


# All tests in this file are skipped because Partner agent is no longer
# used in audio mode (IQS-63)
pytestmark = pytest.mark.skip(
    reason="Partner agent audio functionality deprecated in IQS-63. "
    "Audio mode now uses unified MC agent. Partner is still used in text mode."
)


@pytest.mark.asyncio
async def test_partner_agent_audio_creation():
    """[DEPRECATED] Partner agent for audio should use Live API model."""
    pass


@pytest.mark.asyncio
async def test_partner_voice_is_puck():
    """[DEPRECATED] Partner agent should use Puck voice configuration."""
    pass


@pytest.mark.asyncio
async def test_partner_phase_1_instruction():
    """[DEPRECATED] Partner in Phase 1 should use supportive instruction set."""
    pass


@pytest.mark.asyncio
async def test_partner_phase_2_instruction():
    """[DEPRECATED] Partner in Phase 2 should use fallible instruction set."""
    pass


@pytest.mark.asyncio
async def test_partner_agent_has_audio_capabilities():
    """[DEPRECATED] Partner agent should have audio streaming capabilities."""
    pass


@pytest.mark.asyncio
async def test_partner_phase_transition():
    """[DEPRECATED] Partner agent should handle phase transitions."""
    pass


@pytest.mark.asyncio
async def test_partner_audio_response_format():
    """[DEPRECATED] Partner agent responses should be suitable for TTS."""
    pass


@pytest.mark.asyncio
async def test_partner_agent_distinct_from_mc():
    """[DEPRECATED] Partner agent should have distinct characteristics from MC."""
    pass


@pytest.mark.asyncio
async def test_partner_audio_uses_streaming():
    """[DEPRECATED] Partner agent should support streaming audio responses."""
    pass


@pytest.mark.asyncio
async def test_partner_agent_invalid_phase():
    """[DEPRECATED] Partner agent creation with invalid phase should handle gracefully."""
    pass
