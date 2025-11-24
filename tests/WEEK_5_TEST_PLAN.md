# Week 5 Implementation Test Plan - IQS-46

## Test Scope

Testing the core Week 5 components for ADK Multi-Agent Orchestration:
- Authentication middleware (IAP header extraction) - ALREADY IMPLEMENTED
- BaseImprovAgent class with retry logic - TO BE IMPLEMENTED
- MC Agent with GameDatabase tool - TO BE IMPLEMENTED
- The Room Agent with sentiment logic - TO BE IMPLEMENTED
- Custom tools (GameDatabase, DemographicGenerator, SentimentGauge, ImprovExpertDatabase) - TO BE IMPLEMENTED

**Out of Scope:** Partner Agent, Coach Agent, Stage Manager (Week 6-7), Full E2E sessions

---

## Critical Test Cases

### 1. Authentication Middleware Tests (AUTOMATED - HIGH PRIORITY)

**Status:** Middleware implemented, comprehensive tests needed

- **TC-AUTH-IAP-01**: Valid IAP headers extract user email and ID correctly - Automated
- **TC-AUTH-IAP-02**: Missing `X-Goog-Authenticated-User-Email` returns 401 - Automated
- **TC-AUTH-IAP-03**: Missing `X-Goog-Authenticated-User-ID` returns 401 - Automated
- **TC-AUTH-IAP-04**: Malformed header format (missing "accounts.google.com:") handled gracefully - Automated
- **TC-AUTH-IAP-05**: Health check endpoints bypass authentication - Automated
- **TC-AUTH-IAP-06**: JWT validation succeeds with valid token - Automated
- **TC-AUTH-IAP-07**: JWT validation fails with invalid signature - Automated
- **TC-AUTH-IAP-08**: Request state populated with user_email, user_id - Automated

### 2. BaseImprovAgent Tests (AUTOMATED - HIGH PRIORITY)

**Status:** NOT YET IMPLEMENTED - Design tests first, implement alongside code

- **TC-BASE-01**: Agent initialization with model name succeeds - Automated
- **TC-BASE-02**: Agent makes successful LLM call with retry=0 - Automated
- **TC-BASE-03**: Transient failure retries up to max_retries - Automated
- **TC-BASE-04**: Exponential backoff delays between retries - Automated
- **TC-BASE-05**: Timeout after 8 seconds raises TimeoutError - Automated
- **TC-BASE-06**: Circuit breaker opens after 5 consecutive failures - Automated
- **TC-BASE-07**: Observability logs prompt, tool calls, response - Automated
- **TC-BASE-08**: Token counting tracks input/output tokens - Automated

### 3. MC Agent Tests (AUTOMATED - HIGH PRIORITY)

**Status:** NOT YET IMPLEMENTED

- **TC-MC-01**: MC agent initializes with Flash model - Automated
- **TC-MC-02**: MC invokes GameDatabase tool to select game - Automated
- **TC-MC-03**: MC response includes game name, rules, location reference - Automated
- **TC-MC-04**: MC personality is high-energy (manual eval) - Manual
- **TC-MC-05**: Tool trajectory: GameDatabase.query() called correctly - Automated
- **TC-MC-06**: MC handles GameDatabase errors gracefully - Automated

### 4. The Room Agent Tests (AUTOMATED - HIGH PRIORITY)

**Status:** NOT YET IMPLEMENTED

- **TC-ROOM-01**: Room agent initializes with Flash model - Automated
- **TC-ROOM-02**: Room invokes DemographicGenerator for archetypes - Automated
- **TC-ROOM-03**: Room invokes SentimentGauge for user input analysis - Automated
- **TC-ROOM-04**: Room aggregates sentiment into collective "room vibe" - Automated
- **TC-ROOM-05**: Positive sentiment (>0.6) generates supportive reactions - Automated
- **TC-ROOM-06**: Negative sentiment (<0.3) generates constructive feedback - Automated
- **TC-ROOM-07**: Tool trajectory: DemographicGenerator, SentimentGauge called - Automated
- **TC-ROOM-08**: Room response format: {sentiment_score, vibe_description, reactions} - Automated

### 5. GameDatabase Tool Tests (AUTOMATED - HIGH PRIORITY)

**Status:** Skeleton tests exist, implementation needed

- **TC-GAME-01**: Query short_form games returns list with 5+ games - Automated
- **TC-GAME-02**: Query long_form games returns list with 3+ games - Automated
- **TC-GAME-03**: Get specific game by name returns rules and constraints - Automated
- **TC-GAME-04**: Game schema validation: {name, rules, constraints, difficulty, category} - Automated
- **TC-GAME-05**: Invalid game name returns None - Automated
- **TC-GAME-06**: Recommend game for location includes location context - Automated

