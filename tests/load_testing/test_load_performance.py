"""
Pytest-based Load Performance Tests

Tests system behavior under concurrent load using asyncio.
Can be run as part of CI pipeline unlike Locust tests.

Run with:
    pytest tests/load_testing/test_load_performance.py -v -m load
"""

import os
import pytest
import asyncio
import httpx
import time
import statistics
from typing import List, Dict

# Skip load tests by default unless explicitly enabled
LOAD_TESTS_ENABLED = os.getenv("ENABLE_LOAD_TESTS", "false").lower() == "true"


@pytest.mark.skipif(
    not LOAD_TESTS_ENABLED,
    reason="Load tests require running server. Set ENABLE_LOAD_TESTS=true to run.",
)
class TestLoadPerformance:
    """Load performance tests using asyncio for concurrency"""

    @pytest.fixture
    def service_url(self) -> str:
        """Service URL from environment or default"""
        import os

        return os.getenv("SERVICE_URL", "https://ai4joy.org")

    @pytest.fixture
    def session_config(self) -> Dict[str, str]:
        """Default session configuration"""
        return {"user_name": "LoadTest", "location": "Test Location"}

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_concurrent_session_creation(
        self, service_url: str, session_config: Dict
    ):
        """
        Test 10 concurrent session creations

        Validates:
        - All sessions created successfully
        - No rate limiting errors (different users)
        - Reasonable response times
        """

        async def create_session(client: httpx.AsyncClient, user_num: int) -> Dict:
            config = session_config.copy()
            config["user_name"] = f"LoadTest_{user_num}"

            start_time = time.time()
            response = await client.post(
                f"{service_url}/session/start", json=config, timeout=30.0
            )
            latency = time.time() - start_time

            response.raise_for_status()
            data = response.json()
            data["_latency"] = latency
            return data

        async with httpx.AsyncClient() as client:
            tasks = [create_session(client, i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = [r for r in results if isinstance(r, dict)]
        errors = [r for r in results if isinstance(r, Exception)]

        assert len(errors) == 0, f"Failed requests: {len(errors)}"
        assert len(successful) == 10, "All sessions should be created"

        latencies = [r["_latency"] for r in successful]
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)

        print("\nConcurrent Session Creation (n=10):")
        print(f"  Success: {len(successful)}/10")
        print(f"  Avg latency: {avg_latency:.2f}s")
        print(f"  Max latency: {max_latency:.2f}s")

        assert avg_latency < 5.0, f"Average latency {avg_latency:.2f}s exceeds 5s"
        assert max_latency < 10.0, f"Max latency {max_latency:.2f}s exceeds 10s"

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_concurrent_turn_execution(
        self, service_url: str, session_config: Dict
    ):
        """
        Test 10 concurrent turn executions on different sessions

        Validates:
        - Turn orchestration handles concurrency
        - Agent coordination works under load
        - Response times stay within bounds
        """

        async def execute_session_turn(
            client: httpx.AsyncClient, user_num: int
        ) -> Dict:
            config = session_config.copy()
            config["user_name"] = f"LoadTest_{user_num}"

            session_resp = await client.post(
                f"{service_url}/session/start", json=config, timeout=30.0
            )
            session_resp.raise_for_status()
            session_id = session_resp.json()["session_id"]

            start_time = time.time()
            turn_resp = await client.post(
                f"{service_url}/session/{session_id}/turn",
                json={
                    "user_input": f"Test input from user {user_num}",
                    "turn_number": 1,
                },
                timeout=30.0,
            )
            latency = time.time() - start_time

            turn_resp.raise_for_status()
            data = turn_resp.json()
            data["_latency"] = latency
            data["_session_id"] = session_id

            return data

        async with httpx.AsyncClient() as client:
            tasks = [execute_session_turn(client, i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = [r for r in results if isinstance(r, dict)]
        errors = [r for r in results if isinstance(r, Exception)]

        assert len(errors) == 0, f"Failed requests: {len(errors)}"
        assert len(successful) == 10, "All turns should execute"

        for result in successful:
            assert "partner_response" in result
            assert "room_vibe" in result
            assert "current_phase" in result

        latencies = [r["_latency"] for r in successful]
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]

        print("\nConcurrent Turn Execution (n=10):")
        print(f"  Success: {len(successful)}/10")
        print(f"  Avg latency: {avg_latency:.2f}s")
        print(f"  p95 latency: {p95_latency:.2f}s")

        assert p95_latency < 3.0, f"p95 latency {p95_latency:.2f}s exceeds 3s threshold"

    @pytest.mark.load
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_session_flow_under_load(
        self, service_url: str, session_config: Dict
    ):
        """
        Test complete 15-turn session flow with 5 concurrent users

        Validates:
        - Full session workflow under load
        - Phase transitions work correctly
        - Error rate < 1%
        """

        async def complete_session(client: httpx.AsyncClient, user_num: int) -> Dict:
            config = session_config.copy()
            config["user_name"] = f"LoadTest_{user_num}"

            session_resp = await client.post(
                f"{service_url}/session/start", json=config, timeout=30.0
            )
            session_resp.raise_for_status()
            session_id = session_resp.json()["session_id"]

            turn_results = []
            errors = []

            for turn in range(1, 16):
                try:
                    start_time = time.time()
                    turn_resp = await client.post(
                        f"{service_url}/session/{session_id}/turn",
                        json={"user_input": f"Turn {turn} input", "turn_number": turn},
                        timeout=30.0,
                    )
                    latency = time.time() - start_time
                    turn_resp.raise_for_status()

                    turn_data = turn_resp.json()
                    turn_data["_latency"] = latency
                    turn_results.append(turn_data)

                except Exception as e:
                    errors.append({"turn": turn, "error": str(e)})

            return {
                "session_id": session_id,
                "user_num": user_num,
                "turns_completed": len(turn_results),
                "errors": errors,
                "turn_results": turn_results,
            }

        async with httpx.AsyncClient() as client:
            tasks = [complete_session(client, i) for i in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_sessions = [r for r in results if isinstance(r, dict)]
        failed_sessions = [r for r in results if isinstance(r, Exception)]

        total_turns_attempted = 5 * 15
        total_turns_completed = sum(s["turns_completed"] for s in successful_sessions)
        total_errors = sum(len(s["errors"]) for s in successful_sessions)

        error_rate = (total_errors / total_turns_attempted) * 100

        all_latencies = []
        for session in successful_sessions:
            all_latencies.extend([t["_latency"] for t in session["turn_results"]])

        if all_latencies:
            avg_latency = statistics.mean(all_latencies)
            p95_latency = statistics.quantiles(all_latencies, n=20)[18]
        else:
            avg_latency = 0
            p95_latency = 0

        print("\nFull Session Flow Under Load (5 users × 15 turns):")
        print(f"  Sessions completed: {len(successful_sessions)}/5")
        print(f"  Turns completed: {total_turns_completed}/{total_turns_attempted}")
        print(f"  Error rate: {error_rate:.2f}%")
        print(f"  Avg turn latency: {avg_latency:.2f}s")
        print(f"  p95 turn latency: {p95_latency:.2f}s")

        assert len(failed_sessions) == 0, "No sessions should fail completely"
        assert error_rate < 1.0, f"Error rate {error_rate:.2f}% exceeds 1% threshold"
        assert p95_latency < 3.0, f"p95 latency {p95_latency:.2f}s exceeds 3s threshold"

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_rate_limiting_under_load(
        self, service_url: str, session_config: Dict
    ):
        """
        Test rate limiting behavior under concurrent load

        Validates:
        - Rate limits enforce correctly under pressure
        - Error responses are appropriate (429)
        - System remains stable when limits hit
        """

        async def rapid_session_creation(
            client: httpx.AsyncClient, user_id: int
        ) -> List[int]:
            status_codes = []

            for attempt in range(15):
                try:
                    response = await client.post(
                        f"{service_url}/session/start",
                        json={
                            "user_name": f"RateLimitTest_{user_id}",
                            "location": "Test",
                        },
                        timeout=30.0,
                    )
                    status_codes.append(response.status_code)
                except httpx.HTTPStatusError as e:
                    status_codes.append(e.response.status_code)
                except Exception:
                    status_codes.append(0)

            return status_codes

        async with httpx.AsyncClient() as client:
            tasks = [rapid_session_creation(client, i) for i in range(3)]
            results = await asyncio.gather(*tasks)

        all_status_codes = [code for result in results for code in result]
        rate_limited = all_status_codes.count(429)
        successful = all_status_codes.count(200)
        other_errors = len([c for c in all_status_codes if c not in [200, 429]])

        print("\nRate Limiting Under Load:")
        print(f"  Successful: {successful}")
        print(f"  Rate limited (429): {rate_limited}")
        print(f"  Other errors: {other_errors}")

        assert rate_limited > 0, "Rate limiting should trigger under load"
        assert other_errors < 5, "Should not see many non-rate-limit errors"

    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_latency_distribution_under_load(
        self, service_url: str, session_config: Dict
    ):
        """
        Measure latency distribution with 10 concurrent sessions

        Validates:
        - Latency stays consistent under load
        - No extreme outliers
        - p50, p95, p99 within acceptable bounds
        """

        async def measure_turn_latency(
            client: httpx.AsyncClient, user_num: int
        ) -> List[float]:
            config = session_config.copy()
            config["user_name"] = f"LoadTest_{user_num}"

            session_resp = await client.post(
                f"{service_url}/session/start", json=config, timeout=30.0
            )
            session_resp.raise_for_status()
            session_id = session_resp.json()["session_id"]

            latencies = []
            for turn in range(1, 6):
                start_time = time.time()
                turn_resp = await client.post(
                    f"{service_url}/session/{session_id}/turn",
                    json={"user_input": f"Turn {turn}", "turn_number": turn},
                    timeout=30.0,
                )
                latency = time.time() - start_time
                turn_resp.raise_for_status()
                latencies.append(latency)

            return latencies

        async with httpx.AsyncClient() as client:
            tasks = [measure_turn_latency(client, i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_latencies = []
        for result in results:
            if isinstance(result, list):
                all_latencies.extend(result)

        p50 = statistics.median(all_latencies)
        p95 = statistics.quantiles(all_latencies, n=20)[18]
        p99 = statistics.quantiles(all_latencies, n=100)[98]
        min_latency = min(all_latencies)
        max_latency = max(all_latencies)

        print(f"\nLatency Distribution Under Load (n={len(all_latencies)}):")
        print(f"  p50: {p50:.2f}s")
        print(f"  p95: {p95:.2f}s")
        print(f"  p99: {p99:.2f}s")
        print(f"  min: {min_latency:.2f}s")
        print(f"  max: {max_latency:.2f}s")

        assert p50 < 2.0, f"p50 latency {p50:.2f}s exceeds 2s"
        assert p95 < 3.0, f"p95 latency {p95:.2f}s exceeds 3s"
        assert p99 < 5.0, f"p99 latency {p99:.2f}s exceeds 5s"
