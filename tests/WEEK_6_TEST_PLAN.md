# Week 6 Test Plan - Partner Agent, Coach Agent & Phase Transitions

**Ticket:** IQS-46 Week 6 Implementation
**QA Engineer:** QA Tester Agent
**Date:** 2025-11-24
**Status:** MONITORING IMPLEMENTATION

---

## 1. Executive Summary

This test plan covers Week 6 implementation of:
1. **Partner Agent** (2 phases: supportive + fallible)
2. **Coach Agent** (with improv expert tools)
3. **RateLimiter** (Firestore-based, 10/day, 3 concurrent) - ALREADY IMPLEMENTED
4. **Stage Manager Phase Transitions** (Phase 1 → Phase 2 at turn 4)

### Test Approach
- **Unit tests** for Partner/Coach agent creation and configuration
- **Integration tests** for phase transitions and multi-agent orchestration
- **Mock Firestore** for rate limiter tests (already complete)
- **E2E tests** for complete session flows with all 4 agents

### Risk Assessment
**HIGH RISK:**
- Phase transition logic (turn count tracking, prompt switching)
- Partner agent behavior change between phases
- Coach tool integration (4 improv expert tools)

**MEDIUM RISK:**
- Stage Manager coordination with 4 sub-agents
- Rate limiter edge cases (concurrent access, midnight reset)

**LOW RISK:**
- Agent creation (pattern established with MC/Room)
- Tool availability (improv expert tools already exist)

---

## 2. Component Test Plans

### 2.1 Partner Agent Tests

**File:** `/Users/jpantona/Documents/code/ai4joy/tests/test_agents/test_partner_agent.py`

#### TC-PARTNER-01: Agent Creation and Basic Config
```python
def test_partner_agent_creation():
    """Verify Partner agent is created correctly"""
    partner = create_partner_agent(phase=1)

    assert isinstance(partner, Agent)
    assert partner.name == "partner_agent"
    assert partner.model == "gemini-1.5-pro"
    assert len(partner.tools) == 0  # No tools for Partner
```

**Acceptance Criteria:**
- Agent is instance of `google.adk.Agent`
- Model is `gemini-1.5-pro` (NOT Flash - needs creativity)
- Name is `partner_agent`
- No tools attached

---

#### TC-PARTNER-02: Phase 1 System Prompt (Supportive Mode)
```python
def test_partner_phase1_prompt_is_supportive():
    """Phase 1 partner should have supportive system prompt"""
    partner = create_partner_agent(phase=1)

    instruction = partner.instruction

    # Check for supportive keywords
    assert "support" in instruction.lower() or "help" in instruction.lower()
    assert "encourage" in instruction.lower() or "build" in instruction.lower()

    # Should NOT have fallible keywords
    assert "mistake" not in instruction.lower()
    assert "forget" not in instruction.lower()
```

**Acceptance Criteria:**
- System prompt emphasizes supportive behavior
- Encourages building on user's ideas
- Provides scaffolding for beginners
- No mention of making mistakes or being fallible

**Example Phase 1 Keywords:**
- "support", "help", "encourage", "build on", "yes and", "guide"

---

#### TC-PARTNER-03: Phase 2 System Prompt (Fallible Mode)
```python
def test_partner_phase2_prompt_is_fallible():
    """Phase 2 partner should have fallible system prompt"""
    partner = create_partner_agent(phase=2)

    instruction = partner.instruction

    # Check for fallible keywords
    assert "fallible" in instruction.lower() or "mistake" in instruction.lower()
    assert "realistic" in instruction.lower() or "human" in instruction.lower()

    # Should still be collaborative
    assert "partner" in instruction.lower()
```

**Acceptance Criteria:**
- System prompt mentions being fallible/human-like
- Encourages realistic improv partner behavior
- May forget details or make mistakes intentionally
- Still collaborative (not adversarial)

**Example Phase 2 Keywords:**
- "fallible", "realistic", "human", "forget", "occasionally miss", "like a real scene partner"

---

#### TC-PARTNER-04: Phase Parameter Validation
```python
def test_partner_agent_invalid_phase_raises_error():
    """Invalid phase values should raise ValueError"""
    with pytest.raises(ValueError, match="phase must be 1 or 2"):
        create_partner_agent(phase=3)

    with pytest.raises(ValueError, match="phase must be 1 or 2"):
        create_partner_agent(phase=0)
```