### 6. DemographicGenerator Tool Tests (AUTOMATED - MEDIUM PRIORITY)

**Status:** Skeleton tests exist, implementation needed

- **TC-DEMO-01**: Generate archetypes returns list of 5 personas - Automated
- **TC-DEMO-02**: Archetype schema: {persona, traits, reaction_style, typical_responses} - Automated
- **TC-DEMO-03**: Archetypes are diverse (different reaction styles) - Automated
- **TC-DEMO-04**: Deterministic generation (same seed = same archetypes) - Automated

### 7. SentimentGauge Tool Tests (AUTOMATED - HIGH PRIORITY)

**Status:** Skeleton tests exist, implementation needed

- **TC-SENT-01**: Analyze positive text returns score >0.6 - Automated
- **TC-SENT-02**: Analyze negative text returns score <0.3 - Automated
- **TC-SENT-03**: Analyze neutral text returns score 0.4-0.6 - Automated
- **TC-SENT-04**: Output schema: {sentiment_score, room_temp, spotlight_trigger, spotlight_persona} - Automated
- **TC-SENT-05**: Performance: Analysis completes in <200ms - Automated
- **TC-SENT-06**: No LLM call required (lightweight analysis) - Automated

### 8. ImprovExpertDatabase Tool Tests (AUTOMATED - MEDIUM PRIORITY)

**Status:** Not started

- **TC-EXPERT-01**: Query improv principles returns list of rules - Automated
- **TC-EXPERT-02**: Get "Yes, And" principle returns detailed explanation - Automated
- **TC-EXPERT-03**: Principles include: Yes And, Show Don't Tell, Make Your Partner Look Good - Automated

---

## Risk Areas Requiring Focused Testing

1. **Authentication Race Conditions**: Multiple simultaneous requests with same user_id
2. **Retry Logic Edge Cases**: Network timeouts vs API errors vs rate limits
3. **Tool Invocation Failures**: Agent behavior when tools return errors
4. **Token Overflow**: Large conversation history causing context limits
5. **Firestore Latency Spikes**: Impact on 8s timeout SLA

---

## Automation Approach

**Framework:** pytest with async support
**Mocking Strategy:**
- Mock VertexAI Gemini API calls (use `unittest.mock.AsyncMock`)
- Mock Firestore operations for unit tests
- Use real Firestore in integration tests (emulator or dev instance)

**Test File Structure:**
```
tests/
├── test_middleware/
│   ├── test_iap_auth.py              # TC-AUTH-IAP-*
│   └── test_oauth_auth.py            # Existing OAuth tests
├── test_agents/
│   ├── test_base_agent.py            # TC-BASE-*
│   ├── test_mc_agent.py              # TC-MC-*
│   └── test_room_agent.py            # TC-ROOM-*
├── test_tools/
│   ├── test_game_database.py         # TC-GAME-* (UPDATE EXISTING)
│   ├── test_demographic_generator.py # TC-DEMO-* (UPDATE EXISTING)
│   ├── test_sentiment_gauge.py       # TC-SENT-* (UPDATE EXISTING)
│   └── test_improv_expert_db.py      # TC-EXPERT-* (NEW)
└── test_integration/
    └── test_week5_integration.py     # Cross-component tests
```

**Execution Commands:**
```bash
# Run all Week 5 tests
pytest tests/test_agents/ tests/test_middleware/test_iap_auth.py tests/test_tools/ -v

# Run only authentication tests
pytest tests/test_middleware/test_iap_auth.py -v

# Run only agent tests
pytest tests/test_agents/ -v

# Run only tool tests
pytest tests/test_tools/ -v

# Run with coverage
pytest tests/test_agents/ tests/test_tools/ --cov=app.agents --cov=app.tools --cov-report=html
```

---

## Test Execution Estimates

- **Authentication Middleware Tests**: 15 minutes (8 test cases)
- **BaseImprovAgent Tests**: 20 minutes (8 test cases with retry/timeout testing)
- **MC Agent Tests**: 15 minutes (6 test cases)
- **Room Agent Tests**: 20 minutes (8 test cases)
- **Tool Tests**: 30 minutes (4 tools × ~6 test cases each)

**Total Automated Execution Time**: ~1.5 hours
**Manual Evaluation Time** (agent personality): 30 minutes

---

## Acceptance Criteria from Testing Perspective

Week 5 implementation is ACCEPTED when:

