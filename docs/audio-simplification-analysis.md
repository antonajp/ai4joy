# Audio Architecture Simplification - Technical Analysis

**Date**: 2025-11-30
**Analyst**: Agentic ML Architect
**Request**: Simplify audio orchestration from 3 agents to 1 (MC only)

---

## Executive Summary

Current system uses **3 AI agents** with complex coordination:
- **MC Agent**: Host/game selection (Gemini Live API)
- **Partner Agent**: Scene work with phase-based difficulty (Gemini Live API)
- **Room Agent**: Ambient audience reactions (TTS synthesis)

**Proposed**: Consolidate to **MC Agent only** as both host AND scene partner.

**Key Finding**: ✅ **HIGHLY FEASIBLE** - Architecture already supports this pattern. Minimal code changes required.

---

## Current Architecture Deep-Dive

### 1. Agent Communication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     AudioOrchestrator                        │
│  - Manages 3 agents per session                             │
│  - Routes audio to current_agent (mc/partner/room)          │
│  - Handles agent switching via tool calls                   │
└─────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
    ┌────────┐      ┌──────────┐      ┌──────────┐
    │   MC   │      │ Partner  │      │   Room   │
    │ Agent  │      │  Agent   │      │  Agent   │
    └────────┘      └──────────┘      └──────────┘
         │                │                  │
    Host/Select    Scene Partner    Ambient Audio
```

### 2. Turn Management (AgentTurnManager)

**File**: `app/audio/turn_manager.py`

```python
class AgentTurnManager:
    current_speaker: "mc" | "partner" | "room"
    turn_count: int
    phase: 1 | 2  # Partner difficulty
```

**Current Flow**:
1. **MC speaks** → greets, explains game rules
2. **MC calls `_start_scene`** → switches to Partner
3. **Partner speaks** → performs scene work
4. **Partner calls `_end_scene`** → switches back to MC
5. **Room triggers** → ambient reactions (async, doesn't block)

### 3. Agent Tool Coordination

**MC Tools** (`mc_agent.py`, line 212-216):
- `ImprovGamesToolset` - Game database
- `SceneTransitionToolset` - `_start_scene`, `_resume_scene`
- `AudienceArchetypesToolset` - `_get_suggestion_for_game`

**Partner Tools** (`partner_agent.py`, line 297):
- No tools (pure scene work)

**Room Tools** (`room_agent.py`, line 134-135):
- `SentimentAnalysisToolset`
- `AudienceArchetypesToolset`

### 4. Audio Streaming Architecture

**File**: `app/audio/audio_orchestrator.py`

**Key Method**: `stream_responses()` (line 739-970)
```python
async def stream_responses(session_id):
    while session.active:
        runner = create_runner_for_session(session)  # Current agent

        async for event in runner.run_live(...):
            # Process audio, transcription, tool calls

            # Detect agent switches via tool calls
            if func_name == "_start_scene":
                session.pending_agent_switch = "partner"
            elif func_name == "_end_scene":
                session.pending_agent_switch = "mc"

            # Switch agents and restart stream
            if agent_switch_needed:
                switch_to_partner/mc()
                continue  # Restart with new agent
```

**Critical Insight**: ADK `run_live()` is **per-agent**. Each agent switch requires:
1. Completing current `run_live()` generator
2. Creating new queue
3. Starting new `run_live()` with different agent
4. Sending context to new agent

### 5. Room Agent Implementation

**Ambient Audio Trigger** (`audio_orchestrator.py`, line 1556-1635):
```python
async def trigger_audience_reaction(session, user_input, partner_response):
    # Analyze sentiment/energy
    sentiment = analyze_sentiment(user_input, partner_response)

    # Check cooldown (15s between reactions)
    if should_trigger_ambient(sentiment, energy_level):
        # Generate TTS audio via room_tts.py
        audio_data = await room_tts.generate_ambient_reaction(
            sentiment=sentiment,
            energy_level=energy_level
        )

        # Queue for streaming at 30% volume
        session.pending_room_audio.append(audio_data)