**Acceptance Criteria:**
- Only phase=1 or phase=2 accepted
- Other values raise `ValueError`
- Error message is clear

---

#### TC-PARTNER-05: Temperature Configuration
```python
def test_partner_agent_temperature():
    """Partner should use higher temperature for creativity"""
    partner = create_partner_agent(phase=1)

    # Check if config has temperature setting
    # This depends on ADK implementation
    # May need to check generation_config if available

    # Expected: temperature ~ 0.9 (high creativity)
```

**Acceptance Criteria:**
- Temperature ≥ 0.8 (more creative than MC/Room)
- Allows for spontaneous, varied responses

---

### 2.2 Coach Agent Tests

**File:** `/Users/jpantona/Documents/code/ai4joy/tests/test_agents/test_coach_agent.py`

#### TC-COACH-01: Agent Creation and Config
```python
def test_coach_agent_creation():
    """Verify Coach agent is created correctly"""
    coach = create_coach_agent()

    assert isinstance(coach, Agent)
    assert coach.name == "coach_agent"
    assert coach.model == "gemini-1.5-flash"
    assert len(coach.tools) == 4  # 4 improv expert tools
```

**Acceptance Criteria:**
- Agent is instance of `google.adk.Agent`
- Model is `gemini-1.5-flash` (faster for coaching)
- Name is `coach_agent`
- Has exactly 4 tools attached

---

#### TC-COACH-02: Tool Attachment Verification
```python
def test_coach_agent_has_correct_tools():
    """Coach should have all 4 improv expert tools"""
    coach = create_coach_agent()

    tool_names = [tool.__name__ for tool in coach.tools]

    assert 'get_all_principles' in tool_names
    assert 'get_principle_by_id' in tool_names
    assert 'get_beginner_essentials' in tool_names
    assert 'search_principles_by_keyword' in tool_names
```

**Acceptance Criteria:**
- All 4 improv expert tools present
- Tools are from `app.tools.improv_expert_tools`
- No duplicate tools

**Required Tools:**
1. `get_all_principles()` - Get all 10 core principles
2. `get_principle_by_id(id)` - Get specific principle
3. `get_beginner_essentials()` - Get foundational principles
4. `search_principles_by_keyword(keyword)` - Search principles

---

#### TC-COACH-03: System Prompt Characteristics
```python
def test_coach_agent_system_prompt():
    """Coach should have encouraging, constructive prompt"""
    coach = create_coach_agent()

    instruction = coach.instruction

    # Check for coaching keywords
    assert "coach" in instruction.lower() or "feedback" in instruction.lower()
    assert "encourage" in instruction.lower() or "support" in instruction.lower()

    # Should reference improv principles
    assert "principle" in instruction.lower() or "improv" in instruction.lower()

    # Should be constructive, not critical
    assert len(instruction) > 200  # Substantial instruction
```

**Acceptance Criteria:**
- Emphasizes constructive feedback
- References improv principles
- Encouraging and supportive tone
- Guides users to improve, not criticize

**Example Keywords:**
- "coaching", "feedback", "encourage", "principles", "growth", "improvement"

---

#### TC-COACH-04: Tool Invocation Test
```python
@pytest.mark.asyncio
async def test_coach_can_invoke_tools():
    """Verify coach tools are properly integrated"""
    # Direct tool test (not through agent)
    from app.tools import improv_expert_tools

    principles = await improv_expert_tools.get_all_principles()
    assert len(principles) == 10

    yes_and = await improv_expert_tools.get_principle_by_id("yes_and")
    assert yes_and["name"] == "Yes, And..."

    essentials = await improv_expert_tools.get_beginner_essentials()
    assert len(essentials) >= 5
```

**Acceptance Criteria:**
- All tools return expected data structures
- No errors when invoking tools
- Data is well-formed (has expected fields)

---

### 2.3 Stage Manager Phase Transition Tests

**File:** `/Users/jpantona/Documents/code/ai4joy/tests/test_agents/test_stage_manager_phases.py`

