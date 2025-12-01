"""Audio Mixer for Multi-Stream Audio Processing

This module provides the AudioMixer class for mixing multiple audio streams
from different agents (MC, Partner, Room) with individual volume controls.

Key features:
- Per-agent volume control
- Volume normalization to prevent clipping
- Room agent at 30% volume (ambient background)
- Support for 24kHz 16-bit PCM audio
"""

from typing import Dict, Literal
import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Valid agent types for audio mixing
AgentType = Literal["mc", "partner", "room"]

# Default volume levels per agent
# Room is at 30% to create ambient background effect
DEFAULT_VOLUMES: Dict[str, float] = {
    "mc": 1.0,  # Full volume for host
    "partner": 1.0,  # Full volume for scene partner
    "room": 0.3,  # 30% for ambient background
}


class AudioMixer:
    """Mixes multiple audio streams with individual volume controls.

    The AudioMixer handles combining audio from multiple agents:
    - MC Agent: Primary host audio at full volume
    - Partner Agent: Scene partner audio at full volume
    - Room Agent: Ambient commentary at 30% volume

    Audio is processed as 24kHz 16-bit PCM mono format.
    """

    def __init__(self):
        """Initialize the AudioMixer with default volume settings."""
        self._volumes: Dict[str, float] = DEFAULT_VOLUMES.copy()
        logger.info(
            "AudioMixer initialized",
            default_volumes=self._volumes,
        )

    def get_volume(self, agent_type: str) -> float:
        """Get volume level for an agent type.

        Args:
            agent_type: Agent type ("mc", "partner", or "room")

        Returns:
            Volume level between 0.0 and 1.0

        Raises:
            ValueError: If agent_type is not recognized
        """
        if agent_type not in DEFAULT_VOLUMES:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Must be one of: {list(DEFAULT_VOLUMES.keys())}"
            )
        return self._volumes.get(agent_type, 1.0)

    def set_volume(self, agent_type: str, volume: float) -> None:
        """Set volume level for an agent type.

        Args:
            agent_type: Agent type ("mc", "partner", or "room")
            volume: Volume level (will be clamped to 0.0-1.0)

        Raises:
            ValueError: If agent_type is not recognized
        """
        if agent_type not in DEFAULT_VOLUMES:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Must be one of: {list(DEFAULT_VOLUMES.keys())}"
            )

        # Clamp volume to valid range
        clamped_volume = max(0.0, min(1.0, volume))

        self._volumes[agent_type] = clamped_volume
        logger.debug(
            "Volume updated",
            agent_type=agent_type,
            requested_volume=volume,
            actual_volume=clamped_volume,
        )

    def get_all_volumes(self) -> Dict[str, float]:
        """Get all volume settings.

        Returns:
            Dictionary of agent types to volume levels
        """
        return self._volumes.copy()

    def mix_streams(self, streams: Dict[str, bytes]) -> bytes:
        """Mix multiple audio streams with volume adjustment.

        Combines audio from multiple agents, applying volume levels
        and normalizing to prevent clipping.

        Args:
            streams: Dictionary mapping agent type to audio bytes
                    (16-bit PCM, 24kHz mono)

        Returns:
            Mixed audio bytes in same format

        Raises:
            ValueError: If audio data is malformed (odd byte count for 16-bit PCM)
        """
        if not streams:
            return b""

        # Convert all streams to numpy arrays and apply volume
        arrays = []
        for agent_type, audio_bytes in streams.items():
            if not audio_bytes:
                continue

            # Validate audio bytes - must be even length for 16-bit PCM
            if len(audio_bytes) % 2 != 0:
                logger.warning(
                    "Malformed audio data - odd byte count for 16-bit PCM",
                    agent_type=agent_type,
                    byte_count=len(audio_bytes),
                )
                # Truncate to even length to recover gracefully
                audio_bytes = audio_bytes[:-1]
                if not audio_bytes:
                    continue

            try:
                # Convert bytes to int16 array
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(
                    np.float32
                )

                # Apply volume
                volume = self._volumes.get(agent_type, 1.0)
                audio_array *= volume

                arrays.append(audio_array)
            except Exception as e:
                logger.error(
                    "Failed to process audio stream",
                    agent_type=agent_type,
                    error=str(e),
                )
                continue

        if not arrays:
            return b""

        # Find max length and pad shorter arrays
        max_length = max(len(arr) for arr in arrays)
        padded_arrays = []
        for arr in arrays:
            if len(arr) < max_length:
                padded = np.zeros(max_length, dtype=np.float32)
                padded[: len(arr)] = arr
                padded_arrays.append(padded)
            else:
                padded_arrays.append(arr)

        # Sum all arrays
        mixed = np.sum(padded_arrays, axis=0)

        # Normalize to prevent clipping
        max_val = np.max(np.abs(mixed))
        if max_val > 32767:
            mixed = mixed * (32767 / max_val)
            logger.debug(
                "Audio normalized to prevent clipping",
                original_max=float(max_val),
                normalized_max=32767,
            )

        # Convert back to int16 bytes
        mixed_int16 = mixed.astype(np.int16)
        return mixed_int16.tobytes()

    def mix_with_ambient(
        self,
        primary_audio: bytes,
        primary_agent: str,
        ambient_audio: bytes,
    ) -> bytes:
        """Mix primary audio with Room Agent ambient audio.

        Convenience method for mixing foreground audio with background
        ambient commentary.

        Args:
            primary_audio: Audio from MC or Partner agent
            primary_agent: Agent type ("mc" or "partner")
            ambient_audio: Audio from Room agent

        Returns:
            Mixed audio bytes
        """
        streams = {
            primary_agent: primary_audio,
            "room": ambient_audio,
        }
        return self.mix_streams(streams)
