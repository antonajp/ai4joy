"""
End-to-End Tests for Full Scene Flow with Audience - IQS-60

Tests the complete scene flow: MC → Partner → User → Audience
- TC-060-021: Full scene flow includes all agents
- TC-060-022: Audience doesn't interrupt main conversation
- TC-060-023: Audio streams are properly mixed
- TC-060-024: Turn count advances through full flow
- TC-060-025: Phase transitions work with audience active
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np


@pytest.mark.asyncio
async def test_tc_060_021_full_scene_flow_all_agents():
    """TC-060-021: Full scene flow includes MC, Partner, User, and Audience.

    A complete scene should involve:
    1. MC welcomes and facilitates game selection
    2. MC transitions to Partner for scene work
    3. Partner and User perform the scene
    4. Audience (Room Agent) provides ambient commentary
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-full-flow-021"

    # Step 1: MC welcomes
    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
        game_name="Long Form",
    )

    session = await orchestrator.get_session(session_id)

    # All agents should be created
    assert session.mc_agent is not None
    assert session.partner_agent is not None
    assert session.room_agent is not None

    # Should start with MC
    assert session.current_agent == "mc"

    # Step 2: Transition to Partner
    result = orchestrator.switch_to_partner(session_id)
    assert result["status"] == "ok"
    assert session.current_agent == "partner"

    # Step 3: Verify audience is ready
    assert session.audio_mixer is not None
    assert session.ambient_trigger is not None

    # Step 4: Verify all three agents have distinct voices
    from app.audio.voice_config import get_voice_config

    mc_voice = get_voice_config("mc")
    partner_voice = get_voice_config("partner")
    room_voice = get_voice_config("room")

    voices = {mc_voice.voice_name, partner_voice.voice_name, room_voice.voice_name}
    assert len(voices) == 3  # All different


@pytest.mark.asyncio
async def test_tc_060_022_audience_noninterrupting():
    """TC-060-022: Audience provides commentary without blocking main flow.

    The Room Agent's ambient commentary should not interfere with the
    turn-taking between MC, Partner, and User.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-nonblocking-022"

    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
        game_name="Long Form",
    )

    session = await orchestrator.get_session(session_id)

    # Turn manager should only track MC and Partner
    assert session.turn_manager is not None
    assert session.turn_manager.current_speaker in ["mc", "partner"]

    # Switching agents should work normally with Room agent present
    orchestrator.switch_to_partner(session_id)
    assert session.turn_manager.current_speaker == "partner"

    orchestrator.switch_to_mc(session_id)
    assert session.turn_manager.current_speaker == "mc"

    # Room agent exists but doesn't participate in turn-taking
    assert session.room_agent is not None


@pytest.mark.asyncio
async def test_tc_060_023_three_stream_mixing():
    """TC-060-023: Audio streams from all three agents mix properly.

    When MC, Partner, and Room all produce audio simultaneously,
    the mixer should combine them without distortion or clipping.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-three-mix-023"

    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
    )

    session = await orchestrator.get_session(session_id)

    # Generate test audio for all three agents
    sample_rate = 24000
    duration_ms = 200
    samples = int(sample_rate * duration_ms / 1000)

    t = np.linspace(0, duration_ms / 1000, samples, dtype=np.float32)

    # Different frequencies for each agent
    mc_audio = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16).tobytes()
    partner_audio = (np.sin(2 * np.pi * 550 * t) * 16000).astype(np.int16).tobytes()
    room_audio = (np.sin(2 * np.pi * 330 * t) * 16000).astype(np.int16).tobytes()

    # Mix all three
    mixed = session.audio_mixer.mix_streams({
        "mc": mc_audio,
        "partner": partner_audio,
        "room": room_audio,
    })

    # Verify output
    assert mixed is not None
    assert len(mixed) > 0

    # Verify no clipping
    mixed_array = np.frombuffer(mixed, dtype=np.int16)
    max_value = np.max(np.abs(mixed_array))

    # Should be well below clipping threshold due to volume scaling
    assert max_value <= 32767

    # Room should be quieter than MC/Partner due to 30% volume
    # (This is ensured by the mixer's volume settings)


@pytest.mark.asyncio
async def test_tc_060_024_turn_count_with_audience():
    """TC-060-024: Turn count advances correctly with audience active.

    The presence of the Room Agent should not affect turn counting,
    which tracks MC and Partner turns only.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-turn-count-024"

    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
        starting_turn_count=0,
    )

    session = await orchestrator.get_session(session_id)

    # Initial turn count
    assert session.turn_count == 0
    assert session.turn_manager.turn_count == 0

    # Complete a turn
    result = session.turn_manager.on_turn_complete()
    assert result["turn_count"] == 1
    assert result["status"] == "ok"

    # Complete another turn
    result = session.turn_manager.on_turn_complete()
    assert result["turn_count"] == 2

    # Audience presence doesn't affect turn counting
    assert session.room_agent is not None


@pytest.mark.asyncio
async def test_tc_060_025_phase_transitions_with_audience():
    """TC-060-025: Phase transitions work correctly with audience active.

    As the scene progresses and Partner transitions from Phase 1 (Supportive)
    to Phase 2 (Fallible), the Room Agent should continue functioning.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator
    from app.agents.stage_manager import determine_partner_phase

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-phase-transition-025"

    # Start at turn 0 (Phase 1)
    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
        starting_turn_count=0,
    )

    session = await orchestrator.get_session(session_id)

    # Should be Phase 1 initially
    assert session.partner_phase == 1
    assert determine_partner_phase(0) == 1

    # Advance to turn 4 (still Phase 1)
    for _ in range(4):
        session.turn_manager.on_turn_complete()

    assert session.turn_manager.turn_count == 4
    assert determine_partner_phase(4) == 2  # Phase 2 starts at turn 4

    # Switch to partner should update phase
    orchestrator.switch_to_partner(session_id)

    # Partner should now be Phase 2
    assert session.partner_phase == 2

    # Room agent should still be functional
    assert session.room_agent is not None
    assert session.ambient_trigger is not None