```

**Room TTS** (`app/audio/room_tts.py`):
- Uses `gemini-2.5-flash-preview-tts` model
- Generates brief reactions: "Ooh!", "Ha!", "Nice!"
- Returns PCM16 audio at 24kHz
- Mixed at 30% volume by `AudioMixer`

---

## Simplification Options Analysis

### Option A: MC Only (No Audience)

**Changes Required**:

1. **MC Agent Prompt** - Add scene partner behavior to existing MC prompt
   - File: `app/agents/mc_agent.py`
   - Lines: 60-163 (AUDIO_MC_SYSTEM_PROMPT)
   - Effort: **2 hours**

2. **Remove Agent Switching** - Delete transition logic
   - File: `app/audio/audio_orchestrator.py`
   - Remove: Lines 266-332 (switch_to_partner, switch_to_mc)
   - Remove: Lines 936-967 (agent switch handling)
   - Remove: Lines 1172-1231 (tool call detection)
   - Effort: **3 hours**

3. **Simplify Turn Manager** - Remove multi-agent state
   - File: `app/audio/turn_manager.py`
   - Keep only turn counting (for phase transitions)
   - Remove agent switching methods
   - Effort: **2 hours**

4. **Update Session State** - Remove partner_agent, room_agent
   - File: `app/audio/audio_orchestrator.py`
   - Lines: 86-107 (AudioSession dataclass)
   - Remove: partner_agent, room_agent, scene_context, audio_mixer
   - Effort: **1 hour**

5. **Remove Unused Agents** - Clean up imports
   - File: `app/audio/audio_orchestrator.py`
   - Lines: 16-18 (imports)
   - Effort: **30 min**

6. **Frontend Updates** - Remove agent switch handling
   - WebSocket client expects `agent_switch` events
   - Effort: **2 hours** (if frontend exists)

**Total Effort**: **10.5 hours** (1.5 days)

**Risks**:
- ⚠️ **Loss of specialization**: MC persona different from scene partner
- ⚠️ **Prompt complexity**: Single agent doing 2 jobs may confuse model
- ✅ **Low technical risk**: Clean separation in code

---

### Option B: MC + Text-Only Audience

**Concept**: Keep audience suggestions/reactions as **text events** in audio mode.

**Implementation**:

1. **Audience as Text Service** (not an agent)
   ```python
   class AudienceTextService:
       async def get_suggestion(game_name: str) -> dict:
           # Call AudienceArchetypesToolset directly
           return {
               "type": "audience_suggestion",
               "text": "Someone shouts: 'A coffee shop!'",
               "suggestion": "A coffee shop",
               "demographic": "tech"
           }

       async def generate_reaction(sentiment: str) -> dict:
           return {
               "type": "audience_reaction",
               "text": "The crowd laughs!",
               "sentiment": "positive",
               "color": "#FFD700"  # Gold for positive
           }
   ```

2. **WebSocket Event Emission**
   - Emit text events alongside audio
   - Frontend displays in UI (speech bubbles, color flashes)

3. **MC Integration**
   - MC calls `_get_suggestion_for_game` (existing tool)
   - Returns text suggestion instead of audio
   - MC reads suggestion aloud ("I heard 'coffee shop' from the crowd!")

**Changes Required**:

1. **Create AudienceTextService** - Wrapper for existing toolset
   - New file: `app/services/audience_text_service.py`
   - Effort: **3 hours**

2. **Update MC Tools** - Already has `_get_suggestion_for_game`
   - No changes needed! ✅
   - Effort: **0 hours**

3. **Add Text Event Emission** - In `stream_responses()`
   - File: `app/audio/audio_orchestrator.py`
   - After Partner turns, emit text reaction instead of audio
   - Effort: **2 hours**

4. **Remove Room Agent Audio** - Keep demographic logic
   - Remove TTS generation
   - Keep `AudienceArchetypesToolset` for suggestions
   - Effort: **2 hours**

5. **Frontend UI** - Display text indicators
   - Speech bubble component for suggestions
   - Color flash animation for reactions
   - Effort: **4 hours** (if frontend exists)

**Total Effort**: **11 hours** (1.5 days)

**Benefits**:
- ✅ **Retains audience personality** via demographics
- ✅ **Visual engagement** without audio complexity
- ✅ **Lower API costs** (no TTS calls)
- ✅ **Faster reactions** (text vs audio synthesis)

**Risks**:
- ⚠️ **UI complexity**: Requires frontend work
- ⚠️ **Mixed modality**: Text in audio mode may feel inconsistent

---

## Technical Risks & Mitigation

### Risk 1: Prompt Quality with Merged Roles
**Scenario**: MC tries to be both host AND scene partner, loses effectiveness

**Mitigation**:
- Use clear role markers: "As HOST:" vs "As SCENE PARTNER:"
- Test with Gemini 2.0 Flash Experimental (better instruction following)
- Implement phase transitions within single agent (existing logic works)

### Risk 2: Loss of Voice Differentiation
**Scenario**: User confused when MC switches from host to scene partner

**Mitigation**:
- Use voice config changes (`voice_config.py` already supports this)
- Add explicit transitions: "Alright, I'll be your scene partner now - let's do this!"
- Frontend UI indicator showing current role

### Risk 3: Frontend Breaking Changes
**Scenario**: UI expects 3 agents, breaks with 1

**Mitigation**:
- Backwards compatible events:
  ```json
  {
    "type": "audio",
    "agent": "mc",  // Always "mc" now
    "role": "host" | "scene_partner"  // NEW field
  }
  ```

---

## ADK/Google Agent Toolkit Considerations

### Current ADK Usage

**ADK Components Used**:
- `google.adk.agents.Agent` - Agent creation
- `google.adk.runners.Runner` - run_live() executor
- `google.adk.runners.LiveRequestQueue` - Audio streaming
- `google.genai.types` - Audio/speech configs

**Key ADK Pattern** (from ADK docs):
```python
# ADK run_live() is SINGLE-AGENT, SINGLE-SESSION
async for event in runner.run_live(
    user_id=user_id,
    session_id=session_id,
    live_request_queue=queue,
    run_config=config
):
    # Process events
