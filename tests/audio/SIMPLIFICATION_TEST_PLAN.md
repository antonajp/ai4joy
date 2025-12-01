# Audio Orchestration Simplification - QA Test Plan

## Executive Summary

**Objective**: Simplify audio orchestration by eliminating separate scene partner and audience agents, consolidating functionality into MC agent only.

**Scope**: Audio mode orchestration, agent coordination, suggestion generation, turn-taking, and user experience.

**Risk Level**: HIGH - Major architectural change affecting core audio experience

---

## Current Architecture Analysis

### Existing Components (Before Simplification)

**Agents (3 total)**:
1. **MC Agent** (`mc_agent_audio`)
   - Role: Host, game selection, rule explanation, suggestion gathering
   - Voice: Aoede
   - Toolsets: ImprovGamesToolset, SceneTransitionToolset, AudienceArchetypesToolset
   - System prompt: AUDIO_MC_SYSTEM_PROMPT (lines 60-163 in mc_agent.py)

2. **Partner Agent** (`partner_agent_audio`)
   - Role: Scene partner for improv work
   - Voice: Puck
   - Phase-based behavior: Phase 1 (supportive), Phase 2 (fallible)
   - System prompts: PHASE_1_SYSTEM_PROMPT, PHASE_2_SYSTEM_PROMPT

3. **Room Agent** (`room_agent_audio`)
   - Role: Ambient audience commentary
   - Voice: Charon
   - Volume: 30% (background)
   - Toolsets: SentimentAnalysisToolset, AudienceArchetypesToolset

**Audio Orchestration**:
- `AudioStreamOrchestrator` manages all three agents per session
- `AgentTurnManager` coordinates MC ↔ Partner handoffs
- `AudioMixer` combines streams at different volumes
- `AmbientAudioTrigger` controls Room agent activation

**Agent Switching Flow**:
1. MC welcomes user, explains game
2. MC calls `_start_scene` tool → switches to Partner
3. Partner performs scene work
4. Partner calls `_end_scene` tool → switches back to MC
5. Room agent provides ambient commentary asynchronously

### Current Test Coverage

**Unit Tests** (73 test files found):
- `test_audio_orchestrator.py` - Core orchestration logic (7 test cases)
- `test_mc_audio.py` - MC agent audio integration (6 test cases)
- `test_partner_audio.py` - Partner agent audio tests
- `test_multi_agent.py` - Agent coordination and switching (12 test cases)
- `test_audience_response.py` - Room agent ambient audio (10 test cases)
- `test_turn_manager.py` - Turn-taking coordination
- `test_room_tts.py` - Room agent TTS generation

**Integration Tests**:
- `test_full_scene_with_audience.py` - E2E scene with all agents
- `test_audience_suggestions.py` - Audience suggestion generation
- `test_room_audio.py` - Room agent integration

**Critical Test Coverage**:
- ✅ Agent initialization per session
- ✅ Agent switching via tools (_start_scene, _end_scene, _resume_scene)
- ✅ Voice configuration per agent
- ✅ Phase transitions for Partner agent
- ✅ Audio mixing at different volumes
- ✅ Ambient trigger with cooldown
- ✅ Turn manager coordination

---

## Simplification Options

### Option A: MC Agent Only (Recommended)

**Changes**:
- ELIMINATE: Partner Agent, Room Agent
- MC handles ALL responsibilities:
  - Hosting and game selection
  - Suggestion generation (via AudienceArchetypesToolset)
  - Scene partner behavior
  - No handoffs, no agent switching

**Pros**:
- Simplest architecture - single agent
- No coordination complexity
- Faster response times (no handoff delays)
- Lower token consumption (one agent context)
- Easier to test and debug

**Cons**:
- MC loses focused hosting persona
- No progressive difficulty (Phase 1 → Phase 2)
- Less variety in voice/personality
- All functionality in one system prompt

### Option B: MC + Text-Only Audience (Fallback)

**Changes**:
- ELIMINATE: Partner Agent, Room Agent audio
- KEEP: Audience suggestions as text-only visual elements
- MC handles scene partner + hosting

