"""
Unit tests for Ambient Audio module.
Tests sentiment-based triggers for Room Agent audio.

Test cases:
- TC-AMBIENT-01: AmbientAudioTrigger initializes
- TC-AMBIENT-02: Detect positive sentiment triggers
- TC-AMBIENT-03: Detect negative sentiment triggers
- TC-AMBIENT-04: Energy level detection
- TC-AMBIENT-05: Cooldown prevents rapid triggers
- TC-AMBIENT-06: Get trigger recommendations
- TC-AMBIENT-07: Reset cooldown state
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


def test_tc_ambient_01_initializes():
    """TC-AMBIENT-01: AmbientAudioTrigger should initialize."""
    from app.audio.ambient_audio import AmbientAudioTrigger

    trigger = AmbientAudioTrigger()

    assert trigger is not None
    assert hasattr(trigger, "should_trigger")
    assert hasattr(trigger, "get_commentary_prompt")


def test_tc_ambient_02_positive_sentiment_triggers():
    """TC-AMBIENT-02: Positive sentiment should trigger ambient audio."""
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger()

    # High positive sentiment should trigger
    result = trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.8,
    )

    assert result is True


def test_tc_ambient_03_negative_sentiment_triggers():
    """TC-AMBIENT-03: Negative sentiment should trigger ambient audio."""
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger()

    # Very negative sentiment should always trigger
    result = trigger.should_trigger(
        sentiment=SentimentLevel.VERY_NEGATIVE,
        energy_level=0.5,
    )

    assert result is True


def test_tc_ambient_04_energy_level_detection():
    """TC-AMBIENT-04: High energy should trigger ambient audio."""
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger()

    # High energy should trigger
    result = trigger.should_trigger(
        sentiment=SentimentLevel.NEUTRAL,
        energy_level=0.9,  # Very high energy
    )

    assert result is True


def test_tc_ambient_05_cooldown_prevents_rapid_triggers():
    """TC-AMBIENT-05: Cooldown should prevent rapid triggers."""
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger(cooldown_seconds=5.0)

    # First trigger should succeed
    result1 = trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.8,
    )
    assert result1 is True

    # Immediate second trigger should fail (cooldown)
    result2 = trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.8,
    )
    assert result2 is False


def test_tc_ambient_06_get_commentary_prompt():
    """TC-AMBIENT-06: Should generate appropriate commentary prompts."""
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger()

    # Get prompt for positive moment
    prompt = trigger.get_commentary_prompt(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.8,
        context="They just made a great connection",
    )

    assert prompt is not None
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_tc_ambient_07_reset_cooldown():
    """TC-AMBIENT-07: Reset should clear cooldown state."""
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger(cooldown_seconds=5.0)

    # Trigger once
    trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.8,
    )

    # Should be on cooldown
    assert trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.8,
    ) is False

    # Reset cooldown
    trigger.reset()

    # Should be able to trigger again
    assert trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.8,
    ) is True


def test_tc_ambient_08_neutral_low_energy_no_trigger():
    """TC-AMBIENT-08: Neutral sentiment with low energy should not trigger."""
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger()

    # Neutral, low energy shouldn't trigger ambient audio
    result = trigger.should_trigger(
        sentiment=SentimentLevel.NEUTRAL,
        energy_level=0.3,  # Low energy
    )

    assert result is False


def test_tc_ambient_09_sentiment_level_enum():
    """TC-AMBIENT-09: SentimentLevel enum should have expected values."""
    from app.audio.ambient_audio import SentimentLevel

    assert SentimentLevel.VERY_POSITIVE.value == 2
    assert SentimentLevel.POSITIVE.value == 1
    assert SentimentLevel.NEUTRAL.value == 0
    assert SentimentLevel.NEGATIVE.value == -1
    assert SentimentLevel.VERY_NEGATIVE.value == -2


def test_tc_ambient_10_prompt_varies_by_sentiment():
    """TC-AMBIENT-10: Commentary prompts should vary by sentiment."""
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger()

    positive_prompt = trigger.get_commentary_prompt(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.8,
        context="Great moment",
    )

    negative_prompt = trigger.get_commentary_prompt(
        sentiment=SentimentLevel.NEGATIVE,
        energy_level=0.3,
        context="Tension building",
    )

    # Prompts should be different for different sentiments
    assert positive_prompt != negative_prompt
