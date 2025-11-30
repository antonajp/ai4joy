"""Ambient Audio Triggers for Room Agent

This module provides sentiment-based triggering for Room Agent audio.
It analyzes conversation sentiment and energy to determine when the
Room Agent should provide ambient commentary.

Key features:
- Sentiment-based triggering (positive moments, tension, etc.)
- Energy level detection
- Cooldown to prevent excessive commentary
- Commentary prompt generation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import threading
import time

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SentimentLevel(Enum):
    """Sentiment levels for triggering ambient audio.

    Values:
        VERY_POSITIVE: Excellent moment, high excitement (2)
        POSITIVE: Good moment, positive energy (1)
        NEUTRAL: Normal conversation (0)
        NEGATIVE: Tension or challenge (-1)
        VERY_NEGATIVE: Conflict or problem (-2)
    """

    VERY_POSITIVE = 2
    POSITIVE = 1
    NEUTRAL = 0
    NEGATIVE = -1
    VERY_NEGATIVE = -2


# Commentary prompt templates based on sentiment
COMMENTARY_TEMPLATES = {
    SentimentLevel.VERY_POSITIVE: [
        "The energy is electric! Capture this moment with excitement.",
        "There's a real connection happening. Express the room's delight.",
        "The audience is loving this! Share that enthusiasm briefly.",
    ],
    SentimentLevel.POSITIVE: [
        "Good energy in the room. Acknowledge the positive momentum.",
        "Things are clicking. Note the audience engagement.",
        "The crowd is with them. Express subtle appreciation.",
    ],
    SentimentLevel.NEUTRAL: [
        "Steady energy. The room is attentive.",
        "The audience is watching closely.",
        "Calm anticipation fills the space.",
    ],
    SentimentLevel.NEGATIVE: [
        "There's tension in the air. Acknowledge it subtly.",
        "The room feels the challenge. Note the shift.",
        "A moment of uncertainty. Express quiet concern.",
    ],
    SentimentLevel.VERY_NEGATIVE: [
        "The energy has dropped. Acknowledge the difficulty.",
        "The room feels the struggle. Be supportive.",
        "A tough moment. Express gentle understanding.",
    ],
}

# Energy level thresholds
HIGH_ENERGY_THRESHOLD = 0.75
LOW_ENERGY_THRESHOLD = 0.25


@dataclass
class TriggerState:
    """State for ambient audio triggering.

    Attributes:
        last_trigger_time: Timestamp of last trigger
        trigger_count: Total triggers in session
        lock: Thread lock for concurrent access
    """

    last_trigger_time: float = 0.0
    trigger_count: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


class AmbientAudioTrigger:
    """Determines when Room Agent should provide ambient commentary.

    Uses sentiment analysis and energy levels to decide when ambient
    commentary would enhance the experience without being intrusive.
    """

    def __init__(self, cooldown_seconds: float = 15.0):
        """Initialize the trigger.

        Args:
            cooldown_seconds: Minimum time between triggers
        """
        self._cooldown = cooldown_seconds
        self._state = TriggerState()
        self._template_index = 0
        logger.info(
            "AmbientAudioTrigger initialized",
            cooldown_seconds=cooldown_seconds,
        )

    def should_trigger(
        self,
        sentiment: SentimentLevel,
        energy_level: float,
    ) -> bool:
        """Determine if ambient audio should be triggered.

        Thread-safe implementation using locks to prevent race conditions
        in concurrent session scenarios.

        Args:
            sentiment: Current sentiment level
            energy_level: Energy level from 0.0 to 1.0

        Returns:
            True if ambient audio should play
        """
        # Validate energy_level input
        if not isinstance(energy_level, (int, float)):
            logger.warning(
                "Invalid energy_level type, defaulting to 0.5",
                energy_level=energy_level,
                energy_type=type(energy_level).__name__,
            )
            energy_level = 0.5
        energy_level = max(0.0, min(1.0, float(energy_level)))

        current_time = time.time()

        # Thread-safe access to trigger state
        with self._state.lock:
            # Check cooldown
            if current_time - self._state.last_trigger_time < self._cooldown:
                logger.debug(
                    "Trigger blocked by cooldown",
                    time_since_last=current_time - self._state.last_trigger_time,
                    cooldown=self._cooldown,
                )
                return False

            # Trigger conditions:
            # 1. Very positive or very negative sentiment (significant moments)
            # 2. High energy regardless of sentiment
            # 3. Sentiment shift (positive or negative, not neutral)
            should_trigger = False

            # Significant sentiment moments
            if sentiment in [SentimentLevel.VERY_POSITIVE, SentimentLevel.VERY_NEGATIVE]:
                should_trigger = True
                logger.debug(
                    "Trigger due to significant sentiment",
                    sentiment=sentiment.name,
                )

            # High energy
            elif energy_level >= HIGH_ENERGY_THRESHOLD:
                should_trigger = True
                logger.debug(
                    "Trigger due to high energy",
                    energy_level=energy_level,
                )

            # Non-neutral sentiment with moderate energy
            elif sentiment != SentimentLevel.NEUTRAL and energy_level >= 0.4:
                should_trigger = True
                logger.debug(
                    "Trigger due to sentiment shift",
                    sentiment=sentiment.name,
                    energy_level=energy_level,
                )

            if should_trigger:
                self._state.last_trigger_time = current_time
                self._state.trigger_count += 1
                logger.info(
                    "Ambient audio triggered",
                    sentiment=sentiment.name,
                    energy_level=energy_level,
                    trigger_count=self._state.trigger_count,
                )

            return should_trigger

    def get_commentary_prompt(
        self,
        sentiment: SentimentLevel,
        energy_level: float,
        context: Optional[str] = None,
    ) -> str:
        """Generate a prompt for Room Agent commentary.

        Args:
            sentiment: Current sentiment level
            energy_level: Energy level from 0.0 to 1.0
            context: Optional context about what's happening

        Returns:
            Prompt string for Room Agent
        """
        # Get template for this sentiment
        templates = COMMENTARY_TEMPLATES.get(
            sentiment, COMMENTARY_TEMPLATES[SentimentLevel.NEUTRAL]
        )

        # Rotate through templates
        template = templates[self._template_index % len(templates)]
        self._template_index += 1

        # Build prompt
        energy_desc = "high" if energy_level >= HIGH_ENERGY_THRESHOLD else (
            "low" if energy_level <= LOW_ENERGY_THRESHOLD else "moderate"
        )

        prompt = f"[Room Agent ambient commentary - {energy_desc} energy] {template}"

        if context:
            prompt += f" Context: {context}"

        prompt += " Keep your response to ONE brief sentence."

        logger.debug(
            "Generated commentary prompt",
            sentiment=sentiment.name,
            energy_level=energy_level,
            has_context=bool(context),
        )

        return prompt

    def reset(self) -> None:
        """Reset trigger state including cooldown (thread-safe)."""
        with self._state.lock:
            self._state.last_trigger_time = 0.0
            self._state.trigger_count = 0
        self._template_index = 0
        logger.info("AmbientAudioTrigger state reset")

    @property
    def trigger_count(self) -> int:
        """Get total number of triggers this session (thread-safe)."""
        with self._state.lock:
            return self._state.trigger_count

    @property
    def time_since_last_trigger(self) -> float:
        """Get time since last trigger in seconds (thread-safe)."""
        with self._state.lock:
            if self._state.last_trigger_time == 0:
                return float("inf")
            return time.time() - self._state.last_trigger_time