#### TC-STAGE-01: Stage Manager Has 4 Sub-Agents
```python
def test_stage_manager_has_all_sub_agents():
    """Stage Manager should have MC, Room, Partner, Coach"""
    stage_manager = create_stage_manager()

    assert len(stage_manager.sub_agents) == 4

    agent_names = [agent.name for agent in stage_manager.sub_agents]
    assert 'mc_agent' in agent_names
    assert 'room_agent' in agent_names
    assert 'partner_agent' in agent_names
    assert 'coach_agent' in agent_names
```

**Acceptance Criteria:**
- Stage Manager has exactly 4 sub-agents
- MC, Room, Partner, Coach all present
- All are proper Agent instances

---

#### TC-STAGE-02: Phase Transition Logic - Turn 0-3
```python
def test_phase_transition_turns_0_to_3():
    """Turns 0-3 should use Phase 1 (supportive) Partner"""
    for turn_count in [0, 1, 2, 3]:
        phase = determine_partner_phase(turn_count)
        assert phase == 1, f"Turn {turn_count} should be Phase 1"
```

**Acceptance Criteria:**
- Turns 0, 1, 2, 3 → Phase 1
- Function `determine_partner_phase(turn_count)` exists
- Returns integer 1 or 2

---

#### TC-STAGE-03: Phase Transition Logic - Turn 4+
```python
def test_phase_transition_turn_4_onwards():
    """Turn 4 and beyond should use Phase 2 (fallible) Partner"""
    for turn_count in [4, 5, 6, 10, 14]:
        phase = determine_partner_phase(turn_count)
        assert phase == 2, f"Turn {turn_count} should be Phase 2"
```

**Acceptance Criteria:**
- Turns 4+ → Phase 2
- Transition happens exactly at turn 4
- No off-by-one errors

---

#### TC-STAGE-04: Partner Agent Updated During Session
```python
def test_partner_agent_updates_with_phase_change():
    """Partner agent should be recreated when phase changes"""
    # Mock session state
    session_state = {
        "turn_count": 3,
        "current_phase": 1
    }

    # Get partner for turn 3
    partner_phase1 = get_partner_for_turn(session_state)
    assert "support" in partner_phase1.instruction.lower()

    # Advance to turn 4
    session_state["turn_count"] = 4
    partner_phase2 = get_partner_for_turn(session_state)
    assert "fallible" in partner_phase2.instruction.lower()

    # Prompts should be different
    assert partner_phase1.instruction != partner_phase2.instruction
```

**Acceptance Criteria:**
- Partner agent is recreated with new phase
- System prompt changes between phases
- Phase change is seamless (no errors)

---

#### TC-STAGE-05: Phase Info in Instruction Context
```python
def test_phase_info_in_stage_manager_instruction():
    """Stage Manager should include phase info in instruction"""
    stage_manager = create_stage_manager(turn_count=5)

    instruction = stage_manager.instruction

    # Should mention current phase
    assert "phase" in instruction.lower() or "Phase 2" in instruction

    # Or check if instruction is dynamically generated
    # This depends on implementation
```

**Acceptance Criteria:**
- Stage Manager aware of current phase
- Phase communicated to sub-agents
- Turn count tracked correctly

---

### 2.4 Rate Limiter Tests (Already Implemented)

**File:** `/Users/jpantona/Documents/code/ai4joy/tests/test_rate_limiting.py`

**Status:** ✅ COMPLETE - Tests already exist

**Test Coverage:**
- TC-RATE-01: Daily limit enforcement (10 sessions)
- TC-RATE-02: Firestore persistence
- TC-RATE-03: Midnight UTC reset
- TC-RATE-04: Error response format
- TC-RATE-05: Concurrent session limit (3 sessions)
- TC-RATE-06: Concurrent independent of daily
- TC-RATE-07-09: Edge cases

**No additional tests needed** - RateLimiter is well-tested.

---

## 3. Integration Tests

**File:** `/Users/jpantona/Documents/code/ai4joy/tests/test_integration/test_week6_integration.py`

