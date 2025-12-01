# PRD: Audio System Simplification - Unified MC + Text-Only Audience

**Document Version:** 1.0
**Date:** 2025-11-30
**Status:** Draft for Review
**Author:** PRD Writer Agent

---

## 1. Overview

This PRD proposes a significant architectural simplification of the Improv Olympics audio system by consolidating three AI agents (MC, Partner, Room) into a single MC agent that handles both hosting and scene work, while exploring a text-only audience implementation that preserves demographic-aware suggestions without audio complexity.

**Current State:** Three separate audio agents (MC, Partner, Room) with complex handoff logic, multi-agent coordination, and audio mixing.

**Proposed State:** Single MC agent for all interactions, with audience existing as text-only demographic indicators and visual color reactions.

**Business Impact:** Reduced infrastructure complexity, lower LLM costs, faster response times, simpler codebase maintenance, while maintaining core improv experience quality.

---

## 2. Critical Success Factors

- **CSF-1: Scene Quality Preservation** - User improv scenes maintain same or better quality with unified MC vs separate Partner agent (measured via user satisfaction surveys and session completion rates)

- **CSF-2: Cost Reduction** - 50%+ reduction in audio streaming costs by eliminating two agents (Partner + Room) while maintaining audio quality

- **CSF-3: Response Latency** - Average response time improves by 30%+ by eliminating agent switching overhead (currently ~2-3 second delays during MC → Partner handoffs)

- **CSF-4: Suggestion Quality** - Demographically-appropriate audience suggestions maintain current quality levels (measured by user acceptance rate of suggestions)

- **CSF-5: Development Velocity** - 60%+ reduction in audio orchestration complexity enables faster feature iteration (measured by time to implement new audio features)

---

## 3. Current System Analysis

### 3.1 Current Agent Roles

#### MC Agent (app/agents/mc_agent.py)
**Responsibilities:**
- Welcome users and build energy
- Suggest and explain improv games
- Get audience suggestions via `_get_suggestion_for_game` tool
- Hand off to Partner Agent via `_start_scene` tool
- Handle scene interjections (status shifts, game milestones)
- Resume scene via `_resume_scene` tool

**Key Characteristics:**
- Voice: Aoede (energetic, welcoming)
- Personality: High-energy, enthusiastic host
- Tools: ImprovGamesToolset, SceneTransitionToolset, AudienceArchetypesToolset
- Model: Gemini Live API (vertexai_live_model)

**Current Limitations:**
- Cannot perform scene work (explicitly instructed "DON'T do scene work yourself")
- Must hand off to Partner for all improv scenes
- Handoff creates 2-3 second latency gap

#### Partner Agent (app/agents/partner_agent.py)
**Responsibilities:**
- Perform improv scene work with user
- Phase 1 (Turns 1-3): Supportive, training-wheels partner
- Phase 2 (Turns 4+): Fallible, realistic partner
- Follow game-specific rules
- Signal scene end via `_end_scene` tool

**Key Characteristics:**
- Voice: Puck (playful, supportive)
- Personality: Adaptive scene partner (supportive → realistic)
- Phase transitions at turn 4
- Model: Gemini Live API (vertexai_live_model)

**Current Value:**
- Specialized prompts for scene work
- Phase-based progression system
- Clear separation between hosting and performing

#### Room Agent (app/agents/room_agent.py)
**Responsibilities:**
- Generate ambient audio reactions (laughs, gasps)
- Provide audience suggestions via AudienceArchetypesToolset
- Triggered by sentiment analysis after Partner turns
- Mixed at 30% volume

**Key Characteristics:**
- Voice: Charon (ambient, understated)
- Personality: Collective audience consciousness
- Tools: AudienceArchetypesToolset, SentimentAnalysisToolset
- Model: Gemini Live API + TTS (room_tts.py)

**Current Implementation:**
- Ambient audio triggered by `AmbientAudioTrigger` based on sentiment/energy
- 15-second cooldown between reactions
- Pre-defined reaction texts (AMBIENT_REACTIONS dict)
- Simple sentiment analysis (positive/negative word detection)

### 3.2 Current Audience Implementation

