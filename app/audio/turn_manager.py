"""Turn Manager for Multi-Agent Audio Coordination

This module manages turn-taking between MC and Partner agents during real-time
audio sessions, including phase transitions for adaptive difficulty.
"""

from typing import Literal
from dataclasses import dataclass

from app.agents.stage_manager import determine_partner_phase
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Type alias for agent types
AgentType = Literal["mc", "partner"]


@dataclass
class TurnState:
    """Current turn state in the audio session.

    Attributes:
        current_speaker: Which agent is currently speaking (mc or partner)
        turn_count: Total number of completed turns in session
        phase: Current partner phase (1 or 2)
        last_switch_turn: Turn number when we last switched speakers
    """

    current_speaker: AgentType
    turn_count: int
    phase: int
    last_switch_turn: int = 0


class AgentTurnManager:
    """Manages turn-taking between MC and Partner agents.

    The turn manager coordinates agent transitions during audio sessions:
    - MC Agent starts first (greeting and game selection)
    - After game selection, switches to Partner Agent for scene work
    - Tracks turn count for phase transitions (Phase 1: turns 1-4, Phase 2: turns 5+)
    - Manages agent switching with proper state tracking
    """

    def __init__(self, starting_turn_count: int = 0):
        """Initialize turn manager.

        Args:
            starting_turn_count: Initial turn count (0 for new sessions)
        """
        self._state = TurnState(
            current_speaker="mc",  # MC always starts
            turn_count=starting_turn_count,
            phase=determine_partner_phase(starting_turn_count),
        )

        logger.info(
            "AgentTurnManager initialized",
            current_speaker=self._state.current_speaker,
            turn_count=self._state.turn_count,
            phase=self._state.phase,
        )

    @property
    def current_speaker(self) -> AgentType:
        """Get current speaker agent type."""
        return self._state.current_speaker

    @property
    def turn_count(self) -> int:
        """Get current turn count."""
        return self._state.turn_count

    @property
    def phase(self) -> int:
        """Get current partner phase."""
        return self._state.phase

    def get_current_agent_type(self) -> AgentType:
        """Get the current active agent type.

        Returns:
            "mc" or "partner"
        """
        return self._state.current_speaker

    def start_mc_turn(self) -> dict:
        """Switch to MC Agent for hosting.

        Returns:
            Status dict with transition info
        """
        previous_speaker = self._state.current_speaker
        self._state.current_speaker = "mc"

        logger.info(
            "Switched to MC Agent",
            previous_speaker=previous_speaker,
            turn_count=self._state.turn_count,
        )

        return {
            "status": "ok",
            "current_speaker": "mc",
            "turn_count": self._state.turn_count,
            "phase": self._state.phase,
            "switched": previous_speaker != "mc",
        }

    def start_partner_turn(self) -> dict:
        """Switch to Partner Agent for scene work.

        Returns:
            Status dict with transition info
        """
        previous_speaker = self._state.current_speaker
        self._state.current_speaker = "partner"
        self._state.last_switch_turn = self._state.turn_count

        logger.info(
            "Switched to Partner Agent",
            previous_speaker=previous_speaker,
            turn_count=self._state.turn_count,
            phase=self._state.phase,
        )

        return {
            "status": "ok",
            "current_speaker": "partner",
            "turn_count": self._state.turn_count,
            "phase": self._state.phase,
            "switched": previous_speaker != "partner",
        }

    def on_turn_complete(self) -> dict:
        """Handle turn completion and check for phase transitions.

        Increments turn count and updates partner phase if needed.

        Returns:
            Status dict with turn info and phase transition flag
        """
        # Increment turn count
        self._state.turn_count += 1

        # Check if phase transition is needed (Phase 1: 0-3, Phase 2: 4+)
        new_phase = determine_partner_phase(self._state.turn_count)
        phase_changed = new_phase != self._state.phase

        if phase_changed:
            old_phase = self._state.phase
            self._state.phase = new_phase
            logger.info(
                "Partner phase transition",
                old_phase=old_phase,
                new_phase=new_phase,
                turn_count=self._state.turn_count,
            )

        logger.debug(
            "Turn completed",
            turn_count=self._state.turn_count,
            current_speaker=self._state.current_speaker,
            phase=self._state.phase,
            phase_changed=phase_changed,
        )

        return {
            "status": "ok",
            "turn_count": self._state.turn_count,
            "phase": self._state.phase,
            "phase_changed": phase_changed,
            "current_speaker": self._state.current_speaker,
        }

    def switch_to_agent(self, agent_type: AgentType) -> dict:
        """Switch to specified agent type.

        Args:
            agent_type: Agent to switch to ("mc" or "partner")

        Returns:
            Status dict with transition info

        Raises:
            ValueError: If agent_type is not "mc" or "partner"
        """
        if agent_type not in ["mc", "partner"]:
            raise ValueError(f"Invalid agent_type: {agent_type}")

        if agent_type == "mc":
            return self.start_mc_turn()
        else:
            return self.start_partner_turn()

    def get_state(self) -> dict:
        """Get current turn manager state.

        Returns:
            Dictionary with current state information
        """
        return {
            "current_speaker": self._state.current_speaker,
            "turn_count": self._state.turn_count,
            "phase": self._state.phase,
            "last_switch_turn": self._state.last_switch_turn,
        }

    def should_switch_to_partner(self, game_selected: bool) -> bool:
        """Determine if we should switch from MC to Partner.

        This happens after the MC has helped select a game and is ready
        to transition to scene work.

        Args:
            game_selected: Whether a game has been selected

        Returns:
            True if we should switch to Partner Agent
        """
        # Switch to partner if:
        # 1. Currently on MC
        # 2. A game has been selected
        # 3. We haven't switched yet (or have switched back)
        should_switch = (
            self._state.current_speaker == "mc"
            and game_selected
        )

        if should_switch:
            logger.debug(
                "Should switch to Partner Agent",
                game_selected=game_selected,
                turn_count=self._state.turn_count,
            )

        return should_switch

    def reset(self, turn_count: int = 0) -> None:
        """Reset turn manager state.

        Args:
            turn_count: Turn count to reset to (default 0)
        """
        self._state = TurnState(
            current_speaker="mc",
            turn_count=turn_count,
            phase=determine_partner_phase(turn_count),
        )

        logger.info(
            "AgentTurnManager reset",
            turn_count=turn_count,
            phase=self._state.phase,
        )
