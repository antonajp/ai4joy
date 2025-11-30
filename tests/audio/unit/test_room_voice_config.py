"""
Unit tests for Room Agent voice configuration.
Tests voice selection for Room agent audio mode.

Test cases:
- TC-ROOM-VOICE-01: Room agent voice config returns valid config
- TC-ROOM-VOICE-02: Room agent uses Charon voice (deep, ambient)
- TC-ROOM-VOICE-03: Room voice is distinct from MC and Partner
- TC-ROOM-VOICE-04: Voice config includes room in all configs
- TC-ROOM-VOICE-05: Room voice config is consistent across calls
"""

import pytest


def test_tc_room_voice_01_room_voice_config_returns_valid_config():
    """TC-ROOM-VOICE-01: Room agent should return valid voice configuration."""
    from app.audio.voice_config import get_voice_config

    config = get_voice_config(agent_type="room")

    assert config is not None
    assert config.agent_type == "room"
    assert config.voice_name is not None
    assert len(config.voice_name) > 0


def test_tc_room_voice_02_room_uses_charon_voice():
    """TC-ROOM-VOICE-02: Room agent should use Charon voice (deep, ambient)."""
    from app.audio.voice_config import get_voice_config

    config = get_voice_config(agent_type="room")

    # Charon is a deep, ambient voice suitable for background commentary
    assert config.voice_name == "Charon"


def test_tc_room_voice_03_room_voice_distinct_from_mc_partner():
    """TC-ROOM-VOICE-03: Room voice should be distinct from MC and Partner."""
    from app.audio.voice_config import get_voice_config

    mc_config = get_voice_config(agent_type="mc")
    partner_config = get_voice_config(agent_type="partner")
    room_config = get_voice_config(agent_type="room")

    # All three should have different voices
    assert mc_config.voice_name != partner_config.voice_name
    assert mc_config.voice_name != room_config.voice_name
    assert partner_config.voice_name != room_config.voice_name

    # Verify specific voices
    assert mc_config.voice_name == "Aoede"  # Warm host
    assert partner_config.voice_name == "Puck"  # Playful partner
    assert room_config.voice_name == "Charon"  # Deep ambient


def test_tc_room_voice_04_all_voice_configs_includes_room():
    """TC-ROOM-VOICE-04: get_all_voice_configs should include room."""
    from app.audio.voice_config import get_all_voice_configs

    configs = get_all_voice_configs()

    assert "mc" in configs
    assert "partner" in configs
    assert "room" in configs  # This is the new requirement
    assert configs["room"].voice_name == "Charon"


def test_tc_room_voice_05_room_voice_stability():
    """TC-ROOM-VOICE-05: Room voice configuration should be consistent."""
    from app.audio.voice_config import get_voice_config

    config1 = get_voice_config(agent_type="room")
    config2 = get_voice_config(agent_type="room")

    assert config1.voice_name == config2.voice_name
    assert config1.agent_type == config2.agent_type


def test_tc_room_voice_06_voice_config_validates_agent_type():
    """TC-ROOM-VOICE-06: VoiceConfig should validate room agent type."""
    from app.audio.voice_config import VoiceConfig

    # Should not raise for room type
    config = VoiceConfig(voice_name="Charon", agent_type="room")
    assert config.voice_name == "Charon"
    assert config.agent_type == "room"
