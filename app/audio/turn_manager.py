"""Turn Manager for Audio Session Analytics

This module manages turn counting for audio sessions. It provides a simple
interface to track conversation turns for analytics purposes.

Note: This is a simplified version that no longer manages multi-agent switching.
The audio orchestrator now uses a single MC agent for all interactions.
"""

from dataclasses import dataclass

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TurnState:
    """Current turn state in the audio session.

    Attributes:
        turn_count: Total number of completed turns in session
    """

    turn_count: int


class AgentTurnManager:
    """Manages turn counting for audio sessions.

    The turn manager provides simple turn counting functionality:
    - Tracks total turns in a session
    - Provides turn increment on completion
    - Supports session reset
    """

    def __init__(self, starting_turn_count: int = 0):
        """Initialize turn manager.

        Args:
            starting_turn_count: Initial turn count (0 for new sessions)
        """
        self._state = TurnState(turn_count=starting_turn_count)

        logger.info(
            "AgentTurnManager initialized",
            turn_count=self._state.turn_count,
        )

    @property
    def turn_count(self) -> int:
        """Get current turn count."""
        return self._state.turn_count

    def on_turn_complete(self) -> dict:
        """Handle turn completion.

        Increments turn count for analytics tracking.

        Returns:
            Status dict with:
            - status: "ok" on success
            - turn_count: Updated turn count
            - phase: Legacy field (always "phase_1" for backward compatibility)
            - phase_changed: Legacy field (always False for backward compatibility)

        Note:
            The phase and phase_changed fields are maintained for backward
            compatibility with the audio orchestrator's event processing.
            In the simplified IQS-63 architecture, the unified MC agent
            handles all scene work, so phases are no longer functional.
        """
        # Increment turn count
        self._state.turn_count += 1

        logger.debug(
            "Turn completed",
            turn_count=self._state.turn_count,
        )

        # Return phase_1 for backward compatibility (MC handles all scene work)
        return {
            "status": "ok",
            "turn_count": self._state.turn_count,
            "phase": "phase_1",
            "phase_changed": False,
        }

    def get_state(self) -> dict:
        """Get current turn manager state.

        Returns:
            Dictionary with current turn count
        """
        return {
            "turn_count": self._state.turn_count,
        }

    def reset(self, turn_count: int = 0) -> None:
        """Reset turn manager state.

        Args:
            turn_count: Turn count to reset to (default 0)
        """
        self._state = TurnState(turn_count=turn_count)

        logger.info(
            "AgentTurnManager reset",
            turn_count=turn_count,
        )