### TC-INT-01: Complete Session with Phase Transition
```python
@pytest.mark.asyncio
async def test_complete_session_with_phase_transition():
    """End-to-end test of 15-turn session with phase transition"""

    # Create session
    session = await create_session(user_id="test_user", location="Coffee Shop")

    # Turns 0-3: Phase 1 (supportive)
    for turn in range(4):
        response = await process_turn(session.id, user_input="user message")

        # Verify Phase 1 behavior
        assert session.current_phase == 1
        # Partner should be supportive

    # Turn 4: Phase transition
    response = await process_turn(session.id, user_input="user message")
    assert session.current_phase == 2

    # Turns 5-14: Phase 2 (fallible)
    for turn in range(5, 15):
        response = await process_turn(session.id, user_input="user message")
        assert session.current_phase == 2

    # Verify all agents participated
    assert any(msg.agent == "mc_agent" for msg in session.messages)
    assert any(msg.agent == "room_agent" for msg in session.messages)
    assert any(msg.agent == "partner_agent" for msg in session.messages)
    assert any(msg.agent == "coach_agent" for msg in session.messages)
```

---

### TC-INT-02: Rate Limit Prevents Excessive Sessions
```python
@pytest.mark.asyncio
async def test_rate_limit_prevents_11th_session():
    """User cannot create more than 10 sessions per day"""
    user_id = "rate_limit_test_user"

    # Create 10 sessions
    sessions = []
    for i in range(10):
        session = await create_session(user_id=user_id, location=f"Location {i}")
        sessions.append(session)

    # 11th session should raise RateLimitExceeded
    with pytest.raises(RateLimitExceeded, match="Daily limit"):
        await create_session(user_id=user_id, location="Location 11")
```

---

### TC-INT-03: All 4 Sub-Agents Respond
```python
@pytest.mark.asyncio
async def test_all_four_agents_respond_in_session():
    """Verify MC, Room, Partner, Coach all contribute"""
    session = await create_session(user_id="test_user", location="Park")

    # Turn 1: MC should welcome
    response = await process_turn(session.id, "Hello!")
    assert "mc_agent" in [msg.agent for msg in response.messages]

    # Turn 2: Room should assess
    response = await process_turn(session.id, "I'm excited!")
    assert "room_agent" in [msg.agent for msg in response.messages]

    # Turn 3: Partner should engage
    response = await process_turn(session.id, "Let's play!")
    assert "partner_agent" in [msg.agent for msg in response.messages]

    # Complete session - Coach should provide feedback
    await complete_session(session.id)
    assert "coach_agent" in [msg.agent for msg in session.messages]
```

---

## 4. Mock and Fixture Requirements

### 4.1 Mock Firestore for Rate Limiter
```python
# tests/fixtures/mock_firestore.py

@pytest.fixture
def mock_firestore_client(monkeypatch):
    """Mock Firestore client for rate limiter tests"""

    class MockDocument:
        def __init__(self, data):
            self._data = data
            self.exists = data is not None

        def to_dict(self):
            return self._data

        def get(self, transaction=None):
            return self

    class MockDocumentReference:
        def __init__(self):
            self._data = {}

        def get(self, transaction=None):
            return MockDocument(self._data)

        def set(self, data):
            self._data = data

        def update(self, data):
            self._data.update(data)

    class MockCollection:
        def __init__(self):
            self.docs = {}

        def document(self, doc_id):
            if doc_id not in self.docs:
                self.docs[doc_id] = MockDocumentReference()
            return self.docs[doc_id]

    class MockFirestore:
        def __init__(self):
            self.collections = {}

        def collection(self, name):
            if name not in self.collections:
                self.collections[name] = MockCollection()
            return self.collections[name]

        def transaction(self):
            # Simple mock - not transactional
            class MockTransaction:
                pass
            return MockTransaction()

    mock_client = MockFirestore()

    # Patch firestore.Client
    monkeypatch.setattr("google.cloud.firestore.Client", lambda **kwargs: mock_client)

    return mock_client
```

---

### 4.2 Agent Test Fixtures
```python
# tests/fixtures/agent_fixtures.py

@pytest.fixture
def partner_phase1():
    """Partner agent in Phase 1 (supportive)"""
    return create_partner_agent(phase=1)

@pytest.fixture
def partner_phase2():
    """Partner agent in Phase 2 (fallible)"""
    return create_partner_agent(phase=2)

@pytest.fixture
def coach_agent():
    """Coach agent with improv expert tools"""
    return create_coach_agent()

@pytest.fixture
def stage_manager_with_all_agents():
    """Stage Manager with MC, Room, Partner, Coach"""
    return create_stage_manager()
```