1. All authentication tests pass (100% - 8/8)
2. BaseImprovAgent retry logic verified (100% - 8/8)
3. MC Agent tool trajectory correct (100% - Game selected via GameDatabase)
4. Room Agent sentiment analysis accurate (≥90% - 7/8 test cases)
5. All 4 custom tools return valid schemas (100% - all schema validation passes)
6. No unhandled exceptions in agent execution
7. Latency <8s for single agent call (measured in performance tests)
8. Authentication blocks unauthenticated requests (0% false negatives)

---

## Testability Concerns Identified During Monitoring

1. **Agent Observability Gap**: Need access to intermediate tool calls for trajectory validation
   - **Recommendation**: Add debug mode that logs full agent execution trace

2. **Mock Data Quality**: Gemini API responses need realistic formatting
   - **Recommendation**: Record actual API responses and use as test fixtures

3. **Async Testing Complexity**: pytest-asyncio configuration needed
   - **Recommendation**: Add pytest-asyncio to requirements-test.txt

4. **Firestore Emulator Setup**: Local testing requires emulator
   - **Recommendation**: Document emulator setup in test README

5. **IAP Header Injection**: Local testing can't replicate GCP IAP
   - **Recommendation**: Test middleware with synthetic headers in unit tests

6. **Rate Limiter State Pollution**: Tests may interfere with each other
   - **Recommendation**: Clear Firestore user_limits collection between test runs

---

## Recommended Test Fixtures/Mocks

```python
# conftest.py additions for Week 5

@pytest.fixture
def mock_gemini_flash():
    """Mock Gemini Flash model responses"""
    with patch('vertexai.generative_models.GenerativeModel') as mock:
        mock.return_value.generate_content.return_value.text = "Test response"
        yield mock

@pytest.fixture
def valid_iap_headers():
    """Valid IAP headers for testing"""
    return {
        "X-Goog-Authenticated-User-Email": "accounts.google.com:test@example.com",
        "X-Goog-Authenticated-User-ID": "accounts.google.com:1234567890",
        "X-Goog-IAP-JWT-Assertion": "mock.jwt.token"
    }

@pytest.fixture
def mock_game_database():
    """Mock GameDatabase tool responses"""
    return {
        "name": "World's Worst",
        "rules": "Players suggest worst possible examples...",
        "constraints": ["Keep it family-friendly", "One suggestion per turn"],
        "difficulty": "beginner",
        "category": "short_form"
    }

@pytest.fixture
def mock_sentiment_result():
    """Mock SentimentGauge output"""
    return {
        "sentiment_score": 0.75,
        "room_temp": "warm and supportive",
        "spotlight_trigger": False,
        "spotlight_persona": None
    }

@pytest.fixture
async def firestore_cleanup():
    """Clean up Firestore test data after each test"""
    yield
    # Cleanup logic here
    db = firestore.Client(project="test-project")
    # Delete test collections
```

---

## Test Data Requirements

1. **Sample IAP Headers**: 5 valid variations, 5 invalid variations
2. **Sample User Inputs**: 20 diverse improv lines (positive, negative, neutral sentiment)
3. **Sample Game Rules**: 8 short-form games, 3 long-form games
4. **Sample Demographic Archetypes**: 5 distinct persona types
5. **Sample Agent Responses**: 10 MC responses, 10 Room responses for trajectory validation

---

## Integration Test Scenarios (Week 5 Scope)

**INT-W5-01: Authenticated User Creates Session**
- User with valid IAP headers → POST /api/sessions
- Expected: 201 Created, session_id returned, user_id stored

**INT-W5-02: MC Agent Selects Game**
- MC agent called with location="Mars Colony"
- Expected: GameDatabase queried, game selected, MC response includes game

**INT-W5-03: Room Agent Analyzes Sentiment**
- Room agent called with user_input="I love this game!"
- Expected: SentimentGauge returns positive score, Room generates supportive vibe

**INT-W5-04: Multiple Agents Called in Sequence**
- Call MC → wait for response → call Room
- Expected: Both succeed, no state pollution between calls

---

## Definition of Done for Week 5 Testing

- [ ] All test files created for Week 5 components
- [ ] Authentication middleware: 8/8 tests passing
- [ ] BaseImprovAgent: 8/8 tests passing
- [ ] MC Agent: 6/6 tests passing
- [ ] Room Agent: 8/8 tests passing
- [ ] GameDatabase: 6/6 tests passing
- [ ] DemographicGenerator: 4/4 tests passing
- [ ] SentimentGauge: 6/6 tests passing
- [ ] ImprovExpertDatabase: 3/3 tests passing
- [ ] Integration tests: 4/4 passing
- [ ] Code coverage: ≥80% for new agent/tool code
- [ ] No critical bugs identified
- [ ] Test execution documented in CI/CD pipeline
