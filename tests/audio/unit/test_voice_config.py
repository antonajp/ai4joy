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
    assert config.voice == "aoede"
    assert config.agent_type == "mc"
    assert config.model is not None


def test_get_partner_voice_config():
    """Partner agent should use Puck voice configuration."""
    from app.audio.voice_config import get_voice_config

    config = get_voice_config(agent_type="partner")

    assert config is not None
    assert config.voice == "puck"
    assert config.agent_type == "partner"
    assert config.model is not None


def test_voice_config_dataclass():
    """VoiceConfig dataclass should have correct attributes."""
    from app.audio.voice_config import VoiceConfig

    config = VoiceConfig(
        voice="aoede",
        agent_type="mc",
        model="gpt-4o-realtime-preview-2024-12-17"
    )

    assert config.voice == "aoede"
    assert config.agent_type == "mc"
    assert config.model == "gpt-4o-realtime-preview-2024-12-17"
    assert hasattr(config, "voice")
    assert hasattr(config, "agent_type")
    assert hasattr(config, "model")


def test_invalid_agent_type_raises():
    """Unknown agent type should raise ValueError."""
    from app.audio.voice_config import get_voice_config

    with pytest.raises(ValueError, match="Unknown agent type"):
        get_voice_config(agent_type="invalid_agent")


def test_mc_voice_stability():
    """MC voice configuration should be consistent across calls."""
    from app.audio.voice_config import get_voice_config

    config1 = get_voice_config(agent_type="mc")
    config2 = get_voice_config(agent_type="mc")

    assert config1.voice == config2.voice
    assert config1.agent_type == config2.agent_type


def test_partner_voice_stability():
    """Partner voice configuration should be consistent across calls."""
    from app.audio.voice_config import get_voice_config

    config1 = get_voice_config(agent_type="partner")
    config2 = get_voice_config(agent_type="partner")

    assert config1.voice == config2.voice
    assert config1.agent_type == config2.agent_type


def test_voice_config_uses_realtime_model():
    """Both agents should use OpenAI realtime preview model."""
    from app.audio.voice_config import get_voice_config

    mc_config = get_voice_config(agent_type="mc")
    partner_config = get_voice_config(agent_type="partner")

    assert "realtime" in mc_config.model.lower()
    assert "realtime" in partner_config.model.lower()


def test_voice_differentiation():
    """MC and Partner should have different voices."""
    from app.audio.voice_config import get_voice_config

    mc_config = get_voice_config(agent_type="mc")
    partner_config = get_voice_config(agent_type="partner")

    assert mc_config.voice != partner_config.voice
    assert mc_config.voice == "aoede"
    assert partner_config.voice == "puck"
