"""Voice Configuration for Multi-Agent Audio Sessions

This module defines voice mappings for different agent types in real-time audio mode.
MC Agent uses Aoede (warm host voice), Partner Agent uses Puck (playful scene partner voice).
"""

from dataclasses import dataclass
from typing import Literal

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Agent type literals for type safety
AgentType = Literal["mc", "partner", "room"]

# Voice names for each agent type
# See: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini-live#voices
VOICE_NAMES = {
    "mc": "Aoede",  # Warm, welcoming host voice
    "partner": "Puck",  # Playful, energetic scene partner voice
    "room": "Charon",  # Deep, ambient voice for audience commentary
}


@dataclass
class VoiceConfig:
    """Voice configuration for an agent type.

    Attributes:
        voice_name: Name of the voice to use (Aoede or Puck)
        agent_type: Type of agent (mc or partner)
    """

    voice_name: str
    agent_type: AgentType

    def __post_init__(self):
        """Validate voice configuration."""
        if self.agent_type not in VOICE_NAMES:
            raise ValueError(
                f"Invalid agent_type: {self.agent_type}. "
                f"Must be one of: {list(VOICE_NAMES.keys())}"
            )

        # Ensure voice name matches the expected voice for this agent type
        expected_voice = VOICE_NAMES[self.agent_type]
        if self.voice_name != expected_voice:
            logger.warning(
                "Voice mismatch for agent type",
                agent_type=self.agent_type,
                expected_voice=expected_voice,
                actual_voice=self.voice_name,
            )


def get_voice_config(agent_type: AgentType) -> VoiceConfig:
    """Get voice configuration for an agent type.

    Args:
        agent_type: Type of agent (mc or partner)

    Returns:
        VoiceConfig with appropriate voice name for the agent

    Raises:
        ValueError: If agent_type is not recognized
    """
    if agent_type not in VOICE_NAMES:
        raise ValueError(
            f"Invalid agent_type: {agent_type}. "
            f"Must be one of: {list(VOICE_NAMES.keys())}"
        )

    voice_name = VOICE_NAMES[agent_type]

    logger.debug(
        "Voice configuration retrieved",
        agent_type=agent_type,
        voice_name=voice_name,
    )

    return VoiceConfig(
        voice_name=voice_name,
        agent_type=agent_type,
    )


def get_all_voice_configs() -> dict[AgentType, VoiceConfig]:
    """Get all voice configurations.

    Returns:
        Dictionary mapping agent types to their voice configurations
    """
    return {
        agent_type: get_voice_config(agent_type) for agent_type in VOICE_NAMES.keys()
    }
