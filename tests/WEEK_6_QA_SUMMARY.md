# Week 6 QA Summary - IQS-46 Implementation Monitoring

**QA Engineer:** QA Tester Agent
**Date:** 2025-11-24
**Ticket:** IQS-46 - Week 6 Implementation
**Status:** READY TO MONITOR IMPLEMENTATION

---

## Executive Summary

Comprehensive test suite created for Week 6 implementation:
- **Partner Agent** (Phase 1: Supportive + Phase 2: Fallible)
- **Coach Agent** (with 4 improv expert tools)
- **Stage Manager Phase Transitions** (turn 4 boundary)
- **Rate Limiter** (already tested, no new tests needed)

### Deliverables

**Test Documentation:**
- ✅ `/Users/jpantona/Documents/code/ai4joy/tests/WEEK_6_TEST_PLAN.md` (15-page comprehensive plan)

**Test Code:**
- ✅ `/Users/jpantona/Documents/code/ai4joy/tests/test_agents/test_partner_agent.py` (6 test classes, 15+ tests)
- ✅ `/Users/jpantona/Documents/code/ai4joy/tests/test_agents/test_coach_agent.py` (7 test classes, 18+ tests)
- ✅ `/Users/jpantona/Documents/code/ai4joy/tests/test_agents/test_stage_manager_phases.py` (6 test classes, 20+ tests)

**Total Test Coverage:** 53+ automated test cases

---

## Key Test Cases by Component

### Partner Agent (15 tests)

**Configuration Tests:**
- TC-PARTNER-01: Agent creation (Phase 1 & 2)
- TC-PARTNER-05: Uses gemini-1.5-pro, no tools

**Behavioral Tests:**
- TC-PARTNER-02: Phase 1 supportive prompt validation
- TC-PARTNER-03: Phase 2 fallible prompt validation
- TC-PARTNER-03b: Instructional fading (reduced scaffolding)

**Validation Tests:**
- TC-PARTNER-04: Phase parameter validation (only 1 or 2)
- TC-PARTNER-04c: Type checking (must be integer)

### Coach Agent (18 tests)

**Configuration Tests:**
- TC-COACH-01: Agent creation with 4 tools
- TC-COACH-02: Tool attachment verification
- TC-COACH-05: Uses gemini-1.5-flash

**Tool Integration Tests (Async):**
- TC-COACH-04a: `get_all_principles()` returns 10 principles
- TC-COACH-04b: `get_principle_by_id()` retrieves specific principle
- TC-COACH-04c: `get_beginner_essentials()` filters foundational principles
- TC-COACH-04d: `search_principles_by_keyword()` searches by text

**Prompt Quality Tests:**
- TC-COACH-03: Encouraging, constructive tone
- TC-COACH-03b: Tool awareness in prompt
- TC-COACH-06: Pedagogical approach

### Stage Manager Phase Transitions (20 tests)

**Sub-Agent Verification:**
- TC-STAGE-01: Has 4 sub-agents (MC, Room, Partner, Coach)
- TC-STAGE-01c: All required agents present

**Phase Logic Tests:**
- TC-STAGE-02: Turns 0-3 map to Phase 1
- TC-STAGE-03: Turns 4+ map to Phase 2
- TC-STAGE-03b: Boundary test (turn 3 vs turn 4)

**Partner Update Tests:**
- TC-STAGE-04: Partner agent recreated with new prompt
- TC-STAGE-04b: Phase 1 Partner is supportive
- TC-STAGE-04c: Phase 2 Partner is fallible

**Edge Cases:**
- TC-STAGE-08: Negative turn count handling
- TC-STAGE-08b: Very large turn counts (1000+)
- TC-STAGE-08c: Turn 0 defaults to Phase 1

---

## Test File Structure

```
tests/
├── WEEK_6_TEST_PLAN.md           # Comprehensive test plan (NEW)
├── WEEK_6_QA_SUMMARY.md          # This summary (NEW)
│
├── test_agents/
│   ├── __init__.py
│   ├── test_partner_agent.py      # 15 tests for Partner (NEW)
│   ├── test_coach_agent.py        # 18 tests for Coach (NEW)
│   └── test_stage_manager_phases.py  # 20 tests for phase logic (NEW)
│
└── test_rate_limiting.py          # ✅ Already complete (Week 5)
```

---

## Test Execution Strategy

### Phase 1: Unit Tests (Run as code is written)

```bash
# Partner Agent tests
pytest tests/test_agents/test_partner_agent.py -v

# Coach Agent tests
pytest tests/test_agents/test_coach_agent.py -v

# Stage Manager phase tests
pytest tests/test_agents/test_stage_manager_phases.py -v
```

### Phase 2: All Week 6 Tests

```bash
# Run all agent tests together
pytest tests/test_agents/ -v

# With coverage
pytest tests/test_agents/ -v --cov=app.agents --cov-report=term-missing
```

### Phase 3: Rate Limiter Regression

```bash
# Verify rate limiter still works
pytest tests/test_rate_limiting.py -v
```