**Pros**:
- Retains audience suggestion variety
- Visual feedback for user engagement
- MC can reference audience reactions in text

**Cons**:
- More complex than Option A
- Mixed modality (audio + text) may confuse
- Text might be ignored in audio-focused experience

---

## Test Strategy for Simplification

### Phase 1: Pre-Implementation Analysis (Current Step)

**Goal**: Identify all dependencies and impact areas before code changes.

**Test Analysis Tasks**:
1. ✅ Map all agent usages in codebase
2. ✅ Identify agent switching logic
3. ✅ Document toolset dependencies
4. ✅ List all test files affected
5. ⬜ Create test matrix for regression coverage

### Phase 2: Unit Test Design

**New Tests Required** (Option A - MC Only):

#### TC-SIMP-MC-01: MC Agent Consolidation
```python
@pytest.mark.asyncio
async def test_mc_agent_handles_all_responsibilities():
    """MC agent should handle hosting, suggestions, AND scene work."""
    from app.agents.mc_agent import create_mc_agent_for_audio_simplified

    agent = create_mc_agent_for_audio_simplified()

    # Verify agent has all necessary tools
    assert has_toolset(agent, ImprovGamesToolset)
    assert has_toolset(agent, AudienceArchetypesToolset)

    # Verify system prompt includes scene partner behavior
    assert "scene partner" in agent.instruction.lower()
    assert "yes, and" in agent.instruction.lower()
```

#### TC-SIMP-MC-02: Suggestion Generation
```python
@pytest.mark.asyncio
async def test_mc_generates_audience_suggestions():
    """MC should generate suggestions without Room agent."""
    # MC calls _get_suggestion_for_game tool
    # Should return audience-style suggestions
    # No dependency on Room agent
```

#### TC-SIMP-MC-03: Scene Partner Behavior
```python
@pytest.mark.asyncio
async def test_mc_acts_as_scene_partner():
    """MC should perform scene work directly."""
    # User: "I'm at a bakery"
    # MC: "Yes, and I'm the baker who just burned the croissants!"
    # No handoff to Partner agent
```

#### TC-SIMP-MC-04: Phase Transitions (If Retained)
```python
@pytest.mark.asyncio
async def test_mc_phase_based_difficulty():
    """MC adjusts difficulty based on turn count."""
    # Turns 1-3: Supportive scene partner
    # Turns 4+: More challenging scene partner
    # OR: Remove phases entirely for simplicity
```

#### TC-SIMP-ORCH-01: Single Agent Orchestration
```python
@pytest.mark.asyncio
async def test_orchestrator_single_agent_only():
    """Orchestrator should only manage MC agent."""
    orchestrator = AudioStreamOrchestrator()
    session_id = "test-single-agent"

    await orchestrator.start_session(session_id, user_id="test", user_email="test@example.com")

    session = await orchestrator.get_session(session_id)

    # Should have MC agent only
    assert session.mc_agent is not None
    assert session.partner_agent is None  # ELIMINATED
    assert session.room_agent is None     # ELIMINATED
    assert session.current_agent == "mc"  # Always MC
```

#### TC-SIMP-ORCH-02: No Agent Switching
```python
@pytest.mark.asyncio
async def test_no_agent_switching_needed():
    """Agent switching logic should be removed."""
    orchestrator = AudioStreamOrchestrator()

    # Methods should not exist or should be no-ops
    assert not hasattr(orchestrator, 'switch_to_partner')
    assert not hasattr(orchestrator, 'switch_to_mc')

    # OR: Methods exist but do nothing
    # orchestrator.switch_to_partner(session_id)  # Should raise or no-op
```

#### TC-SIMP-ORCH-03: Simplified Turn Management
```python
@pytest.mark.asyncio
async def test_simplified_turn_tracking():
    """Turn manager only tracks user ↔ MC turns."""
    orchestrator = AudioStreamOrchestrator()
    session_id = "test-turns"

    await orchestrator.start_session(session_id, user_id="test", user_email="test@example.com")

    session = await orchestrator.get_session(session_id)

    # No turn manager needed OR simplified version
    if session.turn_manager:
        assert session.turn_manager.current_speaker in ["user", "mc"]
        # Partner, Room not in rotation
```

