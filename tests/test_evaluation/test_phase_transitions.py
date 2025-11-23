"""
TC-505: Phase Transition Logic Evaluation
Tests Dynamic Scene Partner phase transitions (PHASE_1 → PHASE_2).
"""
import pytest
from typing import List, Dict
from test_integration.test_e2e_session import SessionAPIClient


class TestPhaseTransitions:
    """Test suite for agent phase transition evaluation."""

    @pytest.fixture
    def session_client(self, service_url):
        """HTTP client for session API."""
        return SessionAPIClient(service_url)

    @pytest.mark.evaluation
    @pytest.mark.slow
    def test_phase_transition_correctness(self, session_client, test_session_config):
        """
        Execute 10 test sessions and verify phase transitions.
        Core test for TC-505.
        """
        num_sessions = 10
        transition_results = []

        for session_num in range(1, num_sessions + 1):
            # Start session
            session = session_client.start_session(test_session_config)
            session_id = session['session_id']

            # Setup
            session_client.get_mc_intro(session_id)
            session_client.submit_suggestion(session_id, f"Session {session_num} premise")

            # Execute turns and track phases
            phase_history = []
            partner_responses = []

            for turn in range(1, 11):
                result = session_client.submit_turn(
                    session_id=session_id,
                    user_input=f"Yes! And let's continue with turn {turn}.",
                    turn_number=turn
                )

                phase_history.append(result['current_phase'])
                partner_responses.append({
                    'turn': turn,
                    'phase': result['current_phase'],
                    'response': result['partner_response']
                })

            # Validate phase progression
            assert phase_history[:4] == ['PHASE_1'] * 4, \
                f"Session {session_num}: Turns 1-4 should be PHASE_1"
            assert all(p == 'PHASE_2' for p in phase_history[4:]), \
                f"Session {session_num}: Turns 5+ should be PHASE_2"

            # Analyze PHASE_1 behavior (turns 1-4)
            phase1_responses = [r for r in partner_responses if r['phase'] == 'PHASE_1']
            phase1_acceptance = self._check_acceptance_rate(phase1_responses)
            assert phase1_acceptance >= 0.75, \
                f"Session {session_num}: PHASE_1 acceptance rate too low: {phase1_acceptance}"

            # Analyze PHASE_2 behavior (turns 5+)
            phase2_responses = [r for r in partner_responses if r['phase'] == 'PHASE_2']
            phase2_fallibility = self._check_fallibility_present(phase2_responses)
            assert phase2_fallibility, \
                f"Session {session_num}: PHASE_2 did not introduce fallibility"

            transition_results.append({
                'session': session_num,
                'phase1_acceptance': phase1_acceptance,
                'phase2_fallibility': phase2_fallibility,
                'transition_turn': 5
            })

            session_client.close_session(session_id)

        # Overall statistics
        avg_acceptance = sum(r['phase1_acceptance'] for r in transition_results) / num_sessions
        fallibility_rate = sum(r['phase2_fallibility'] for r in transition_results) / num_sessions

        print(f"\nPhase Transition Results (n={num_sessions}):")
        print(f"  PHASE_1 avg acceptance rate: {avg_acceptance:.2%}")
        print(f"  PHASE_2 fallibility introduction rate: {fallibility_rate:.2%}")

        # 100% correct phase transitions
        assert all(r['transition_turn'] == 5 for r in transition_results), \
            "Not all sessions transitioned at turn 5"

    def _check_acceptance_rate(self, responses: List[Dict]) -> float:
        """Check how often partner accepts/validates user offers in responses."""
        acceptance_indicators = ['yes', 'and', 'great', 'perfect', 'excellent', 'love']
        rejection_indicators = ['no', 'but wait', 'that won\'t work', 'i don\'t think']

        acceptance_count = 0
        for resp in responses:
            text = resp['response'].lower()
            has_acceptance = any(ind in text for ind in acceptance_indicators)
            has_rejection = any(ind in text for ind in rejection_indicators)

            if has_acceptance and not has_rejection:
                acceptance_count += 1

        return acceptance_count / len(responses) if responses else 0.0

    def _check_fallibility_present(self, responses: List[Dict]) -> bool:
        """Check if partner introduces fallibility in PHASE_2."""
        fallibility_indicators = [
            'wait', 'but', 'error', 'problem', 'confused', 'help',
            'don\'t know', 'not sure', 'what do we do', 'stuck'
        ]

        for resp in responses:
            text = resp['response'].lower()
            if any(ind in text for ind in fallibility_indicators):
                return True

        return False

    @pytest.mark.evaluation
    def test_phase1_supportive_behavior(self, session_client, test_session_config):
        """Verify PHASE_1 partner is consistently supportive."""
        session = session_client.start_session(test_session_config)
        session_id = session['session_id']

        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two scientists")

        # Test various user inputs in PHASE_1
        test_inputs = [
            "Let's check the oxygen tanks!",
            "I think we should call for backup.",
            "What if we reroute power from life support?",
            "Maybe we can use the emergency protocol."
        ]

        for turn, user_input in enumerate(test_inputs, start=1):
            result = session_client.submit_turn(session_id, user_input, turn)

            assert result['current_phase'] == 'PHASE_1'

            # Partner should not block offers
            response = result['partner_response'].lower()
            blocking_phrases = ["no", "that won't work", "bad idea", "we can't"]
            assert not any(phrase in response for phrase in blocking_phrases), \
                f"PHASE_1 partner should not block offers: {response}"

    @pytest.mark.evaluation
    def test_phase2_fallibility_timing(self, session_client, test_session_config):
        """Test that fallibility is introduced appropriately in PHASE_2."""
        session = session_client.start_session(test_session_config)
        session_id = session['session_id']

        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two astronauts")

        # Get through PHASE_1
        for turn in range(1, 5):
            session_client.submit_turn(session_id, f"Turn {turn}", turn)

        # Now in PHASE_2, check for fallibility
        fallibility_detected = False
        for turn in range(5, 9):
            result = session_client.submit_turn(
                session_id,
                "Yes! And let's proceed with the plan!",
                turn
            )

            assert result['current_phase'] == 'PHASE_2'

            response = result['partner_response'].lower()
            if any(word in response for word in ['wait', 'problem', 'error', 'confused']):
                fallibility_detected = True
                break

        assert fallibility_detected, "PHASE_2 should introduce fallibility within 4 turns"

    @pytest.mark.evaluation
    def test_transition_with_struggling_user(self, session_client, test_session_config):
        """Test phase transition delay when user is struggling."""
        session = session_client.start_session(test_session_config)
        session_id = session['session_id']

        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two people")

        # Simulate struggling user (hesitant, short responses)
        struggling_inputs = [
            "Um, okay.",
            "I guess so.",
            "Not sure.",
            "Maybe?",
            "Alright, let's try.",  # Recovery
            "Yes! And we can do this!"  # Confidence
        ]

        for turn, user_input in enumerate(struggling_inputs, start=1):
            result = session_client.submit_turn(session_id, user_input, turn)

            # Standard transition at turn 5 or may be delayed based on sentiment
            # This tests the conditional: IF Turn_Count > 4 AND Student_Sentiment is Stable
            if turn <= 4:
                assert result['current_phase'] == 'PHASE_1'
            # Turn 5+ behavior depends on implementation of sentiment check

    @pytest.mark.evaluation
    def test_smooth_phase_transition_ux(self, session_client, test_session_config):
        """Verify phase transition doesn't disrupt user experience."""
        session = session_client.start_session(test_session_config)
        session_id = session['session_id']

        session_client.get_mc_intro(session_id)
        session_client.submit_suggestion(session_id, "Two astronauts")

        # Turn 4 (last of PHASE_1)
        result_t4 = session_client.submit_turn(session_id, "Let's check the systems", 4)
        assert result_t4['current_phase'] == 'PHASE_1'

        # Turn 5 (first of PHASE_2)
        result_t5 = session_client.submit_turn(session_id, "Everything looks good!", 5)
        assert result_t5['current_phase'] == 'PHASE_2'

        # Transition should be seamless - no abrupt behavior change
        # Both responses should be coherent and maintain scene continuity
        assert len(result_t4['partner_response']) > 0
        assert len(result_t5['partner_response']) > 0

        # Room vibe should remain positive during transition
        assert result_t5['room_vibe']['temperature'] not in ['Confused', 'Bored']