---

## Implementation Requirements Detected

Based on test suite, implementation team needs to create:

### 1. Partner Agent (`/Users/jpantona/Documents/code/ai4joy/app/agents/partner_agent.py`)

```python
def create_partner_agent(phase: int) -> Agent:
    """Create Partner agent with phase-specific behavior

    Args:
        phase: 1 (supportive) or 2 (fallible)

    Returns:
        Configured Agent instance

    Raises:
        ValueError: If phase not 1 or 2
    """
    if phase not in [1, 2]:
        raise ValueError("phase must be 1 or 2")

    # Phase-specific prompts
    # Use gemini-1.5-pro
    # No tools
    # Return Agent instance
```

### 2. Coach Agent (`/Users/jpantona/Documents/code/ai4joy/app/agents/coach_agent.py`)

```python
def create_coach_agent() -> Agent:
    """Create Coach agent with improv expert tools

    Returns:
        Configured Agent with 4 tools attached
    """
    from app.tools import improv_expert_tools

    # Use gemini-1.5-flash
    # Attach 4 tools: get_all_principles, get_principle_by_id,
    #                 get_beginner_essentials, search_principles_by_keyword
    # Encouraging, constructive prompt
    # Return Agent instance
```

### 3. Stage Manager Updates (`/Users/jpantona/Documents/code/ai4joy/app/agents/stage_manager.py`)

**Add Functions:**
```python
def determine_partner_phase(turn_count: int) -> int:
    """Determine which phase based on turn count

    Args:
        turn_count: Current turn number (0-indexed)

    Returns:
        1 if turn_count < 4, else 2
    """
    return 1 if turn_count < 4 else 2


def get_partner_agent_for_turn(turn_count: int) -> Agent:
    """Get appropriate Partner agent for current turn

    Args:
        turn_count: Current turn number

    Returns:
        Partner agent with correct phase
    """
    phase = determine_partner_phase(turn_count)
    return create_partner_agent(phase)
```

**Update `create_stage_manager()`:**
- Add Partner and Coach to sub_agents list
- Now has 4 sub-agents: [mc, room, partner, coach]

---

## Test Dependencies

### Python Packages
```
pytest>=7.4.0
pytest-asyncio>=0.21.0
google-adk>=0.1.0
```

### Files/Modules Required
```
app/agents/partner_agent.py    # NEW - to be implemented
app/agents/coach_agent.py      # NEW - to be implemented
app/agents/stage_manager.py    # UPDATE - add Partner/Coach
app/tools/improv_expert_tools.py  # ✅ Already exists
```

---

## Critical Test Scenarios

### Scenario 1: Phase Transition at Turn 4
```
Turn 0-3: Partner uses supportive prompt (Phase 1)
Turn 4:   Partner switches to fallible prompt (Phase 2)
Turn 5+:  Partner continues with fallible prompt
```

**Tests:**
- `test_tc_stage_02_turns_0_to_3_are_phase_1()`
- `test_tc_stage_03_turn_4_onwards_is_phase_2()`
- `test_tc_stage_03_phase_transition_boundary()`

### Scenario 2: Coach Tool Integration
```
Coach agent created → has 4 tools attached
Each tool invoked → returns valid data structure
Tools contain: 10 principles, examples, coaching tips
```

**Tests:**
- `test_tc_coach_02_has_all_four_tools()`
- `test_tc_coach_04_get_all_principles_works()`
- `test_tc_coach_04_tools_return_consistent_structure()`

### Scenario 3: Partner Prompt Differentiation
```
Phase 1 prompt: "support", "help", "encourage", "guide"
Phase 2 prompt: "fallible", "realistic", "forget", "miss"
Scaffolding reduced from Phase 1 to Phase 2
```

**Tests:**
- `test_tc_partner_02_phase1_prompt_is_supportive()`
- `test_tc_partner_03_phase2_prompt_is_fallible()`
- `test_tc_partner_03_phase2_reduces_scaffolding()`

---

## Testability Concerns

### CONCERN 1: Phase Transition Implementation
**Issue:** Unclear where turn_count tracking happens
**Impact:** HIGH - Phase transition won't trigger correctly
**Mitigation:**
- Explicit tests for `determine_partner_phase()` function
- Tests verify turn_count → phase mapping
- Edge case tests for boundaries

### CONCERN 2: Partner Agent Prompt Switching
**Issue:** Agent recreation vs prompt update performance
**Impact:** MEDIUM - Potential latency overhead
**Recommendation:**
- Cache Phase 1 and Phase 2 Partner agents
- Switch between cached instances rather than recreating
- Monitor performance in integration tests

### CONCERN 3: Coach Invocation Timing
**Issue:** When does Coach provide feedback?
**Impact:** MEDIUM - Unclear acceptance criteria
**Questions for Product:**
- After every turn?
- Only at end of session?
- On-demand when user requests feedback?

### CONCERN 4: Rate Limiter Concurrent Access
**Issue:** Firestore transaction testing
**Impact:** LOW - Already tested, but watch for race conditions
**Mitigation:**
- Existing tests cover daily and concurrent limits
- No new tests needed
- Monitor production logs for race conditions

