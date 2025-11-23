# Improv Olympics Test Suite

Comprehensive testing suite for GCP production deployment of the Improv Olympics multi-agent system.

## Test Structure

```
tests/
├── GCP_DEPLOYMENT_TEST_PLAN.md    # Comprehensive test plan with all test cases
├── conftest.py                     # Shared pytest fixtures and configuration
├── requirements-test.txt           # Python testing dependencies
│
├── test_container_build.py         # TC-001: Container build verification
├── test_agent_initialization.py    # TC-002: ADK agent initialization
├── test_model_integration.py       # TC-003: Gemini model access
│
├── test_tools/
│   ├── test_game_database.py      # TC-004: GameDatabase tool
│   ├── test_demographic_generator.py  # TC-005: DemographicGenerator tool
│   └── test_sentiment_gauge.py    # TC-006: SentimentGauge tool
│
├── test_integration/
│   └── test_e2e_session.py        # TC-201: End-to-end session flow
│
├── test_performance/
│   └── test_latency.py            # TC-301: Multi-agent latency testing
│
└── test_evaluation/
    ├── test_phase_transitions.py  # TC-505: Phase transition evaluation
    └── test_tool_trajectories.py  # TC-502/503: Tool trajectory analysis
```

## Setup

### 1. Install Test Dependencies

```bash
cd /Users/jpantona/Documents/code/ai4joy
pip install -r tests/requirements-test.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# GCP Configuration
export GCP_PROJECT_ID="ImprovOlympics"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Service URLs
export SERVICE_URL="https://ai4joy.org"  # Production
export LOCAL_SERVICE_URL="http://localhost:8080"  # Local testing
```

Load environment:
```bash
source .env
```

### 3. Verify GCP Access

```bash
gcloud auth application-default login
gcloud config set project ImprovOlympics
```

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run by Category

**Pre-Deployment (Container & Local)**
```bash
pytest tests/test_container_build.py -v
pytest tests/test_agent_initialization.py -v
pytest tests/test_model_integration.py -v
pytest tests/test_tools/ -v
```

**Integration Tests**
```bash
pytest tests/test_integration/ -v -m integration
```

**Performance Tests**
```bash
pytest tests/test_performance/ -v -m performance
```

**Agent Evaluation Tests**
```bash
pytest tests/test_evaluation/ -v -m evaluation
```

### Run Specific Test

```bash
pytest tests/test_integration/test_e2e_session.py::TestE2ESession::test_complete_session_flow -v
```

### Exclude Slow Tests

```bash
pytest tests/ -v -m "not slow"
```

### Run Tests in Parallel

```bash
pytest tests/ -v -n auto  # Uses all CPU cores
```

## Test Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.integration` - Integration tests requiring deployed services
- `@pytest.mark.performance` - Performance and load tests
- `@pytest.mark.evaluation` - Agent evaluation tests
- `@pytest.mark.security` - Security validation tests
- `@pytest.mark.slow` - Long-running tests (>30s)

### Examples

```bash
# Run only integration tests
pytest -v -m integration

# Run performance tests excluding slow ones
pytest -v -m "performance and not slow"

# Run everything except evaluation tests
pytest -v -m "not evaluation"
```

## Test Execution Strategy

### Phase 1: Pre-Deployment (Local)
Execute before deploying to GCP:
```bash
pytest tests/test_container_build.py -v
pytest tests/test_agent_initialization.py -v
pytest tests/test_model_integration.py -v
pytest tests/test_tools/ -v
```
**Gate:** 100% pass rate required.

### Phase 2: Integration (Staging/Production)
Execute after deployment:
```bash
pytest tests/test_integration/ -v
pytest tests/test_performance/test_latency.py -v
```
**Gate:** E2E session success + latency within SLA.

### Phase 3: Full Validation
Execute for complete validation:
```bash
pytest tests/ -v
```
**Gate:** All critical tests pass, monitoring operational.

