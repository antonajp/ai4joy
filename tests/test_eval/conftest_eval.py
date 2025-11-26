"""Evaluation-Specific Pytest Fixtures for ADK Evaluation Framework"""
import pytest
import os
from typing import Dict, Any, List
from datetime import datetime, timezone

from app.agents.stage_manager import create_stage_manager
from app.agents.partner_agent import create_partner_agent
from app.agents.mc_agent import create_mc_agent
from app.agents.room_agent import create_room_agent
from app.agents.coach_agent import create_coach_agent
from app.services.turn_orchestrator import reset_runner
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def pytest_configure(config):
    """Register evaluation-specific markers"""
    config.addinivalue_line(
        "markers",
        "evaluation: Agent evaluation tests using ADK evaluation framework"
    )
    config.addinivalue_line(
        "markers",
        "eval_phase1: Tests for Phase 1 (supportive) partner behavior"
    )
    config.addinivalue_line(
        "markers",
        "eval_phase2: Tests for Phase 2 (fallible) partner behavior"
    )
    config.addinivalue_line(
        "markers",
        "eval_coach: Tests for coach feedback behavior"
    )
    config.addinivalue_line(
        "markers",
        "eval_transitions: Tests for phase transition handling"
    )


@pytest.fixture(scope="session")
def eval_config():
    """Evaluation configuration settings"""
    return {
        "model": "gemini-1.5-flash",
        "temperature": 0.7,
        "max_output_tokens": 2048,
        "phase_1_turns": [0, 1, 2, 3],
        "phase_2_turns": [4, 5, 6, 7, 8, 9, 10],
        "coach_feedback_turn": 15,
        "timeout_seconds": 30,
        "max_retries": 3
    }


@pytest.fixture
def mock_phase1_agent():
    """Create Phase 1 (supportive) Partner Agent for testing"""
    return create_partner_agent(phase=1)


@pytest.fixture
def mock_phase2_agent():
    """Create Phase 2 (fallible) Partner Agent for testing"""
    return create_partner_agent(phase=2)


@pytest.fixture
def mock_mc_agent():
    """Create MC Agent for testing"""
    return create_mc_agent()


@pytest.fixture
def mock_room_agent():
    """Create Room Agent for testing"""
    return create_room_agent()


@pytest.fixture
def mock_coach_agent():
    """Create Coach Agent for testing"""
    return create_coach_agent()


@pytest.fixture
def mock_stage_manager_phase1():
    """Create Stage Manager configured for Phase 1 (turn 0-3)"""
    return create_stage_manager(turn_count=0)


@pytest.fixture
def mock_stage_manager_phase2():
    """Create Stage Manager configured for Phase 2 (turn 4+)"""
    return create_stage_manager(turn_count=4)


@pytest.fixture
def mock_stage_manager_coach():
    """Create Stage Manager configured for coach feedback turn"""
    return create_stage_manager(turn_count=15)


@pytest.fixture
def sample_phase1_inputs():
    """Sample user inputs for Phase 1 evaluation"""
    return [
        "Welcome to the bakery! I'm so glad you're here.",
        "Yes, and we have fresh bread just out of the oven!",
        "That's perfect! What's your favorite kind?",
        "I'll grab it for you right away!"
    ]


@pytest.fixture
def sample_phase2_inputs():
    """Sample user inputs for Phase 2 evaluation"""
    return [
        "We need to solve this problem together.",
        "I'm not sure that's going to work.",
        "Maybe we should try a different approach?",
        "This is getting more complicated than I thought.",
        "Let's focus on what we can control."
    ]


@pytest.fixture
def sample_coach_inputs():
    """Sample user inputs that should trigger coach feedback"""
    return [
        "That was an intense scene! What do you think?",
        "How did I do with the 'Yes, and' principle?",
        "I'm ready for feedback on my performance."
    ]


@pytest.fixture
def sample_edge_case_inputs():
    """Edge case inputs for robustness testing"""
    return [
        "",
        " ",
        "A" * 1000,
        "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
        "Multiple\nline\ninput\nwith\nbreaks",
        "Unicode: 你好世界 🎭🎪🎨",
        "Repeated words " * 50,
        "Mix of UPPERCASE and lowercase and nUmBeRs 123",
    ]


@pytest.fixture
def evaluation_context_factory():
    """Factory for creating evaluation contexts with different configurations"""
    def create_context(
        turn_count: int = 0,
        phase: int = 1,
        session_id: str = "eval_test_session",
        user_history: List[str] = None
    ) -> Dict[str, Any]:
        """Create evaluation context dictionary"""
        return {
            "turn_count": turn_count,
            "phase": phase,
            "session_id": session_id,
            "user_history": user_history or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expected_phase": 1 if turn_count < 4 else 2,
            "should_have_coach": turn_count >= 15
        }
    return create_context