#### TC-SIMP-AUDIO-01: Audio Mixer Simplified
```python
@pytest.mark.asyncio
async def test_audio_mixer_single_stream():
    """Audio mixer only handles MC stream (no mixing needed)."""
    orchestrator = AudioStreamOrchestrator()
    session_id = "test-audio-mix"

    await orchestrator.start_session(session_id, user_id="test", user_email="test@example.com")

    session = await orchestrator.get_session(session_id)

    # Audio mixer should not exist OR only handle MC
    if session.audio_mixer:
        assert session.audio_mixer.get_volume("mc") == 1.0
        # No partner or room volumes
```

#### TC-SIMP-VOICE-01: Single Voice Configuration
```python
def test_voice_config_mc_only():
    """Voice configuration should only return MC voice."""
    orchestrator = AudioStreamOrchestrator()

    voice = orchestrator.get_voice_config()
    assert voice.voice_name == "Aoede"  # MC voice

    # No agent-specific voice switching needed
```

### Phase 3: Integration Testing

#### TC-SIMP-INT-01: Full Audio Session Flow
```python
@pytest.mark.asyncio
async def test_full_audio_session_mc_only():
    """Complete audio session with MC handling everything."""
    orchestrator = AudioStreamOrchestrator()
    session_id = "test-full-session"

    # Start session
    await orchestrator.start_session(session_id, user_id="test", user_email="test@example.com")

    # MC welcomes user
    # MC suggests game
    # MC gets audience suggestion
    # MC starts scene directly (no handoff)
    # MC performs scene work
    # MC ends scene

    # All in one continuous flow, no agent switching
```

#### TC-SIMP-INT-02: Suggestion Generation Without Room Agent
```python
@pytest.mark.asyncio
async def test_suggestions_without_room_agent():
    """MC generates suggestions using toolset directly."""
    orchestrator = AudioStreamOrchestrator()
    session_id = "test-suggestions"

    await orchestrator.start_session(session_id, user_id="test", user_email="test@example.com")

    # Mock tool call response
    # MC calls _get_suggestion_for_game("first_line_last_line")
    # Should return: "Someone from the crowd shouts: 'I can't believe you ate all the pizza!'"
    # No Room agent involved
```

#### TC-SIMP-INT-03: Scene Work Without Partner Agent
```python
@pytest.mark.asyncio
async def test_scene_work_without_partner():
    """MC performs scene work in same turn as hosting."""
    orchestrator = AudioStreamOrchestrator()

    # User speaks
    # MC responds with scene work (no handoff delay)
    # User continues scene
    # MC continues scene

    # Seamless conversation, no agent transition overhead
```

### Phase 4: Regression Testing

**Tests to Update** (existing tests that will break):

1. **test_audio_orchestrator.py**:
   - ❌ `test_tc_orch_01_orchestrator_initializes_with_per_session_agents` - Update to single agent
   - ✅ `test_tc_orch_02_orchestrator_creates_live_request_queue` - Should still work
   - ✅ `test_tc_orch_03_audio_chunks_forwarded_to_queue` - Should still work
   - ✅ `test_tc_orch_04_agent_responses_streamed_back` - Update to remove agent field
   - ✅ `test_tc_orch_05_session_lifecycle_start_stop` - Should still work
   - ✅ `test_tc_orch_06_graceful_shutdown_on_close` - Should still work
   - ✅ `test_tc_orch_07_error_handling_malformed_audio` - Should still work

2. **test_mc_audio.py**:
   - ✅ All tests should pass with updated MC behavior
   - Update: MC now handles scene work, not just hosting

3. **test_partner_audio.py**:
   - ❌ DELETE entire file (Partner agent eliminated)

4. **test_multi_agent.py**:
   - ❌ DELETE entire file (multi-agent coordination eliminated)
   - Key functionality to retain:
     - Turn completion tracking
     - Session state management
     - Voice configuration

5. **test_audience_response.py**:
   - ❌ DELETE or REPLACE based on Option A vs B
   - Option A: Delete (no audience)
   - Option B: Keep but modify for text-only

