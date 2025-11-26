"""
TC-201: End-to-End Session Flow
Tests complete session from initialization to coach feedback.
"""

import pytest
import requests
from typing import Dict, Any


class TestE2ESession:
    """Test suite for end-to-end session orchestration."""

    @pytest.fixture
    def session_client(self, service_url):
        """HTTP client for session API."""
        return SessionAPIClient(service_url)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_complete_session_flow(
        self, session_client, test_session_config, test_user_inputs
    ):
        """
        Execute complete session: initialization → MC → scene loop → coach.
        This is the primary E2E test for TC-201.
        """
        # 1. INITIALIZATION
        session = session_client.start_session(test_session_config)
        assert session["session_id"] is not None
        assert session["status"] == "initialized"
        session_id = session["session_id"]

        # 2. MC PHASE
        mc_response = session_client.get_mc_intro(session_id)
        assert (
            "welcome" in mc_response["message"].lower()
            or "hello" in mc_response["message"].lower()
        )
        assert (
            "location" in mc_response["message"].lower()
            or "suggestion" in mc_response["message"].lower()
        )

        # User provides relationship suggestion
        relationship = "Two scientists arguing over oxygen rations"
        game_selection = session_client.submit_suggestion(session_id, relationship)
        assert "game" in game_selection
        assert game_selection["game"]["name"] is not None

        # 3. SCENE LOOP (10 turns)
        turn_results = []
        for turn_num, user_input in enumerate(test_user_inputs, start=1):
            turn_result = session_client.submit_turn(
                session_id=session_id, user_input=user_input, turn_number=turn_num
            )

            # Validate turn structure
            assert "partner_response" in turn_result
            assert "room_vibe" in turn_result
            assert "current_phase" in turn_result

            # Check phase transitions
            if turn_num <= 4:
                assert (
                    turn_result["current_phase"] == "PHASE_1"
                ), f"Turn {turn_num} should be PHASE_1"
                # PHASE_1: Partner should be supportive
                assert (
                    "yes" in turn_result["partner_response"].lower()
                    or "and" in turn_result["partner_response"].lower()
                )
            else:
                assert (
                    turn_result["current_phase"] == "PHASE_2"
                ), f"Turn {turn_num} should be PHASE_2"
                # PHASE_2: Partner introduces fallibility (at least once)
                # This is checked in aggregate below

            turn_results.append(turn_result)

        # Validate PHASE_2 fallibility was introduced
        phase2_responses = [r["partner_response"] for r in turn_results[4:]]
        fallibility_indicators = ["wait", "but", "error", "problem", "confused", "help"]
        fallibility_found = any(
            indicator in response.lower()
            for response in phase2_responses
            for indicator in fallibility_indicators
        )
        assert fallibility_found, "PHASE_2 should introduce fallibility"

        # 4. SCENE END
        end_response = session_client.end_scene(session_id)
        assert end_response["status"] == "scene_complete"

        # 5. COACH PHASE
        coach_feedback = session_client.get_coach_feedback(session_id)
        assert "feedback" in coach_feedback
        assert len(coach_feedback["feedback"]) > 0

        # Coach should reference improv principles
        feedback_text = " ".join(coach_feedback["feedback"]).lower()
        principles = ["yes-and", "listening", "support", "recovery", "lead"]
        assert any(
            principle in feedback_text for principle in principles
        ), "Coach feedback should reference improv principles"

        # 6. SESSION CLOSE
        close_response = session_client.close_session(session_id)
        assert close_response["status"] == "closed"

    @pytest.mark.integration
    def test_session_initialization(self, session_client, test_session_config):
        """Test session initialization only."""
        session = session_client.start_session(test_session_config)

        assert session["session_id"] is not None
        assert session["status"] == "initialized"
        assert session["location"] == test_session_config["location"]

    @pytest.mark.integration
    def test_phase_transition_timing(self, session_client, test_session_config):
        """Test phase transitions occur at correct turn count."""
        session = session_client.start_session(test_session_config)
        session_id = session["session_id"]

        # Complete MC phase
        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two astronauts")

        # Execute turns and verify phase transitions
        for turn in range(1, 8):
            result = session_client.submit_turn(
                session_id=session_id, user_input=f"Turn {turn} input", turn_number=turn
            )

            expected_phase = "PHASE_1" if turn <= 4 else "PHASE_2"
            assert (
                result["current_phase"] == expected_phase
            ), f"Turn {turn}: expected {expected_phase}, got {result['current_phase']}"

    @pytest.mark.integration
    def test_room_vibe_check_present(self, session_client, test_session_config):
        """Test The Room provides vibe checks each turn."""
        session = session_client.start_session(test_session_config)
        session_id = session["session_id"]

        # Setup
        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two scientists")

        # Submit several turns
        for turn in range(1, 4):
            result = session_client.submit_turn(
                session_id=session_id,
                user_input="Yes! And let's continue the scene!",
                turn_number=turn,
            )

            assert "room_vibe" in result
            assert "temperature" in result["room_vibe"]
            assert result["room_vibe"]["temperature"] in [
                "Engaged",
                "Enthusiastic",
                "Neutral",
                "Bored",
                "Confused",
                "Tense",
            ]

    @pytest.mark.integration
    def test_invalid_session_id(self, session_client):
        """Test error handling for invalid session ID."""
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            session_client.submit_turn(
                session_id="invalid-session-id", user_input="Test", turn_number=1
            )
        assert exc_info.value.response.status_code in [400, 404]

    @pytest.mark.integration
    def test_session_timeout_handling(self, session_client, test_session_config):
        """Test session timeout behavior."""
        session = session_client.start_session(test_session_config)
        session_id = session["session_id"]

        # Check timeout configuration
        timeout_info = session_client.get_session_info(session_id)
        assert "timeout_minutes" in timeout_info or "expires_at" in timeout_info