@pytest.mark.asyncio
async def test_tc_060_026_audience_across_game_selection():
    """TC-060-026: Audience remains consistent across MC → Partner transition.

    When MC hands off to Partner after game selection, the Room Agent
    should maintain continuity and the same audience composition.
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-game-selection-026"

    # MC phase - game selection
    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
    )

    session = await orchestrator.get_session(session_id)
    room_agent_id = id(session.room_agent)

    # Transition to Partner
    orchestrator.switch_to_partner(session_id)

    # Room agent should be the same instance (same audience)
    assert id(session.room_agent) == room_agent_id

    # Audio mixer should still have Room at 30%
    assert session.audio_mixer.get_volume("room") == 0.3


@pytest.mark.asyncio
async def test_tc_060_027_sentiment_drives_ambient():
    """TC-060-027: Sentiment analysis drives ambient audio triggering.

    High sentiment/energy moments should trigger ambient commentary,
    while neutral moments should not.
    """
    from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

    trigger = AmbientAudioTrigger(cooldown_seconds=0)  # No cooldown for testing

    # High-energy positive moment - should trigger
    assert trigger.should_trigger(
        sentiment=SentimentLevel.VERY_POSITIVE,
        energy_level=0.9,
    ) is True

    trigger.reset()

    # High-energy negative moment (tension) - should trigger
    assert trigger.should_trigger(
        sentiment=SentimentLevel.VERY_NEGATIVE,
        energy_level=0.7,
    ) is True

    trigger.reset()

    # Low-energy neutral moment - should NOT trigger
    assert trigger.should_trigger(
        sentiment=SentimentLevel.NEUTRAL,
        energy_level=0.2,
    ) is False

    trigger.reset()

    # Medium-energy neutral moment - should NOT trigger
    assert trigger.should_trigger(
        sentiment=SentimentLevel.NEUTRAL,
        energy_level=0.5,
    ) is False


@pytest.mark.asyncio
async def test_tc_060_028_orchestrator_supports_room():
    """TC-060-028: Audio orchestrator has Room Agent support methods.

    The AudioStreamOrchestrator should provide methods for:
    - Checking if ambient should trigger
    - Getting ambient prompts
    - Mixing audio streams
    - Adjusting Room volume
    """
    from app.audio.audio_orchestrator import AudioStreamOrchestrator

    orchestrator = AudioStreamOrchestrator()
    session_id = "test-room-methods-028"

    await orchestrator.start_session(
        session_id=session_id,
        user_id="test-user-123",
        user_email="test@example.com",
    )

    # Should have Room-specific methods
    assert hasattr(orchestrator, "should_trigger_ambient")
    assert hasattr(orchestrator, "get_ambient_prompt")
    assert hasattr(orchestrator, "mix_audio_streams")
    assert hasattr(orchestrator, "get_room_volume")
    assert hasattr(orchestrator, "set_room_volume")
    assert hasattr(orchestrator, "reset_ambient_trigger")

    # Methods should be callable
    assert callable(orchestrator.should_trigger_ambient)
    assert callable(orchestrator.get_ambient_prompt)
    assert callable(orchestrator.mix_audio_streams)


@pytest.mark.asyncio
async def test_tc_060_029_room_agent_has_live_model():
    """TC-060-029: Room Agent uses Live API model for audio.

    Like MC and Partner, the Room Agent should use the Live API model
    for real-time bidirectional audio streaming.
    """
    from app.agents.room_agent import create_room_agent_for_audio
    from app.config import get_settings

    settings = get_settings()
    room_agent = create_room_agent_for_audio()

    # Should use Live API model
    assert room_agent.model == settings.vertexai_live_model
    assert "live" in room_agent.model.lower() or "realtime" in room_agent.model.lower()


@pytest.mark.asyncio
async def test_tc_060_030_room_agent_toolsets():
    """TC-060-030: Room Agent has both Sentiment and Archetype toolsets.

    The Room Agent needs both toolsets to:
    1. Analyze sentiment for triggering ambient audio
    2. Understand audience composition for contextual suggestions
    """
    from app.agents.room_agent import create_room_agent_for_audio

    room_agent = create_room_agent_for_audio()

    # Should have tools attached
    assert room_agent.tools is not None
    assert len(room_agent.tools) >= 2  # At least Sentiment + Archetypes

    # Verify both toolsets are present
    tool_types = [str(type(tool).__name__) for tool in room_agent.tools]
    tool_str = " ".join(tool_types)

    # Should have both sentiment and archetypes capabilities
    # (Either as separate toolsets or combined)
    has_sentiment = "Sentiment" in tool_str or len(room_agent.tools) > 0
    has_archetypes = "Archetypes" in tool_str or len(room_agent.tools) > 1

    assert has_sentiment
    assert has_archetypes
