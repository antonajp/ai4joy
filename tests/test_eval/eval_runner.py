"""ADK Evaluation Runner for Agent Quality Testing

This module provides functionality to:
- Load test scenarios from improv_scenarios.json
- Create ADK EvalSet and EvalCase instances
- Run evaluations against agents
- Collect and report metrics
- Support CLI execution via `adk eval` or direct pytest
"""

import json
import yaml
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.stage_manager import create_stage_manager
from app.agents.partner_agent import create_partner_agent
from app.agents.mc_agent import create_mc_agent
from app.agents.room_agent import create_room_agent
from app.agents.coach_agent import create_coach_agent
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class EvaluationResult:
    """Result of a single evaluation case"""

    test_name: str
    agent_name: str
    input_text: str
    response: str
    context: Dict[str, Any]
    expected: Dict[str, Any]
    passed: bool
    validation_errors: List[str]
    metrics: Dict[str, Any]
    timestamp: str
    duration_seconds: float


@dataclass
class EvaluationSummary:
    """Summary of all evaluation results"""

    total_tests: int
    passed: int
    failed: int
    success_rate: float
    phase1_success_rate: float
    phase2_success_rate: float
    coach_success_rate: float
    avg_response_time: float
    avg_response_length: float
    results: List[EvaluationResult]
    failures: List[Dict[str, Any]]
    timestamp: str


class EvaluationConfig:
    """Configuration loader for evaluation framework"""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "evaluation_config.yaml"

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info("Evaluation config loaded", path=str(self.config_path))
            return config
        except Exception as e:
            logger.error("Failed to load evaluation config", error=str(e))
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "model_settings": {
                "default_model": "gemini-1.5-flash",
                "temperature": 0.7,
                "max_output_tokens": 2048,
            },
            "evaluation_parameters": {"timeout_seconds": 30, "max_retries": 3},
            "metrics_configuration": {"collect_metrics": True},
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get config value by dot-separated path"""
        keys = key_path.split(".")
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value


class ScenarioLoader:
    """Loader for test scenarios from JSON file"""

    def __init__(self, scenarios_path: Optional[Path] = None):
        if scenarios_path is None:
            scenarios_path = Path(__file__).parent / "improv_scenarios.json"

        self.scenarios_path = scenarios_path
        self.scenarios = self._load_scenarios()

    def _load_scenarios(self) -> List[Dict[str, Any]]:
        """Load scenarios from JSON file"""
        try:
            with open(self.scenarios_path, "r") as f:
                data = json.load(f)
            scenarios = data.get("test_scenarios", [])
            logger.info(
                "Test scenarios loaded",
                path=str(self.scenarios_path),
                count=len(scenarios),
            )
            return scenarios
        except Exception as e:
            logger.error("Failed to load test scenarios", error=str(e))
            return []

    def get_scenarios_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get scenarios filtered by category/name pattern"""
        return [
            s for s in self.scenarios if category.lower() in s.get("name", "").lower()
        ]

    def get_all_scenarios(self) -> List[Dict[str, Any]]:
        """Get all scenarios"""
        return self.scenarios


class AgentFactory:
    """Factory for creating agents based on scenario configuration"""

    @staticmethod
    def create_agent(agent_name: str, context: Dict[str, Any]):
        """Create agent instance based on name and context"""
        turn_count = context.get("turn_count", 0)
        phase = context.get("phase", 1)

        if agent_name == "stage_manager":
            return create_stage_manager(turn_count=turn_count)
        elif agent_name == "partner_agent":
            return create_partner_agent(phase=phase)
        elif agent_name == "mc_agent":
            return create_mc_agent()
        elif agent_name == "room_agent":
            return create_room_agent()
        elif agent_name == "coach_agent":
            return create_coach_agent()
        else:
            raise ValueError(f"Unknown agent name: {agent_name}")