6. **test_turn_manager.py**:
   - ❌ SIMPLIFY - Only user ↔ MC turns
   - Remove: MC ↔ Partner switching
   - Remove: Room agent coordination

7. **test_room_tts.py**:
   - ❌ DELETE (Room agent eliminated)

8. **test_full_scene_with_audience.py**:
   - ❌ REWRITE for MC-only flow
   - No agent switching
   - MC handles all scene work

9. **test_audience_suggestions.py**:
   - ⚠️ MODIFY - MC calls suggestion tools directly
   - No Room agent intermediary

### Phase 5: User Experience Testing

#### TC-SIMP-UX-01: Response Latency
```python
@pytest.mark.asyncio
async def test_response_latency_improved():
    """MC-only should be faster (no handoff overhead)."""
    # Measure time from user audio end to MC response start
    # Should be < 1 second (faster than multi-agent)
```

#### TC-SIMP-UX-02: Conversation Flow
```python
@pytest.mark.asyncio
async def test_conversation_feels_natural():
    """Single MC voice should feel coherent."""
    # User: "I'm ready to play"
    # MC: "Great! Let's do Status Shift. You start high status!"
    # User: "I'm the CEO"
    # MC: "Yes, and I'm your nervous intern with the quarterly reports..."

    # Natural flow, no personality switch
```

#### TC-SIMP-UX-03: Game Rule Clarity
```python
@pytest.mark.asyncio
async def test_game_rules_still_clear():
    """MC explains AND models game rules."""
    # MC: "In Status Shift, we swap high/low status. I'll start low."
    # MC behavior demonstrates the rules
    # User learns by example
```

---

## Test Execution Strategy

### Automation Priority

**P0 - Critical (Must Automate)**:
1. Agent initialization (TC-SIMP-MC-01, TC-SIMP-ORCH-01)
2. Suggestion generation (TC-SIMP-MC-02, TC-SIMP-INT-02)
3. Session lifecycle (TC-SIMP-ORCH-01)
4. Audio streaming (existing tests)
5. Tool execution (suggestion tools)

**P1 - High (Should Automate)**:
1. Scene partner behavior (TC-SIMP-MC-03)
2. Full session flow (TC-SIMP-INT-01)
3. Turn tracking (TC-SIMP-ORCH-03)
4. Voice configuration (TC-SIMP-VOICE-01)

**P2 - Medium (Manual/Exploratory)**:
1. Conversation naturalness (TC-SIMP-UX-02)
2. Game rule clarity (TC-SIMP-UX-03)
3. Response quality
4. User satisfaction

**P3 - Low (Optional)**:
1. Phase transitions (if removed)
2. Advanced audio mixing (not needed for single stream)

### Test Execution Order

**Pre-Implementation** (before code changes):
1. Run ALL existing tests → establish baseline
2. Document all passing tests
3. Identify tests that will break

**During Implementation**:
1. Update unit tests first (TDD approach)
2. Fix breaking tests incrementally
3. Add new simplified tests
4. Remove obsolete tests (Partner, Room)

**Post-Implementation**:
1. Full regression suite
2. Integration tests
3. Manual UX testing
4. Performance benchmarking

---

## Risk Assessment & Mitigation

### High-Risk Areas

**1. MC Prompt Complexity**
- **Risk**: Single prompt trying to do too much (hosting + scene work)
- **Impact**: Confused behavior, poor scene quality
- **Mitigation**:
  - Split prompt into clear sections
  - Test with varied scenarios
  - Gradual prompt refinement
- **Test Coverage**: TC-SIMP-MC-01, TC-SIMP-MC-03, TC-SIMP-UX-02

**2. Loss of Persona Variety**
- **Risk**: Single voice feels monotonous vs. 3 distinct agents
- **Impact**: User engagement drops
- **Mitigation**:
  - MC adopts different "modes" within scenes
  - Use emotion/tone modulation
  - Vary response style by context
- **Test Coverage**: TC-SIMP-UX-02, TC-SIMP-UX-03

**3. Suggestion Quality**
- **Risk**: MC-generated suggestions feel less authentic than "Room agent"
- **Impact**: Suggestions feel forced or artificial
- **Mitigation**:
  - Keep AudienceArchetypesToolset for demographic variety
  - MC frames suggestions as "from the audience"
  - Test suggestion diversity
