# Week 6 Agent Tests - Quick Reference

## Test Files Overview

### test_partner_agent.py
Tests for Partner Agent with 2-phase behavior (supportive → fallible)

**Test Classes:**
1. `TestPartnerAgentCreation` - Agent instantiation
2. `TestPartnerPhase1Behavior` - Supportive mode validation
3. `TestPartnerPhase2Behavior` - Fallible mode validation
4. `TestPartnerParameterValidation` - Input validation
5. `TestPartnerConfiguration` - Model and tool config
6. `TestPartnerPromptQuality` - Prompt quality checks

**Total:** 15 test cases

### test_coach_agent.py
Tests for Coach Agent with improv expert tool integration

**Test Classes:**
1. `TestCoachAgentCreation` - Agent instantiation
2. `TestCoachToolAttachment` - Tool configuration
3. `TestCoachSystemPrompt` - Prompt characteristics
4. `TestCoachToolFunctionality` - Async tool invocation
5. `TestCoachConfiguration` - Model and config details
6. `TestCoachPromptQuality` - Prompt quality
7. `TestCoachIntegration` - Integration compatibility

**Total:** 18 test cases (includes async tests)

### test_stage_manager_phases.py
Tests for Stage Manager phase transition logic

**Test Classes:**
1. `TestStageManagerSubAgents` - 4 sub-agent verification
2. `TestPhaseTransitionLogic` - Turn → phase mapping
3. `TestPartnerAgentUpdates` - Partner recreation logic
4. `TestPhaseInformation` - Phase tracking
5. `TestStageManagerConfiguration` - Stage Manager config
6. `TestPhaseTransitionIntegration` - Integration tests
7. `TestPhaseEdgeCases` - Edge case handling

**Total:** 20 test cases

---

## Running Tests

### Run All Week 6 Tests
```bash
cd /Users/jpantona/Documents/code/ai4joy
pytest tests/test_agents/ -v
```

### Run Individual Test Files
```bash
# Partner Agent tests
pytest tests/test_agents/test_partner_agent.py -v

# Coach Agent tests
pytest tests/test_agents/test_coach_agent.py -v

# Stage Manager phase tests
pytest tests/test_agents/test_stage_manager_phases.py -v
```

### Run Specific Test Class
```bash
# Example: Only Partner Phase 1 tests
pytest tests/test_agents/test_partner_agent.py::TestPartnerPhase1Behavior -v

# Example: Only Coach tool tests
pytest tests/test_agents/test_coach_agent.py::TestCoachToolFunctionality -v
```

### Run Specific Test Case
```bash
# Example: Only phase transition boundary test
pytest tests/test_agents/test_stage_manager_phases.py::TestPhaseTransitionLogic::test_tc_stage_03_phase_transition_boundary -v
```

### Run with Coverage
```bash
pytest tests/test_agents/ -v \
  --cov=app.agents.partner_agent \
  --cov=app.agents.coach_agent \
  --cov=app.agents.stage_manager \
  --cov-report=term-missing
```

### Run Only Async Tests
```bash
pytest tests/test_agents/ -v -m asyncio
```

---

## Expected Test Results (When Implementation Complete)

### Before Implementation
```
FAILED - ImportError: cannot import name 'create_partner_agent'
FAILED - ImportError: cannot import name 'create_coach_agent'
FAILED - ImportError: cannot import name 'determine_partner_phase'
```

### After Partner Agent Implementation
```
test_partner_agent.py::TestPartnerAgentCreation::test_tc_partner_01_agent_creation_phase1 PASSED
test_partner_agent.py::TestPartnerPhase1Behavior::test_tc_partner_02_phase1_prompt_is_supportive PASSED
...
```

### After Coach Agent Implementation
```
test_coach_agent.py::TestCoachAgentCreation::test_tc_coach_01_agent_creation PASSED
test_coach_agent.py::TestCoachToolAttachment::test_tc_coach_02_has_all_four_tools PASSED
...
```

