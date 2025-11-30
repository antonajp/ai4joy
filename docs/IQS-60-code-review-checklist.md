# IQS-60 Code Review Checklist
## Phase 3: Real-time Audio - Room Agent & Full Immersive Experience

**Ticket**: [IQS-60](https://linear.app/iqsubagents/issue/IQS-60)
**Reviewer**: Principal Code Review Agent
**Date**: 2025-11-30

---

## Executive Summary

This checklist provides a systematic framework for reviewing the Room Agent audio integration implementation. The feature adds ambient audience audio to the existing MC/Partner agent conversation flow, creating a fully immersive improv training experience.

### Critical Success Factors
1. Non-blocking Room Agent execution (asynchronous)
2. Audio mixing maintains quality at 30% Room volume
3. Proper turn flow: MC → Partner → User → **Audience** → Partner...
4. Session isolation maintained across concurrent users
5. No performance degradation from Phase 2 baseline

---

## 1. Functional Requirements Review

### FR1: Room Agent Audio Integration

#### ✅ Checklist Items

- [ ] **Room Agent triggers after each turn completion**
  - Verify `audio_orchestrator.py` calls Room Agent in `_process_event()` on `turn_complete`
  - Check trigger occurs AFTER user turn, BEFORE Partner continues
  - Confirm asynchronous execution (doesn't block main flow)

- [ ] **Audience suggestions reflect demographics**
  - Verify `audience_archetypes_toolset.py` generates diverse suggestions
  - Check demographic data influences suggestion content
  - Confirm suggestions match archetype preferences (vocal/quiet, experienced/beginner)

- [ ] **MC asks audience for suggestions (not user)**
  - Review `mc_agent.py` AUDIO_MC_SYSTEM_PROMPT changes
  - Verify MC prompts audience archetypes, not direct user input
  - Check wording: "Let's hear from the audience..." vs "What would you like?"

- [ ] **Audio mixing maintains 30% Room volume**
  - Verify `audio_mixer.py` DEFAULT_VOLUMES["room"] = 0.3
  - Check `mix_streams()` applies volume correctly
  - Confirm no volume drift during session

- [ ] **Turn flow sequence correct**
  - MC speaks → Partner performs → User interacts → **Room reacts** → Partner continues
  - Verify `turn_manager.py` supports Room agent type
  - Check turn completion triggers Room audio generation

### FR2: Audio Quality & Mixing

- [ ] **Multi-stream mixing works**
  - Verify `AudioMixer.mix_streams()` handles 3 concurrent streams
  - Check normalization prevents clipping (max_val > 32767 check)
  - Confirm padding aligns streams of different lengths

- [ ] **Room audio as background layer**
  - Verify Room voice config uses appropriate persona
  - Check audio doesn't overpower MC/Partner
  - Confirm mixing maintains clarity of foreground agents

- [ ] **No audio degradation**
  - Verify output remains 24kHz 16-bit PCM mono
  - Check no artifacts from volume scaling
  - Confirm no latency increase from mixing operations

### FR3: Sentiment-Based Triggering

- [ ] **AmbientAudioTrigger logic correct**
  - Verify `ambient_audio.py` triggers on appropriate sentiment levels
  - Check energy threshold detection (HIGH_ENERGY_THRESHOLD = 0.75)
  - Confirm cooldown prevents rapid-fire triggers (15s default)

- [ ] **Trigger conditions appropriate**
  - VERY_POSITIVE or VERY_NEGATIVE sentiment triggers
  - High energy (>= 0.75) triggers regardless of sentiment
  - Non-neutral sentiment with moderate energy (>= 0.4) triggers

- [ ] **Commentary prompts match sentiment**
  - Verify COMMENTARY_TEMPLATES provide variety
  - Check prompts rotate (template_index cycling)
  - Confirm brevity requirement (1-2 sentences max)

---

## 2. Code Quality Review

### Files Under Review

1. `app/audio/audio_orchestrator.py` (~1508 lines - **OVER LIMIT**)
2. `app/toolsets/audience_archetypes_toolset.py` (276 lines - ✅)
3. `app/agents/mc_agent.py` (200 lines - ✅)
4. `app/agents/room_agent.py` (149 lines - ✅)
5. `app/audio/turn_manager.py` (257 lines - ✅)
6. `app/audio/audio_mixer.py` (214 lines - ✅)
7. `app/audio/ambient_audio.py` (263 lines - ✅)

#### 🚨 CRITICAL: File Size Violations

- [ ] **audio_orchestrator.py EXCEEDS 550 line limit**
  - Current: ~1508 lines
  - Target: < 550 lines
  - **ACTION REQUIRED**: Refactor into smaller modules
  - Suggested splits:
    - `audio_session_manager.py` (session lifecycle)
    - `audio_event_processor.py` (event handling)
    - `audio_agent_coordinator.py` (agent switching)

### KISS & DRY Principles

- [ ] **No unnecessary complexity**
  - Check Room Agent integration doesn't add convoluted logic
  - Verify audio mixing is straightforward
  - Confirm trigger logic is simple and clear

- [ ] **No code duplication**
  - Check MC/Partner/Room agent creation follows same pattern
  - Verify audio processing code isn't duplicated
  - Confirm volume control logic is centralized in AudioMixer

- [ ] **No inline styles/handlers**
  - Not applicable (backend-only changes)

### Self-Documenting Code

- [ ] **Clear function names**
  - `should_trigger_ambient()` vs ambiguous names
  - `mix_audio_streams()` vs generic names
  - `get_commentary_prompt()` vs unclear purpose

- [ ] **Descriptive variable names**
  - `sentiment_level` vs `sl`
  - `energy_threshold` vs `et`
  - `room_volume` vs `vol`

- [ ] **Minimal comments (code explains itself)**
  - Check for over-commenting obvious code
  - Verify complex algorithms have brief explanations
  - Confirm no "what" comments, only "why" when needed

### Logger Statements

- [ ] **Debug logging for flow tracking**
  - Room Agent trigger decisions logged
  - Audio mixing operations logged
  - Turn transitions logged with agent types

- [ ] **Info logging for key events**
  - Room Agent activation
  - Sentiment-based triggers
  - Audio stream mixing

- [ ] **Error logging at boundaries**
  - Audio processing failures
  - Room Agent execution errors
  - Mixing normalization issues

- [ ] **Structured logging (no string concatenation)**
  - ✅ `logger.info("Room triggered", sentiment=..., energy=...)`
  - ❌ `logger.info(f"Room triggered with {sentiment}")`

### Naming Conventions

- [ ] **Follows codebase patterns**
  - `create_room_agent_for_audio()` matches `create_mc_agent_for_audio()`
  - `AmbientAudioTrigger` follows PascalCase for classes
  - `should_trigger()` follows snake_case for methods

- [ ] **Consistent terminology**
  - "Room Agent" vs "Audience Agent" (pick one)
  - "ambient audio" vs "background audio" (pick one)
  - "sentiment level" vs "mood" (pick one)

---

## 3. Architectural Review

### Non-Blocking Execution

- [ ] **Room Agent runs asynchronously**
  - Verify no `await` blocking main conversation flow
  - Check Room audio generation happens in parallel
  - Confirm timeout/failure doesn't crash session

- [ ] **Existing patterns followed**
  - Room Agent creation mirrors MC/Partner patterns
  - Audio streaming uses same LiveRequestQueue pattern
  - Session management follows established practices

- [ ] **No over-engineering**
  - Check Room integration doesn't add unnecessary abstractions
  - Verify trigger logic isn't overly complex
  - Confirm no premature optimization

### Proper Error Handling

- [ ] **Error handling at system boundaries**
  - Audio mixer handles malformed data (odd byte counts)
  - Room Agent errors don't crash MC/Partner flow
  - Sentiment analysis failures gracefully degrade

- [ ] **Graceful degradation**
  - Missing Room Agent voice config falls back to default
  - Audio mixing continues with available streams
  - Trigger failures skip ambient audio (don't block)

- [ ] **No silent failures**
  - Audio processing errors are logged
  - Room Agent timeouts are tracked
  - Mixing failures are visible in logs

### Session Isolation

- [ ] **Per-session Room Agent instances**
  - Verify `AudioSession.room_agent` is per-session
  - Check no shared state between sessions
  - Confirm `AmbientAudioTrigger` is session-scoped

- [ ] **Concurrent session safety**
  - Verify `TriggerState.lock` prevents race conditions
  - Check `AudioMixer` has no shared mutable state
  - Confirm no cross-session audio mixing

- [ ] **Proper cleanup on session end**
  - Room Agent queue closed in `stop_session()`
  - AmbientAudioTrigger reset or garbage collected
  - AudioMixer resources released

---

## 4. Testing Coverage

### Unit Tests

- [ ] **AmbientAudioTrigger tests pass**
  - All 10 tests in `test_ambient_audio.py` pass
  - New trigger conditions are tested
  - Cooldown behavior is verified

- [ ] **AudioMixer tests exist**
  - Volume control tests
  - Multi-stream mixing tests
  - Normalization tests

- [ ] **Room Agent tests exist**
  - Agent creation tests
  - Audio mode configuration tests
  - Toolset integration tests

### Integration Tests

- [ ] **Room audio integration test exists**
  - End-to-end flow with Room Agent
  - Audio mixing with all three agents
  - Turn sequence with Room reactions

- [ ] **Existing tests still pass**
  - `test_multi_agent.py` passes
  - `test_turn_manager.py` passes
  - `test_partner_audio.py` passes

### Edge Cases

- [ ] **Empty/missing audio streams**
  - Room Agent fails to generate audio
  - Missing MC or Partner stream
  - Zero-length audio chunks

- [ ] **Rapid turn transitions**
  - Room Agent triggered multiple times quickly
  - Cooldown prevents audio spam
  - No queue overflow

- [ ] **Concurrent sessions**
  - Multiple users get isolated Room Agents
  - No audio cross-contamination
  - Performance remains stable

---

## 5. Performance & Scalability

### Performance Benchmarks

- [ ] **No latency increase from Phase 2**
  - Audio response time <= Phase 2 baseline
  - Turn completion time unchanged
  - WebSocket throughput maintained

- [ ] **Audio mixing overhead acceptable**
  - Mixing time < 10ms per chunk
  - No perceptible delay to user
  - CPU usage within budget

- [ ] **Memory footprint reasonable**
  - Room Agent memory per session < 50MB
  - Audio buffers properly bounded
  - No memory leaks over long sessions

### Scalability Targets

- [ ] **50 concurrent sessions supported**
  - Load test with 50 simultaneous users
  - All sessions get Room Agent audio
  - No degradation in quality

- [ ] **Cost target met**
  - Total infrastructure cost < $500/month at scale
  - Room Agent API calls within budget
  - Audio processing costs accounted for

### Resource Management

- [ ] **Proper queue cleanup**
  - Room Agent queue closed on disconnect
  - No orphaned queues after session end
  - Queue memory released promptly

- [ ] **Audio buffer management**
  - Buffers don't grow unbounded
  - Old audio chunks discarded appropriately
  - No memory accumulation over time

---

## 6. Potential Issues to Watch For

### Race Conditions

- [ ] **Turn completion vs Room trigger timing**
  - Room Agent triggered AFTER turn_complete event
  - No race between Partner continuation and Room audio
  - Proper event ordering guaranteed

- [ ] **Concurrent session access**
  - TriggerState.lock prevents concurrent access
  - AudioSession fields accessed atomically
  - No TOCTOU (Time-Of-Check-Time-Of-Use) bugs

### Memory Leaks

- [ ] **Queue cleanup on errors**
  - Room Agent queue closed even on exceptions
  - Error paths don't skip cleanup
  - Try-finally blocks ensure cleanup

- [ ] **Audio buffer leaks**
  - NumPy arrays garbage collected
  - Large buffers not retained unnecessarily
  - Session cleanup releases all audio resources

- [ ] **Agent instance cleanup**
  - Room Agent instances freed after session
  - No circular references preventing GC
  - WeakRef patterns if needed

### Performance Degradation

- [ ] **Audio mixing CPU usage**
  - NumPy operations vectorized efficiently
  - No O(n²) algorithms in mixing
  - Profiling shows acceptable performance

- [ ] **Room Agent API calls**
  - Cooldown prevents excessive API usage
  - Trigger conditions prevent spam
  - API quota limits respected

### Circular Dependencies

- [ ] **Import cycles avoided**
  - `audio_orchestrator.py` doesn't import from `room_agent.py` and vice versa
  - Toolsets don't import agents
  - Shared types in separate modules

---

## 7. Security & Privacy

### Input Validation

- [ ] **Energy level bounds checked**
  - Clamped to 0.0-1.0 range
  - Invalid types handled gracefully
  - No injection attacks via energy values

- [ ] **Sentiment enum validated**
  - Only valid SentimentLevel values accepted
  - String inputs converted safely
  - No arbitrary value injection

### PII Protection

- [ ] **No user data in Room Agent prompts**
  - Demographic archetypes are synthetic
  - No real user names or info
  - Session IDs properly anonymized in logs

### Rate Limiting

- [ ] **Cooldown prevents abuse**
  - 15s cooldown between triggers
  - Per-session limits enforced
  - No global rate limit bypass

---

## 8. Documentation & Maintainability

### Code Documentation

- [ ] **Docstrings complete**
  - All new functions have docstrings
  - Args, Returns, Raises documented
  - Examples provided for complex functions

- [ ] **Module-level documentation**
  - `audio_mixer.py` explains mixing algorithm
  - `ambient_audio.py` explains trigger logic
  - `audience_archetypes_toolset.py` explains usage

### Type Hints

- [ ] **Type hints on all functions**
  - Parameters typed (sentiment: SentimentLevel)
  - Return types specified (-> bool)
  - Optional types used correctly

- [ ] **Literal types for constants**
  - AgentType = Literal["mc", "partner", "room"]
  - Prevents typo bugs
  - IDE autocomplete enabled

### Future Maintenance

- [ ] **Clear extension points**
  - Adding new sentiment levels is straightforward
  - Changing trigger conditions is localized
  - New agent types can be added easily

- [ ] **Configuration externalized**
  - Cooldown seconds configurable
  - Volume levels adjustable
  - Thresholds tunable without code changes

---

## 9. Deployment & Operations

### Configuration

- [ ] **Environment variables used correctly**
  - Room Agent voice config from settings
  - Live API model from settings
  - No hardcoded credentials

### Monitoring

- [ ] **Metrics instrumented**
  - Room Agent trigger count tracked
  - Audio mixing performance logged
  - Error rates monitored

### Rollback Plan

- [ ] **Feature flag exists**
  - Room Agent can be disabled
  - Graceful degradation to Phase 2
  - No breaking changes to existing flow

---

## 10. Summary of Critical Findings

### 🚨 Blocking Issues (Must Fix Before Merge)

1. **FILE SIZE**: `audio_orchestrator.py` exceeds 550-line limit (1508 lines)
   - **Impact**: Violates code quality standards, hard to maintain
   - **Fix**: Refactor into 3-4 smaller modules
   - **Effort**: 4-6 hours

### ⚠️ Significant Concerns (Should Address)

2. **PERFORMANCE**: No load test results for 50 concurrent sessions
   - **Impact**: Unknown scalability characteristics
   - **Fix**: Run load tests and optimize bottlenecks
   - **Effort**: 2-4 hours

3. **ERROR HANDLING**: Room Agent failures may not gracefully degrade
   - **Impact**: Could block main conversation flow
   - **Fix**: Add comprehensive error handling and fallbacks
   - **Effort**: 2-3 hours

4. **TESTING**: Missing integration test for full MC→Partner→Room flow
   - **Impact**: Core functionality may break without detection
   - **Fix**: Add end-to-end integration test
   - **Effort**: 3-4 hours

### 💡 Suggestions (Nice to Have)

5. **CONFIGURABILITY**: Hardcoded cooldown and volume levels
   - **Impact**: Requires code changes to tune behavior
   - **Fix**: Move to config/environment variables
   - **Effort**: 1-2 hours

6. **OBSERVABILITY**: Missing OpenTelemetry spans for Room Agent
   - **Impact**: Harder to debug performance issues in production
   - **Fix**: Add tracing to Room Agent operations
   - **Effort**: 1-2 hours

---

## 11. Approval Checklist

### Before Approving for Merge

- [ ] All 🚨 **Blocking Issues** resolved
- [ ] All ⚠️ **Significant Concerns** addressed or documented as tech debt
- [ ] Existing test suite passes (100%)
- [ ] New tests added for Room Agent functionality
- [ ] Code review discussion items resolved
- [ ] Performance benchmarks meet targets
- [ ] Documentation updated (API docs, deployment guide)

### Post-Merge Monitoring

- [ ] Watch error rates for first 48 hours
- [ ] Monitor Room Agent API usage
- [ ] Track audio quality metrics
- [ ] Verify cost projections match actuals

---

## 12. Reviewer Notes

### Positive Observations

- ✅ Existing `ambient_audio.py` and `audio_mixer.py` are well-structured
- ✅ Per-session agent pattern correctly followed
- ✅ Sentiment-based triggering logic is clear and testable
- ✅ Volume control centralized in AudioMixer
- ✅ Thread-safe trigger state management

### Areas for Improvement

- ⚠️ File size violations need immediate attention
- ⚠️ Missing comprehensive integration tests
- ⚠️ Error handling could be more robust
- ⚠️ Load testing results not yet available

### Questions for Implementation Team

1. What is the plan for refactoring `audio_orchestrator.py`?
2. How will Room Agent errors be handled to prevent blocking?
3. What are the actual load test results for 50 concurrent sessions?
4. Is there a feature flag for gradual rollout?
5. How will cost monitoring work in production?

---

**Review Status**: ⏳ Pending Implementation
**Next Action**: Implementation team to address blocking issues
**Follow-up Date**: Upon completion of IQS-60 implementation

---

*This checklist generated by Principal Code Review Agent*
*Based on IQS-60 requirements and existing codebase analysis*
