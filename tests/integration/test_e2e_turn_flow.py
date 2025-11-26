"""
End-to-End Integration Tests - Week 8 Production Readiness

These tests validate complete turn flow from API endpoint through to Firestore persistence.
They require running FastAPI application, real ADK credentials, and real Firestore database.

Test Coverage:
- TC-E2E-01: Complete 15-Turn Session
- TC-E2E-02: Error Handling Scenarios
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.session_manager import SessionManager


@pytest.mark.integration
@pytest.mark.skip(reason="Requires running FastAPI app with real infrastructure")
class TestE2ETurnFlow:
    """End-to-end integration tests for complete session flow"""

    @pytest.fixture
    async def async_client(self):
        """Async HTTP client for API testing"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.fixture
    def auth_headers(self):
        """Mock IAP authentication headers"""
        return {
            "X-Goog-Authenticated-User-Id": "e2e-test-user-123",
            "X-Goog-Authenticated-User-Email": "e2e-test@example.com",
        }

    @pytest.fixture
    async def cleanup_session(self):
        """Cleanup session after test"""
        session_ids = []

        def register_session(sid):
            session_ids.append(sid)

        yield register_session

        for sid in session_ids:
            manager = SessionManager()
            try:
                await manager.close_session(sid)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_tc_e2e_01_complete_15_turn_session(
        self, async_client, auth_headers, cleanup_session
    ):
        """
        TC-E2E-01: Complete 15-Turn Session

        Execute a full 15-turn session end-to-end validating:
        - Session creation
        - Turn execution with phase transitions
        - Coach feedback appearance
        - Session closure
        """
        response = await async_client.post(
            "/api/v1/session/start",
            json={"location": "E2E Test Spaceship Bridge"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        session_data = response.json()
        session_id = session_data["session_id"]
        cleanup_session(session_id)

        assert session_id is not None
        assert session_data["status"] == "initialized"
        assert session_data["location"] == "E2E Test Spaceship Bridge"

        user_inputs = [
            "Captain's log: We've just entered orbit around Mars.",
            "The crew is preparing for the landing sequence.",
            "I'm checking the fuel levels now.",
            "Everything looks nominal so far.",
            "Wait, there's an anomaly in the starboard thruster.",
            "We need to investigate this immediately.",
            "I'm running a diagnostic on the thruster system.",
            "The problem seems to be in the fuel injector.",
            "Can you help me with the repair protocol?",
            "Let's coordinate with mission control.",
            "The repair is taking longer than expected.",
            "We're making progress on the thruster issue.",
            "Almost there, just need to calibrate.",
            "The thruster is back online!",
            "Mission accomplished, ready for landing sequence.",
        ]

        turn_responses = []

        for turn_num, user_input in enumerate(user_inputs, start=1):
            turn_response = await async_client.post(
                f"/api/v1/session/{session_id}/turn",
                json={"user_input": user_input, "turn_number": turn_num},
                headers=auth_headers,
                timeout=30.0,
            )

            assert (
                turn_response.status_code == 200
            ), f"Turn {turn_num} failed: {turn_response.status_code}"

            data = turn_response.json()
            turn_responses.append(data)

            assert "partner_response" in data
            assert data[
                "partner_response"
            ], f"Partner response empty for turn {turn_num}"

            assert "room_vibe" in data
            assert "analysis" in data["room_vibe"]

            assert "current_phase" in data
            if turn_num <= 4:
                assert data["current_phase"] == 1, f"Turn {turn_num} should be Phase 1"
            else:
                assert data["current_phase"] == 2, f"Turn {turn_num} should be Phase 2"

            if turn_num >= 15:
                assert (
                    data["coach_feedback"] is not None
                ), f"Coach feedback missing at turn {turn_num}"
                assert (
                    len(data["coach_feedback"]) > 50
                ), "Coach feedback should be substantial"
            else:
                assert (
                    data.get("coach_feedback") is None
                ), f"Coach feedback should not appear before turn 15 (turn {turn_num})"

        get_response = await async_client.get(
            f"/api/v1/session/{session_id}", headers=auth_headers
        )

        assert get_response.status_code == 200
        session_info = get_response.json()
        assert session_info["turn_count"] == 15

        close_response = await async_client.post(
            f"/api/v1/session/{session_id}/close", headers=auth_headers
        )

        assert close_response.status_code == 200
        close_data = close_response.json()
        assert close_data["status"] == "closed"

    @pytest.mark.asyncio
    async def test_tc_e2e_02_error_handling(self, async_client, auth_headers):
        """
        TC-E2E-02: Error Handling Scenarios

        Validate error handling throughout the stack:
        - Invalid session ID
        - Out-of-sequence turn numbers
        - Unauthorized access
        """
        response = await async_client.post(
            "/api/v1/session/invalid-session-id/turn",
            json={"user_input": "Test input", "turn_number": 1},
            headers=auth_headers,
        )

        assert response.status_code == 404

        create_response = await async_client.post(
            "/api/v1/session/start",
            json={"location": "Error Test Arena"},
            headers=auth_headers,
        )

        session_id = create_response.json()["session_id"]

        try:
            out_of_sequence_response = await async_client.post(
                f"/api/v1/session/{session_id}/turn",
                json={"user_input": "Skipped turn", "turn_number": 5},
                headers=auth_headers,
            )

            assert out_of_sequence_response.status_code == 400

            wrong_user_headers = {
                "X-Goog-Authenticated-User-Id": "different-user-456",
                "X-Goog-Authenticated-User-Email": "different@example.com",
            }

            unauthorized_response = await async_client.post(
                f"/api/v1/session/{session_id}/turn",
                json={"user_input": "Unauthorized", "turn_number": 1},
                headers=wrong_user_headers,
            )

            assert unauthorized_response.status_code == 403

        finally:
            await async_client.post(
                f"/api/v1/session/{session_id}/close", headers=auth_headers
            )

    @pytest.mark.asyncio
    async def test_tc_e2e_03_session_retrieval(
        self, async_client, auth_headers, cleanup_session
    ):
        """
        TC-E2E-03: Session Retrieval

        Verify session information can be retrieved at any point.
        """
        create_response = await async_client.post(
            "/api/v1/session/start",
            json={"location": "Retrieval Test Zone"},
            headers=auth_headers,
        )

        session_id = create_response.json()["session_id"]
        cleanup_session(session_id)

        get_response = await async_client.get(
            f"/api/v1/session/{session_id}", headers=auth_headers
        )

        assert get_response.status_code == 200
        session_data = get_response.json()

        assert session_data["session_id"] == session_id
        assert session_data["location"] == "Retrieval Test Zone"
        assert session_data["turn_count"] == 0

        await async_client.post(
            f"/api/v1/session/{session_id}/turn",
            json={"user_input": "First turn", "turn_number": 1},
            headers=auth_headers,
            timeout=30.0,
        )

        get_after_turn = await async_client.get(
            f"/api/v1/session/{session_id}", headers=auth_headers
        )

        assert get_after_turn.status_code == 200
        updated_data = get_after_turn.json()
        assert updated_data["turn_count"] == 1

    @pytest.mark.asyncio
    async def test_tc_e2e_04_rate_limits(self, async_client, auth_headers):
        """
        TC-E2E-04: Rate Limit Status

        Verify rate limit endpoint returns current status.
        """
        response = await async_client.get("/api/v1/user/limits", headers=auth_headers)

        assert response.status_code == 200
        limits_data = response.json()

        assert "user_id" in limits_data
        assert "limits" in limits_data
        assert "daily_sessions_used" in limits_data["limits"]
        assert "concurrent_sessions_count" in limits_data["limits"]

    @pytest.mark.asyncio
    async def test_tc_e2e_05_health_endpoints(self, async_client):
        """
        TC-E2E-05: Health Endpoints

        Verify health and readiness endpoints work.
        """
        health_response = await async_client.get("/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "healthy"

        ready_response = await async_client.get("/ready")
        assert ready_response.status_code == 200
        ready_data = ready_response.json()
        assert ready_data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_tc_e2e_06_input_validation(
        self, async_client, auth_headers, cleanup_session
    ):
        """
        TC-E2E-06: Input Validation

        Verify API validates input parameters correctly.
        """
        invalid_location = await async_client.post(
            "/api/v1/session/start", json={"location": ""}, headers=auth_headers
        )

        assert invalid_location.status_code == 422

        valid_session = await async_client.post(
            "/api/v1/session/start",
            json={"location": "Valid Location"},
            headers=auth_headers,
        )

        session_id = valid_session.json()["session_id"]
        cleanup_session(session_id)

        empty_input = await async_client.post(
            f"/api/v1/session/{session_id}/turn",
            json={"user_input": "", "turn_number": 1},
            headers=auth_headers,
        )

        assert empty_input.status_code == 422

        too_long_input = await async_client.post(
            f"/api/v1/session/{session_id}/turn",
            json={"user_input": "A" * 1001, "turn_number": 1},
            headers=auth_headers,
        )

        assert too_long_input.status_code == 422


@pytest.mark.integration
@pytest.mark.skip(reason="Requires deployed Cloud Run service")
class TestDeployedE2E:
    """Tests for deployed Cloud Run service"""

    @pytest.fixture
    def service_url(self):
        """Cloud Run service URL"""
        import os

        return os.getenv("CLOUD_RUN_URL", "https://improv-olympics-service.run.app")

    @pytest.mark.asyncio
    async def test_deployed_health_check(self, service_url):
        """Verify deployed service responds to health checks"""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{service_url}/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_deployed_requires_auth(self, service_url):
        """Verify deployed service requires authentication"""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{service_url}/api/v1/session/start", json={"location": "Test"}
            )

            assert response.status_code in [401, 403]