**Audio Component (Room Agent):**
- Generates TTS audio reactions ("Ha!", "Ooh!", "Mmm!")
- Sentiment-based triggering (positive/negative/neutral)
- Energy-level detection from conversation length/punctuation
- Mixed at 30% volume via AudioMixer
- Cooldown mechanism to prevent over-triggering

**Suggestion Component (AudienceArchetypesToolset):**
- Firestore-backed audience archetypes (demographics, preferences)
- Generates demographically-appropriate suggestions
- Maps game types to suggestion types (location, relationship, topic, etc.)
- Rich suggestion pools per demographic (tech, healthcare, education, arts, finance)
- Example: Tech audience gets "A hackathon" vs mixed audience gets "A coffee shop"

**Complexity Drivers:**
- Separate audio generation pipeline (room_tts.py)
- Sentiment analysis logic
- Audio mixing coordination
- Trigger cooldown management
- Per-session Room Agent instances

### 3.3 Current Audio Orchestration

**Session Management (audio_orchestrator.py):**
- Creates 3 per-session agent instances (MC, Partner, Room)
- Manages agent switching via `pending_agent_switch` flag
- Coordinates turn-taking with AgentTurnManager
- Handles phase transitions for Partner Agent
- Triggers Room Agent reactions asynchronously

**Agent Switching Flow:**
1. MC calls `_start_scene` tool → sets `pending_agent_switch = "partner"`
2. On turn completion, breaks run_live stream
3. Switches to Partner Agent, creates new queue
4. Sends scene context via `_send_partner_scene_start()`
5. Restarts run_live with Partner Agent
6. Partner calls `_end_scene` → switches back to MC

**Complexity Issues:**
- ~200+ lines of agent switching logic
- Multiple queue management
- Scene context passing between agents
- Turn count coordination across agents
- Error recovery complexity

---

## 4. Functional Requirements

### FR-1: Unified MC Agent for All Interactions
**Description:** MC Agent must handle both hosting duties AND scene work without Partner Agent.

**Acceptance Criteria:**
- MC Agent prompt includes scene partner behaviors from current Partner Agent
- MC Agent maintains high-energy hosting personality while also being competent scene partner
- No `_start_scene` or `_resume_scene` tools needed
- MC performs improv scenes directly with user

**Technical Approach:**
- Merge AUDIO_MC_SYSTEM_PROMPT with PHASE_1_SYSTEM_PROMPT concepts
- Create unified prompt that balances hosting energy with scene work skills
- Remove SceneTransitionToolset from MC Agent
- Maintain ImprovGamesToolset and AudienceArchetypesToolset

**Open Questions:**
- Can a single agent maintain both high-energy hosting AND nuanced scene work? (May need prompt engineering experimentation)
- Should we preserve Phase 1/Phase 2 progression or simplify to single approach? (Recommendation: Start with Phase 1 supportive approach only)

---

### FR-2: Remove Partner Agent Entirely
**Description:** Eliminate Partner Agent and all associated infrastructure.

**Acceptance Criteria:**
- `app/agents/partner_agent.py` removed or deprecated
- `SceneTransitionToolset` removed
- `AgentTurnManager` simplified to single-agent mode
- `audio_orchestrator.py` removes Partner Agent creation
- All Partner-related tests removed or updated

**Impact Analysis:**
- **Files to Remove/Modify:**
  - app/agents/partner_agent.py (remove)
  - app/toolsets/scene_transition_toolset.py (remove)
  - app/audio/turn_manager.py (simplify)
  - app/audio/audio_orchestrator.py (remove partner logic ~150 lines)
  - app/agents/stage_manager.py (phase determination logic no longer needed)

- **Cost Savings:**
  - 50% reduction in Live API calls (no Partner Agent streaming)
  - Simplified session state (no partner_agent, partner_phase, scene_context)

---

### FR-3: Text-Only Audience Implementation
**Description:** Audience exists as text-based demographic indicators with visual reactions, not audio.

**Acceptance Criteria:**
- Audience suggestions remain demographically-appropriate via AudienceArchetypesToolset
- MC Agent calls `_get_suggestion_for_game` tool to get text suggestions
- Frontend displays text suggestions as "shouted" from audience
- Frontend shows visual color reactions based on sentiment (green = positive, red = negative, yellow = neutral)
- No Room Agent audio generation or mixing

**Implementation Details:**

