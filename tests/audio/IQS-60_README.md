# IQS-60 Audience Audio Test Suite - Quick Reference

## 📋 Overview
Complete test suite for Room Agent (audience) audio integration in ai4joy improv app.

## ✅ Status: ALL TESTS PASSING (30/30)

## 📁 Test Files

### Integration Tests
```
tests/audio/integration/
├── test_audience_response.py       # 10 tests - Room Agent audio behavior
└── test_audience_suggestions.py    # 10 tests - Archetype toolset integration
```

### E2E Tests
```
tests/audio/e2e/
└── test_full_scene_with_audience.py  # 10 tests - Full scene flow validation
```

### Documentation
```
tests/audio/
├── IQS-60_TEST_PLAN.md     # Comprehensive test strategy
├── IQS-60_TEST_SUMMARY.md  # Executive summary with results
└── IQS-60_README.md        # This quick reference
```

## 🚀 Quick Start

### Run All IQS-60 Tests (30 tests)
```bash
source venv/bin/activate
python -m pytest tests/audio/integration/test_audience_response.py \
                 tests/audio/integration/test_audience_suggestions.py \
                 tests/audio/e2e/test_full_scene_with_audience.py -v
```

### Run Individual Test Files
```bash
# Audience response tests (10 tests - audio mixing, triggering, volume)
python -m pytest tests/audio/integration/test_audience_response.py -v

# Audience suggestions tests (10 tests - demographics, archetypes, MC interaction)
python -m pytest tests/audio/integration/test_audience_suggestions.py -v

# Full scene E2E tests (10 tests - complete MC → Partner → Room flow)
python -m pytest tests/audio/e2e/test_full_scene_with_audience.py -v
```

### Run with Coverage
```bash
python -m pytest tests/audio/ --cov=app/audio --cov=app/agents --cov-report=html
open htmlcov/index.html
```

## 🎯 What's Tested

