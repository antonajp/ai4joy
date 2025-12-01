# IQS-60 Audience Audio Integration - Test Plan

## Overview
This test plan covers the Room Agent (audience) audio integration for the ai4joy improv comedy app. The Room Agent provides ambient commentary during scenes, simulating audience reactions and energy.

## Test Scope

### In Scope
- Room Agent audio generation and voice configuration
- Audience sentiment-based triggering of ambient commentary
- Audio mixing of MC, Partner, and Room Agent streams
- Audience archetype toolset for suggestion generation
- MC interaction with Room Agent for audience suggestions
- Integration with existing turn management and phase transitions

### Out of Scope
- User interface changes (frontend testing)
- Network/WebSocket performance testing
- Production deployment validation
- Real user acceptance testing

## Test Files Created

### 1. `/tests/audio/integration/test_audience_response.py` (10 tests)
Tests the Room Agent's ambient audio behavior during scenes.

**Test Cases:**
- `TC-060-001`: Audience responds after partner turns
- `TC-060-002`: Audience uses Charon voice
- `TC-060-003`: Audience audio at 30% volume
- `TC-060-004`: Audience reactions are brief
- `TC-060-005`: Ambient trigger respects cooldown
- `TC-060-006`: Room agent doesn't block main conversation
- `TC-060-007`: Ambient prompt generation
- `TC-060-008`: Audio mixing three streams
- `TC-060-009`: Room volume adjustable
- `TC-060-010`: Reset ambient trigger

### 2. `/tests/audio/integration/test_audience_suggestions.py` (10 tests)
Tests the audience archetype toolset and MC-Room Agent interaction for suggestions.

**Test Cases:**
- `TC-060-011`: Suggestions reflect demographics
- `TC-060-012`: Tech audience gets tech suggestions
- `TC-060-013`: MC asks audience not user
- `TC-060-014`: Suggestion type matches game
- `TC-060-015`: Multiple archetypes influence
- `TC-060-016`: Audience archetypes toolset integration
- `TC-060-017`: Get all archetypes
- `TC-060-018`: Vibe check provides indicators
- `TC-060-019`: Reserved audience different vibe
- `TC-060-020`: Audience sample respects size

### 3. `/tests/audio/e2e/test_full_scene_with_audience.py` (10 tests)
End-to-end tests for complete scene flow with all agents.

**Test Cases:**
- `TC-060-021`: Full scene flow all agents
- `TC-060-022`: Audience non-interrupting
- `TC-060-023`: Three stream mixing
- `TC-060-024`: Turn count with audience
- `TC-060-025`: Phase transitions with audience
- `TC-060-026`: Audience across game selection
- `TC-060-027`: Sentiment drives ambient
- `TC-060-028`: Orchestrator supports room
- `TC-060-029`: Room agent has live model
- `TC-060-030`: Room agent toolsets

## Total: 30 Test Cases

## Existing Test Coverage (Already Passing)

From existing test files:
- `/tests/audio/integration/test_room_audio.py` - Room Agent creation and configuration (8 tests)
- `/tests/audio/e2e/test_full_experience.py` - Full 3-agent experience (11 tests)
- `/tests/audio/unit/test_audio_orchestrator.py` - Orchestrator basics (10 tests)

## Test Execution Commands

### Run All IQS-60 Tests
```bash
source venv/bin/activate
python -m pytest tests/audio/integration/test_audience_response.py -v
python -m pytest tests/audio/integration/test_audience_suggestions.py -v
python -m pytest tests/audio/e2e/test_full_scene_with_audience.py -v
```

### Run All Audio Tests
```bash
python -m pytest tests/audio/ -v
```

### Run with Coverage
```bash
python -m pytest tests/audio/ --cov=app/audio --cov=app/agents --cov=app/toolsets --cov-report=html
```

## Critical Test Scenarios

### Priority 1: Core Functionality
1. **TC-060-001**: Audience responds after partner turns - Validates basic Room Agent triggering
2. **TC-060-002**: Audience uses Charon voice - Ensures voice differentiation
3. **TC-060-003**: Audience at 30% volume - Prevents overpowering main conversation
4. **TC-060-021**: Full scene flow - End-to-end integration

### Priority 2: User Experience
5. **TC-060-004**: Brief reactions - Ensures ambient nature of commentary
6. **TC-060-006**: Non-blocking - Doesn't interrupt main flow
7. **TC-060-022**: Non-interrupting - E2E validation of smooth flow
8. **TC-060-011**: Demographic suggestions - Contextual audience behavior

### Priority 3: Technical Correctness
9. **TC-060-005**: Cooldown respects - Prevents spam
10. **TC-060-008/023**: Three-stream mixing - No audio clipping
11. **TC-060-024**: Turn count accuracy - Doesn't break existing logic
12. **TC-060-025**: Phase transitions - Works with Partner phase changes

## Risk Areas Requiring Focused Testing