**Backend Changes:**
- Remove Room Agent audio functionality
- Keep AudienceArchetypesToolset for suggestion generation
- MC Agent retains audience toolset
- Remove room_tts.py
- Remove AmbientAudioTrigger logic
- Remove AudioMixer (no multi-stream mixing needed)

**Frontend Changes:**
- Display audience suggestions as text overlays (e.g., "Someone shouts: 'A coffee shop!'")
- Show visual sentiment indicators:
  - Positive: Green glow/pulse animation
  - Negative: Red glow/pulse
  - Neutral: Yellow/amber glow
  - Very Positive: Bright green sparkles
  - Very Negative: Dark red flash
- Sentiment analysis happens client-side or backend sends sentiment with transcription
- No audio playback for audience reactions

**Example User Experience:**
1. MC: "Audience, give me a location for our scene!"
2. [MC calls `_get_suggestion_for_game("long_form")`]
3. Backend returns: `{"suggestion": "A coffee shop", "sentiment": "positive"}`
4. Frontend displays text: "**Someone from the crowd shouts:** *A coffee shop!*"
5. Frontend shows green pulse animation around audience area
6. MC: "I heard 'A coffee shop' - love it! Let's use that!"

---

### FR-4: Simplified Audio Orchestration
**Description:** Remove all multi-agent coordination logic from audio_orchestrator.py.

**Acceptance Criteria:**
- No agent switching logic (no `pending_agent_switch`, no stream restarts)
- Single `run_live` stream for entire session
- No partner phase transitions
- No scene context passing
- Session only creates one agent instance (MC)

**Code Reduction Estimate:**
- Remove ~200 lines from audio_orchestrator.py
- Remove ~100 lines from turn_manager.py
- Remove ~50 lines from agent handoff logic
- Total: ~350 lines removed

**Performance Benefits:**
- Eliminate 2-3 second handoff latency
- Reduce memory usage (2 fewer agent instances per session)
- Simpler error recovery (no mid-stream switches)

---

### FR-5: Maintain Suggestion Quality
**Description:** Audience suggestions must remain demographically-aware and game-appropriate.

**Acceptance Criteria:**
- `AudienceArchetypesToolset` remains fully functional
- `_get_suggestion_for_game` tool provides game-appropriate suggestions
- Suggestion pools remain unchanged (tech/healthcare/education/arts/finance demographics)
- MC Agent can call audience tools successfully

**Test Cases:**
- Tech audience → tech-related suggestions ("A hackathon", "Co-founders")
- Healthcare audience → medical suggestions ("An operating room", "Doctor and patient")
- Mixed audience → universal suggestions ("A coffee shop", "Roommates")
- Game-specific mapping works (Long Form → relationship, Questions Only → location)

---

## 5. Non-Functional Requirements

### NFR-1: Response Latency Reduction
**Target:** Average response time < 2 seconds (down from 3-5 seconds with agent switching).

**Acceptance Criteria:**
- P95 latency for MC responses < 2.5 seconds
- No multi-second gaps during sessions
- Latency metrics tracked via logging

**Measurement:**
- Log timestamps for user input → agent response
- Compare pre/post simplification latency distributions
- Monitor ADK Live API response times

---

### NFR-2: Cost Reduction
**Target:** 50%+ reduction in audio infrastructure costs.

**Acceptance Criteria:**
- Live API costs reduced by eliminating Partner and Room agents
- TTS generation costs eliminated (no Room Agent TTS)
- Session memory footprint reduced by 66% (1 agent vs 3)

**Measurement:**
- Track Live API usage per session
- Calculate cost per session pre/post change
- Monitor concurrent session capacity

---

### NFR-3: Code Maintainability
**Target:** 40%+ reduction in audio orchestration code complexity.

**Acceptance Criteria:**
- Cyclomatic complexity of `audio_orchestrator.py` reduced by 40%+
- Test coverage maintained at >80% for audio components
- Documentation updated for simplified architecture

**Measurement:**
- LOC count for audio orchestration modules
- Complexity metrics via pylint/radon
- Test suite execution time

---

### NFR-4: Backward Compatibility
**Target:** Existing sessions gracefully migrate to new system.

**Acceptance Criteria:**
- Active sessions complete successfully on old system
- New sessions use new simplified system
- No data loss during transition
- Feature flag controls rollout

