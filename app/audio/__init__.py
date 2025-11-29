"""Audio module for real-time conversational features (Premium tier)

This module provides:
- AudioStreamOrchestrator: ADK Live API integration for streaming
- AudioWebSocketHandler: WebSocket connection management
- Premium middleware: Tier-based access control
- Audio codec utilities: PCM16/base64 encoding with security validation
"""

from app.audio.codec import (
    encode_pcm16_to_base64,
    decode_base64_to_pcm16,
    AudioCodecError,
)
from app.audio.premium_middleware import (
    AudioAccessResponse,
    FallbackMode,
    check_audio_access,
    track_audio_usage,
    get_fallback_mode,
)
from app.audio.audio_orchestrator import AudioStreamOrchestrator
from app.audio.websocket_handler import AudioWebSocketHandler, audio_handler

__all__ = [
    "encode_pcm16_to_base64",
    "decode_base64_to_pcm16",
    "AudioCodecError",
    "AudioAccessResponse",
    "FallbackMode",
    "check_audio_access",
    "track_audio_usage",
    "get_fallback_mode",
    "AudioStreamOrchestrator",
    "AudioWebSocketHandler",
    "audio_handler",
]