```

**Current Workaround**: Create new `Runner` + `queue` for each agent switch.

**Post-Simplification**: **No workarounds needed!** ✅
- Single agent = single `run_live()` session
- No queue recreation
- Simpler error handling
- Better ADK session management

---

## Recommendations

### Primary Recommendation: **Option A (MC Only)**

**Why**:
1. **Cleanest architecture** - Single agent, single responsibility
2. **Aligns with ADK design** - No multi-agent coordination hacks
3. **Fastest to implement** - 1.5 days
4. **Lower operational cost** - 1 Gemini Live API call instead of 2+
5. **Easier to debug** - Single conversation thread

**Implementation Priority**:
```
Phase 1: Core Simplification (8 hours)
├── Update MC prompt with scene partner behavior
├── Remove agent switching logic
├── Simplify turn manager
└── Update session state

Phase 2: Testing & Refinement (4 hours)
├── Test prompt quality across games
├── Verify phase transitions work
└── Frontend compatibility check

Phase 3: Cleanup (2 hours)
├── Remove unused agent files
├── Update documentation
└── Remove room_tts.py dependencies
```

### Secondary Option: **Option B (Text Audience)** - If needed

**When to use**:
- User feedback indicates missing "audience energy"
- Want demographic-aware suggestions without audio complexity

**Implementation**: Can be added AFTER Option A is complete (additive change).

---

## Cost Analysis

### Current System
- **MC Agent**: Gemini 2.0 Flash (Live API) - $X/hour
- **Partner Agent**: Gemini 2.0 Flash (Live API) - $X/hour
- **Room Agent**: Gemini 2.5 Flash TTS - $Y/request
- **Total**: ~2-3x base cost per session

### Simplified System (Option A)
- **MC Agent**: Gemini 2.0 Flash (Live API) - $X/hour
- **Total**: Base cost per session
- **Savings**: **~60-70%** on API costs

### Simplified System (Option B)
- **MC Agent**: Gemini 2.0 Flash (Live API) - $X/hour
- **Audience Service**: Free (Firestore reads only)
- **Total**: Base cost + negligible
- **Savings**: **~60%** on API costs

---

## Action Plan

### Immediate Next Steps (User Decision Required)

**Question 1**: Do you want audience presence at all?
- **Yes** → Proceed with Option B (text-only audience)
- **No** → Proceed with Option A (MC only)

**Question 2**: What about Partner Agent's fallible behavior (Phase 2)?
- **Keep it** → MC inherits both phases (1-3 turns supportive, 4+ fallible)
- **Remove it** → MC always supportive

**Question 3**: Timeline priority?
- **Fast** → Option A (1.5 days)
- **Feature-rich** → Option B (1.5 days + frontend work)

### Post-Decision Implementation

Once direction confirmed, I can:
1. **Create Linear ticket** with detailed acceptance criteria
2. **Write tests first** (TDD approach via `/claude-flow-develop`)
3. **Implement changes** with code review
4. **Update documentation**

---

## Appendix: File Impact Map

### Files to Modify (Option A)
```
app/agents/mc_agent.py          - Update prompt (major)
app/audio/audio_orchestrator.py - Remove switching (major)
app/audio/turn_manager.py       - Simplify (moderate)
app/audio/websocket_handler.py  - Remove events (minor)
```

### Files to Delete (Option A)
```
app/agents/partner_agent.py     - Unused
app/agents/room_agent.py        - Unused
app/audio/room_tts.py           - Unused
app/audio/ambient_audio.py      - Unused
app/audio/audio_mixer.py        - Unused
tests/audio/unit/test_room_tts.py - Unused
```

### Files to Create (Option B)
```
app/services/audience_text_service.py - New service
tests/services/test_audience_text.py  - New tests
```

### Files to Keep (Both Options)
```
app/toolsets/audience_archetypes_toolset.py - Demographics
app/toolsets/scene_transition_toolset.py    - May be removed (no switching)
```

---

## Questions for Clarification

1. **Frontend Impact**: Do you have a React/Vue frontend consuming these WebSocket events?
2. **User Testing**: How critical is the "audience feel" to your users?
3. **Game Mechanics**: Do any games REQUIRE multiple agents? (e.g., "Character Swap")
4. **Voice Identity**: Should MC sound different as host vs scene partner?
5. **Migration Path**: Existing users mid-session - graceful degradation needed?

---

**Ready to proceed with implementation once direction is confirmed.**