**Migration Strategy:**
- Deploy with feature flag `ENABLE_UNIFIED_MC` (default false)
- Gradually enable for new sessions
- Monitor error rates and user satisfaction
- Full rollout after 7-day validation period

---

## 6. Explicit Scope Exclusions

### Out of Scope for This Initiative

- **Voice-Based Audience Reactions:** No audio laughs, gasps, or ambient commentary. Only text + visual indicators.

- **Multi-Agent Coordination for Other Use Cases:** This simplification is audio-only. Text mode may still use multiple agents if beneficial.

- **Advanced Sentiment Analysis:** Simple positive/negative/neutral detection only. No ML-based emotion analysis.

- **Real-Time Audio Mixing:** No AudioMixer needed with single agent. Client plays single audio stream.

- **Phase Progression System:** Initial implementation uses single partner approach (Phase 1 supportive). Phase 2 fallible behavior deferred for future consideration.

- **Audience Personality Variations:** Audience suggestions remain demographically varied, but no individual audience member personalities or voices.

- **Room Agent for Non-Audio Features:** If Room Agent has text-mode analytics value, that's a separate decision. This PRD focuses on audio simplification only.

---

## 7. Dependencies & Assumptions

### Technical Dependencies

- **Google ADK Live API:** Must support extended prompts for unified MC Agent (no API limitations on prompt size)

- **AudienceArchetypesToolset:** Must remain fully functional for suggestion generation

- **Frontend WebSocket Implementation:** Must handle text-based audience suggestions + sentiment data

- **Firestore:** Audience archetype data remains available

### Assumptions

- **Assumption 1:** A single agent can perform both hosting and scene work competently with proper prompt engineering.
  - **Risk:** Prompt may not balance both roles effectively.
  - **Mitigation:** A/B test unified prompt vs current system with beta users.

- **Assumption 2:** Users will accept text-based audience reactions as sufficient for immersion.
  - **Risk:** Audio reactions may be more engaging than text + visual.
  - **Mitigation:** User testing with prototype. Fallback: Keep Room Agent if feedback negative.

- **Assumption 3:** Frontend can implement visual sentiment indicators without major refactor.
  - **Risk:** UI/UX complexity for visual reactions.
  - **Mitigation:** Design review with frontend team before committing.

- **Assumption 4:** Eliminating agent switching won't cause session quality degradation.
  - **Risk:** Context loss or performance issues with long sessions.
  - **Mitigation:** Monitor session duration and completion rates post-launch.

---

## 8. Text-Only Audience Feasibility Analysis

### 8.1 What Would Text-Only Look Like?

**Current Audio Experience:**
1. User and Partner have conversation
2. Sentiment detected ("positive", energy: 0.8)
3. Room Agent generates TTS: "Ha ha!" (audio)
4. Audio mixed at 30% volume and played
5. User hears ambient laughter in background

**Proposed Text+Visual Experience:**
1. User and MC have conversation
2. Sentiment detected ("positive", energy: 0.8)
3. Backend sends sentiment with transcription
4. Frontend displays:
   - Text badge: "Audience reaction: Laughter" (optional, could be just visual)
   - Visual: Green pulse animation in audience area
   - Color intensity maps to energy level
5. User sees visual feedback, no audio

### 8.2 Visual Indicators Currently Available

**Current Frontend (Inferred from Context):**
- WebSocket receives transcription events
- Displays user/agent transcriptions
- Likely has audio player for agent audio

**Required Visual Additions:**
- Sentiment indicator overlay (CSS animations)
- Color-coded feedback (green/red/yellow)
- Optional text descriptions ("Laughter", "Gasps", "Applause")
- Positioned in dedicated "audience area" of UI

