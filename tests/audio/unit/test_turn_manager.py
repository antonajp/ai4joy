"""
Unit tests for AgentTurnManager.

Tests turn counting logic for the simplified audio architecture where
the MC agent handles all interactions (hosting + scene work).

Note: Multi-agent switching tests have been removed as the audio architecture
no longer uses separate Partner/Room agents.
"""

import pytest
from unittest.mock import MagicMock, patch


def test_initial_turn_count_is_zero():
    """Turn manager should start with turn count of zero."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    assert manager.turn_count == 0


def test_custom_starting_turn_count():
    """Turn manager should accept custom starting turn count."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager(starting_turn_count=5)

    assert manager.turn_count == 5


def test_on_turn_complete_increments_count():
    """Turn count should increment on turn completion."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()
    initial_count = manager.turn_count

    manager.on_turn_complete()

    assert manager.turn_count == initial_count + 1


def test_turn_count_tracking():
    """Turn count should accurately track number of completions."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    for i in range(1, 11):
        manager.on_turn_complete()
        assert manager.turn_count == i


def test_on_turn_complete_returns_phase_1_for_early_turns():
    """Turn completion should return phase_1 for turns 1-7 (supportive MC).

    IQS-81: Updated to reflect dynamic phase calculation.
    """
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    result = manager.on_turn_complete()

    assert result["phase"] == "phase_1"
    assert result["phase_changed"] is False


def test_on_turn_complete_returns_status_ok():
    """Turn completion should return ok status."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    result = manager.on_turn_complete()

    assert result["status"] == "ok"


def test_on_turn_complete_returns_turn_count():
    """Turn completion should return updated turn count."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    result = manager.on_turn_complete()

    assert result["turn_count"] == 1

    result2 = manager.on_turn_complete()

    assert result2["turn_count"] == 2


def test_get_state_returns_turn_count():
    """get_state should return current turn count."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()
    manager.on_turn_complete()
    manager.on_turn_complete()
    manager.on_turn_complete()

    state = manager.get_state()

    assert state["turn_count"] == 3


def test_reset_clears_turn_count():
    """Reset should clear turn count to zero."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    # Advance state
    for _ in range(5):
        manager.on_turn_complete()

    assert manager.turn_count == 5

    # Reset
    manager.reset()

    assert manager.turn_count == 0


def test_reset_with_custom_turn_count():
    """Reset should accept custom turn count."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()
    manager.on_turn_complete()

    manager.reset(turn_count=10)

    assert manager.turn_count == 10


def test_phase_transitions_at_turn_8():
    """Phase should transition from phase_1 to phase_2 at turn 8.

    IQS-81: Updated to verify dynamic phase calculation.
    Phase 1 (Supportive): turns 1-7
    Phase 2 (Fallible): turns 8+
    """
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    # Turns 1-7 should be phase_1
    for i in range(1, 8):
        result = manager.on_turn_complete()
        assert result["turn_count"] == i
        assert result["phase"] == "phase_1", f"Turn {i} should be phase_1"
        assert result["phase_changed"] is False, f"Turn {i} should not trigger phase change"

    # Turn 8 should transition to phase_2
    result = manager.on_turn_complete()
    assert result["turn_count"] == 8
    assert result["phase"] == "phase_2", "Turn 8 should be phase_2"
    assert result["phase_changed"] is True, "Turn 8 should trigger phase change"

    # Turns 9+ should remain phase_2
    for i in range(9, 12):
        result = manager.on_turn_complete()
        assert result["turn_count"] == i
        assert result["phase"] == "phase_2", f"Turn {i} should be phase_2"
        assert result["phase_changed"] is False, f"Turn {i} should not trigger phase change"
