"""
Locust Load Testing for Improv Olympics ADK Multi-Agent System

Run with:
    locust -f locustfile.py --host=https://ai4joy.org

Configuration:
    - Target: 10 concurrent users
    - Wait time: 1-3 seconds between requests
    - Scenarios: session creation, turn execution, full session flow
"""

import random
from locust import HttpUser, TaskSet, task, between, events
from typing import Optional


class ImprovSessionBehavior(TaskSet):
    """User behavior simulating improv session interactions"""

    def on_start(self):
        """Initialize session state when user starts"""
        self.session_id: Optional[str] = None
        self.turn_number: int = 0
        self.max_turns: int = 15

    @task(3)
    def create_and_execute_session(self):
        """
        Simulate complete user session:
        1. Create session
        2. Execute 15 turns
        3. Close session

        Weight: 3 (most common scenario)
        """
        session_id = self._create_session()
        if not session_id:
            return

        for turn in range(1, self.max_turns + 1):
            success = self._execute_turn(session_id, turn)
            if not success:
                break

        self._close_session(session_id)

    @task(1)
    def single_turn_execution(self):
        """
        Execute single turn on existing session

        Weight: 1 (less common, used for rate limiting tests)
        """
        if not self.session_id or self.turn_number >= self.max_turns:
            self.session_id = self._create_session()
            self.turn_number = 0

        if self.session_id:
            self.turn_number += 1
            self._execute_turn(self.session_id, self.turn_number)

    def _create_session(self) -> Optional[str]:
        """Create new improv session"""
        locations = [
            "Mars Colony Alpha",
            "Underwater Research Station",
            "International Space Station",
            "Antarctic Research Base",
            "Desert Archaeological Dig",
        ]

        with self.client.post(
            "/session/start",
            json={
                "user_name": f"LoadTestUser_{random.randint(1000, 9999)}",
                "location": random.choice(locations),
            },
            catch_response=True,
            name="/session/start",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                session_id = data.get("session_id")
                response.success()
                return session_id
            else:
                response.failure(f"Failed to create session: {response.status_code}")
                return None

    def _execute_turn(self, session_id: str, turn_number: int) -> bool:
        """Execute single turn with agent orchestration"""
        user_inputs = [
            "Yes! And let's explore this situation further.",
            "I agree! And we should work together on this.",
            "Absolutely! And I have an idea about that.",
            "That's great! And maybe we can try something new.",
            "I see what you mean! And here's what I'm thinking.",
        ]

        with self.client.post(
            f"/session/{session_id}/turn",
            json={"user_input": random.choice(user_inputs), "turn_number": turn_number},
            catch_response=True,
            name="/session/turn",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "partner_response" in data and "room_vibe" in data:
                    response.success()
                    return True
                else:
                    response.failure("Missing expected response fields")
                    return False
            else:
                response.failure(f"Turn failed: {response.status_code}")
                return False

    def _close_session(self, session_id: str):
        """Close session and cleanup"""
        with self.client.post(
            f"/session/{session_id}/close", catch_response=True, name="/session/close"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to close session: {response.status_code}")


class RateLimitingBehavior(TaskSet):
    """Behavior to test rate limiting under load"""

    @task
    def rapid_session_creation(self):
        """Rapidly create sessions to test rate limits"""
        for _ in range(5):
            with self.client.post(
                "/session/start",
                json={"user_name": "RateLimitTest", "location": "Test Location"},
                catch_response=True,
                name="/session/start [rate-limit]",
            ) as response:
                if response.status_code == 429:
                    response.success()
                elif response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Unexpected status: {response.status_code}")


class ImprovUser(HttpUser):
    """
    Load test user simulating real user behavior

    Configuration:
        - wait_time: 1-3 seconds between requests (realistic user think time)
        - tasks: Weighted mix of behaviors
    """

    wait_time = between(1, 3)
    tasks = {ImprovSessionBehavior: 9, RateLimitingBehavior: 1}


class PerformanceMonitorUser(HttpUser):
    """
    User focused on performance monitoring

    Executes shorter sessions to measure latency under sustained load
    """

    wait_time = between(0.5, 1.5)

    @task
    def quick_turn_flow(self):
        """Execute 5-turn session quickly"""
        with self.client.post(
            "/session/start", json={"user_name": "PerfTest", "location": "Test"}
        ) as response:
            if response.status_code != 200:
                return

            session_id = response.json()["session_id"]

            for turn in range(1, 6):
                self.client.post(
                    f"/session/{session_id}/turn",
                    json={"user_input": f"Turn {turn}", "turn_number": turn},
                    name="/session/turn [quick]",
                )

            self.client.post(f"/session/{session_id}/close")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start"""
    print(f"Load test starting with target host: {environment.host}")
    print("Target concurrent users: 10")
    print("Expected p95 latency: < 3s")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion and summary"""
    print("\nLoad test completed")
    print("Check results for:")
    print("  - p95 latency < 3s")
    print("  - Error rate < 1%")
    print("  - Successful session completion rate")
