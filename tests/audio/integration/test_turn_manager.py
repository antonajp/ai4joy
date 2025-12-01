"""
Integration tests for turn-taking coordination.

NOTE: These tests have been deprecated as of IQS-63.

The simplified audio architecture now uses a single unified MC agent that handles
both hosting AND scene partner work. Turn-taking between MC and Partner agents
has been removed from audio mode.

For turn counting functionality, see tests/audio/unit/test_turn_manager.py

The remaining tests in this file are kept for historical reference but marked as skipped.
"""

import pytest


# All tests in this file are skipped because multi-agent turn-taking
# has been removed in favor of a unified MC agent (IQS-63)
pytestmark = pytest.mark.skip(
    reason="Multi-agent turn-taking removed in IQS-63. "
    "Audio mode now uses unified MC agent. See unit tests for turn counting."
)


@pytest.mark.asyncio
async def test_mc_to_partner_transition():
    """[DEPRECATED] MC to Partner turn transition should work smoothly."""
    pass


@pytest.mark.asyncio
async def test_partner_to_mc_transition():
    """[DEPRECATED] Partner to MC turn transition should work if needed."""
    pass


@pytest.mark.asyncio
async def test_concurrent_user_agent_speech_prevented():
    """[DEPRECATED] User and agent should not speak simultaneously."""
    pass


@pytest.mark.asyncio
async def test_turn_taking_accuracy():
    """[DEPRECATED] Correct agent should respond in turn sequence."""
    pass


@pytest.mark.asyncio
async def test_natural_turn_timing():
    """[DEPRECATED] Turn transitions should feel natural without awkward pauses."""
    pass


@pytest.mark.asyncio
async def test_turn_end_detection():
    """[DEPRECATED] System should detect when agent finishes speaking."""
    pass


@pytest.mark.asyncio
async def test_interrupt_handling():
    """[DEPRECATED] System should handle user interruptions gracefully."""
    pass


@pytest.mark.asyncio
async def test_turn_history_persistence():
    """[DEPRECATED] Turn history should be persisted to session state."""
    pass


@pytest.mark.asyncio
async def test_simultaneous_turn_requests():
    """[DEPRECATED] System should serialize simultaneous turn requests."""
    pass


@pytest.mark.asyncio
async def test_turn_taking_with_phase_transition():
    """[DEPRECATED] Turn-taking should continue smoothly through phase transitions."""
    pass


@pytest.mark.asyncio
async def test_voice_continuity_across_turns():
    """[DEPRECATED] Voice configuration should remain consistent within agent turns."""
    pass
