"""
Integration tests for multi-agent audio orchestration.

NOTE: These tests have been deprecated as of IQS-63.

The simplified audio architecture now uses a single unified MC agent that handles
both hosting AND scene partner work. Multi-agent switching (MC <-> Partner) has
been removed from audio mode.

For multi-agent orchestration in TEXT mode, see tests/agents/integration/test_stage_manager.py

The remaining tests in this file are kept for historical reference but marked as skipped.
"""

import pytest


# All tests in this file are skipped because multi-agent audio orchestration
# has been removed in favor of a unified MC agent (IQS-63)
pytestmark = pytest.mark.skip(
    reason="Multi-agent audio orchestration removed in IQS-63. "
    "Audio mode now uses unified MC agent for both hosting and scene work."
)


@pytest.mark.asyncio
async def test_orchestrator_has_both_agents():
    """[DEPRECATED] Audio orchestrator should initialize both MC and Partner agents."""
    pass


@pytest.mark.asyncio
async def test_switch_to_partner():
    """[DEPRECATED] Orchestrator should be able to switch to partner agent."""
    pass


@pytest.mark.asyncio
async def test_switch_to_mc():
    """[DEPRECATED] Orchestrator should be able to switch back to MC agent."""
    pass


@pytest.mark.asyncio
async def test_voice_config_changes_on_switch():
    """[DEPRECATED] Voice configuration should change when switching agents."""
    pass


@pytest.mark.asyncio
async def test_turn_completion_triggers_phase_check():
    """[DEPRECATED] Completing turns should trigger phase transition checks."""
    pass


@pytest.mark.asyncio
async def test_session_state_tracks_agent_turns():
    """[DEPRECATED] Session state should track which agent spoke in each turn."""
    pass


@pytest.mark.asyncio
async def test_orchestrator_phase_affects_both_agents():
    """[DEPRECATED] Phase transitions should affect both MC and Partner behavior."""
    pass


@pytest.mark.asyncio
async def test_concurrent_agent_responses_prevented():
    """[DEPRECATED] Only one agent should respond at a time."""
    pass


@pytest.mark.asyncio
async def test_orchestrator_maintains_conversation_context():
    """[DEPRECATED] Orchestrator should maintain context across agent switches."""
    pass


@pytest.mark.asyncio
async def test_orchestrator_handles_empty_user_input():
    """[DEPRECATED] Orchestrator should gracefully handle empty or invalid input."""
    pass


@pytest.mark.asyncio
async def test_orchestrator_initialization_with_session():
    """[DEPRECATED] Orchestrator should initialize with existing session data."""
    pass


@pytest.mark.asyncio
async def test_orchestrator_audio_stream_routing():
    """[DEPRECATED] Audio streams should route to correct agent based on current state."""
    pass


@pytest.mark.asyncio
async def test_orchestrator_latency_tracking():
    """[DEPRECATED] Orchestrator should track latency for multi-agent responses."""
    pass
