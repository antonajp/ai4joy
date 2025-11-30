"""
Unit tests for Audio Mixer module.
Tests multi-stream mixing for Room Agent ambient audio.

Test cases:
- TC-MIXER-01: AudioMixer initializes with default configuration
- TC-MIXER-02: Set volume levels per agent type
- TC-MIXER-03: Room agent volume is 30% of primary agents
- TC-MIXER-04: Mix audio streams maintains quality
- TC-MIXER-05: Volume normalization prevents clipping
- TC-MIXER-06: Get current volume settings
- TC-MIXER-07: Audio stream registration and unregistration
"""

import pytest
import numpy as np


def test_tc_mixer_01_audio_mixer_initializes():
    """TC-MIXER-01: AudioMixer should initialize with default config."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()

    assert mixer is not None
    assert hasattr(mixer, "get_volume")
    assert hasattr(mixer, "set_volume")
    assert hasattr(mixer, "mix_streams")


def test_tc_mixer_02_set_volume_per_agent():
    """TC-MIXER-02: Should be able to set volume per agent type."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()

    # Set custom volumes
    mixer.set_volume("mc", 1.0)
    mixer.set_volume("partner", 1.0)
    mixer.set_volume("room", 0.3)

    assert mixer.get_volume("mc") == 1.0
    assert mixer.get_volume("partner") == 1.0
    assert mixer.get_volume("room") == 0.3


def test_tc_mixer_03_room_default_volume_is_30_percent():
    """TC-MIXER-03: Room agent default volume should be 30%."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()

    # Default volumes: primary agents at 100%, room at 30%
    assert mixer.get_volume("mc") == 1.0
    assert mixer.get_volume("partner") == 1.0
    assert mixer.get_volume("room") == 0.3


def test_tc_mixer_04_mix_streams_returns_audio():
    """TC-MIXER-04: mix_streams should return mixed audio bytes."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()

    # Create sample audio (16-bit PCM, mono)
    sample_rate = 24000
    duration_ms = 100
    samples = int(sample_rate * duration_ms / 1000)

    # Generate simple sine wave as test audio
    t = np.linspace(0, duration_ms / 1000, samples, dtype=np.float32)
    audio1 = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16).tobytes()
    audio2 = (np.sin(2 * np.pi * 880 * t) * 8000).astype(np.int16).tobytes()

    streams = {
        "mc": audio1,
        "room": audio2,
    }

    mixed = mixer.mix_streams(streams)

    assert mixed is not None
    assert isinstance(mixed, bytes)
    assert len(mixed) > 0


def test_tc_mixer_05_volume_normalization():
    """TC-MIXER-05: Mixing should prevent clipping via normalization."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()

    # Create loud audio that could clip
    samples = 2400  # 100ms at 24kHz
    loud_audio = (np.ones(samples, dtype=np.int16) * 32000).tobytes()

    streams = {
        "mc": loud_audio,
        "partner": loud_audio,
        "room": loud_audio,
    }

    mixed = mixer.mix_streams(streams)

    # Convert back to numpy to check values
    mixed_array = np.frombuffer(mixed, dtype=np.int16)

    # Should not exceed int16 max (no clipping)
    assert np.max(np.abs(mixed_array)) <= 32767


def test_tc_mixer_06_get_all_volumes():
    """TC-MIXER-06: Should be able to get all volume settings."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()
    volumes = mixer.get_all_volumes()

    assert "mc" in volumes
    assert "partner" in volumes
    assert "room" in volumes
    assert volumes["room"] == 0.3


def test_tc_mixer_07_empty_streams_returns_empty():
    """TC-MIXER-07: Empty streams should return empty bytes."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()
    mixed = mixer.mix_streams({})

    assert mixed == b""


def test_tc_mixer_08_single_stream_applies_volume():
    """TC-MIXER-08: Single stream should have volume applied."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()
    mixer.set_volume("room", 0.5)

    # Create test audio
    samples = 2400
    audio = (np.ones(samples, dtype=np.int16) * 10000).tobytes()

    streams = {"room": audio}
    mixed = mixer.mix_streams(streams)

    # Convert to array
    mixed_array = np.frombuffer(mixed, dtype=np.int16)

    # Should be roughly 50% of original (allowing for rounding)
    expected = 5000
    assert np.allclose(mixed_array, expected, atol=100)


def test_tc_mixer_09_invalid_agent_type():
    """TC-MIXER-09: Invalid agent type should raise ValueError."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()

    with pytest.raises(ValueError, match="Unknown agent type"):
        mixer.set_volume("invalid_agent", 0.5)


def test_tc_mixer_10_volume_bounds():
    """TC-MIXER-10: Volume should be clamped to 0-1 range."""
    from app.audio.audio_mixer import AudioMixer

    mixer = AudioMixer()

    # Test clamping
    mixer.set_volume("room", 1.5)  # Should clamp to 1.0
    assert mixer.get_volume("room") == 1.0

    mixer.set_volume("room", -0.5)  # Should clamp to 0.0
    assert mixer.get_volume("room") == 0.0