**Design Recommendation:**
```
┌─────────────────────────────────────┐
│  Improv Olympics - Audio Mode      │
├─────────────────────────────────────┤
│  [MC Transcription]                 │
│  "Let's start with a relationship!" │
│                                      │
│  [User Transcription]               │
│  "How about siblings?"              │
│                                      │
│  ┌──────────────────────────────┐  │
│  │  AUDIENCE                    │  │
│  │  🟢 "Someone shouts: Siblings!" │
│  │     [green pulse animation]   │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 8.3 Complexity Analysis

**Audio Audience (Current Complexity: HIGH):**
- Room Agent instance per session
- TTS generation (5-second latency)
- Sentiment analysis logic
- Audio mixing (AudioMixer)
- Trigger cooldown management
- Async audio generation
- Error handling for TTS failures
- Volume balancing
- **Lines of Code:** ~300-400 across multiple files

**Text+Visual Audience (Proposed Complexity: LOW):**
- Sentiment detection (reuse existing simple logic)
- Send sentiment with transcription events
- Frontend CSS animations
- Optional text descriptions
- **Lines of Code:** ~50-100 backend, ~100-150 frontend CSS/JS

**Complexity Reduction:** 60-70% reduction

### 8.4 Recommendation: Text-Only Audience

**Reasoning:**
1. **Cost/Benefit:** Audio reactions add ~30% overhead for marginal immersion benefit
2. **User Focus:** Users focus on scene work, not background audio
3. **Technical Simplicity:** Text+visual much simpler to maintain
4. **Suggestion Quality Preserved:** Demographic-aware suggestions retained
5. **Performance:** Eliminates TTS latency and audio mixing complexity

**Fallback Plan:**
If user feedback strongly favors audio reactions:
- Implement simple pre-recorded audio clips (not TTS)
- 5-10 laugh/gasp/applause clips triggered by sentiment
- Simpler than current Room Agent, but more immersive than text

---

## 9. Implementation Phases

### Phase 1: Unified MC Agent Prompt Engineering (Week 1)
**Goal:** Create and validate unified MC prompt that handles hosting + scene work.

**Tasks:**
- Draft unified prompt merging MC + Partner Phase 1 behaviors
- Create A/B test with beta users (current system vs unified)
- Measure scene quality via user surveys
- Iterate prompt based on feedback

**Success Metrics:**
- User satisfaction >= current system
- Scene completion rate >= current system

---

### Phase 2: Backend Simplification (Week 2)
**Goal:** Remove Partner and Room agents, simplify orchestration.

**Tasks:**
- Update audio_orchestrator.py to single-agent mode
- Remove Partner Agent files
- Remove Room Agent audio functionality
- Keep AudienceArchetypesToolset intact
- Update tests

**Success Metrics:**
- All tests passing
- Code coverage >= 80%
- No regressions in suggestion quality

---

### Phase 3: Frontend Text+Visual Audience (Week 3)
**Goal:** Implement visual sentiment indicators.

**Tasks:**
- Add sentiment field to WebSocket events
- Create CSS animations for color reactions
- Design audience area UI component
- Test with various sentiment scenarios

**Success Metrics:**
- Visual reactions display correctly
- Performance: <16ms frame time (60fps)
- User feedback positive

---

### Phase 4: Integration Testing + Rollout (Week 4)
**Goal:** End-to-end validation and gradual rollout.

**Tasks:**
- E2E testing with full user flows
- Feature flag rollout (10% → 50% → 100%)
- Monitor latency, costs, errors
- Gather user feedback

**Success Metrics:**
- P95 latency < 2.5 seconds
- Cost reduction >= 50%
- Error rate < 1%
- User satisfaction maintained

---

## 10. Open Questions

### Q1: Prompt Engineering Feasibility
**Question:** Can a single unified prompt effectively balance high-energy hosting with nuanced scene work?

**Current Gaps:**
- MC prompt optimized for hosting energy and enthusiasm
- Partner prompt optimized for improv scene dynamics
- Risk: Merged prompt may dilute both strengths

**Recommendation:** Build prototype and A/B test with users. If quality suffers, consider:
- Fallback Option A: Keep Partner Agent but merge MC + Room
- Fallback Option B: Use in-prompt role switching ("Now as scene partner...")

---

### Q2: Phase Progression Value
**Question:** Should we preserve Phase 1 (supportive) → Phase 2 (fallible) progression?

**Analysis:**
- Phase system adds value for learning progression
- Simplification argument: Single phase easier to maintain
- User benefit unclear: Do users prefer supportive-only or progression?

**Recommendation:** Launch with Phase 1 (supportive) only. Add Phase 2 if user feedback requests challenge.

---

### Q3: Room Agent for Non-Audio Use Cases
**Question:** Does Room Agent provide value in text mode for analytics/insights?

**Current State:**
- Room Agent has text mode with SentimentAnalysisToolset
- Could provide "room vibe check" for MC decisions
- Not currently used in production

**Recommendation:** Out of scope for this PRD. Evaluate separately if text-mode Room Agent has analytics value.

---

### Q4: Audience Suggestion Delivery Mechanism
**Question:** How should MC deliver audience suggestions in unified system?

**Current Flow:**
1. MC asks audience for suggestion
2. MC calls `_get_suggestion_for_game` tool
3. Tool returns: `{"suggestion": "A coffee shop", "reasoning": "..."}`
4. MC says: "I heard 'A coffee shop' from the audience!"

**Proposed Flow (Same):**
1. Unified MC asks audience
2. Calls `_get_suggestion_for_game`
3. Receives suggestion
4. MC incorporates into scene setup

**Status:** No change needed. Unified MC retains audience toolset.

---

## 11. Risk Assessment

### High Risks

**Risk 1: Scene Quality Degradation**
- **Likelihood:** Medium
- **Impact:** High
- **Mitigation:** A/B testing, user feedback, fallback to current system if needed

**Risk 2: User Perception of "Cheapness"**
- **Likelihood:** Low-Medium
- **Impact:** Medium
- **Mitigation:** Frame text audience as "streamlined experience", high-quality visual design

### Medium Risks

**Risk 3: Frontend Implementation Complexity**
- **Likelihood:** Low
- **Impact:** Medium
- **Mitigation:** Design review, prototype early, allocate frontend dev time

**Risk 4: Suggestion Quality Regression**
- **Likelihood:** Low
- **Impact:** Medium
- **Mitigation:** Comprehensive testing of AudienceArchetypesToolset after changes

### Low Risks

**Risk 5: Cost Savings Not Realized**
- **Likelihood:** Low
- **Impact:** Low
- **Mitigation:** Measure API usage before/after with metrics

---

## 12. Success Metrics

### Primary KPIs

1. **Response Latency:** P95 < 2.5 seconds (target: 30% improvement)
2. **Cost per Session:** 50% reduction in audio infrastructure costs
3. **User Satisfaction:** NPS >= current baseline (measure via post-session survey)
4. **Session Completion Rate:** >= current baseline (~85%)

### Secondary KPIs

5. **Code Maintainability:** 40% reduction in audio orchestration LOC
6. **Error Rate:** < 1% of sessions experience errors
7. **Suggestion Acceptance:** >= 90% of audience suggestions accepted by users
8. **Development Velocity:** Time to implement new audio features reduced by 50%

---

## 13. Recommendation Summary

### ✅ PROCEED with Simplification

**Rationale:**
1. **Clear Cost/Complexity Reduction:** 50%+ cost savings, 60%+ code reduction
2. **Feasibility:** Text-only audience is technically straightforward
3. **Risk Manageable:** A/B testing and feature flags mitigate quality risks
4. **User Value Preserved:** Demographic suggestions maintained, core improv experience intact

### 📋 Implementation Approach

**Path A (Recommended): Unified MC + Text Audience**
- Single MC agent for hosting and scene work
- Text-based audience suggestions with visual sentiment
- 4-week phased rollout with testing

**Path B (Fallback): Unified MC + Simple Audio Audience**
- Same unified MC
- Pre-recorded audio clips for reactions (not TTS)
- If user feedback demands audio

### ⚠️ Critical Success Factors

1. **Prompt Engineering:** Unified MC prompt quality is make-or-break
2. **User Testing:** A/B test before full rollout
3. **Visual Design:** High-quality UI for text audience reactions
4. **Monitoring:** Track latency, costs, satisfaction closely

---

## 14. Next Steps

1. **Stakeholder Review:** Product, Engineering, Design review this PRD
2. **Decision:** Approve Path A (recommended) or Path B (fallback)
3. **Prompt Engineering:** Prototype unified MC prompt (1 week)
4. **User Testing:** A/B test with beta users (1 week)
5. **Implementation:** Execute 4-phase plan (4 weeks)
6. **Rollout:** Feature flag gradual rollout with monitoring

---

**Document Status:** Ready for Stakeholder Review
**Recommended Decision:** APPROVE Path A - Unified MC + Text Audience
**Timeline:** 6 weeks total (2 weeks design/testing + 4 weeks implementation)
