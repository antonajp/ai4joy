"""
TC-502: Inside-Out Agent Evaluation
TC-503: Tool Trajectory Score Evaluation
Tests correct tool invocation and agent reasoning.
"""
import pytest
from typing import List, Dict, Tuple
from test_integration.test_e2e_session import SessionAPIClient


class TestToolTrajectories:
    """Test suite for tool trajectory analysis."""

    @pytest.fixture
    def session_client(self, service_url):
        """HTTP client for session API."""
        return SessionAPIClient(service_url)

    @pytest.fixture
    def golden_trajectories(self) -> Dict[str, List[str]]:
        """Define golden/expected tool trajectories."""
        return {
            'mc_phase': [
                'GameDatabase.query',
                'DemographicGenerator.generate'
            ],
            'scene_turn': [
                'DynamicScenePartner.generate_response',
                'SentimentGauge.analyze'
            ],
            'coach_phase': [
                'ImprovExpertDatabase.query',
                'CoachAgent.analyze_session'
            ]
        }

    @pytest.mark.evaluation
    @pytest.mark.integration
    def test_mc_phase_tool_trajectory(self, session_client, test_session_config):
        """Verify MC phase invokes GameDatabase and DemographicGenerator."""
        session = session_client.start_session(test_session_config)
        session_id = session['session_id']

        # Get MC intro (should trigger tool calls)
        session_client.get_mc_intro(session_id)

        # Submit suggestion (should trigger GameDatabase)
        session_client.submit_suggestion(session_id, "Two scientists")

        # Retrieve tool call logs
        tool_logs = session_client.get_tool_logs(session_id, phase='mc')

        # Verify GameDatabase was called
        assert any('GameDatabase' in log['tool'] for log in tool_logs), \
            "GameDatabase not called during MC phase"

        # Verify DemographicGenerator was called
        assert any('DemographicGenerator' in log['tool'] for log in tool_logs), \
            "DemographicGenerator not called during MC phase"

    @pytest.mark.evaluation
    @pytest.mark.integration
    def test_scene_turn_tool_trajectory(self, session_client, test_session_config):
        """Verify each scene turn invokes Partner generation and SentimentGauge."""
        session = session_client.start_session(test_session_config)
        session_id = session['session_id']

        # Setup
        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two astronauts")

        # Execute a turn
        session_client.submit_turn(session_id, "Let's fix the airlock!", 1)

        # Retrieve tool logs for this turn
        tool_logs = session_client.get_tool_logs(session_id, phase='scene', turn=1)

        # Verify DynamicScenePartner generated response
        assert any('DynamicScenePartner' in log['tool'] or
                  'generate_response' in log['tool']
                  for log in tool_logs), \
            "Partner generation not called during turn"

        # Verify SentimentGauge analyzed the exchange
        assert any('SentimentGauge' in log['tool'] for log in tool_logs), \
            "SentimentGauge not called during turn"

    @pytest.mark.evaluation
    @pytest.mark.integration
    def test_coach_phase_tool_trajectory(self, session_client, test_session_config):
        """Verify Coach phase invokes ImprovExpertDatabase."""
        session = session_client.start_session(test_session_config)
        session_id = session['session_id']

        # Complete a minimal session
        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two people")
        for turn in range(1, 4):
            session_client.submit_turn(session_id, f"Turn {turn}", turn)
        session_client.end_scene(session_id)

        # Get coach feedback
        session_client.get_coach_feedback(session_id)

        # Retrieve tool logs
        tool_logs = session_client.get_tool_logs(session_id, phase='coach')

        # Verify ImprovExpertDatabase was called
        assert any('ImprovExpertDatabase' in log['tool'] for log in tool_logs), \
            "ImprovExpertDatabase not called during Coach phase"

    @pytest.mark.evaluation
    @pytest.mark.integration
    def test_tool_parameter_correctness(self, session_client, test_session_config):
        """Verify tool parameters are correctly extracted."""
        session = session_client.start_session(test_session_config)
        session_id = session['session_id']

        # MC phase with specific location
        session_client.get_mc_intro(session_id)

        # Check DemographicGenerator parameters
        tool_logs = session_client.get_tool_logs(session_id, phase='mc')
        demo_gen_calls = [log for log in tool_logs if 'DemographicGenerator' in log['tool']]

        if demo_gen_calls:
            # Should have count parameter = 5 (for 5 archetypes)
            assert any(log['parameters'].get('count') == 5 for log in demo_gen_calls), \
                "DemographicGenerator should request 5 archetypes"

    @pytest.mark.evaluation
    @pytest.mark.integration
    def test_no_redundant_tool_calls(self, session_client, test_session_config):
        """Check for redundant or unnecessary tool invocations."""
        session = session_client.start_session(test_session_config)
        session_id = session['session_id']

        # Complete full session
        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two astronauts")
        for turn in range(1, 6):
            session_client.submit_turn(session_id, f"Turn {turn}", turn)

        # Get all tool logs
        all_tool_logs = session_client.get_tool_logs(session_id)

        # Check for duplicate calls with same parameters
        tool_signatures = []
        for log in all_tool_logs:
            signature = f"{log['tool']}:{str(sorted(log['parameters'].items()))}"
            tool_signatures.append(signature)

        # Count duplicates
        from collections import Counter
        signature_counts = Counter(tool_signatures)
        duplicates = {sig: count for sig, count in signature_counts.items() if count > 1}

        # Some duplication is expected (e.g., SentimentGauge on each turn)
        # But excessive duplication indicates inefficiency
        assert len(duplicates) < len(all_tool_logs) * 0.3, \
            f"Too many redundant tool calls: {duplicates}"

    @pytest.mark.evaluation
    @pytest.mark.integration
    @pytest.mark.slow
    def test_trajectory_accuracy_score(self, session_client, test_session_config,
                                       golden_trajectories):
        """
        Calculate trajectory accuracy score across 20 sessions.
        Core test for TC-503.
        """
        num_sessions = 20
        accuracy_scores = []

        for session_num in range(1, num_sessions + 1):
            session = session_client.start_session(test_session_config)
            session_id = session['session_id']

            # Execute standard session
            session_client.get_mc_intro(session_id)
            session_client.submit_suggestion(session_id, f"Session {session_num}")
            for turn in range(1, 6):
                session_client.submit_turn(session_id, f"Turn {turn}", turn)
            session_client.end_scene(session_id)
            session_client.get_coach_feedback(session_id)

            # Get actual tool trajectory
            actual_trajectory = self._extract_trajectory(
                session_client.get_tool_logs(session_id)
            )

            # Compare against golden trajectory
            accuracy = self._calculate_trajectory_accuracy(
                actual_trajectory,
                golden_trajectories
            )
            accuracy_scores.append(accuracy)

            session_client.close_session(session_id)

        # Calculate overall accuracy
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores)

        print(f"\nTrajectory Accuracy Results (n={num_sessions}):")
        print(f"  Average accuracy: {avg_accuracy:.2%}")
        print(f"  Min accuracy: {min(accuracy_scores):.2%}")
        print(f"  Max accuracy: {max(accuracy_scores):.2%}")

        # Assert >= 95% accuracy
        assert avg_accuracy >= 0.95, \
            f"Trajectory accuracy {avg_accuracy:.2%} below 95% threshold"

    @pytest.mark.evaluation
    @pytest.mark.integration
    @pytest.mark.slow
    def test_trajectory_efficiency_score(self, session_client, test_session_config,
                                         golden_trajectories):
        """
        Calculate trajectory efficiency score.
        Efficiency = necessary calls / actual calls
        """
        num_sessions = 10
        efficiency_scores = []

        for session_num in range(1, num_sessions + 1):
            session = session_client.start_session(test_session_config)
            session_id = session['session_id']

            # Execute session
            session_client.get_mc_intro(session_id)
            session_client.submit_suggestion(session_id, "Test")
            for turn in range(1, 4):
                session_client.submit_turn(session_id, f"Turn {turn}", turn)
            session_client.end_scene(session_id)
            session_client.get_coach_feedback(session_id)

            # Count tool calls
            tool_logs = session_client.get_tool_logs(session_id)
            actual_call_count = len(tool_logs)

            # Calculate expected minimum calls
            # MC: 2 (GameDB + DemoGen)
            # Scene: 2 per turn * 3 turns = 6 (Partner + Sentiment)
            # Coach: 1 (ImprovExpertDB)
            expected_min_calls = 2 + (2 * 3) + 1  # = 9

            efficiency = expected_min_calls / actual_call_count
            efficiency_scores.append(efficiency)

            session_client.close_session(session_id)

        avg_efficiency = sum(efficiency_scores) / len(efficiency_scores)

        print(f"\nTrajectory Efficiency Results (n={num_sessions}):")
        print(f"  Average efficiency: {avg_efficiency:.2%}")

        # Assert >= 90% efficiency
        assert avg_efficiency >= 0.90, \
            f"Trajectory efficiency {avg_efficiency:.2%} below 90% threshold"

    def _extract_trajectory(self, tool_logs: List[Dict]) -> List[str]:
        """Extract ordered list of tool calls from logs."""
        return [log['tool'] for log in tool_logs]

    def _calculate_trajectory_accuracy(self, actual: List[str],
                                       golden: Dict[str, List[str]]) -> float:
        """Calculate accuracy of actual trajectory vs golden."""
        # Flatten golden trajectories
        expected_tools = []
        for phase_tools in golden.values():
            expected_tools.extend(phase_tools)

        # Count correct tool calls
        correct_calls = 0
        for tool in actual:
            if any(expected in tool for expected in expected_tools):
                correct_calls += 1

        return correct_calls / len(actual) if actual else 0.0


# Extend SessionAPIClient with tool log retrieval
# This would be added to the actual SessionAPIClient class
# Shown here as standalone function for clarity

def get_tool_logs_extension(session_client, session_id: str,
                            phase: str = None, turn: int = None) -> List[Dict]:
    """
    Retrieve tool invocation logs for a session.
    This is a mock - actual implementation depends on observability setup.
    """
    # In real implementation, this would query Cloud Logging or
    # a dedicated observability endpoint
    #
    # response = session_client.session.get(
    #     f"{session_client.base_url}/session/{session_id}/tools",
    #     params={'phase': phase, 'turn': turn},
    #     timeout=10
    # )
    # response.raise_for_status()
    # return response.json()['tool_logs']

    pytest.skip("Tool log retrieval requires observability implementation")