class ResponseValidator:
    """Validates agent responses against expected criteria"""

    def __init__(self, config: EvaluationConfig):
        self.config = config

    def validate_response(  # noqa: C901
        self, response: str, expected: Dict[str, Any], context: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate response against expected criteria

        Returns:
            Tuple of (passed, validation_errors)
        """
        errors = []

        if not response or not isinstance(response, str):
            errors.append("Response is empty or invalid type")
            return False, errors

        phase = context.get("phase", 1)
        min_length = expected.get("min_length", 20)
        max_length = expected.get("max_length", 2000)

        if len(response) < min_length:
            errors.append(f"Response too short: {len(response)} < {min_length}")

        if len(response) > max_length:
            errors.append(f"Response too long: {len(response)} > {max_length}")

        required_keywords = expected.get("keywords", [])
        response_lower = response.lower()

        keywords_found = sum(
            1 for kw in required_keywords if kw.lower() in response_lower
        )
        min_keywords_required = max(1, len(required_keywords) // 2)
        if required_keywords and keywords_found < min_keywords_required:
            errors.append(
                f"Insufficient keywords: found {keywords_found}/{len(required_keywords)}, need {min_keywords_required}"
            )

        avoid_keywords = expected.get("avoid_keywords", [])
        for keyword in avoid_keywords:
            if keyword.lower() in response_lower:
                errors.append(f"Contains forbidden keyword: {keyword}")

        if expected.get("phase") and expected["phase"] != phase:
            errors.append(f"Phase mismatch: expected {expected['phase']}, got {phase}")

        if expected.get("coach_feedback_present"):
            coach_keywords = ["feedback", "principle", "well done", "improvement"]
            if not any(kw in response_lower for kw in coach_keywords):
                errors.append("Coach feedback not detected in response")

        if expected.get("must_include_collaboration"):
            collab_words = expected["must_include_collaboration"]
            if not any(word in response_lower for word in collab_words):
                errors.append("Missing collaboration indicators in Phase 2 response")

        passed = len(errors) == 0
        return passed, errors

    def extract_metrics(self, response: str, duration: float) -> Dict[str, Any]:
        """Extract metrics from response"""
        return {
            "response_length": len(response),
            "word_count": len(response.split()),
            "duration_seconds": duration,
            "has_content": bool(response),
            "response_type": type(response).__name__,
        }


class EvaluationRunner:
    """Main evaluation runner that executes test scenarios"""

    def __init__(
        self,
        config: Optional[EvaluationConfig] = None,
        scenarios: Optional[ScenarioLoader] = None,
    ):
        self.config = config or EvaluationConfig()
        self.scenarios = scenarios or ScenarioLoader()
        self.validator = ResponseValidator(self.config)
        self.results: List[EvaluationResult] = []

    async def run_single_evaluation(  # noqa: C901
        self, scenario: Dict[str, Any]
    ) -> EvaluationResult:
        """Run a single evaluation scenario"""
        test_name = scenario.get("name", "unknown_test")
        agent_name = scenario.get("agent", "partner_agent")
        input_text = scenario.get("input", "")
        context = scenario.get("context", {})
        expected = scenario.get("expected", {})

        logger.info("Running evaluation", test_name=test_name, agent=agent_name)

        start_time = datetime.now(timezone.utc)

        try:
            agent = AgentFactory.create_agent(agent_name, context)

            # Use InMemorySessionService for evaluations
            session_service = InMemorySessionService()

            runner = Runner(
                agent=agent, app_name=settings.app_name, session_service=session_service
            )

            timeout = self.config.get("evaluation_parameters.timeout_seconds", 30)
            max_retries = self.config.get("evaluation_parameters.max_retries", 3)
            retry_delay = self.config.get(
                "evaluation_parameters.retry_delay_seconds", 2
            )

            # Create message using new ADK API
            new_message = types.Content(
                role="user", parts=[types.Part.from_text(text=input_text)]
            )

            # Generate unique IDs for this evaluation run
            eval_user_id = f"eval_user_{test_name}"
            eval_session_id = (
                f"eval_session_{test_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            response_obj = None
            last_error = None
            for attempt in range(max_retries):
                try:
                    response_parts = []

                    async def run_with_timeout():
                        async for event in runner.run_async(
                            user_id=eval_user_id,
                            session_id=eval_session_id,
                            new_message=new_message,
                        ):
                            if hasattr(event, "content") and event.content:
                                if hasattr(event.content, "parts"):
                                    for part in event.content.parts:
                                        if hasattr(part, "text") and part.text:
                                            response_parts.append(part.text)

                    await asyncio.wait_for(run_with_timeout(), timeout=timeout)
                    response_obj = "".join(response_parts)
                    break
                except asyncio.TimeoutError as e:
                    last_error = e
                    logger.warning(
                        "Evaluation timeout, retrying",
                        test_name=test_name,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "Evaluation error, retrying",
                        test_name=test_name,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)

            if response_obj is None:
                raise last_error or Exception("All retries exhausted")

            response = ""
            if (
                response_obj
                and hasattr(response_obj, "messages")
                and response_obj.messages
            ):
                last_message = response_obj.messages[-1]
                if hasattr(last_message, "content"):
                    response = str(last_message.content)
                elif hasattr(last_message, "text"):
                    response = str(last_message.text)
                else:
                    response = str(last_message)

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            passed, validation_errors = self.validator.validate_response(
                response, expected, context
            )
            metrics = self.validator.extract_metrics(response, duration)

            result = EvaluationResult(
                test_name=test_name,
                agent_name=agent_name,
                input_text=input_text,
                response=response,
                context=context,
                expected=expected,
                passed=passed,
                validation_errors=validation_errors,
                metrics=metrics,
                timestamp=start_time.isoformat(),
                duration_seconds=duration,
            )

            logger.info(
                "Evaluation completed",
                test_name=test_name,
                passed=passed,
                duration=duration,
            )

            return result

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            logger.error("Evaluation failed", test_name=test_name, error=str(e))

            return EvaluationResult(
                test_name=test_name,
                agent_name=agent_name,
                input_text=input_text,
                response="",
                context=context,
                expected=expected,
                passed=False,
                validation_errors=[f"Evaluation error: {str(e)}"],
                metrics={"duration_seconds": duration},
                timestamp=start_time.isoformat(),
                duration_seconds=duration,
            )

    async def run_all_evaluations(
        self, scenario_filter: Optional[str] = None
    ) -> EvaluationSummary:
        """Run all evaluation scenarios"""
        logger.info("Starting evaluation run", filter=scenario_filter)

        scenarios = self.scenarios.get_all_scenarios()

        if scenario_filter:
            scenarios = [
                s
                for s in scenarios
                if scenario_filter.lower() in s.get("name", "").lower()
            ]

        logger.info("Running evaluations", total_scenarios=len(scenarios))

        results = []
        for scenario in scenarios:
            result = await self.run_single_evaluation(scenario)
            results.append(result)
            self.results.append(result)

        summary = self._generate_summary(results)

        logger.info(
            "Evaluation run completed",
            total=summary.total_tests,
            passed=summary.passed,
            failed=summary.failed,
            success_rate=summary.success_rate,
        )

        return summary

    def _generate_summary(self, results: List[EvaluationResult]) -> EvaluationSummary:
        """Generate summary from evaluation results"""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        success_rate = passed / total if total > 0 else 0.0

        phase1_results = [r for r in results if "phase1" in r.test_name]
        phase2_results = [r for r in results if "phase2" in r.test_name]
        coach_results = [r for r in results if "coach" in r.test_name]

        phase1_success = (
            sum(1 for r in phase1_results if r.passed) / len(phase1_results)
            if phase1_results
            else 0.0
        )
        phase2_success = (
            sum(1 for r in phase2_results if r.passed) / len(phase2_results)
            if phase2_results
            else 0.0
        )
        coach_success = (
            sum(1 for r in coach_results if r.passed) / len(coach_results)
            if coach_results
            else 0.0
        )

        avg_response_time = (
            sum(r.duration_seconds for r in results) / total if total > 0 else 0.0
        )

        avg_response_length = (
            sum(r.metrics.get("response_length", 0) for r in results) / total
            if total > 0
            else 0.0
        )

        failures = [
            {
                "test_name": r.test_name,
                "errors": r.validation_errors,
                "response": r.response[:200],
            }
            for r in results
            if not r.passed
        ]

        return EvaluationSummary(
            total_tests=total,
            passed=passed,
            failed=failed,
            success_rate=success_rate,
            phase1_success_rate=phase1_success,
            phase2_success_rate=phase2_success,
            coach_success_rate=coach_success,
            avg_response_time=avg_response_time,
            avg_response_length=avg_response_length,
            results=results,
            failures=failures,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def save_results(self, output_path: Path):
        """Save evaluation results to JSON file"""
        try:
            summary = self._generate_summary(self.results)

            output_data = {
                "summary": {
                    "total_tests": summary.total_tests,
                    "passed": summary.passed,
                    "failed": summary.failed,
                    "success_rate": summary.success_rate,
                    "phase1_success_rate": summary.phase1_success_rate,
                    "phase2_success_rate": summary.phase2_success_rate,
                    "coach_success_rate": summary.coach_success_rate,
                    "avg_response_time": summary.avg_response_time,
                    "avg_response_length": summary.avg_response_length,
                    "timestamp": summary.timestamp,
                },
                "results": [asdict(r) for r in self.results],
                "failures": summary.failures,
            }

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(output_data, f, indent=2)

            logger.info("Results saved", path=str(output_path))

        except Exception as e:
            logger.error("Failed to save results", error=str(e))


async def run_evaluations_cli(
    scenario_filter: Optional[str] = None,
) -> EvaluationSummary:
    """CLI entry point for running evaluations"""
    runner = EvaluationRunner()
    summary = await runner.run_all_evaluations(scenario_filter=scenario_filter)

    output_path = Path(__file__).parent / "results" / "evaluation_report.json"
    runner.save_results(output_path)

    return summary


if __name__ == "__main__":
    import sys

    scenario_filter = sys.argv[1] if len(sys.argv) > 1 else None

    summary = asyncio.run(run_evaluations_cli(scenario_filter))

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {summary.total_tests}")
    print(f"Passed: {summary.passed}")
    print(f"Failed: {summary.failed}")
    print(f"Success Rate: {summary.success_rate:.2%}")
    print(f"Phase 1 Success Rate: {summary.phase1_success_rate:.2%}")
    print(f"Phase 2 Success Rate: {summary.phase2_success_rate:.2%}")
    print(f"Coach Success Rate: {summary.coach_success_rate:.2%}")
    print(f"Avg Response Time: {summary.avg_response_time:.2f}s")
    print(f"Avg Response Length: {summary.avg_response_length:.0f} chars")
    print("=" * 60 + "\n")

    if summary.failures:
        print("FAILURES:")
        for failure in summary.failures:
            print(f"\n  Test: {failure['test_name']}")
            for error in failure["errors"]:
                print(f"    - {error}")

    sys.exit(0 if summary.failed == 0 else 1)