---

### 4.3 Session State Fixtures
```python
# tests/fixtures/session_fixtures.py

@pytest.fixture
def mock_session_phase1():
    """Mock session in Phase 1"""
    return {
        "session_id": "test_session_1",
        "user_id": "test_user",
        "location": "Coffee Shop",
        "turn_count": 2,
        "current_phase": 1,
        "messages": []
    }

@pytest.fixture
def mock_session_phase2():
    """Mock session in Phase 2"""
    return {
        "session_id": "test_session_2",
        "user_id": "test_user",
        "location": "Park",
        "turn_count": 6,
        "current_phase": 2,
        "messages": []
    }
```

---

## 5. Test Execution Strategy

### 5.1 Test Phases

**Phase 1: Unit Tests (Run First)**
```bash
# Partner Agent tests
pytest tests/test_agents/test_partner_agent.py -v

# Coach Agent tests
pytest tests/test_agents/test_coach_agent.py -v

# Stage Manager phase tests
pytest tests/test_agents/test_stage_manager_phases.py -v
```

**Phase 2: Integration Tests**
```bash
# Week 6 integration tests
pytest tests/test_integration/test_week6_integration.py -v
```

**Phase 3: Rate Limiter Verification**
```bash
# Verify rate limiter still works after changes
pytest tests/test_rate_limiting.py -v
```

---

### 5.2 Coverage Goals

**Minimum Coverage:**
- Partner Agent: 95%+ (simple agent, few branches)
- Coach Agent: 95%+ (simple agent, tool attachment)
- Phase Transition Logic: 100% (critical functionality)
- Rate Limiter: 90%+ (already tested)

**Critical Paths:**
- Phase 1 → Phase 2 transition
- All 4 agents in Stage Manager
- Rate limit enforcement

---

### 5.3 Test Data

**Phase Transition Test Data:**
```python
PHASE_TRANSITION_TEST_CASES = [
    (0, 1, "Turn 0 should be Phase 1"),
    (1, 1, "Turn 1 should be Phase 1"),
    (2, 1, "Turn 2 should be Phase 1"),
    (3, 1, "Turn 3 should be Phase 1"),
    (4, 2, "Turn 4 should be Phase 2"),
    (5, 2, "Turn 5 should be Phase 2"),
    (14, 2, "Turn 14 should be Phase 2"),
]
```

**Rate Limiter Test Users:**
```python
TEST_USERS = {
    "user_daily_limit": "test_user_daily_001",
    "user_concurrent_limit": "test_user_concurrent_001",
    "user_normal": "test_user_normal_001"
}
```

---

## 6. Testability Concerns & Recommendations

### 6.1 Identified Concerns

**CONCERN 1: Phase Transition Implementation**
- **Issue:** Unclear where turn_count tracking happens
- **Risk:** Phase transition may not trigger correctly
- **Recommendation:** Explicitly test turn_count increment in SessionManager

**CONCERN 2: Partner Agent Prompt Switching**
- **Issue:** Agent recreation vs prompt update
- **Risk:** Performance overhead if recreating agent every turn
- **Recommendation:** Consider caching Phase 1 and Phase 2 agents, switch between them

**CONCERN 3: Coach Timing**
- **Issue:** When does Coach provide feedback? After every turn? End of session?
- **Risk:** Unclear acceptance criteria
- **Recommendation:** Clarify Coach invocation trigger with product team

**CONCERN 4: Rate Limiter Concurrent Access**
- **Issue:** Firestore transaction testing
- **Risk:** Race conditions with multiple concurrent requests
- **Recommendation:** Add stress test with 10 concurrent session creation attempts

---

### 6.2 Missing Implementation Details

**NEEDS CLARIFICATION:**
1. **Coach Invocation:** When does Coach speak? Every turn? Only at end?
2. **Partner Temperature:** What temperature setting for Partner agent?
3. **Stage Manager Orchestration:** Sequential or parallel sub-agent execution?
4. **Phase Display:** Should phase info be visible to user?

