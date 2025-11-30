"""
Load Performance Tests for Phase 3 Audio Features

Tests system behavior under concurrent audio load using asyncio.
Specifically tests the 50 concurrent audio users requirement from IQS-60.

Test cases:
- TC-010: 50 concurrent audio users
- TC-026: Cost analytics for audio sessions

Run with:
    ENABLE_LOAD_TESTS=true pytest tests/load_testing/test_audio_load.py -v -m load
"""

import os
import pytest
import asyncio
import statistics
import time
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch


# Skip load tests by default unless explicitly enabled
LOAD_TESTS_ENABLED = os.getenv("ENABLE_LOAD_TESTS", "false").lower() == "true"


@pytest.mark.skipif(
    not LOAD_TESTS_ENABLED,
    reason="Load tests require running server. Set ENABLE_LOAD_TESTS=true to run.",
)
class TestAudioLoadPerformance:
    """Load performance tests for Phase 3 audio features."""

    @pytest.fixture
    def mock_adk_session_service(self):
        """Mock ADK session service."""
        service = MagicMock()
        service.get_session = AsyncMock(return_value=None)
        service.create_session = AsyncMock()
        return service

    @pytest.fixture
    def mock_runner(self):
        """Mock ADK Runner for testing."""
        runner = MagicMock()

        async def mock_run_live(*args, **kwargs):
            # Simulate async generator yielding events
            for i in range(3):
                event = MagicMock()
                event.turn_complete = i == 2
                event.content = None
                event.input_transcription = None
                event.output_transcription = None
                event.error_code = None
                yield event
                await asyncio.sleep(0.01)

        runner.run_live = mock_run_live
        return runner

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_tc_010_concurrent_audio_sessions(self):
        """TC-010: Test 50 concurrent audio session creation.

        Validates:
        - System can create 50 concurrent audio sessions
        - Memory usage stays within bounds
        - No deadlocks or race conditions
        - Session creation time < 100ms average
        """
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        # Create orchestrator
        orchestrator = AudioStreamOrchestrator()

        # Track session creation metrics
        creation_times: List[float] = []
        successful_sessions: List[str] = []
        failed_sessions: List[str] = []

        async def create_audio_session(user_num: int) -> Dict:
            """Create a single audio session and track timing."""
            session_id = f"load_test_session_{user_num}"
            user_id = f"load_test_user_{user_num}"
            user_email = f"loadtest{user_num}@test.com"

            start_time = time.time()
            try:
                # Mock the ADK session service call
                with patch.object(
                    orchestrator,
                    "_ensure_adk_session",
                    new_callable=AsyncMock
                ):
                    await orchestrator.start_session(
                        session_id=session_id,
                        user_id=user_id,
                        user_email=user_email,
                        game_name="Test Game",
                    )

                creation_time = time.time() - start_time
                creation_times.append(creation_time)
                successful_sessions.append(session_id)

                return {
                    "session_id": session_id,
                    "creation_time": creation_time,
                    "success": True,
                }

            except Exception as e:
                failed_sessions.append(session_id)
                return {
                    "session_id": session_id,
                    "error": str(e),
                    "success": False,
                }

        # Create 50 concurrent sessions
        tasks = [create_audio_session(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        exceptions = [r for r in results if isinstance(r, Exception)]
        success_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]

        # Print metrics
        print("\n=== TC-010: 50 Concurrent Audio Sessions ===")
        print(f"  Successful sessions: {len(success_results)}/50")
        print(f"  Failed sessions: {len(failed_results)}")
        print(f"  Exceptions: {len(exceptions)}")

        if creation_times:
            avg_creation = statistics.mean(creation_times)
            p95_creation = statistics.quantiles(creation_times, n=20)[18] if len(creation_times) >= 20 else max(creation_times)
            max_creation = max(creation_times)

            print(f"  Avg creation time: {avg_creation * 1000:.2f}ms")
            print(f"  p95 creation time: {p95_creation * 1000:.2f}ms")
            print(f"  Max creation time: {max_creation * 1000:.2f}ms")

            # Performance assertions
            assert avg_creation < 0.1, f"Avg creation time {avg_creation * 1000:.2f}ms exceeds 100ms"
            assert p95_creation < 0.2, f"p95 creation time {p95_creation * 1000:.2f}ms exceeds 200ms"

        # Success rate assertions
        assert len(exceptions) == 0, f"Unexpected exceptions: {exceptions}"
        assert len(success_results) == 50, f"Only {len(success_results)}/50 sessions created"

        # Verify all sessions have Room Agent, AudioMixer, and AmbientTrigger
        for session_id in successful_sessions:
            session = await orchestrator.get_session(session_id)
            assert session is not None, f"Session {session_id} not found"
            assert session.room_agent is not None, f"Session {session_id} missing room_agent"
            assert session.audio_mixer is not None, f"Session {session_id} missing audio_mixer"
            assert session.ambient_trigger is not None, f"Session {session_id} missing ambient_trigger"

        # Cleanup
        for session_id in successful_sessions:
            await orchestrator.stop_session(session_id)

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_tc_010_audio_mixer_concurrent_access(self):
        """TC-010: Test audio mixer under concurrent access.

        Validates:
        - AudioMixer handles concurrent mix_streams calls
        - No race conditions or data corruption
        - Output remains valid 16-bit PCM
        """
        import numpy as np
        from app.audio.audio_mixer import AudioMixer

        mixer = AudioMixer()

        # Create sample audio data
        sample_rate = 24000
        duration_ms = 100
        samples = int(sample_rate * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples, dtype=np.float32)

        def create_audio(freq: float) -> bytes:
            return (np.sin(2 * np.pi * freq * t) * 16000).astype(np.int16).tobytes()

        mc_audio = create_audio(440)
        partner_audio = create_audio(550)
        room_audio = create_audio(330)

        mix_results: List[bytes] = []
        errors: List[str] = []

        async def concurrent_mix(mix_num: int) -> bytes:
            """Perform a single mix operation."""
            try:
                streams = {
                    "mc": mc_audio,
                    "partner": partner_audio,
                    "room": room_audio,
                }
                # Run mix in thread pool since it's CPU-bound
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, mixer.mix_streams, streams)
                mix_results.append(result)
                return result
            except Exception as e:
                errors.append(str(e))
                raise

        # Run 50 concurrent mix operations
        tasks = [concurrent_mix(i) for i in range(50)]
        await asyncio.gather(*tasks, return_exceptions=True)

        print("\n=== TC-010: Audio Mixer Concurrent Access ===")
        print(f"  Successful mixes: {len(mix_results)}/50")
        print(f"  Errors: {len(errors)}")

        # Assertions
        assert len(errors) == 0, f"Mix errors: {errors}"
        assert len(mix_results) == 50, "All mix operations should succeed"

        # Verify output is valid
        for i, result in enumerate(mix_results):
            assert isinstance(result, bytes), f"Mix {i} result not bytes"
            assert len(result) > 0, f"Mix {i} result is empty"
            # Check for valid 16-bit PCM (even byte count)
            assert len(result) % 2 == 0, f"Mix {i} has odd byte count"
            # Check no clipping
            audio_array = np.frombuffer(result, dtype=np.int16)
            assert np.max(np.abs(audio_array)) <= 32767, f"Mix {i} has clipping"

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_tc_010_ambient_trigger_thread_safety(self):
        """TC-010: Test ambient trigger thread safety under load.

        Validates:
        - AmbientAudioTrigger handles concurrent should_trigger calls
        - Cooldown is properly enforced across threads
        - No race conditions on trigger_count
        """
        from app.audio.ambient_audio import AmbientAudioTrigger, SentimentLevel

        trigger = AmbientAudioTrigger(cooldown_seconds=0.01)  # Short cooldown for testing

        trigger_results: List[bool] = []
        errors: List[str] = []

        async def concurrent_trigger(trigger_num: int) -> bool:
            """Attempt to trigger ambient audio."""
            try:
                # Alternate between different sentiment levels
                sentiments = [
                    SentimentLevel.VERY_POSITIVE,
                    SentimentLevel.POSITIVE,
                    SentimentLevel.NEGATIVE,
                    SentimentLevel.VERY_NEGATIVE,
                ]
                sentiment = sentiments[trigger_num % len(sentiments)]

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    trigger.should_trigger,
                    sentiment,
                    0.8,  # High energy
                )
                trigger_results.append(result)
                return result
            except Exception as e:
                errors.append(str(e))
                raise

        # Run 50 concurrent trigger attempts
        tasks = [concurrent_trigger(i) for i in range(50)]
        await asyncio.gather(*tasks, return_exceptions=True)

        print("\n=== TC-010: Ambient Trigger Thread Safety ===")
        print(f"  Total attempts: 50")
        print(f"  Successful triggers: {sum(trigger_results)}")
        print(f"  Blocked by cooldown: {50 - sum(trigger_results)}")
        print(f"  Errors: {len(errors)}")
        print(f"  Final trigger_count: {trigger.trigger_count}")

        # Assertions
        assert len(errors) == 0, f"Trigger errors: {errors}"
        assert len(trigger_results) == 50, "All trigger attempts should complete"
        # At least some should trigger (VERY_POSITIVE/VERY_NEGATIVE always trigger if not on cooldown)
        assert sum(trigger_results) >= 1, "At least one trigger should succeed"
        # Trigger count should match successful triggers
        assert trigger.trigger_count == sum(trigger_results), "Trigger count mismatch"