## Performance Thresholds

The test suite enforces these performance thresholds:

- **p50 latency:** < 2 seconds per turn
- **p95 latency:** < 4 seconds per turn
- **p99 latency:** < 6 seconds per turn
- **Concurrent sessions:** 20 simultaneous sessions supported
- **Latency degradation:** < 20% under sustained load

## Continuous Testing

### CI/CD Integration

Add to your CI pipeline (e.g., GitHub Actions, Cloud Build):

```yaml
- name: Run Pre-Deployment Tests
  run: |
    pytest tests/test_container_build.py tests/test_agent_initialization.py -v

- name: Run Integration Tests
  run: |
    pytest tests/test_integration/ -v -m integration
```

### Recommended Schedule

- **On every commit:** Container build tests
- **Nightly:** Regression tests
- **Weekly:** Performance tests
- **Monthly:** Security tests
- **Quarterly:** Full agent evaluation

## Troubleshooting

### Docker Tests Failing

Ensure Docker daemon is running:
```bash
docker ps
```

### GCP Authentication Errors

Verify credentials:
```bash
gcloud auth application-default print-access-token
```

### Import Errors

Ensure application code is in Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:/Users/jpantona/Documents/code/ai4joy"
```

### Timeout Errors

Increase timeout for slow tests:
```bash
pytest tests/ -v --timeout=300
```

## Test Data

Test fixtures provide standard test data:

- **Locations:** Mars Colony, Corporate Boardroom, Medieval Castle
- **Relationships:** Scientists, Coworkers, Rivals, Family
- **Turn count:** 10 turns per session (default)
- **Concurrent sessions:** 20 (for load tests)

Modify fixtures in `conftest.py` to adjust test data.

## Observability During Tests

### View Logs

```bash
# Cloud Logging
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=improv-olympics" --limit 50

# Follow logs in real-time
gcloud logging tail "resource.type=cloud_run_revision"
```

### Monitor Metrics

```bash
# Cloud Monitoring
gcloud monitoring dashboards list
```

### Inspect Containers

```bash
# List running containers
docker ps

# Inspect container
docker inspect improv-olympics:test

# View container logs
docker logs <container_id>
```

## Writing New Tests

### Template

```python
import pytest

class TestNewFeature:
    """Test suite for new feature."""

    @pytest.mark.integration
    def test_feature_behavior(self, session_client, test_session_config):
        \"\"\"Test that new feature works correctly.\"\"\"
        # Arrange
        session = session_client.start_session(test_session_config)

        # Act
        result = session_client.invoke_feature(session['session_id'])

        # Assert
        assert result['status'] == 'success'
        assert 'output' in result
```

### Best Practices

1. **Use descriptive test names** - `test_phase_transition_correctness` not `test_phases`
2. **Follow AAA pattern** - Arrange, Act, Assert
3. **Use fixtures** - Don't duplicate setup code
4. **Add markers** - Mark integration, performance, slow tests
5. **Document expectations** - Comment on why assertions matter
6. **Clean up resources** - Close sessions, remove containers
7. **Print diagnostics** - Use print() for debugging info

## Coverage Reports

Generate coverage report:

```bash
pytest tests/ --cov=improv_olympics --cov-report=html
open htmlcov/index.html
```

## Contributing

When adding new tests:

1. Add test case to `GCP_DEPLOYMENT_TEST_PLAN.md`
2. Implement test in appropriate subdirectory
3. Add necessary fixtures to `conftest.py`
4. Update this README with execution instructions
5. Ensure tests pass locally before committing

## Support

For questions or issues:
- Review test plan: `GCP_DEPLOYMENT_TEST_PLAN.md`
- Check Cloud Logging for deployment issues
- Verify GCP quotas and permissions

---

**Last Updated:** 2025-11-23
**Test Suite Version:** 1.0
**Target Platform:** GCP ImprovOlympics project