class SessionAPIClient:
    """Helper client for session API interactions."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def start_session(self, config: Dict[str, Any]) -> Dict:
        """Start a new session."""
        response = self.session.post(
            f"{self.base_url}/session/start", json=config, timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_mc_intro(self, session_id: str) -> Dict:
        """Get MC introduction."""
        response = self.session.get(
            f"{self.base_url}/session/{session_id}/mc", timeout=10
        )
        response.raise_for_status()
        return response.json()

    def submit_suggestion(self, session_id: str, suggestion: str) -> Dict:
        """Submit user suggestion for game selection."""
        response = self.session.post(
            f"{self.base_url}/session/{session_id}/suggestion",
            json={"suggestion": suggestion},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def submit_turn(self, session_id: str, user_input: str, turn_number: int) -> Dict:
        """Submit user input for a turn."""
        response = self.session.post(
            f"{self.base_url}/session/{session_id}/turn",
            json={"user_input": user_input, "turn_number": turn_number},
            timeout=15,  # Longer timeout for agent orchestration
        )
        response.raise_for_status()
        return response.json()

    def end_scene(self, session_id: str) -> Dict:
        """End the current scene."""
        response = self.session.post(
            f"{self.base_url}/session/{session_id}/end", timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_coach_feedback(self, session_id: str) -> Dict:
        """Get coach feedback for completed session."""
        response = self.session.get(
            f"{self.base_url}/session/{session_id}/coach", timeout=15
        )
        response.raise_for_status()
        return response.json()

    def close_session(self, session_id: str) -> Dict:
        """Close and cleanup session."""
        response = self.session.post(
            f"{self.base_url}/session/{session_id}/close", timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_session_info(self, session_id: str) -> Dict:
        """Get session information."""
        response = self.session.get(f"{self.base_url}/session/{session_id}", timeout=10)
        response.raise_for_status()
        return response.json()