### 1. Audio Mixing Quality
- **Risk**: Clipping or distortion when mixing three audio streams
- **Tests**: TC-060-008, TC-060-023
- **Mitigation**: Volume scaling (Room at 30%) tested extensively

### 2. Turn Management Integration
- **Risk**: Room Agent interfering with MC/Partner turn-taking
- **Tests**: TC-060-006, TC-060-022, TC-060-024
- **Mitigation**: Room Agent is not part of turn-taking system

### 3. Sentiment Triggering
- **Risk**: Too frequent or too rare ambient commentary
- **Tests**: TC-060-001, TC-060-005, TC-060-027
- **Mitigation**: Cooldown mechanism tested

### 4. Voice Differentiation
- **Risk**: Confusion between agents due to similar voices
- **Tests**: TC-060-002, TC-060-021
- **Mitigation**: Three distinct voices (Aoede, Puck, Charon) verified

## Automation Approach

All tests are fully automated using pytest with:
- **AsyncMock**: For async operations
- **MagicMock**: For complex object mocking
- **NumPy**: For audio waveform generation in mixing tests
- **Patch**: For isolating Firestore dependencies

### Test Patterns Used
1. **Fixture-based setup**: Consistent session and agent creation
2. **Mocking external dependencies**: Firestore service calls mocked
3. **Integration testing**: Real AudioOrchestrator with real AudioMixer
4. **End-to-end validation**: Full flow from MC → Partner → Room

## Success Criteria

### Test Execution
- ✅ All 30 new tests pass
- ✅ All existing audio tests continue to pass (no regressions)
- ✅ Code coverage for new functionality > 90%

### Functional Requirements
- ✅ Room Agent creates ambient commentary after partner turns
- ✅ Room Agent uses Charon voice at 30% volume
- ✅ Comments are brief (1-2 sentences as per system prompt)
- ✅ Cooldown prevents spam (15-second default)
- ✅ Audience suggestions reflect demographics from archetypes
- ✅ MC interacts with Room Agent (not user) for suggestions

### Non-Functional Requirements
- ✅ No audio clipping in three-stream mixing
- ✅ Room Agent doesn't block turn-taking
- ✅ Turn count and phase transitions work correctly
- ✅ Session isolation maintained (per-session agents)

## Test Data Requirements

### Audience Archetypes (Mocked)
- Tech Professional
- Improviser
- Student
- Corporate Professional
- Creative Artist
- College Student
- Retiree
- Healthcare Worker

### Sentiment Levels
- VERY_POSITIVE (energy > 0.8)
- POSITIVE (energy > 0.6)
- NEUTRAL (energy 0.3-0.6)
- NEGATIVE (energy < 0.4)
- VERY_NEGATIVE (energy < 0.3)

### Audio Test Data
- Sample rate: 24kHz (ADK Live API output)
- Format: 16-bit PCM mono
- Test frequencies: 440Hz (MC), 550Hz (Partner), 330Hz (Room)

## Dependencies

### System Under Test
- `app/audio/audio_orchestrator.py` - Main orchestration service
- `app/agents/room_agent.py` - Room Agent creation
- `app/toolsets/audience_archetypes_toolset.py` - Archetype toolset
- `app/audio/audio_mixer.py` - Multi-stream audio mixing
- `app/audio/ambient_audio.py` - Sentiment-based triggering
- `app/audio/voice_config.py` - Voice configuration

### External Dependencies (Mocked)
- Firestore (audience archetypes data)
- ADK Live API (audio streaming)
- Google Vertex AI (LLM for Room Agent)

## Known Limitations

1. **Real-time audio testing**: Tests use synthetic audio, not actual ADK Live API responses
2. **Latency testing**: No tests for real-time performance under load
3. **Voice quality**: Voice characteristics not tested (assumes ADK handles correctly)
4. **Network resilience**: WebSocket error handling not covered in these tests

## Manual Testing Recommendations

After automated tests pass, perform manual validation:

1. **Voice Quality Check**: Listen to actual Room Agent audio to verify Charon voice sounds ambient
2. **Volume Levels**: Confirm 30% volume is appropriate in real scenes
3. **Timing**: Verify cooldown feels natural (not too long or short)
4. **Suggestions**: Test that audience suggestions match demographics
5. **User Experience**: Ensure Room Agent enhances rather than distracts

## Regression Testing

These tests should be run:
- Before each commit touching audio/agent code
- In CI/CD pipeline (pre-merge)
- Before each production deployment
- After any dependency updates (ADK, Vertex AI)

## Next Steps

1. ✅ Run all tests to establish baseline
2. ⏳ Fix any failing tests
3. ⏳ Review code coverage reports
4. ⏳ Add tests for any uncovered edge cases
5. ⏳ Update tests as implementation evolves
6. ⏳ Create performance benchmarks for audio mixing

## Test Maintenance

- **Owner**: QA Team
- **Review Frequency**: Weekly during development, monthly after release
- **Update Triggers**:
  - New Room Agent features
  - Changes to audio orchestration
  - ADK API updates
  - Voice configuration changes