@pytest.fixture
def expected_phase1_behaviors():
    """Expected behaviors for Phase 1 evaluation"""
    return {
        "keywords": ["yes", "and", "great", "perfect", "love"],
        "supportive_indicators": [
            "accepts offer",
            "builds on idea",
            "enthusiastic",
            "encouraging"
        ],
        "avoid_keywords": ["no", "but", "however", "block", "deny"],
        "min_response_length": 20,
        "max_response_length": 500
    }


@pytest.fixture
def expected_phase2_behaviors():
    """Expected behaviors for Phase 2 evaluation"""
    return {
        "keywords": ["but", "however", "although", "challenge", "different"],
        "fallible_indicators": [
            "realistic",
            "friction",
            "point of view",
            "adaptation required"
        ],
        "still_collaborative": [
            "yes",
            "accept",
            "build",
            "scene"
        ],
        "min_response_length": 20,
        "max_response_length": 500
    }


@pytest.fixture
def expected_coach_behaviors():
    """Expected behaviors for coach feedback"""
    return {
        "keywords": [
            "feedback",
            "principle",
            "well done",
            "improvement",
            "next time"
        ],
        "feedback_components": [
            "celebration",
            "constructive",
            "specific",
            "actionable"
        ],
        "principle_references": True,
        "min_feedback_length": 100,
        "max_feedback_length": 1000
    }


@pytest.fixture
def eval_metrics_tracker():
    """Tracker for collecting evaluation metrics"""
    class MetricsTracker:
        def __init__(self):
            self.metrics = {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "phase1_success_rate": 0.0,
                "phase2_success_rate": 0.0,
                "coach_success_rate": 0.0,
                "avg_response_time": 0.0,
                "errors": []
            }

        def record_test(self, test_name: str, passed: bool, response_time: float = 0.0, error: str = None):
            """Record test result"""
            self.metrics["total_tests"] += 1
            if passed:
                self.metrics["passed"] += 1
            else:
                self.metrics["failed"] += 1
                if error:
                    self.metrics["errors"].append({
                        "test": test_name,
                        "error": error
                    })

            if response_time > 0:
                current_avg = self.metrics["avg_response_time"]
                total = self.metrics["total_tests"]
                self.metrics["avg_response_time"] = (
                    (current_avg * (total - 1) + response_time) / total
                )

        def get_summary(self) -> Dict[str, Any]:
            """Get metrics summary"""
            return self.metrics.copy()

    return MetricsTracker()


@pytest.fixture
def agent_runner_factory():
    """Factory for creating ADK Runner instances for evaluation"""
    def create_runner(agent, session_id: str = None):
        """Create Runner instance with agent"""
        from google.adk.runners import Runner

        runner = Runner(
            agent=agent,
            app_name=settings.app_name,
            session_service=None
        )

        return runner

    return create_runner


@pytest.fixture(autouse=True)
async def reset_runner_state():
    """Reset runner state between tests with proper async cleanup"""
    yield
    try:
        reset_runner()
    except Exception as e:
        logger.warning("Runner reset warning", error=str(e))


@pytest.fixture
def eval_logger():
    """Logger configured for evaluation tests"""
    return get_logger("eval_tests")


@pytest.fixture
def validation_helpers():  # noqa: C901
    """Helper functions for validating agent responses"""
    class ValidationHelpers:
        @staticmethod
        def validate_response_structure(response: Any) -> bool:
            """Validate response has expected structure"""
            if not response:
                return False
            if isinstance(response, str):
                return len(response) > 0
            if isinstance(response, dict):
                return len(response) > 0
            return False

        @staticmethod
        def validate_phase_appropriate(response: str, phase: int) -> bool:
            """Validate response is appropriate for phase"""
            if phase == 1:
                supportive_words = ["yes", "and", "great", "love", "perfect"]
                return any(word in response.lower() for word in supportive_words)
            elif phase == 2:
                has_friction = any(word in response.lower() for word in ["but", "however", "although"])
                has_collaboration = any(word in response.lower() for word in ["yes", "and", "scene"])
                return has_friction or has_collaboration
            return False

        @staticmethod
        def validate_coach_feedback(feedback: str) -> bool:
            """Validate coach feedback contains expected components"""
            if not feedback or len(feedback) < 100:
                return False

            components = ["principle", "feedback", "well done", "improvement", "next time"]
            found = sum(1 for comp in components if comp in feedback.lower())

            return found >= 2

        @staticmethod
        def validate_response_length(response: str, min_len: int = 20, max_len: int = 1000) -> bool:
            """Validate response length is within bounds"""
            return min_len <= len(response) <= max_len

        @staticmethod
        def extract_metrics(response: Any) -> Dict[str, Any]:
            """Extract metrics from response"""
            metrics = {
                "response_length": len(str(response)),
                "has_content": bool(response),
                "response_type": type(response).__name__
            }
            return metrics

    return ValidationHelpers()


@pytest.fixture
def skip_if_no_gcp_credentials():
    """Skip test if GCP credentials not available"""
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.getenv("GCP_PROJECT_ID"):
        pytest.skip("GCP credentials not configured for evaluation tests")
