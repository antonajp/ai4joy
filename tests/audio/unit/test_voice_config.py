"""
Unit tests for voice configuration module.
Tests voice selection for MC and Partner agents.
"""

import pytest
from unittest.mock import patch, MagicMock


def test_get_mc_voice_config():
    """MC agent should use Aoede voice configuration."""
    from app.audio.voice_config import get_voice_config

    config = get_voice_config(agent_type="mc")

    assert config is not None
    assert config.voice_name == "Aoede"
    assert config.agent_type == "mc"


def test_get_partner_voice_config():
    """Partner agent should use Puck voice configuration."""
    from app.audio.voice_config import get_voice_config

    config = get_voice_config(agent_type="partner")

    assert config is not None
    assert config.voice_name == "Puck"
    assert config.agent_type == "partner"


def test_voice_config_dataclass():
    """VoiceConfig dataclass should have correct attributes."""
    from app.audio.voice_config import VoiceConfig

    config = VoiceConfig(
        voice_name="Aoede",
        agent_type="mc",
    )

    assert config.voice_name == "Aoede"
    assert config.agent_type == "mc"
    assert hasattr(config, "voice_name")
    assert hasattr(config, "agent_type")


def test_invalid_agent_type_raises():
    """Unknown agent type should raise ValueError."""
    from app.audio.voice_config import get_voice_config

    with pytest.raises(ValueError, match="Invalid agent_type"):
        get_voice_config(agent_type="invalid_agent")


def test_mc_voice_stability():
    """MC voice configuration should be consistent across calls."""
    from app.audio.voice_config import get_voice_config

    config1 = get_voice_config(agent_type="mc")
    config2 = get_voice_config(agent_type="mc")

    assert config1.voice_name == config2.voice_name
    assert config1.agent_type == config2.agent_type


def test_partner_voice_stability():
    """Partner voice configuration should be consistent across calls."""
    from app.audio.voice_config import get_voice_config

    config1 = get_voice_config(agent_type="partner")
    config2 = get_voice_config(agent_type="partner")

    assert config1.voice_name == config2.voice_name
    assert config1.agent_type == config2.agent_type


def test_voice_differentiation():
    """MC and Partner should have different voices."""
    from app.audio.voice_config import get_voice_config

    mc_config = get_voice_config(agent_type="mc")
    partner_config = get_voice_config(agent_type="partner")

    assert mc_config.voice_name != partner_config.voice_name
    assert mc_config.voice_name == "Aoede"
    assert partner_config.voice_name == "Puck"


def test_get_all_voice_configs():
    """get_all_voice_configs should return configs for all agent types."""
    from app.audio.voice_config import get_all_voice_configs

    configs = get_all_voice_configs()

    assert "mc" in configs
    assert "partner" in configs
    assert configs["mc"].voice_name == "Aoede"
    assert configs["partner"].voice_name == "Puck"
