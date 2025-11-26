"""
TC-301: Multi-Agent Response Latency
Measures end-to-end latency for agent orchestration.
"""

import pytest
import time
import statistics
from test_integration.test_e2e_session import SessionAPIClient


class TestLatency:
    """Test suite for performance and latency measurement."""

    @pytest.fixture
    def session_client(self, service_url):
        """HTTP client for session API."""
        return SessionAPIClient(service_url)

    @pytest.mark.performance
    @pytest.mark.slow
    def test_turn_latency_measurement(
        self, session_client, test_session_config, latency_thresholds
    ):
        """
        Measure latency for 50 user turns.
        Core test for TC-301.
        """
        # Setup session
        session = session_client.start_session(test_session_config)
        session_id = session["session_id"]
        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two astronauts")

        # Measure latency for 50 turns
        latencies = []
        for turn in range(1, 51):
            start_time = time.time()

            result = session_client.submit_turn(
                session_id=session_id,
                user_input=f"Yes! And let's try approach number {turn}!",
                turn_number=turn,
            )

            latency = time.time() - start_time
            latencies.append(latency)

            # Ensure we got valid response
            assert "partner_response" in result
            assert "room_vibe" in result

        # Calculate percentiles
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99 = statistics.quantiles(latencies, n=100)[98]  # 99th percentile

        print(f"\nLatency Results (n={len(latencies)}):")
        print(f"  p50: {p50:.2f}s")
        print(f"  p95: {p95:.2f}s")
        print(f"  p99: {p99:.2f}s")
        print(f"  min: {min(latencies):.2f}s")
        print(f"  max: {max(latencies):.2f}s")

        # Assert against thresholds
        assert p50 < latency_thresholds["p50"], (
            f"p50 latency {p50:.2f}s exceeds threshold {latency_thresholds['p50']}s"
        )
        assert p95 < latency_thresholds["p95"], (
            f"p95 latency {p95:.2f}s exceeds threshold {latency_thresholds['p95']}s"
        )
        assert p99 < latency_thresholds["p99"], (
            f"p99 latency {p99:.2f}s exceeds threshold {latency_thresholds['p99']}s"
        )

    @pytest.mark.performance
    def test_component_latency_breakdown(self, session_client, test_session_config):
        """Measure latency breakdown by component."""
        session = session_client.start_session(test_session_config)
        session_id = session["session_id"]

        # MC initialization
        start = time.time()
        session_client.get_mc_intro(session_id)
        mc_latency = time.time() - start
        print(f"MC initialization: {mc_latency:.2f}s")

        # Game selection
        start = time.time()
        session_client.submit_suggestion(session_id, "Two scientists")
        selection_latency = time.time() - start
        print(f"Game selection: {selection_latency:.2f}s")

        # Scene turn (Partner + Room)
        start = time.time()
        session_client.submit_turn(session_id, "Test input", 1)
        turn_latency = time.time() - start
        print(f"Scene turn: {turn_latency:.2f}s")

        # Coach feedback
        session_client.end_scene(session_id)
        start = time.time()
        session_client.get_coach_feedback(session_id)
        coach_latency = time.time() - start
        print(f"Coach feedback: {coach_latency:.2f}s")

        # All components should complete reasonably quickly
        assert mc_latency < 5.0
        assert selection_latency < 5.0
        assert turn_latency < 6.0  # Most critical for UX
        assert coach_latency < 10.0  # Can be longer, end-of-session

    @pytest.mark.performance
    def test_cold_start_vs_warm_latency(self, session_client, test_session_config):
        """Compare cold start vs warm request latency."""
        # Cold start (first session)
        start = time.time()
        session1 = session_client.start_session(test_session_config)
        cold_start_latency = time.time() - start

        session_client.close_session(session1["session_id"])

        # Wait a moment
        time.sleep(1)

        # Warm start (subsequent session)
        start = time.time()
        session2 = session_client.start_session(test_session_config)
        warm_start_latency = time.time() - start

        session_client.close_session(session2["session_id"])

        print(f"Cold start: {cold_start_latency:.2f}s")
        print(f"Warm start: {warm_start_latency:.2f}s")

        # Warm should be faster (unless cold start caching is excellent)
        # At minimum, both should complete in reasonable time
        assert cold_start_latency < 10.0
        assert warm_start_latency < 10.0

    @pytest.mark.performance
    def test_phase_transition_latency(self, session_client, test_session_config):
        """Measure latency impact of phase transitions."""
        session = session_client.start_session(test_session_config)
        session_id = session["session_id"]
        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two astronauts")

        phase1_latencies = []
        phase2_latencies = []

        # Measure turns 1-4 (PHASE_1)
        for turn in range(1, 5):
            start = time.time()
            session_client.submit_turn(session_id, f"Turn {turn}", turn)
            latency = time.time() - start
            phase1_latencies.append(latency)

        # Measure turns 5-8 (PHASE_2)
        for turn in range(5, 9):
            start = time.time()
            session_client.submit_turn(session_id, f"Turn {turn}", turn)
            latency = time.time() - start
            phase2_latencies.append(latency)

        avg_phase1 = statistics.mean(phase1_latencies)
        avg_phase2 = statistics.mean(phase2_latencies)

        print(f"PHASE_1 avg latency: {avg_phase1:.2f}s")
        print(f"PHASE_2 avg latency: {avg_phase2:.2f}s")

        # Phase transition shouldn't significantly impact latency
        assert abs(avg_phase1 - avg_phase2) < 2.0, (
            "Phase transition causes significant latency change"
        )

    @pytest.mark.performance
    @pytest.mark.slow
    def test_sustained_load_latency_degradation(
        self, session_client, test_session_config
    ):
        """Test latency degradation under sustained load."""
        session = session_client.start_session(test_session_config)
        session_id = session["session_id"]
        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two astronauts")

        # Measure latency in batches
        batch_size = 10
        num_batches = 5
        batch_latencies = []

        for batch in range(num_batches):
            batch_times = []
            for turn in range(batch * batch_size + 1, (batch + 1) * batch_size + 1):
                start = time.time()
                session_client.submit_turn(session_id, f"Turn {turn}", turn)
                batch_times.append(time.time() - start)

            avg_latency = statistics.mean(batch_times)
            batch_latencies.append(avg_latency)
            print(f"Batch {batch + 1} avg latency: {avg_latency:.2f}s")

        # Check for degradation
        first_batch_avg = batch_latencies[0]
        last_batch_avg = batch_latencies[-1]
        degradation_pct = ((last_batch_avg - first_batch_avg) / first_batch_avg) * 100

        print(f"Latency degradation: {degradation_pct:.1f}%")

        # Allow up to 20% degradation under sustained load
        assert degradation_pct < 20, (
            f"Latency degraded {degradation_pct:.1f}%, expected <20%"
        )

    @pytest.mark.performance
    def test_timeout_handling(self, session_client, test_session_config):
        """Test that requests timeout appropriately if latency is excessive."""
        session = session_client.start_session(test_session_config)
        session_id = session["session_id"]
        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two astronauts")

        # Normal request should complete well within timeout
        start = time.time()
        try:
            result = session_client.submit_turn(session_id, "Test", 1)
            latency = time.time() - start
            assert latency < 15.0  # Session client timeout
            assert result is not None
        except Exception as e:
            pytest.fail(f"Request timed out unexpectedly: {e}")
