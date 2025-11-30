"""
Unit tests for AgentTurnManager.
Tests turn-taking logic, phase transitions, and agent switching.
"""

import pytest
from unittest.mock import MagicMock, patch


def test_initial_state_is_mc():
    """Turn manager should start with MC as current agent."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    assert manager.get_current_agent_type() == "mc"
    assert manager.turn_count == 0
    assert manager.phase == 1


def test_start_partner_turn():
    """Should successfully switch to partner agent."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()
    manager.start_partner_turn()

    assert manager.get_current_agent_type() == "partner"


def test_start_mc_turn():
    """Should successfully switch back to MC agent."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()
    manager.start_partner_turn()
    manager.start_mc_turn()

    assert manager.get_current_agent_type() == "mc"


def test_on_turn_complete_increments_count():
    """Turn count should increment on turn completion."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()
    initial_count = manager.turn_count

    manager.on_turn_complete()

    assert manager.turn_count == initial_count + 1


def test_phase_transition_at_turn_5():
    """Phase should transition from 1 to 2 after 5 turns."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    # Complete 5 turns
    for _ in range(5):
        manager.on_turn_complete()

    assert manager.phase == 2


def test_phase_remains_2_after_transition():
    """Phase should remain 2 after transition, not go to 3."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    # Complete 10 turns (well past phase transition)
    for _ in range(10):
        manager.on_turn_complete()

    assert manager.phase == 2


def test_get_current_agent():
    """Should return correct agent type string."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    assert manager.get_current_agent_type() in ["mc", "partner"]
    assert isinstance(manager.get_current_agent_type(), str)


def test_turn_count_tracking():
    """Turn count should accurately track number of completions."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    for i in range(1, 11):
        manager.on_turn_complete()
        assert manager.turn_count == i


def test_multiple_agent_switches():
    """Should handle multiple agent switches correctly."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    # MC → Partner → MC → Partner
    assert manager.get_current_agent_type() == "mc"
    manager.start_partner_turn()
    assert manager.get_current_agent_type() == "partner"
    manager.start_mc_turn()
    assert manager.get_current_agent_type() == "mc"
    manager.start_partner_turn()
    assert manager.get_current_agent_type() == "partner"


def test_phase_query_method():
    """Should have method to query current phase."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    # Phase is a property, not a method
    assert hasattr(manager, "phase")
    assert manager.phase == 1

    for _ in range(5):
        manager.on_turn_complete()

    assert manager.phase == 2


def test_turn_manager_reset():
    """Should be able to reset turn manager state."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    # Advance state
    manager.start_partner_turn()
    for _ in range(3):
        manager.on_turn_complete()

    # Reset
    manager.reset()

    assert manager.get_current_agent_type() == "mc"
    assert manager.turn_count == 0
    assert manager.phase == 1


def test_concurrent_turn_protection():
    """Should prevent concurrent turn modifications."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    # Attempting to start partner turn while already in partner turn
    manager.start_partner_turn()
    current_agent = manager.get_current_agent_type()
    manager.start_partner_turn()  # Should be idempotent or raise error

    assert manager.get_current_agent_type() == current_agent


@pytest.mark.skip(reason="Turn history tracking not yet implemented")
def test_turn_history_tracking():
    """Should track turn history for debugging."""
    from app.audio.turn_manager import AgentTurnManager

    manager = AgentTurnManager()

    manager.start_partner_turn()
    manager.on_turn_complete()
    manager.start_mc_turn()
    manager.on_turn_complete()

    assert hasattr(manager, "get_turn_history")
    history = manager.get_turn_history()
    assert len(history) >= 2
