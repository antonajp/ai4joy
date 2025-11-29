"""Audio encoding/decoding utilities for real-time streaming

This module provides PCM16/base64 encoding and decoding with security validation.
"""

import base64
import binascii

SAMPLE_RATE = 16000
CHANNELS = 1
BIT_DEPTH = 16
BYTES_PER_SAMPLE = BIT_DEPTH // 8
BYTES_PER_SECOND = SAMPLE_RATE * BYTES_PER_SAMPLE

# Security: Limit to 10MB base64 (~7.5MB audio = ~4 minutes at 16kHz 16-bit)
MAX_BASE64_LENGTH = 10 * 1024 * 1024
MAX_AUDIO_BYTES = 7.5 * 1024 * 1024


class AudioCodecError(Exception):
    """Raised when audio encoding/decoding fails."""

    pass


def encode_pcm16_to_base64(audio_bytes: bytes) -> str:
    """
    Encode PCM16 audio bytes to base64 string for transmission.

    Args:
        audio_bytes: Raw PCM16 audio data (16-bit signed integers, mono, 16kHz)

    Returns:
        Base64-encoded string representation of audio data

    Raises:
        AudioCodecError: If input is invalid or too large
    """
    if not isinstance(audio_bytes, bytes):
        raise AudioCodecError(f"Expected bytes, got {type(audio_bytes).__name__}")

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise AudioCodecError(
            f"Audio data too large: {len(audio_bytes)} bytes (max: {MAX_AUDIO_BYTES})"
        )

    return base64.b64encode(audio_bytes).decode("utf-8")


def decode_base64_to_pcm16(encoded: str) -> bytes:
    """
    Decode base64 string back to PCM16 audio bytes.

    Args:
        encoded: Base64-encoded audio data string

    Returns:
        Raw PCM16 audio bytes (16-bit signed integers, mono, 16kHz)

    Raises:
        AudioCodecError: If input is invalid, too large, or not valid base64
    """
    if not isinstance(encoded, str):
        raise AudioCodecError(f"Expected string, got {type(encoded).__name__}")

    if len(encoded) > MAX_BASE64_LENGTH:
        raise AudioCodecError(
            f"Encoded data too large: {len(encoded)} chars (max: {MAX_BASE64_LENGTH})"
        )

    try:
        decoded = base64.b64decode(encoded.encode("utf-8"))
    except binascii.Error as e:
        raise AudioCodecError(f"Invalid base64 encoding: {e}") from e

    # Validate PCM16 format (must be even number of bytes for 16-bit samples)
    if len(decoded) % BYTES_PER_SAMPLE != 0:
        raise AudioCodecError(
            f"Invalid PCM16 format: {len(decoded)} bytes is not divisible by {BYTES_PER_SAMPLE}"
        )

    return decoded