- **Test Coverage**: TC-SIMP-MC-02, TC-SIMP-INT-02

**4. Progressive Difficulty Loss**
- **Risk**: Removing Phase 1→2 transition makes training less effective
- **Impact**: Users don't improve as quickly
- **Mitigation**:
  - Retain phase transitions in MC behavior
  - Use turn count to adjust MC difficulty
  - OR: Accept simpler experience for architectural gain
- **Test Coverage**: TC-SIMP-MC-04

**5. Regression in Existing Features**
- **Risk**: Breaking working audio features during refactor
- **Impact**: Production bugs, user complaints
- **Mitigation**:
  - Comprehensive regression suite before changes
  - Feature flags for gradual rollout
  - Keep Option B as fallback
- **Test Coverage**: All Phase 4 regression tests

### Medium-Risk Areas

**6. Tool Execution Changes**
- **Risk**: Removing _start_scene/_end_scene breaks tool calling flow
- **Impact**: Tool call errors, confused agent behavior
- **Mitigation**:
  - Update MC toolset gradually
  - Test tool calling in isolation
  - Remove tools only after MC updated
- **Test Coverage**: TC-SIMP-MC-01, existing tool tests

**7. Turn Tracking Simplification**
- **Risk**: Turn manager bugs when removing multi-agent support
- **Impact**: Turn count inaccurate, phase transitions break
- **Mitigation**:
  - Simplify turn manager incrementally
  - Test turn counting thoroughly
  - Consider removing turn manager entirely
- **Test Coverage**: TC-SIMP-ORCH-03

**8. Audio Mixer Removal**
- **Risk**: Breaking audio playback when removing mixer
- **Impact**: No audio output, playback errors
- **Mitigation**:
  - Keep mixer but simplify to single stream
  - OR: Remove mixer and pass-through MC audio
  - Test audio playback at each step
- **Test Coverage**: TC-SIMP-AUDIO-01

---

## Test Metrics & Success Criteria

### Code Coverage Targets

**Before Simplification**:
- Unit test coverage: ~85% (estimated from existing tests)
- Integration test coverage: ~60%
- Audio orchestration: ~90%

