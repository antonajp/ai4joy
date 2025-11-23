"""
Pytest configuration and shared fixtures for Improv Olympics testing.
"""
import os
import pytest
from typing import Dict, Any
from google.cloud import secretmanager


@pytest.fixture(scope="session")
def gcp_project_id() -> str:
    """Return GCP project ID for testing."""
    return os.environ.get("GCP_PROJECT_ID", "ImprovOlympics")


@pytest.fixture(scope="session")
def service_url() -> str:
    """Return deployed service URL."""
    return os.environ.get("SERVICE_URL", "https://ai4joy.org")


@pytest.fixture(scope="session")
def local_service_url() -> str:
    """Return local service URL for pre-deployment testing."""
    return os.environ.get("LOCAL_SERVICE_URL", "http://localhost:8080")


@pytest.fixture(scope="session")
def gcp_credentials():
    """Load GCP credentials from environment."""
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        pytest.skip("GOOGLE_APPLICATION_CREDENTIALS not set")
    return creds_path


@pytest.fixture(scope="session")
def vertexai_config(gcp_project_id) -> Dict[str, str]:
    """VertexAI model configuration."""
    return {
        "project_id": gcp_project_id,
        "location": "us-central1",
        "flash_model": "gemini-1.5-flash",
        "pro_model": "gemini-1.5-pro"
    }


@pytest.fixture
def test_session_config() -> Dict[str, Any]:
    """Standard test session configuration."""
    return {
        "location": "Mars Colony Breakroom",
        "user_name": "Test User",
        "session_id": None  # Will be generated
    }


@pytest.fixture
def test_user_inputs() -> list:
    """Standard test user inputs for session testing."""
    return [
        "Two scientists arguing over oxygen rations",
        "Yes! And I think we should ration by seniority",
        "But what if we based it on mission-critical roles?",
        "That makes sense. Let me check the manifest.",
        "I found it! But the computer is showing an error.",
        "Don't panic. Let me try rebooting the system.",
        "Good idea! While you do that, I'll check the backup tanks.",
        "Wait - the backup gauge is reading zero!",
        "Stay calm. We can split my personal reserve.",
        "That's incredibly generous. Let's do this together."
    ]


@pytest.fixture
def agent_names() -> list:
    """List of agent names in the system."""
    return ["MC", "TheRoom", "DynamicScenePartner", "Coach"]


@pytest.fixture
def tool_names() -> list:
    """List of custom tool names."""
    return [
        "GameDatabase",
        "DemographicGenerator",
        "SentimentGauge",
        "ImprovExpertDatabase"
    ]


@pytest.fixture
def expected_game_schema() -> Dict[str, type]:
    """Expected schema for GameDatabase output."""
    return {
        "name": str,
        "rules": str,
        "constraints": list,
        "difficulty": str,
        "category": str
    }


@pytest.fixture
def expected_archetype_schema() -> Dict[str, type]:
    """Expected schema for DemographicGenerator output."""
    return {
        "persona": str,
        "traits": list,
        "reaction_style": str,
        "typical_responses": list
    }


@pytest.fixture
def expected_sentiment_schema() -> Dict[str, type]:
    """Expected schema for SentimentGauge output."""
    return {
        "sentiment_score": float,
        "room_temp": str,
        "spotlight_trigger": bool,
        "spotlight_persona": str
    }


@pytest.fixture
def latency_thresholds() -> Dict[str, float]:
    """Performance latency thresholds in seconds."""
    return {
        "p50": 2.0,
        "p95": 4.0,
        "p99": 6.0,
        "timeout": 10.0
    }


@pytest.fixture
def load_test_config() -> Dict[str, int]:
    """Configuration for load testing."""
    return {
        "concurrent_sessions": 20,
        "turns_per_session": 10,
        "spawn_rate": 2,  # sessions per second
        "ramp_up_time": 10  # seconds
    }


def pytest_configure(config):
    """Pytest configuration hook."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "security: marks tests as security tests"
    )
    config.addinivalue_line(
        "markers", "evaluation: marks tests as agent evaluation tests"
    )