---

## Success Criteria

### Week 6 Tests PASS When:

**Partner Agent:**
- ✅ Created with phase=1 or phase=2
- ✅ Phase 1 prompt contains supportive keywords
- ✅ Phase 2 prompt contains fallible keywords
- ✅ Invalid phase values raise ValueError
- ✅ Uses gemini-1.5-pro model
- ✅ Has no tools attached

**Coach Agent:**
- ✅ Created with 4 improv expert tools
- ✅ Uses gemini-1.5-flash model
- ✅ All 4 tools return valid data
- ✅ Prompt is encouraging and constructive
- ✅ Tools are from improv_expert_tools module

**Stage Manager:**
- ✅ Has 4 sub-agents (MC, Room, Partner, Coach)
- ✅ Phase transition happens at turn 4
- ✅ Partner agent updates when phase changes
- ✅ Phase 1 = supportive, Phase 2 = fallible

**Integration:**
- ✅ All tests run without import errors
- ✅ No conflicts between agents
- ✅ Rate limiter still functions correctly

---

## Next Steps for Implementation Team

### Step 1: Create Partner Agent
```bash
touch app/agents/partner_agent.py
```

**Requirements:**
- Function: `create_partner_agent(phase: int) -> Agent`
- Phase 1 prompt: Supportive, scaffolding
- Phase 2 prompt: Fallible, realistic
- Model: gemini-1.5-pro
- Tools: None

### Step 2: Create Coach Agent
```bash
touch app/agents/coach_agent.py
```

**Requirements:**
- Function: `create_coach_agent() -> Agent`
- Model: gemini-1.5-flash
- Tools: 4 from improv_expert_tools
- Prompt: Encouraging, pedagogical

### Step 3: Update Stage Manager
**File:** `app/agents/stage_manager.py`

**Add:**
- `determine_partner_phase(turn_count: int) -> int`
- `get_partner_agent_for_turn(turn_count: int) -> Agent`

**Update:**
- Add Partner and Coach to sub_agents list

### Step 4: Run Tests Incrementally
```bash
# After Partner implementation
pytest tests/test_agents/test_partner_agent.py -v

# After Coach implementation
pytest tests/test_agents/test_coach_agent.py -v

# After Stage Manager updates
pytest tests/test_agents/test_stage_manager_phases.py -v
```

---

## QA Monitoring Plan

### During Implementation:
1. **Watch for new files** in `app/agents/`
2. **Run tests immediately** when code is pushed
3. **Log failures** with clear reproduction steps
4. **Verify test assumptions** match implementation

### Post-Implementation:
1. **Run full test suite** (all 53+ tests)
2. **Generate coverage report**
3. **Document deviations** from requirements
4. **Create bug tickets** for failures

### Reporting:
- Daily status updates on test passage rate
- Highlight blocking failures
- Recommend fixes with specific test cases

---

## Test Metrics Targets

**Code Coverage:**
- Partner Agent: 95%+
- Coach Agent: 95%+
- Stage Manager (phase logic): 100%

**Test Passage Rate:**
- Unit tests: 100% (all pass)
- Integration tests: 95%+ (allowing for minor edge cases)

**Performance:**
- All tests complete in < 30 seconds
- No timeout failures

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Phase transition doesn't trigger | MEDIUM | HIGH | Explicit boundary tests, logging |
| Partner prompts too similar | LOW | MEDIUM | Keyword validation tests |
| Coach tools not invoked correctly | LOW | HIGH | Direct tool tests, async validation |
| Rate limiter regression | LOW | MEDIUM | Run existing tests, monitor logs |
| Performance degradation (4 agents) | MEDIUM | HIGH | (Out of scope for this test suite) |

---

## Contact & Escalation

**For Test Failures:**
1. Check test output for specific assertion
2. Review implementation against test expectations
3. Check for import errors or missing modules
4. Escalate to QA Tester Agent if unclear

**For Requirements Clarification:**
1. Review IQS-46 ticket description
2. Check WEEK_6_TEST_PLAN.md for details
3. Ask specific questions with test case references

**For Test Code Issues:**
1. All test files are in `/Users/jpantona/Documents/code/ai4joy/tests/test_agents/`
2. Tests use pytest framework
3. Async tests marked with `@pytest.mark.asyncio`

---

## Summary Statistics

**Test Files Created:** 3
**Test Classes:** 19
**Test Functions:** 53+
**Lines of Test Code:** ~1,200
**Documentation Pages:** 15 (test plan) + 6 (this summary)

**Coverage:**
- Partner Agent: 15 tests
- Coach Agent: 18 tests
- Stage Manager: 20 tests

**Implementation Readiness:** ✅ READY
**Documentation Completeness:** ✅ COMPLETE
**Monitoring Status:** 🟢 ACTIVE

---

**Document Version:** 1.0
**Last Updated:** 2025-11-24
**Next Review:** After implementation begins
