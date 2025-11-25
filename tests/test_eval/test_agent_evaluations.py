"""Pytest-based Agent Evaluation Tests

This test module integrates with pytest and the ADK evaluation framework
to test agent quality across different scenarios.

Usage:
    pytest tests/test_eval/test_agent_evaluations.py
    pytest tests/test_eval/test_agent_evaluations.py -m evaluation
    pytest tests/test_eval/test_agent_evaluations.py -m eval_phase1
    pytest tests/test_eval/test_agent_evaluations.py -k phase2
"""
import pytest
from pathlib import Path

from tests.test_eval.eval_runner import (
    EvaluationRunner,
    EvaluationConfig,
    ScenarioLoader,
    AgentFactory,
    ResponseValidator
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


@pytest.fixture(scope="module")
def evaluation_runner():
    """Create evaluation runner for tests"""
    return EvaluationRunner()


@pytest.fixture(scope="module")
def scenario_loader():
    """Create scenario loader for tests"""
    return ScenarioLoader()


@pytest.fixture(scope="module")
def eval_config():
    """Load evaluation configuration"""
    return EvaluationConfig()


@pytest.mark.evaluation
class TestPhase1Evaluation:
    """Tests for Phase 1 (Supportive) Partner Agent behavior"""

    @pytest.mark.asyncio
    @pytest.mark.eval_phase1
    async def test_phase1_basic_yes_and(self, evaluation_runner, scenario_loader):
        """Test Phase 1 basic 'Yes, and' response"""
        scenarios = scenario_loader.get_scenarios_by_category('phase1_basic_yes_and')
        assert len(scenarios) > 0, "No phase1_basic_yes_and scenarios found"

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"
        assert result.response, "Response should not be empty"
        assert len(result.response) >= 20, "Response too short"

    @pytest.mark.asyncio
    @pytest.mark.eval_phase1
    async def test_phase1_relationship_building(self, evaluation_runner, scenario_loader):
        """Test Phase 1 relationship establishment"""
        scenarios = scenario_loader.get_scenarios_by_category('phase1_relationship')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"
        assert 'sister' in result.response.lower() or 'family' in result.response.lower()

    @pytest.mark.asyncio
    @pytest.mark.eval_phase1
    async def test_phase1_location_acceptance(self, evaluation_runner, scenario_loader):
        """Test Phase 1 accepts and builds on location"""
        scenarios = scenario_loader.get_scenarios_by_category('phase1_location')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"

    @pytest.mark.asyncio
    @pytest.mark.eval_phase1
    async def test_phase1_emotional_support(self, evaluation_runner, scenario_loader):
        """Test Phase 1 supportive emotional response"""
        scenarios = scenario_loader.get_scenarios_by_category('phase1_emotional')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"

    @pytest.mark.asyncio
    @pytest.mark.eval_phase1
    @pytest.mark.slow
    async def test_all_phase1_scenarios(self, evaluation_runner, scenario_loader):
        """Run all Phase 1 scenarios"""
        scenarios = scenario_loader.get_scenarios_by_category('phase1')

        results = []
        for scenario in scenarios:
            result = await evaluation_runner.run_single_evaluation(scenario)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        success_rate = passed / total if total > 0 else 0.0

        logger.info(
            "Phase 1 evaluation complete",
            passed=passed,
            total=total,
            success_rate=success_rate
        )

        assert success_rate >= 0.75, f"Phase 1 success rate too low: {success_rate:.2%}"


@pytest.mark.evaluation
class TestPhase2Evaluation:
    """Tests for Phase 2 (Fallible) Partner Agent behavior"""

    @pytest.mark.asyncio
    @pytest.mark.eval_phase2
    async def test_phase2_realistic_friction(self, evaluation_runner, scenario_loader):
        """Test Phase 2 creates realistic friction"""
        scenarios = scenario_loader.get_scenarios_by_category('phase2_realistic')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"
        assert result.response, "Response should not be empty"

    @pytest.mark.asyncio
    @pytest.mark.eval_phase2
    async def test_phase2_point_of_view(self, evaluation_runner, scenario_loader):
        """Test Phase 2 has strong point of view"""
        scenarios = scenario_loader.get_scenarios_by_category('phase2_point_of_view')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"

    @pytest.mark.asyncio
    @pytest.mark.eval_phase2
    async def test_phase2_unexpected_choice(self, evaluation_runner, scenario_loader):
        """Test Phase 2 makes unexpected but justifiable choices"""
        scenarios = scenario_loader.get_scenarios_by_category('phase2_unexpected')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"

    @pytest.mark.asyncio
    @pytest.mark.eval_phase2
    @pytest.mark.slow
    async def test_all_phase2_scenarios(self, evaluation_runner, scenario_loader):
        """Run all Phase 2 scenarios"""
        scenarios = scenario_loader.get_scenarios_by_category('phase2')

        results = []
        for scenario in scenarios:
            result = await evaluation_runner.run_single_evaluation(scenario)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        success_rate = passed / total if total > 0 else 0.0

        logger.info(
            "Phase 2 evaluation complete",
            passed=passed,
            total=total,
            success_rate=success_rate
        )

        assert success_rate >= 0.70, f"Phase 2 success rate too low: {success_rate:.2%}"


@pytest.mark.evaluation
class TestCoachEvaluation:
    """Tests for Coach Agent feedback behavior"""

    @pytest.mark.asyncio
    @pytest.mark.eval_coach
    async def test_coach_feedback_turn15(self, evaluation_runner, scenario_loader):
        """Test coach feedback appears at turn 15"""
        scenarios = scenario_loader.get_scenarios_by_category('coach_feedback_turn15')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"
        assert len(result.response) >= 100, "Coach feedback should be substantial"

    @pytest.mark.asyncio
    @pytest.mark.eval_coach
    async def test_coach_feedback_quality(self, evaluation_runner, scenario_loader):
        """Test coach feedback quality and completeness"""
        scenarios = scenario_loader.get_scenarios_by_category('coach')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        response_lower = result.response.lower()
        feedback_components = ['principle', 'feedback', 'improvement']
        found_components = sum(1 for comp in feedback_components if comp in response_lower)

        assert found_components >= 2, "Coach feedback missing key components"


@pytest.mark.evaluation
class TestPhaseTransitions:
    """Tests for phase transition handling"""

    @pytest.mark.asyncio
    @pytest.mark.eval_transitions
    async def test_phase_transition_turn3_to_4(self, evaluation_runner, scenario_loader):
        """Test phase transition from Phase 1 to Phase 2"""
        scenarios = scenario_loader.get_scenarios_by_category('phase_transition')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"


@pytest.mark.evaluation
class TestRoomAgentEvaluation:
    """Tests for Room Agent sentiment analysis"""

    @pytest.mark.asyncio
    async def test_room_agent_mood_analysis(self, evaluation_runner, scenario_loader):
        """Test Room Agent analyzes audience mood"""
        scenarios = scenario_loader.get_scenarios_by_category('room_agent')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"
        assert 'room' in result.response.lower() or 'audience' in result.response.lower()


@pytest.mark.evaluation
class TestMCAgentEvaluation:
    """Tests for MC Agent game hosting"""

    @pytest.mark.asyncio
    async def test_mc_agent_game_introduction(self, evaluation_runner, scenario_loader):
        """Test MC Agent introduces games with energy"""
        scenarios = scenario_loader.get_scenarios_by_category('mc_agent')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"


@pytest.mark.evaluation
class TestEdgeCases:
    """Tests for edge case handling and robustness"""

    @pytest.mark.asyncio
    async def test_empty_input_handling(self, evaluation_runner, scenario_loader):
        """Test handling of empty input"""
        scenarios = scenario_loader.get_scenarios_by_category('edge_case_empty')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.response, "Agent should respond to empty input"

    @pytest.mark.asyncio
    async def test_long_input_handling(self, evaluation_runner, scenario_loader):
        """Test handling of very long input"""
        scenarios = scenario_loader.get_scenarios_by_category('edge_case_long')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.response, "Agent should handle long input"

    @pytest.mark.asyncio
    async def test_special_characters_handling(self, evaluation_runner, scenario_loader):
        """Test handling of special characters"""
        scenarios = scenario_loader.get_scenarios_by_category('edge_case_special')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_all_edge_cases(self, evaluation_runner, scenario_loader):
        """Run all edge case scenarios"""
        scenarios = scenario_loader.get_scenarios_by_category('edge_case')

        results = []
        for scenario in scenarios:
            result = await evaluation_runner.run_single_evaluation(scenario)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        success_rate = passed / total if total > 0 else 0.0

        logger.info(
            "Edge case evaluation complete",
            passed=passed,
            total=total,
            success_rate=success_rate
        )


@pytest.mark.evaluation
class TestMultiTurnConsistency:
    """Tests for multi-turn conversation consistency"""

    @pytest.mark.asyncio
    async def test_multi_turn_consistency(self, evaluation_runner, scenario_loader):
        """Test consistency across multiple turns"""
        scenarios = scenario_loader.get_scenarios_by_category('multi_turn')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.passed, f"Test failed: {result.validation_errors}"


@pytest.mark.evaluation
class TestErrorRecovery:
    """Tests for error recovery scenarios"""

    @pytest.mark.asyncio
    async def test_error_recovery_context_loss(self, evaluation_runner, scenario_loader):
        """Test recovery from context loss"""
        scenarios = scenario_loader.get_scenarios_by_category('error_recovery')
        assert len(scenarios) > 0

        result = await evaluation_runner.run_single_evaluation(scenarios[0])

        assert result.response, "Agent should recover from context loss"


@pytest.mark.evaluation
@pytest.mark.slow
@pytest.mark.integration
class TestFullEvaluationSuite:
    """Full evaluation suite running all scenarios"""

    @pytest.mark.asyncio
    async def test_run_all_evaluations(self, evaluation_runner):
        """Run complete evaluation suite"""
        summary = await evaluation_runner.run_all_evaluations()

        logger.info(
            "Full evaluation suite complete",
            total=summary.total_tests,
            passed=summary.passed,
            failed=summary.failed,
            success_rate=summary.success_rate
        )

        output_path = Path(__file__).parent / "results" / "full_evaluation_report.json"
        evaluation_runner.save_results(output_path)

        assert summary.success_rate >= 0.70, (
            f"Overall success rate too low: {summary.success_rate:.2%}. "
            f"Expected >= 70%"
        )

        assert summary.phase1_success_rate >= 0.75, (
            f"Phase 1 success rate too low: {summary.phase1_success_rate:.2%}"
        )

        assert summary.phase2_success_rate >= 0.70, (
            f"Phase 2 success rate too low: {summary.phase2_success_rate:.2%}"
        )


@pytest.mark.evaluation
class TestAgentFactory:
    """Tests for AgentFactory"""

    def test_create_stage_manager(self):
        """Test creating stage manager"""
        agent = AgentFactory.create_agent('stage_manager', {'turn_count': 0})
        assert agent is not None
        assert agent.name == 'stage_manager'

    def test_create_partner_phase1(self):
        """Test creating Phase 1 partner"""
        agent = AgentFactory.create_agent('partner_agent', {'phase': 1})
        assert agent is not None
        assert agent.name == 'partner_agent'

    def test_create_partner_phase2(self):
        """Test creating Phase 2 partner"""
        agent = AgentFactory.create_agent('partner_agent', {'phase': 2})
        assert agent is not None
        assert agent.name == 'partner_agent'

    def test_create_mc_agent(self):
        """Test creating MC agent"""
        agent = AgentFactory.create_agent('mc_agent', {})
        assert agent is not None
        assert agent.name == 'mc_agent'

    def test_create_room_agent(self):
        """Test creating room agent"""
        agent = AgentFactory.create_agent('room_agent', {})
        assert agent is not None
        assert agent.name == 'room_agent'

    def test_create_coach_agent(self):
        """Test creating coach agent"""
        agent = AgentFactory.create_agent('coach_agent', {})
        assert agent is not None
        assert agent.name == 'coach_agent'

    def test_invalid_agent_name(self):
        """Test error on invalid agent name"""
        with pytest.raises(ValueError):
            AgentFactory.create_agent('invalid_agent', {})


@pytest.mark.evaluation
class TestResponseValidator:
    """Tests for ResponseValidator"""

    def test_validate_response_structure(self, eval_config):
        """Test response structure validation"""
        validator = ResponseValidator(eval_config)

        response = "This is a valid response with sufficient length."
        expected = {"min_length": 20, "max_length": 500}
        context = {"phase": 1}

        passed, errors = validator.validate_response(response, expected, context)
        assert passed
        assert len(errors) == 0

    def test_validate_empty_response(self, eval_config):
        """Test validation of empty response"""
        validator = ResponseValidator(eval_config)

        passed, errors = validator.validate_response("", {}, {})
        assert not passed
        assert len(errors) > 0

    def test_validate_required_keywords(self, eval_config):
        """Test keyword validation"""
        validator = ResponseValidator(eval_config)

        response = "Yes, and I love this idea!"
        expected = {"keywords": ["yes", "and"], "min_length": 10, "max_length": 500}
        context = {"phase": 1}

        passed, errors = validator.validate_response(response, expected, context)
        assert passed

    def test_validate_avoid_keywords(self, eval_config):
        """Test forbidden keyword detection"""
        validator = ResponseValidator(eval_config)

        response = "No, but that won't work."
        expected = {"avoid_keywords": ["no", "but"], "min_length": 10, "max_length": 500}
        context = {"phase": 1}

        passed, errors = validator.validate_response(response, expected, context)
        assert not passed
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "evaluation"])
