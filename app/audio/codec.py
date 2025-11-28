"""Audio encoding/decoding utilities for real-time streaming"""

import base64

SAMPLE_RATE = 16000
CHANNELS = 1
BIT_DEPTH = 16


def encode_pcm16_to_base64(audio_bytes: bytes) -> str:
    """
    Encode PCM16 audio bytes to base64 string for transmission.

    Args:
        audio_bytes: Raw PCM16 audio data (16-bit signed integers, mono, 16kHz)

    Returns:
        Base64-encoded string representation of audio data
    """
    return base64.b64encode(audio_bytes).decode("utf-8")


def decode_base64_to_pcm16(encoded: str) -> bytes:
    """
    Decode base64 string back to PCM16 audio bytes.

    Args:
        encoded: Base64-encoded audio data string

    Returns:
        Raw PCM16 audio bytes (16-bit signed integers, mono, 16kHz)
    """
    return base64.b64decode(encoded.encode("utf-8"))