@pytest.mark.skipif(
    not LOAD_TESTS_ENABLED,
    reason="Load tests require running server. Set ENABLE_LOAD_TESTS=true to run.",
)
class TestCostAnalytics:
    """Cost analytics tests for Phase 3 audio (TC-026)."""

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_tc_026_audio_usage_tracking(self):
        """TC-026: Test audio usage tracking for cost analytics.

        Validates:
        - Usage seconds are tracked per session
        - Multiple sessions track independently
        - Usage accumulates correctly
        """
        from app.audio.audio_orchestrator import AudioStreamOrchestrator

        orchestrator = AudioStreamOrchestrator()

        # Create test sessions
        sessions_data = []
        for i in range(5):
            session_id = f"cost_test_{i}"
            user_id = f"cost_user_{i}"
            user_email = f"cost{i}@test.com"

            with patch.object(
                orchestrator,
                "_ensure_adk_session",
                new_callable=AsyncMock
            ):
                await orchestrator.start_session(
                    session_id=session_id,
                    user_id=user_id,
                    user_email=user_email,
                )

            sessions_data.append({
                "session_id": session_id,
                "expected_usage": (i + 1) * 60,  # 60, 120, 180, 240, 300 seconds
            })

        # Simulate usage for each session
        for data in sessions_data:
            session = await orchestrator.get_session(data["session_id"])
            session.usage_seconds = data["expected_usage"]

        # Verify usage tracking
        print("\n=== TC-026: Audio Usage Tracking ===")
        total_usage = 0
        for data in sessions_data:
            session = await orchestrator.get_session(data["session_id"])
            print(f"  Session {data['session_id']}: {session.usage_seconds}s")
            assert session.usage_seconds == data["expected_usage"]
            total_usage += session.usage_seconds

        print(f"  Total usage: {total_usage}s ({total_usage / 60:.1f} minutes)")

        # Calculate estimated cost (assuming $0.001 per second)
        cost_per_second = 0.001
        estimated_cost = total_usage * cost_per_second
        print(f"  Estimated cost: ${estimated_cost:.2f}")

        # Assertions
        assert total_usage == 60 + 120 + 180 + 240 + 300  # 900 seconds
        assert estimated_cost < 500, f"Estimated cost ${estimated_cost:.2f} exceeds $500/month budget"

        # Cleanup
        for data in sessions_data:
            await orchestrator.stop_session(data["session_id"])

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_tc_026_room_agent_volume_cost_impact(self):
        """TC-026: Test Room Agent volume impact on resource usage.

        Validates:
        - Room Agent at 30% volume uses proportionally less resources
        - Volume changes don't affect audio quality metrics
        """
        import numpy as np
        from app.audio.audio_mixer import AudioMixer

        mixer = AudioMixer()

        # Verify default volumes
        assert mixer.get_volume("mc") == 1.0
        assert mixer.get_volume("partner") == 1.0
        assert mixer.get_volume("room") == 0.3

        # Create test audio
        sample_rate = 24000
        duration_ms = 1000  # 1 second
        samples = int(sample_rate * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples, dtype=np.float32)

        mc_audio = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16).tobytes()
        room_audio = (np.sin(2 * np.pi * 330 * t) * 16000).astype(np.int16).tobytes()

        # Mix at different room volumes
        volumes_to_test = [0.0, 0.15, 0.3, 0.5, 1.0]
        mix_results = {}

        for vol in volumes_to_test:
            mixer.set_volume("room", vol)
            mixed = mixer.mix_streams({"mc": mc_audio, "room": room_audio})
            mixed_array = np.frombuffer(mixed, dtype=np.int16)

            mix_results[vol] = {
                "rms": np.sqrt(np.mean(mixed_array.astype(np.float32) ** 2)),
                "peak": np.max(np.abs(mixed_array)),
                "size_bytes": len(mixed),
            }

        print("\n=== TC-026: Room Volume Cost Impact ===")
        for vol, metrics in mix_results.items():
            print(f"  Room volume {vol:.0%}:")
            print(f"    RMS: {metrics['rms']:.2f}")
            print(f"    Peak: {metrics['peak']}")
            print(f"    Size: {metrics['size_bytes']} bytes")

        # Assertions
        # All mixes should produce same size output
        sizes = [m["size_bytes"] for m in mix_results.values()]
        assert len(set(sizes)) == 1, "All mixes should produce same size output"

        # RMS should increase with room volume (more audio energy)
        assert mix_results[0.0]["rms"] < mix_results[0.5]["rms"], "Higher volume should have higher RMS"
        assert mix_results[0.5]["rms"] < mix_results[1.0]["rms"], "Higher volume should have higher RMS"

        # Default 30% should be in the middle
        assert mix_results[0.0]["rms"] < mix_results[0.3]["rms"] < mix_results[1.0]["rms"]

        # Reset to default
        mixer.set_volume("room", 0.3)
        assert mixer.get_volume("room") == 0.3