**After Simplification** (Target):
- Unit test coverage: ≥85% (maintain or improve)
- Integration test coverage: ≥70% (improve with simpler architecture)
- MC agent coverage: ≥95% (comprehensive since it's the only agent)

### Performance Benchmarks

**Latency Improvements** (Expected):
- Agent handoff delay: ELIMINATED (~200-500ms saved)
- Response time: Faster (single agent context)
- Audio start latency: <1s (vs current ~1.5s)

**Token Efficiency**:
- Context size: Reduced (1 agent vs 3)
- Tool calls: Reduced (no _start_scene/_end_scene handoffs)
- Cost per session: ~30-40% reduction

### Quality Metrics

**Automated Test Success Rate**:
- All new tests: 100% pass
- Regression tests: 100% pass (after updates)
- Integration tests: 100% pass

**Manual Test Criteria**:
- Conversation feels natural: ≥4/5 rating
- Suggestions feel authentic: ≥4/5 rating
- Scene quality maintained: ≥3.5/5 rating (may decrease slightly)
- Overall experience: ≥4/5 rating

---

## Implementation Recommendations

### Recommended Approach: Option A with Phased Rollout

**Phase 1: MC Consolidation** (Week 1)
1. Create new `create_mc_agent_for_audio_simplified()` factory
2. Update MC system prompt to include scene partner behavior
3. Add AudienceArchetypesToolset to MC
4. Test MC in isolation with new prompt
5. **Tests**: TC-SIMP-MC-01, TC-SIMP-MC-02, TC-SIMP-MC-03

**Phase 2: Orchestrator Simplification** (Week 2)
1. Update `AudioStreamOrchestrator` to use MC only
2. Remove Partner/Room agent initialization
3. Simplify or remove turn manager
4. Remove agent switching logic
5. **Tests**: TC-SIMP-ORCH-01, TC-SIMP-ORCH-02, TC-SIMP-ORCH-03

**Phase 3: Cleanup & Optimization** (Week 3)
1. Remove SceneTransitionToolset (no handoffs needed)
2. Simplify audio mixer (single stream)
3. Remove obsolete tests
4. Update integration tests
5. **Tests**: Phase 4 regression suite

**Phase 4: Production Validation** (Week 4)
1. Feature flag rollout (10% → 50% → 100%)
2. Monitor latency, errors, user feedback
3. A/B test if possible (old vs new)
4. Roll back to Option B if issues found

### Fallback Plan: Option B

If Option A shows quality issues:
1. Keep MC-only architecture
2. Add text-only audience suggestions in UI
3. Visual color indicators for "audience reactions"
4. MC references text suggestions: "I see the audience suggested 'coffee shop'!"

**Pros**:
- Retains suggestion variety
- Simple to implement (just UI changes)
- No audio complexity

**Cons**:
- Mixed modality (audio + text)
- Users may ignore text in audio mode

---

## Test Deliverables

### Documentation
- ✅ This test plan
- ⬜ Test case specifications (detailed)
- ⬜ Test execution report
- ⬜ Bug/issue tracking sheet
- ⬜ Performance benchmarking results

### Code
- ⬜ New test files (TC-SIMP-* series)
- ⬜ Updated existing tests
- ⬜ Test fixtures for MC-only scenarios
- ⬜ Mock data for suggestions
- ⬜ Performance test harness

### Reports
- ⬜ Pre-implementation test baseline
- ⬜ Post-implementation regression report
- ⬜ UX testing summary
- ⬜ Performance comparison (before/after)
- ⬜ Final recommendation (proceed/rollback)

---

## Timeline Estimate

**Total Duration**: 3-4 weeks

**Week 1**: Pre-implementation analysis, test design, baseline establishment
**Week 2**: Implementation + unit test updates
**Week 3**: Integration testing, regression testing, cleanup
**Week 4**: Production validation, monitoring, documentation

**Effort Breakdown**:
- QA Engineer: 80 hours (test design, execution, reporting)
- Developer: 60 hours (implementation, test fixes)
- Product Manager: 10 hours (UX validation, decision-making)

---

## Open Questions for Product/Engineering

1. **Phase Transitions**: Should we retain Phase 1 → Phase 2 difficulty progression in MC, or simplify to single behavior?
   - **Recommendation**: Retain for training value, minimal complexity

2. **Audience Suggestions**: Option A (none) or Option B (text-only)?
   - **Recommendation**: Option A initially, add Option B if users miss variety

3. **Rollout Strategy**: Feature flag vs full cutover?
   - **Recommendation**: Feature flag with A/B testing if possible

4. **Backward Compatibility**: Support both old and new architecture temporarily?
   - **Recommendation**: No - clean break is simpler

5. **Voice Modulation**: Should MC use tone/emotion changes to simulate persona variety?
   - **Recommendation**: Yes - investigate Gemini voice parameters

6. **Turn Manager**: Simplify or remove entirely?
   - **Recommendation**: Simplify to user ↔ MC only (keep for phase transitions)

---

## Conclusion

This simplification is **HIGH RISK but HIGH REWARD**:

**Benefits**:
- Simpler architecture (1 agent vs 3)
- Faster responses (no handoffs)
- Lower cost (fewer tokens)
- Easier to maintain and debug

**Risks**:
- Persona variety loss
- Scene quality degradation
- Suggestion authenticity concerns
- Large refactor scope

**QA Recommendation**:
- **PROCEED with Option A + phased rollout**
- **Comprehensive test coverage BEFORE implementation**
- **Feature flag with A/B testing**
- **Option B as fallback if quality suffers**
- **Continuous monitoring post-launch**

The architectural simplification benefits outweigh the risks IF we:
1. Invest in robust testing upfront
2. Refine MC prompt carefully
3. Monitor quality metrics closely
4. Have rollback plan ready

---

**Test Plan Author**: QA Agent
**Date**: 2025-01-30
**Status**: Ready for Review
**Next Steps**: Review with engineering team, refine test cases, establish baseline