---

## 7. Test File Structure

```
tests/
├── test_agents/
│   ├── __init__.py
│   ├── test_partner_agent.py      # TC-PARTNER-01 through TC-PARTNER-05
│   ├── test_coach_agent.py        # TC-COACH-01 through TC-COACH-04
│   └── test_stage_manager_phases.py  # TC-STAGE-01 through TC-STAGE-05
│
├── test_integration/
│   └── test_week6_integration.py  # TC-INT-01 through TC-INT-03
│
├── fixtures/
│   ├── __init__.py
│   ├── mock_firestore.py          # Mock Firestore client
│   ├── agent_fixtures.py          # Agent fixtures
│   └── session_fixtures.py        # Session state fixtures
│
└── test_rate_limiting.py          # ✅ Already complete
```

---

## 8. Success Criteria

### Week 6 Tests Pass When:

**Partner Agent:**
- ✅ Agent created with phase parameter
- ✅ Phase 1 prompt is supportive
- ✅ Phase 2 prompt is fallible
- ✅ Invalid phase raises ValueError

**Coach Agent:**
- ✅ Agent created with 4 tools
- ✅ Tools are improv expert functions
- ✅ System prompt is encouraging
- ✅ Tools return valid data

**Stage Manager:**
- ✅ Has 4 sub-agents (MC, Room, Partner, Coach)
- ✅ Phase transitions at turn 4
- ✅ Partner agent updates with phase change
- ✅ Phase info tracked in session state

**Integration:**
- ✅ 15-turn session completes with phase transition
- ✅ All 4 agents respond during session
- ✅ Rate limits still enforced
- ✅ No errors or exceptions

---

## 9. Test Automation

### 9.1 CI/CD Integration
```yaml
# .github/workflows/week6_tests.yml
name: Week 6 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt -r tests/requirements-test.txt
      - run: pytest tests/test_agents/ -v
      - run: pytest tests/test_integration/test_week6_integration.py -v
```

---

## 10. Next Steps

### For Implementation Team:
1. Create `partner_agent.py` with phase parameter
2. Create `coach_agent.py` with 4 improv expert tools
3. Update `stage_manager.py` to include Partner and Coach
4. Implement phase transition logic (turn_count → phase)
5. Add turn_count tracking to SessionManager

### For QA Team:
1. Write unit tests as agents are implemented
2. Run tests incrementally (TDD approach)
3. Create integration tests after unit tests pass
4. Document any bugs or deviations
5. Provide feedback on testability

---

## 11. Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Phase transition doesn't trigger | HIGH | MEDIUM | Explicit turn_count tests, logging |
| Partner prompts too similar | MEDIUM | LOW | Manual prompt review, A/B testing |
| Coach tools not invoked | HIGH | LOW | Direct tool integration tests |
| Rate limiter race conditions | MEDIUM | MEDIUM | Stress testing, Firestore transactions |
| Performance degradation (4 agents) | HIGH | MEDIUM | Latency tests, parallel execution |

---

## 12. Appendix

### 12.1 Key Files to Monitor
- `/Users/jpantona/Documents/code/ai4joy/app/agents/partner_agent.py` (NEW)
- `/Users/jpantona/Documents/code/ai4joy/app/agents/coach_agent.py` (NEW)
- `/Users/jpantona/Documents/code/ai4joy/app/agents/stage_manager.py` (UPDATE)
- `/Users/jpantona/Documents/code/ai4joy/app/services/session_manager.py` (UPDATE for turn_count)

### 12.2 Dependencies
- `google.adk` - Agent framework
- `google.cloud.firestore` - Rate limiting storage
- `app.tools.improv_expert_tools` - Coach tools
- `pytest`, `pytest-asyncio` - Testing framework

### 12.3 Environment Variables
```bash
# For testing
export GCP_PROJECT_ID="coherent-answer-479115-e1"
export FIRESTORE_DATABASE="(default)"
export RATE_LIMIT_DAILY_SESSIONS=10
export RATE_LIMIT_CONCURRENT_SESSIONS=3
```

---

**Document Status:** DRAFT
**Last Updated:** 2025-11-24
**Next Review:** After implementation begins