### After Stage Manager Updates
```
test_stage_manager_phases.py::TestStageManagerSubAgents::test_tc_stage_01_has_four_sub_agents PASSED
test_stage_manager_phases.py::TestPhaseTransitionLogic::test_tc_stage_02_turns_0_to_3_are_phase_1 PASSED
...
```

### All Tests Passing
```
tests/test_agents/test_partner_agent.py::TestPartnerAgentCreation::test_tc_partner_01_agent_creation_phase1 PASSED
tests/test_agents/test_partner_agent.py::TestPartnerAgentCreation::test_tc_partner_01_agent_creation_phase2 PASSED
...
================================ 53 passed in 2.45s ================================
```

---

## Common Issues and Solutions

### Issue: ImportError for create_partner_agent
**Cause:** `app/agents/partner_agent.py` not yet created
**Solution:** Wait for implementation or create file

### Issue: ImportError for determine_partner_phase
**Cause:** `stage_manager.py` not yet updated with phase logic
**Solution:** Add function to stage_manager.py

### Issue: Async test warnings
**Cause:** Missing pytest-asyncio plugin
**Solution:** `pip install pytest-asyncio`

### Issue: Tool function not found
**Cause:** Improv expert tools import issue
**Solution:** Verify `app/tools/improv_expert_tools.py` exists

### Issue: Agent missing 'instruction' attribute
**Cause:** Agent created incorrectly or ADK version issue
**Solution:** Verify ADK Agent constructor parameters

---

## Test Maintenance

### Adding New Tests
```python
# Add to appropriate test class in test file
class TestPartnerAgentCreation:
    def test_new_behavior(self):
        """Test description"""
        # Test implementation
        assert condition, "Error message"
```

### Marking Tests for Skip
```python
@pytest.mark.skip(reason="Feature not yet implemented")
def test_future_feature(self):
    pass
```

### Marking Expected Failures
```python
@pytest.mark.xfail(reason="Known issue IQS-47")
def test_with_known_bug(self):
    pass
```

---

## Test Output Examples

### Successful Test
```
tests/test_agents/test_partner_agent.py::TestPartnerAgentCreation::test_tc_partner_01_agent_creation_phase1 PASSED
✓ Partner Agent Phase 1 created successfully
  - Name: partner_agent
  - Model: gemini-1.5-pro
  - Tools: 0
  - Instruction length: 487 chars
```

### Failed Test
```
tests/test_agents/test_partner_agent.py::TestPartnerPhase1Behavior::test_tc_partner_02_phase1_prompt_is_supportive FAILED
____________ TestPartnerPhase1Behavior.test_tc_partner_02_phase1_prompt_is_supportive ____________

    def test_tc_partner_02_phase1_prompt_is_supportive(self):
        from app.agents.partner_agent import create_partner_agent

        partner = create_partner_agent(phase=1)
        instruction = partner.instruction.lower()

        supportive_keywords = ["support", "help", "encourage", "build", "scaffold", "guide"]
        found_supportive = [kw for kw in supportive_keywords if kw in instruction]

>       assert len(found_supportive) >= 2, \
            f"Phase 1 prompt should contain supportive keywords. Found: {found_supportive}"
E       AssertionError: Phase 1 prompt should contain supportive keywords. Found: ['help']
```

---

## Dependencies

**Required Packages:**
```
pytest>=7.4.0
pytest-asyncio>=0.21.0
google-adk>=0.1.0
```

**Required Modules:**
```
app.agents.partner_agent (NEW)
app.agents.coach_agent (NEW)
app.agents.stage_manager (UPDATE)
app.tools.improv_expert_tools (EXISTS)
```

---

## Documentation References

- **Test Plan:** `/Users/jpantona/Documents/code/ai4joy/tests/WEEK_6_TEST_PLAN.md`
- **QA Summary:** `/Users/jpantona/Documents/code/ai4joy/tests/WEEK_6_QA_SUMMARY.md`
- **Ticket:** IQS-46 - Implement ADK Multi-Agent Orchestration

---

**Last Updated:** 2025-11-24
**Test Count:** 53 tests
**Async Tests:** 5 tests
**Implementation Status:** Awaiting code