### Core Functionality
- ✅ Room Agent ambient audio generation
- ✅ Charon voice configuration (distinct from MC/Partner)
- ✅ 30% volume mixing (doesn't overpower main conversation)
- ✅ Brief reactions (1-2 sentences enforced by prompt)
- ✅ Sentiment-based triggering with cooldown
- ✅ Non-blocking behavior (doesn't interfere with turn-taking)

### Audience Interaction
- ✅ Audience archetype demographics
- ✅ Tech/comedy/mixed audience analysis
- ✅ MC-Room Agent interaction for suggestions
- ✅ Vibe check generation
- ✅ Multiple archetype influence on suggestions

### Integration
- ✅ Full MC → Partner → Room flow
- ✅ Three-stream audio mixing (no clipping)
- ✅ Turn counting with Room Agent present
- ✅ Phase transitions (Partner Phase 1 → Phase 2)
- ✅ Session isolation (per-session agents)

## 📊 Test Results

```
PASSED tests/audio/integration/test_audience_response.py ............ [10/10]
PASSED tests/audio/integration/test_audience_suggestions.py ......... [10/10]
PASSED tests/audio/e2e/test_full_scene_with_audience.py ............. [10/10]

============================== 30 passed in 2.39s ===============================
```

## 🔍 Test Case Index

### TC-060-001 to TC-060-010: Audience Response
- Room Agent triggering after partner turns
- Charon voice usage
- 30% volume configuration
- Brief reaction enforcement
- Cooldown mechanism
- Non-blocking behavior
- Prompt generation
- Three-stream mixing
- Volume adjustment
- Trigger reset

### TC-060-011 to TC-060-020: Audience Suggestions
- Demographics reflection
- Tech audience analysis
- MC-audience interaction
- Game-specific suggestions
- Multiple archetype influence
- Toolset integration
- Archetype catalog access
- Vibe check indicators
- Audience type differentiation
- Sample size handling

### TC-060-021 to TC-060-030: Full Scene Flow
- All agent coordination
- Non-interrupting ambient audio
- Three-stream mixing validation
- Turn count accuracy
- Phase transition compatibility
- Cross-transition persistence
- Sentiment-driven triggering
- Orchestrator method availability
- Live API model usage
- Toolset attachment

## 🛠️ Technical Details

### Dependencies
- **pytest** 9.0.1 - Test framework
- **pytest-asyncio** 1.3.0 - Async test support
- **numpy** - Audio waveform generation
- **AsyncMock** - Async operation mocking
- **MagicMock** - Object mocking

### Test Patterns
- Fixture-based setup for consistent environments
- Mocking of Firestore dependencies
- Real AudioOrchestrator and AudioMixer (not mocked)
- Synthetic audio for mixing tests (440Hz, 550Hz, 330Hz)

### Audio Test Data
- Sample Rate: 24kHz (ADK Live API output)
- Format: 16-bit PCM mono
- Test Frequencies:
  - MC: 440Hz
  - Partner: 550Hz
  - Room: 330Hz

## 📝 Key Assertions

### Volume Levels
```python
assert mixer.get_volume("mc") == 1.0
assert mixer.get_volume("partner") == 1.0
assert mixer.get_volume("room") == 0.3  # Room at 30%
```

### Voice Configuration
```python
assert mc_voice.voice_name == "Aoede"
assert partner_voice.voice_name == "Puck"
assert room_voice.voice_name == "Charon"
```

### Ambient Triggering
```python
# High energy should trigger
assert trigger.should_trigger(
    sentiment=SentimentLevel.VERY_POSITIVE,
    energy_level=0.9
) is True

# Low energy should NOT trigger
assert trigger.should_trigger(
    sentiment=SentimentLevel.NEUTRAL,
    energy_level=0.2
) is False
```

## 🐛 Troubleshooting

### Tests Fail with "Event loop is closed"
- **Cause**: Firestore async operations
- **Fix**: Use mocking for Firestore calls (already implemented)

### Tests Fail with Import Errors
- **Cause**: Missing dependencies
- **Fix**: `pip install -r requirements.txt`

### Tests Hang on Firestore
- **Cause**: Real Firestore connection attempted
- **Fix**: Ensure mocks are properly applied

## 📚 Related Files

### Implementation Files
- `app/audio/audio_orchestrator.py` - Main orchestration service
- `app/agents/room_agent.py` - Room Agent factory
- `app/toolsets/audience_archetypes_toolset.py` - Demographics toolset
- `app/audio/audio_mixer.py` - Multi-stream mixing
- `app/audio/ambient_audio.py` - Sentiment triggering
- `app/audio/voice_config.py` - Voice selection

### Existing Related Tests
- `tests/audio/integration/test_room_audio.py` - Room Agent basics (8 tests)
- `tests/audio/e2e/test_full_experience.py` - 3-agent experience (11 tests)
- `tests/audio/unit/test_audio_orchestrator.py` - Orchestrator unit tests (10 tests)

## ✨ Success Criteria

All criteria from IQS-60 acceptance requirements met:
- ✅ Room Agent creates ambient commentary after partner turns
- ✅ Room Agent uses Charon voice at 30% volume
- ✅ Comments are brief (1-2 sentences from system prompt)
- ✅ Cooldown prevents spam (15-second default)
- ✅ Audience suggestions reflect demographics from archetypes
- ✅ MC interacts with Room Agent (not user) for suggestions
- ✅ No audio clipping in three-stream mixing
- ✅ Room Agent doesn't block turn-taking

## 👥 Team Contacts

- **QA Lead**: Responsible for test maintenance
- **Dev Lead**: Code review and implementation validation
- **Product Owner**: Acceptance criteria sign-off

## 📅 Maintenance Schedule

- **Weekly**: During active development
- **Pre-Release**: Full regression suite
- **Post-Release**: Monthly smoke tests
- **After Dependencies**: Complete test run

---

**Last Updated**: 2025-11-30
**Ticket**: IQS-60
**Test Count**: 30
**Pass Rate**: 100%
**Status**: ✅ Ready for Code Review
