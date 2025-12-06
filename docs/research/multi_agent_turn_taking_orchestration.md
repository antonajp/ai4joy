# Multi-Agent Turn-Taking and Conversation Orchestration Research Report

**Research Date:** 2025-12-01
**Context:** Improv Olympics AI4Joy Application - Multi-Agent Voice Orchestration
**Researchers:** Claude (Research Agent)

---

## Executive Summary

This research report provides a comprehensive analysis of turn-taking protocols and conversation orchestration mechanisms for multi-agent dialogue systems, with specific application to an improv comedy application requiring coordinated speech between:

- **User** (microphone input)
- **MC Agent** (game hosting and scene work)
- **Partner Agent** (scene partner - text mode only)
- **Audience Agent** (ambient reactions - text mode only)

### Key Findings

1. **Current State**: The ai4joy application already implements **two distinct orchestration architectures** - text mode (HTTP-based, multi-agent with Stage Manager) and audio mode (WebSocket-based, single MC agent with consolidated audience vibes)

2. **Critical Discovery**: **Audio mode already solves the turn-taking problem elegantly** through:
   - Single unified MC agent (no agent switching complexity)
   - Push-to-talk with manual activity signals (no automatic VAD conflicts)
   - Turn counting via `AgentTurnManager` for phase transitions
   - MC naturally weaves audience reactions into speech (no separate Room Agent needed)

3. **Research Recommendations**: The challenge is NOT multi-agent turn-taking in audio (already solved via single-agent design), but rather **extending audio mode to support multiple distinct voices** while maintaining coordination simplicity.

---

## Table of Contents

1. [Academic Research on Turn-Taking](#1-academic-research-on-turn-taking)
2. [Floor Control Mechanisms](#2-floor-control-mechanisms)
3. [Interruption and Barge-In Handling](#3-interruption-and-barge-in-handling)
4. [Priority Systems and Speaker Allocation](#4-priority-systems-and-speaker-allocation)
5. [Event-Driven Architecture Patterns](#5-event-driven-architecture-patterns)
6. [Agent Coordination Protocols (2024-2025)](#6-agent-coordination-protocols-2024-2025)
7. [Backchanneling and Ambient Reactions](#7-backchanneling-and-ambient-reactions)
8. [Current Implementation Analysis](#8-current-implementation-analysis)
9. [Recommended Protocol for Improv-Style Multi-Agent Dialogue](#9-recommended-protocol-for-improv-style-multi-agent-dialogue)
10. [Implementation Roadmap](#10-implementation-roadmap)

---

## 1. Academic Research on Turn-Taking

### 1.1 Murder Mystery AI Study (2025)

**Source:** [Who speaks next? Multi-party AI discussion leveraging the systematics of turn-taking in Murder Mystery games](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1582287/full)

**Key Findings:**
- Human turn-taking systematics are effective for controlling dialogue among AI agents
- Agents can engage in flexible, immediate interactions when turn-taking mechanisms are implemented
- Memory management is crucial for multi-agent systems to store past statements and recall them when necessary

**Relevance to Improv:**
- Improv shares similar collaborative turn-taking dynamics with murder mystery games
- Memory of previous contributions is essential for scene continuity
- "Yes, and..." principle aligns with collaborative turn-taking research

### 1.2 LLM Multi-Turn Conversation Challenges (2024)

**Source:** [Evaluating LLM-based Agents for Multi-Turn Conversations Survey](https://arxiv.org/pdf/2503.22458)

**Key Challenges Identified:**
- Task success tracking across multiple turns
- Response quality degradation over long conversations
- Context window limitations in extended dialogues

**Solutions:**
- **Memory mechanisms** for conversation state
- **Turn-level evaluation metrics** for quality tracking
- **Context compaction strategies** for long sessions

---

## 2. Floor Control Mechanisms

### 2.1 Token-Passing Floor Control

**Source:** [Token-Passing Floor Control - Usability Glossary](https://www.usabilityfirst.com/glossary/token-passing-floor-control/)

**Definition:** A floor control method that allocates the floor to the person/agent who holds the token. The token can be passed to another participant.

**Implementation Patterns:**

```python
class FloorToken:
    """Represents speaking permission in multi-agent system"""
    current_holder: AgentType
    request_queue: List[AgentRequest]

    def pass_token(self, next_speaker: AgentType):
        """Explicit handoff to next speaker"""
        self.current_holder = next_speaker

    def request_floor(self, agent: AgentType, priority: int):
        """Agent requests permission to speak"""
        self.request_queue.append(AgentRequest(agent, priority))
```

**Pros:**
- Clear ownership of speaking rights
- No simultaneous speech conflicts
- Predictable turn transitions

**Cons:**
- Requires explicit handoff logic
- Can feel rigid for natural conversation
- Delays if token holder is silent

### 2.2 Multi-Party Conversation Floor Control

**Source:** [Supporting Engagement and Floor Control in Hybrid Meetings](https://link.springer.com/chapter/10.1007/978-3-642-03320-9_26)

**Key Mechanisms:**
- **Visual cues** (gaze, head-turning) for floor management
- **Speech patterns** (discourse markers, pitch changes)
- **Automatic recognition** of conversational behavior

**Research Finding:** *"Head-turning and gaze have been shown to serve communicative functions in managing turn-taking and floor control"*

**Application to Voice-Only Systems:**
- Replace visual cues with **prosodic signals** (pitch, pause duration)
- Use **verbal handoff cues** ("What do you think, [agent name]?")
- Implement **silence threshold detection** for turn completion

---

## 3. Interruption and Barge-In Handling

### 3.1 Intelligent Barge-In Classification

**Source:** [Contextual Acoustic Barge-in Classification - Amazon Science](https://www.amazon.science/publications/contextual-acoustic-barge-in-classification-for-spoken-dialog-systems)

**Classification Framework:**

```
Barge-In Detection → Classification → Response Strategy
                          ↓
    ┌────────────────────────────────────┐
    │  True Barge-In  │  False Barge-In  │
    ├─────────────────┼──────────────────┤
    │ User interrupts │ Background noise │
    │ Stop & Listen   │ Continue speaking│
    └─────────────────┴──────────────────┘
```

**Key Techniques:**
- **Self-supervised learning models** for barge-in verification (38% faster, 4.5% F1 improvement)
- **Audio-only classification** (no ASR required for detection)
- **False positive handling** with resume-from-pause behavior

**Implementation Metrics:**
- **Detection latency:** <200ms for real-time responsiveness
- **False positive rate:** <5% to avoid awkward interruptions
- **Context window:** 1-2 seconds of audio for classification

### 3.2 Interruption Taxonomy (Research-Based)

**Source:** [Interruption Handling for Conversational Robots](https://arxiv.org/html/2501.01568v1)

**Interruption Types:**

1. **Cooperative Agreement** (backchannels)
   - "uh-huh", "yeah", "I see"
   - **Strategy:** Continue speaking, acknowledge subtly

2. **Cooperative Assistance**
   - User provides missing word/idea
   - **Strategy:** Incorporate assistance, continue

3. **Cooperative Clarification**
   - User asks for elaboration
   - **Strategy:** Pause, provide clarification, resume

4. **Disruptive Interruption**
   - User disagrees, changes topic, or takes floor
   - **Strategy:** Truncate response, yield floor

**GPT-4o-mini Classification:** Can classify interruption intent in real-time for adaptive handling

### 3.3 Turn Detection Beyond VAD

**Source:** [Turn Detection and Interruptions - LiveKit Docs](https://docs.livekit.io/agents/build/turns/)

**Key Insight:** *"Turn detection is the contextual evolution beyond Voice Activity Detection. While VAD answers 'Is this speech or noise?', turn detection answers: 'Has the speaker finished their complete thought?'"*

**Modern Approaches:**

1. **Neural Turn Detection Models** (AssemblyAI, TEN Framework)
   - Fine-tuned LLMs deployed on GPU
   - Analyze meaning and flow of speech
   - Detect end-of-turn with semantic understanding

2. **LLM + Acoustic Fusion** (Amazon Research)
   - Combine acoustic features with language model predictions
   - Predict turn-taking and backchannel locations continuously
   - Handle overlapping speech gracefully

**Latency Requirements:**
- **Real-time processing:** <100ms for turn detection
- **Streaming transcription:** Chunk-based analysis (every 200-500ms)
- **End-of-turn signals:** Return `end_of_turn=True` when thought complete

---

## 4. Priority Systems and Speaker Allocation

### 4.1 Priority Queue Scheduling for Real-Time Voice

**Source:** [Low-Latency Queuing - Wikipedia](https://en.wikipedia.org/wiki/Low-latency_queuing)

**VoIP Priority Mechanisms:**

```python
class VoicePriorityQueue:
    """
    Priority queue for real-time voice traffic
    Strict priority: High-priority packets always processed first
    """
    def __init__(self):
        self.high_priority = Queue()  # Interactive voice (user, MC)
        self.medium_priority = Queue()  # Partner responses
        self.low_priority = Queue()  # Background (audience reactions)

    def dequeue_next(self) -> Packet:
        if not self.high_priority.empty():
            return self.high_priority.get()
        elif not self.medium_priority.empty():
            return self.medium_priority.get()
        else:
            return self.low_priority.get()
```

**Fairness Concerns:**
- High-priority queue can **starve lower priorities**
- Solution: **Voice Priority Queue (VPQ) Scheduler**
  - Fair time allocation despite variable data rates
  - Temporal fairness for all speakers
  - Prevents packet drops in low-priority queues

### 4.2 Speaker Priority Levels for Improv

**Proposed Priority Hierarchy:**

| Priority | Speaker | Rationale | Latency Target |
|----------|---------|-----------|----------------|
| **CRITICAL** | User | Human must never be interrupted | <50ms response |
| **HIGH** | MC Agent | Primary host, guides conversation | <200ms response |
| **MEDIUM** | Partner Agent | Scene partner, responds to user | <500ms response |
| **LOW** | Audience Agent | Background reactions, can be deferred | <1000ms response |

**Implementation Strategy:**
- **User speech triggers** interrupt all agents immediately
- **MC has floor** unless user speaks or explicitly hands off
- **Partner waits** for explicit cue from MC or natural pause
- **Audience interjects** only during low-activity windows (>2s silence)

### 4.3 Audio Ducking for Background Speakers

**Source:** [What is Audio Ducking - iZotope](https://www.izotope.com/en/learn/what-is-audio-ducking)

**Technique:** Automatically reduce volume of one audio signal when another (higher-priority) signal is present.

**Application to Multi-Agent Improv:**

```python
class AudioDucker:
    def __init__(self):
        self.primary_threshold = -20  # dB - User/MC speaking
        self.duck_ratio = 0.3  # Reduce background to 30% volume
        self.fade_duration_ms = 50  # Quick fade for natural feel

    def mix_audio(self, primary: AudioStream, background: AudioStream):
        if primary.volume > self.primary_threshold:
            # Duck background audio
            background.apply_gain(self.duck_ratio, fade_ms=self.fade_duration_ms)
        else:
            # Restore background to full volume
            background.apply_gain(1.0, fade_ms=self.fade_duration_ms)
```

**Benefits:**
- **Audience reactions** remain audible but don't overpower dialogue
- **Smooth transitions** via fade duration (50-100ms)
- **Natural feel** - mimics how humans focus on primary speaker

---

## 5. Event-Driven Architecture Patterns

### 5.1 Event-Driven Dialogue Systems

**Source:** [An Event Driven Model for Dialogue Systems](https://www.researchgate.net/publication/221488934_An_event_driven_model_for_dialogue_systems)

**Core Components:**

1. **Events** - Immutable state changes (e.g., `UserStartedSpeaking`, `TurnComplete`)
2. **Event Producers** - Agents that generate events (User, MC, Partner, Audience)
3. **Event Consumers** - Listeners that react to events (TurnManager, AudioMixer)
4. **Event Channels** - Message queues/event buses for transmission
5. **Event Store** - Persistent log for audit/replay

**Architecture Pattern:**

```
User Speech Event
    ↓
Event Bus (RabbitMQ/Kafka)
    ↓
┌─────────────────────────────────┐
│  Event Consumers (Parallel)     │
├─────────────────────────────────┤
│ • TurnManager (update state)    │
│ • AudioMixer (duck background)  │
│ • TranscriptionLogger (record)  │
│ • MC Agent (prepare response)   │
└─────────────────────────────────┘
```

### 5.2 Broker vs Mediator Topology

**Source:** [Event-Driven Architecture Patterns - Solace](https://solace.com/event-driven-architecture-patterns/)

**Broker Topology** (Recommended for Improv):
- **No central orchestrator** - agents broadcast events directly
- **High performance** - minimal latency
- **Scalability** - easy to add new agents
- **Best for:** Real-time, low-latency voice systems

**Mediator Topology** (Alternative):
- **Central orchestrator** controls workflow
- **Better error handling** and circuit breaking
- **Complex coordination** logic in one place
- **Best for:** Text-based systems with multi-step workflows

### 5.3 Key EDA Patterns for Multi-Agent Voice

**Event Sourcing:**
```python
class ConversationEventStore:
    """Persist all conversation events for replay/debugging"""
    events: List[Event] = [
        UserStartedSpeaking(timestamp="2025-12-01T10:00:00Z"),
        UserTranscriptionPartial(text="Hey there..."),
        UserFinishedSpeaking(final_text="Hey there!"),
        MCAgentStartedResponse(agent="mc"),
        MCAudioChunk(data=b"..."),
        TurnComplete(turn_number=1, phase="phase_1")
    ]
```

**Saga Pattern** (for multi-step agent coordination):
```python
class TurnSaga:
    """
    Orchestrate turn execution across agents with compensation
    If any step fails, roll back previous steps
    """
    steps = [
        UserSpeech(),         # Step 1: Capture user input
        MCResponse(),         # Step 2: MC responds
        PartnerResponse(),    # Step 3: Partner adds to scene
        AudienceReaction(),   # Step 4: Audience reacts
        TurnComplete()        # Step 5: Update state
    ]
```

**Dead Letter Queue** (for failed agent responses):
- When agent fails to respond within timeout, route to DLQ
- Retry with exponential backoff
- Fallback to simpler response if retries exhausted

---

## 6. Agent Coordination Protocols (2024-2025)

### 6.1 Modern Agent Communication Protocols

**Source:** [Survey of Agent Interoperability Protocols - MCP, ACP, A2A, ANP](https://arxiv.org/html/2505.02279v1)

**Key Protocols (2024-2025):**

1. **Model Context Protocol (MCP)** - Anthropic (May 2024)
   - **Purpose:** Standardized tool/resource access across agents
   - **Architecture:** JSON-RPC client-server
   - **Use Case:** Shared tool invocation (e.g., Firestore queries, game databases)

2. **Agent-to-Agent Protocol (A2A)** - Google
   - **Purpose:** Direct agent collaboration without central orchestrator
   - **Architecture:** Peer-to-peer with capability discovery
   - **Use Case:** MC ↔ Partner direct handoffs for scene work

3. **Agent Communication Protocol (ACP)** - IBM
   - **Purpose:** Task delegation and workflow coordination
   - **Architecture:** REST-native messaging with async streaming
   - **Use Case:** Text mode - Stage Manager coordinates sub-agents

4. **Agent Network Protocol (ANP)**
   - **Purpose:** Decentralized agent networks
   - **Architecture:** Gossip-based consensus
   - **Use Case:** Distributed audience simulation (future)

### 6.2 Protocol Selection Matrix

| Protocol | Latency | Coordination Style | Best For |
|----------|---------|-------------------|----------|
| **MCP** | Medium | Centralized tools | Shared resources (DB, tools) |
| **A2A** | Low | Peer-to-peer | Real-time agent handoffs |
| **ACP** | Medium | Orchestrated | Complex workflows (text mode) |
| **ANP** | High | Decentralized | Scalable, fault-tolerant |

**Recommendation for Audio Improv:**
- **Primary:** A2A for real-time MC ↔ Partner communication
- **Secondary:** MCP for shared tool access (game rules, principles)
- **Avoid:** ACP (too high latency for voice), ANP (overkill for 3-4 agents)

### 6.3 Modular Speaker Architecture (MSA)

**Source:** [Modular Speaker Architecture for Multi-Agent Communication](https://arxiv.org/html/2506.01095)

**Key Concepts:**

1. **Pragmatic Control Language (G-code)** - Low-level speaker control
2. **Speaker Configuration Schema** - Declarative agent voice definitions
3. **Dynamic Speaker Simulation** - Runtime voice assignment
4. **Responsibility Chains** - Track which agent said what
5. **Context Drift Detection** - Identify when conversation goes off-track

**Application to Improv:**

```yaml
# speaker_config.yaml
speakers:
  - id: mc
    voice: "Aoede"
    personality: "energetic_host"
    priority: high
    interruption_policy: "yield_to_user_only"

  - id: partner
    voice: "Kore"
    personality: "supportive_scene_partner"
    priority: medium
    interruption_policy: "yield_to_user_and_mc"

  - id: audience
    voice: "Puck"
    personality: "playful_heckler"
    priority: low
    interruption_policy: "background_only"
```

---

## 7. Backchanneling and Ambient Reactions

### 7.1 What is Backchanneling?

**Source:** [What is Backchanneling? - Retell AI](https://www.retellai.com/blog/how-backchanneling-improves-user-experience-in-ai-powered-voice-agents)

**Definition (Victor Yngve, 1970):** Brief verbal/non-verbal signals that listeners provide during conversation to indicate engagement and understanding (e.g., "uh-huh", "I see", nods).

**Types of Backchannels:**

1. **Go-On Signals**
   - "uh-huh", "yeah", "mm-hmm"
   - Head nods (visual)
   - Encourage speaker to continue

2. **Do-Not-Go-On Signals**
   - "wait", "hold on"
   - Confused facial expressions
   - Request pause or clarification

**Backchannel Opportunity Points (BOPs):**
- **Acoustic triggers:** Notably low-pitch utterances
- **Timing:** Correlates with pitch drops (research from Japan)
- **Context:** End of idea/clause boundaries

### 7.2 Backchanneling Implementation for AI

**Source:** [Turn-taking and Backchannel Prediction with LLM Fusion - Amazon Science](https://www.amazon.science/publications/turn-taking-and-backchannel-prediction-with-acoustic-and-large-language-model-fusion)

**Technical Approach:**
- **Neural acoustic model** + **LLM fusion**
- **Continuous prediction** of backchannel locations
- **Real-time STT** streaming for LLM analysis

**Implementation Challenges:**

1. **Context Recognition**
   - Distinguish natural pauses (backchannel appropriate) from turn-end
   - Analyze speech patterns, breathing, intonation in **milliseconds**

2. **TTS Limitations**
   - Traditional TTS trained on **read-speech** (monologue)
   - Lacks natural backchanneling from conversational data
   - Solution: Train TTS on **improv/dialogue corpora**

3. **Cultural Adaptation**
   - Backchanneling patterns vary across cultures
   - American vs Japanese expectations differ significantly
   - Solution: Culturally-aware systems based on user demographics

### 7.3 Audience Backchanneling in Improv Context

**Application to Improv Olympics:**

**Current Approach (Text Mode):**
- **Room Agent** emits text reactions ("Someone from the audience shouts...")
- Background color changes reflect sentiment

**Proposed Audio Approach:**

```python
class AudienceBackchanneler:
    """
    Generates ambient audience reactions during improv scenes
    Reacts to scene energy, but doesn't interrupt dialogue
    """
    def __init__(self):
        self.backchannel_sounds = {
            "laughter": ["chuckle.wav", "laugh_1.wav", "laugh_2.wav"],
            "applause": ["clap_small.wav", "clap_big.wav"],
            "gasp": ["gasp_1.wav", "gasp_2.wav"],
            "groan": ["groan.wav", "disappointed.wav"],
        }
        self.last_reaction_time = 0
        self.min_interval_seconds = 3  # Don't overwhelm dialogue

    async def react_to_scene(self, scene_sentiment: float, dialogue_active: bool):
        """
        Generate audience reaction if appropriate
        Only react during pauses or low dialogue activity
        """
        if dialogue_active or time_since_last_reaction() < self.min_interval_seconds:
            return None  # Wait for opportunity

        if scene_sentiment > 0.7:
            return self.play_sound("laughter", volume=0.3)
        elif scene_sentiment < -0.3:
            return self.play_sound("groan", volume=0.2)
```

**Design Principles:**
1. **Non-intrusive:** Only during pauses (>1s silence)
2. **Ducked volume:** 20-30% of dialogue volume
3. **Sentiment-driven:** React to detected scene mood
4. **Rate-limited:** Max 1 reaction every 3 seconds

### 7.4 User Study Findings on Backchanneling

**Source:** [Robotic Backchanneling in Online Conversation Facilitation](https://ieeexplore.ieee.org/document/10309362/)

**Key Findings:**
- Younger adults perceived backchanneling robot as **kinder, more trustworthy, more accepting**
- Backchanneling increases **receptiveness** and **enjoyment** of conversation
- Especially important for **inbound systems** (user has bulk of message to convey)

**Application:** In improv, user is primary performer - backchanneling from MC/Audience validates contributions and encourages continuation.

---

## 8. Current Implementation Analysis

### 8.1 Text Mode Architecture (HTTP-Based)

**File:** `/home/jantona/Documents/code/ai4joy/app/services/turn_orchestrator.py`

**Current Pattern:**

```
User HTTP POST → TurnOrchestrator
    ↓
Singleton Runner (shared InMemoryRunner)
    ↓
Stage Manager Agent (orchestrator)
    ↓
┌──────────────────────────────────────┐
│ Sub-Agents (sequential execution)    │
├──────────────────────────────────────┤
│ 1. MC Agent (game context)           │
│ 2. Partner Agent (scene response)    │
│ 3. Room Agent (audience vibe)        │
│ 4. Coach Agent (feedback, if turn >=5)│
└──────────────────────────────────────┘
    ↓
Response parsed (PARTNER:, ROOM:, COACH:)
    ↓
Firestore update (atomic)
```

**Turn-Taking Mechanism:**
- **Sequential HTTP turns** - user waits for full multi-agent response
- **No simultaneous speech** - text-based, no audio conflicts
- **Phase transitions** tracked via `determine_partner_phase(turn_count)`
- **Coach appears** at turns 5, 10, 15+ for feedback

**Strengths:**
- ✅ Simple, proven HTTP request/response model
- ✅ Clear turn boundaries (no ambiguity)
- ✅ All agents participate every turn
- ✅ Easy to debug and monitor

**Limitations:**
- ⚠️ High latency (2-4 seconds per turn)
- ⚠️ No real-time interaction
- ⚠️ Rigid turn structure

### 8.2 Audio Mode Architecture (WebSocket-Based)

**File:** `/home/jantona/Documents/code/ai4joy/app/audio/audio_orchestrator.py`

**Current Pattern (IQS-63 Simplified):**

```
User WebSocket → AudioStreamOrchestrator
    ↓
Per-Session Runner (isolated MC agent)
    ↓
Single MC Agent (unified hosting + scene work)
    ↓
ADK run_live() (bidirectional audio streaming)
    ↓
┌──────────────────────────────────────┐
│ Push-to-Talk Flow                    │
├──────────────────────────────────────┤
│ 1. User presses talk button          │
│ 2. send_activity_start()             │
│ 3. User speaks → audio chunks        │
│ 4. User releases → send_activity_end()│
│ 5. ADK processes speech              │
│ 6. MC responds with audio + TTS      │
│ 7. turn_complete event fires         │
│ 8. AgentTurnManager increments count │
└──────────────────────────────────────┘
    ↓
Mood extraction from MC transcriptions
    ↓
WebSocket events: audio, transcription, room_vibe, turn_complete
```

**Turn-Taking Mechanism:**
- **Manual activity signals** (push-to-talk) - no automatic VAD conflicts
- **Single voice** (MC only) - no agent switching
- **Turn counting** via `AgentTurnManager`
- **Audience vibes consolidated** into MC's natural speech

**Strengths:**
- ✅ **Elegant simplicity** - one agent, one voice
- ✅ **Low latency** (~1 second response)
- ✅ **No coordination complexity** - no handoffs needed
- ✅ **Same visual feedback** as text mode (mood extraction)
- ✅ **Cost reduction** (~67% vs multi-agent design)

**Limitations:**
- ⚠️ **Single voice** - no distinct Partner or Audience voices
- ⚠️ **MC does all scene work** - no separate scene partner
- ⚠️ **Mood extraction heuristic** - relies on MC phrasing (e.g., "crowd is loving this")

### 8.3 Turn Management Implementation

**File:** `/home/jantona/Documents/code/ai4joy/app/audio/turn_manager.py`

```python
class AgentTurnManager:
    """Manages turn counting for audio sessions."""

    def __init__(self, starting_turn_count: int = 0):
        self._state = TurnState(turn_count=starting_turn_count)

    def on_turn_complete(self) -> dict:
        """Increments turn count, returns phase info"""
        self._state.turn_count += 1
        return {
            "status": "ok",
            "turn_count": self._state.turn_count,
            "phase": "phase_1",  # Always phase_1 (legacy)
            "phase_changed": False
        }
```

**Analysis:**
- ✅ **Simple, robust turn tracking**
- ✅ **Phase transitions supported** (though not functional in current IQS-63)
- ⚠️ **No agent switching logic** (intentionally removed for simplicity)

**Key Insight:** The `TurnManager` is **NOT managing multi-agent coordination**. It's purely a **turn counter** for analytics and phase tracking. The actual "who speaks when" is handled by:
- **Text mode:** Stage Manager's sequential sub-agent invocation
- **Audio mode:** Single MC agent (no switching needed)

### 8.4 Critical Gap Analysis

**What's Missing for Multi-Agent Audio?**

1. **No Distinct Agent Voices**
   - Audio mode uses single MC voice for everything
   - Partner and Audience reactions are narrated by MC, not voiced separately

2. **No Agent Handoff Protocol**
   - Text mode: Stage Manager orchestrates sub-agents sequentially
   - Audio mode: Single agent, no handoffs needed
   - **Gap:** No protocol for MC → Partner → Audience transitions in voice

3. **No Concurrent Speech Handling**
   - Push-to-talk prevents user interruptions (good!)
   - But also prevents **overlapping ambient reactions** (audience backchannels)
   - **Gap:** Need audio mixing for background audience sounds during dialogue

4. **No Priority-Based Interruption**
   - User can interrupt (manual activity signals)
   - But MC cannot be interrupted by Partner or Audience
   - **Gap:** Need priority queue for agent speech during user pauses

---

## 9. Recommended Protocol for Improv-Style Multi-Agent Dialogue

### 9.1 Design Principles

Based on research and current implementation analysis, the optimal multi-agent voice protocol should:

1. **Preserve Simplicity** - Avoid complex state machines if possible
2. **User Always Priority** - User speech interrupts all agents immediately
3. **Natural Turn-Taking** - Mimic improv comedy turn-taking (e.g., tag-outs, yes-and handoffs)
4. **Ambient Audience** - Background reactions don't block main dialogue
5. **Explicit Handoffs** - MC explicitly cues Partner (e.g., "What do you think?")
6. **Graceful Degradation** - System works even if one agent fails to respond

### 9.2 Proposed Architecture: Hybrid Floor Control

**Core Pattern: Priority-Based Event-Driven System with Explicit Handoffs**

```
┌─────────────────────────────────────────────────────────┐
│              Conversation State Manager                 │
│                                                          │
│  Current State:                                          │
│    • floor_holder: AgentType (USER | MC | PARTNER)      │
│    • activity_status: ActivityStatus (SPEAKING | SILENT)│
│    • turn_count: int                                     │
│    • phase: Phase (PHASE_1 | PHASE_2)                   │
│    • pending_handoff: Optional[AgentType]                │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                 Event Bus (Real-Time)                    │
│                                                          │
│  Events:                                                 │
│    • UserStartedSpeaking                                 │
│    • UserFinishedSpeaking(transcription)                 │
│    • AgentReceivedHandoff(agent_type)                    │
│    • AgentStartedSpeaking(agent_type, audio_stream)      │
│    • AgentFinishedSpeaking(agent_type)                   │
│    • SilenceDetected(duration_ms)                        │
│    • TurnComplete(turn_number)                           │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              Priority-Based Floor Allocation             │
│                                                          │
│  Priority Levels:                                        │
│    CRITICAL (0): User speech (always interrupts)         │
│    HIGH (1): MC Agent (primary host)                     │
│    MEDIUM (2): Partner Agent (scene partner)             │
│    LOW (3): Audience Agent (background reactions)        │
│                                                          │
│  Rules:                                                  │
│    1. User speech → all agents yield immediately         │
│    2. Higher priority can interrupt lower priority       │
│    3. Same priority → explicit handoff required          │
│    4. Background (Audience) → only during silence >2s    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                   Audio Mixer Layer                      │
│                                                          │
│  Mixing Strategy:                                        │
│    • Primary Speaker: 100% volume (User/MC/Partner)      │
│    • Background Speaker: 30% volume (Audience)           │
│    • Ducking: 50ms fade when primary starts              │
│    • Overlap Handling: Audience continues at low volume  │
└─────────────────────────────────────────────────────────┘
```

### 9.3 State Machine for Floor Control

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class AgentType(Enum):
    USER = "user"
    MC = "mc"
    PARTNER = "partner"
    AUDIENCE = "audience"

class ActivityStatus(Enum):
    SPEAKING = "speaking"
    SILENT = "silent"

@dataclass
class FloorState:
    """Current floor ownership and activity"""
    floor_holder: AgentType
    activity_status: ActivityStatus
    pending_handoff: Optional[AgentType] = None
    silence_duration_ms: int = 0

class FloorController:
    """
    Manages floor control for multi-agent improv dialogue
    Implements priority-based interruption with explicit handoffs
    """

    # Priority levels (lower number = higher priority)
    PRIORITIES = {
        AgentType.USER: 0,      # Critical - always interrupts
        AgentType.MC: 1,        # High - primary host
        AgentType.PARTNER: 2,   # Medium - scene partner
        AgentType.AUDIENCE: 3,  # Low - background only
    }

    def __init__(self):
        self.state = FloorState(
            floor_holder=AgentType.MC,  # MC starts with floor
            activity_status=ActivityStatus.SILENT
        )
        self.silence_threshold_ms = 2000  # 2s silence for audience

    def request_floor(self, requester: AgentType) -> bool:
        """
        Request permission to speak

        Returns:
            True if floor granted, False if request denied
        """
        requester_priority = self.PRIORITIES[requester]
        holder_priority = self.PRIORITIES[self.state.floor_holder]

        # User always gets floor immediately
        if requester == AgentType.USER:
            self._grant_floor(requester)
            return True

        # Higher priority can interrupt lower priority
        if requester_priority < holder_priority:
            self._grant_floor(requester)
            return True

        # Same or lower priority → check for explicit handoff
        if self.state.pending_handoff == requester:
            self._grant_floor(requester)
            return True

        # Audience can only speak during silence
        if requester == AgentType.AUDIENCE:
            if self.state.activity_status == ActivityStatus.SILENT:
                if self.state.silence_duration_ms >= self.silence_threshold_ms:
                    self._grant_floor(requester)
                    return True

        # Request denied
        return False

    def _grant_floor(self, agent: AgentType):
        """Internal: Grant floor to agent"""
        self.state.floor_holder = agent
        self.state.activity_status = ActivityStatus.SPEAKING
        self.state.pending_handoff = None
        self.state.silence_duration_ms = 0
        logger.info(f"Floor granted to {agent.value}")

    def release_floor(self, agent: AgentType):
        """Agent finished speaking, release floor"""
        if self.state.floor_holder == agent:
            self.state.activity_status = ActivityStatus.SILENT
            logger.info(f"{agent.value} released floor")

    def handoff_floor(self, current: AgentType, next_agent: AgentType):
        """Explicit handoff from current speaker to next"""
        if self.state.floor_holder == current:
            self.state.pending_handoff = next_agent
            logger.info(f"{current.value} handed off to {next_agent.value}")

    def update_silence(self, duration_ms: int):
        """Track silence duration for audience opportunities"""
        if self.state.activity_status == ActivityStatus.SILENT:
            self.state.silence_duration_ms = duration_ms
```

### 9.4 Turn-Taking Rules (Improv-Inspired)

**Rule 1: User as Priority Speaker**
- User speech detected → `send_activity_start()` → all agents yield
- User finishes → `send_activity_end()` → MC evaluates response

**Rule 2: MC as Primary Floor Holder**
- MC holds floor by default after user turns
- MC can explicitly hand off: *"[to partner] What do you think?"*
- Detected handoff phrases trigger `pending_handoff` state

**Rule 3: Partner as Scene Partner**
- Partner only speaks when:
  1. Explicitly cued by MC ("What do you think?", "Add to this...")
  2. Natural pause >1.5s after MC finishes (interpreted as invitation)
- Partner yields immediately if user or MC start speaking

**Rule 4: Audience as Background Reactors**
- Audience only speaks during silence windows (>2s)
- Audience audio is ducked to 30% volume
- Audience continues in background even if MC/Partner start speaking (but ducked further to 15%)

**Rule 5: Interruption Handling**
- User interruption → truncate current agent response, flush buffers
- MC interruption of Partner → Partner yields gracefully
- Audience never interrupts (background layer only)

### 9.5 Handoff Detection via NLP

**Challenge:** How does the system know MC is handing off to Partner?

**Solution: Handoff Phrase Detection**

```python
class HandoffDetector:
    """
    Detects explicit handoffs in MC transcriptions
    Uses regex patterns + semantic similarity
    """

    HANDOFF_PATTERNS = {
        AgentType.PARTNER: [
            r"\[to partner\]",
            r"what do you think",
            r"add to this",
            r"your turn",
            r"take it away",
            r"build on that",
        ],
        AgentType.AUDIENCE: [
            r"any suggestions",
            r"what should we",
            r"ideas from the crowd",
            r"what do you all think",
        ]
    }

    def detect_handoff(self, mc_transcription: str) -> Optional[AgentType]:
        """
        Analyze MC transcription for handoff cues

        Returns:
            AgentType if handoff detected, None otherwise
        """
        text_lower = mc_transcription.lower()

        # Check direct handoff patterns
        for agent_type, patterns in self.HANDOFF_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    logger.info(f"Handoff detected to {agent_type.value}")
                    return agent_type

        # Check semantic similarity with sentence-transformers (optional)
        # handoff_score = self.semantic_model.similarity(
        #     mc_transcription,
        #     "Pass the conversation to my scene partner"
        # )
        # if handoff_score > 0.7:
        #     return AgentType.PARTNER

        return None
```

### 9.6 Audio Mixing Strategy

**Simultaneous Speech Handling:**

```python
class MultiAgentAudioMixer:
    """
    Mixes audio from multiple agents with priority-based ducking
    Allows background audio (audience) during primary dialogue
    """

    def __init__(self):
        self.primary_gain = 1.0      # 100% volume
        self.background_gain = 0.3   # 30% volume
        self.ducked_gain = 0.15      # 15% volume (background during overlap)
        self.fade_duration_ms = 50   # Quick fade

    async def mix_frame(
        self,
        user_audio: Optional[bytes],
        mc_audio: Optional[bytes],
        partner_audio: Optional[bytes],
        audience_audio: Optional[bytes]
    ) -> bytes:
        """
        Mix audio frame from all sources with priority ducking

        Priority: user > mc > partner > audience
        """
        # Convert bytes to numpy arrays for mixing
        user_frame = self._to_numpy(user_audio) if user_audio else None
        mc_frame = self._to_numpy(mc_audio) if mc_audio else None
        partner_frame = self._to_numpy(partner_audio) if partner_audio else None
        audience_frame = self._to_numpy(audience_audio) if audience_audio else None

        # Determine primary speaker (highest priority present)
        if user_frame is not None:
            primary = user_frame
            background = [mc_frame, partner_frame, audience_frame]
        elif mc_frame is not None:
            primary = mc_frame
            background = [partner_frame, audience_frame]
        elif partner_frame is not None:
            primary = partner_frame
            background = [audience_frame]
        else:
            # Only audience speaking (background only)
            if audience_frame is not None:
                return self._to_bytes(audience_frame * self.background_gain)
            else:
                return b'\x00' * 320  # Silence frame (160 samples * 2 bytes)

        # Mix primary at full volume
        mixed = primary * self.primary_gain

        # Add background sources at ducked volume
        for bg_frame in background:
            if bg_frame is not None:
                mixed += bg_frame * self.ducked_gain

        # Normalize to prevent clipping
        max_val = np.max(np.abs(mixed))
        if max_val > 32767:  # PCM16 max
            mixed = mixed * (32767 / max_val)

        return self._to_bytes(mixed.astype(np.int16))
```

### 9.7 Silence Detection for Turn Completion

**Challenge:** How do we know when a speaker has finished their turn?

**Solution: Multi-Level Silence Detection**

```python
class SilenceDetector:
    """
    Detects silence windows for turn completion and audience opportunities
    Uses Voice Activity Detection (VAD) + semantic turn detection
    """

    def __init__(self):
        self.vad_threshold_energy = 0.02  # Voice energy threshold
        self.silence_window_ms = 1500     # 1.5s silence = turn complete
        self.audience_window_ms = 2000    # 2.0s silence = audience can speak
        self.current_silence_ms = 0
        self.last_vad_time = time.time()

    def process_audio_frame(self, audio_frame: bytes) -> dict:
        """
        Analyze audio frame for silence

        Returns:
            dict with silence_detected, duration_ms, turn_complete
        """
        # Calculate frame energy
        audio_np = np.frombuffer(audio_frame, dtype=np.int16)
        energy = np.sqrt(np.mean(audio_np.astype(float)**2))
        normalized_energy = energy / 32767.0

        # VAD: is there voice activity?
        if normalized_energy > self.vad_threshold_energy:
            # Voice detected, reset silence counter
            self.current_silence_ms = 0
            self.last_vad_time = time.time()
            return {
                "silence_detected": False,
                "duration_ms": 0,
                "turn_complete": False,
                "audience_opportunity": False
            }
        else:
            # Silence detected, increment counter
            frame_duration_ms = 20  # Assume 20ms frames (320 bytes @ 16kHz PCM16)
            self.current_silence_ms += frame_duration_ms

            turn_complete = self.current_silence_ms >= self.silence_window_ms
            audience_opportunity = self.current_silence_ms >= self.audience_window_ms

            return {
                "silence_detected": True,
                "duration_ms": self.current_silence_ms,
                "turn_complete": turn_complete,
                "audience_opportunity": audience_opportunity
            }
```

**Enhancement: Semantic Turn Detection**

For more sophisticated turn detection, use an LLM-based model:

```python
class SemanticTurnDetector:
    """
    Uses LLM to detect semantic turn completion
    More accurate than silence alone for conversational AI
    """

    async def check_turn_complete(
        self,
        transcription_stream: List[str],
        silence_duration_ms: int
    ) -> bool:
        """
        Analyze streaming transcription to detect turn completion
        Combines semantic analysis with silence duration
        """
        # Get latest transcription window (last 5 seconds)
        recent_text = " ".join(transcription_stream[-10:])

        # Check for semantic completion markers
        completion_markers = [
            "?",  # Question asked
            "!",  # Exclamation
            "...", # Trailing off
            # Sentence-ending patterns
            r"\.\s+$",  # Period followed by space
            r"right\?$",  # Tag questions
            r"okay\?$",
        ]

        for marker in completion_markers:
            if re.search(marker, recent_text):
                # Semantic marker found, check silence
                if silence_duration_ms >= 800:  # Shorter threshold with semantic cue
                    return True

        # Fallback: long silence always indicates turn completion
        if silence_duration_ms >= 1500:
            return True

        return False
```

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Goal:** Implement core floor control and priority system without audio mixing

**Tasks:**
1. **Create FloorController** (`app/audio/floor_controller.py`)
   - Priority-based floor allocation
   - Handoff detection
   - State management

2. **Extend AudioStreamOrchestrator** with multi-agent support
   - Per-session agents: MC, Partner (both with separate voices)
   - Floor controller integration
   - Event emission for floor changes

3. **Implement HandoffDetector** for MC → Partner transitions
   - Regex pattern matching
   - Integration with MC transcription events

**Success Criteria:**
- MC and Partner can take turns in voice (sequential, not simultaneous)
- Handoff cues detected and processed
- User interruption works correctly

### Phase 2: Audio Mixing (Week 3)

**Goal:** Add audio ducking for background audience reactions

**Tasks:**
1. **Create MultiAgentAudioMixer** (`app/audio/multi_agent_mixer.py`)
   - Priority-based volume control
   - Real-time ducking (50ms fade)
   - Frame-by-frame mixing

2. **Add Audience Agent** with ambient reactions
   - Background laughter/applause sounds
   - Triggered by sentiment detection
   - Ducked to 30% volume, 15% during dialogue

3. **Test simultaneous speech handling**
   - Audience reactions during MC/Partner dialogue
   - Volume balance verification
   - Latency measurement

**Success Criteria:**
- Audience reactions audible but not intrusive
- Smooth volume transitions (no pops/clicks)
- Primary dialogue remains clear

### Phase 3: Advanced Turn Detection (Week 4)

**Goal:** Improve turn completion detection with semantic analysis

**Tasks:**
1. **Implement SemanticTurnDetector**
   - LLM-based turn completion prediction
   - Integration with VAD silence detection
   - Adaptive thresholds

2. **Add backchannel support**
   - Detect "uh-huh", "yeah" backchannels
   - Allow without floor handoff
   - Don't interrupt primary speaker

3. **Performance optimization**
   - Reduce latency to <200ms for floor decisions
   - Parallel audio processing
   - Stream buffering

**Success Criteria:**
- Natural turn transitions (no awkward pauses)
- Backchannels work smoothly
- <200ms floor decision latency

### Phase 4: Production Hardening (Week 5-6)

**Goal:** Error handling, fallbacks, and monitoring

**Tasks:**
1. **Error handling**
   - Agent failure fallbacks (MC continues if Partner fails)
   - Audio stream recovery
   - Graceful degradation

2. **Monitoring and metrics**
   - Track floor handoff success rate
   - Measure turn completion accuracy
   - Audio quality metrics (clipping detection)

3. **A/B testing framework**
   - Single-agent mode (current IQS-63)
   - Multi-agent mode (new protocol)
   - User preference tracking

**Success Criteria:**
- System remains stable even if one agent fails
- Comprehensive metrics for optimization
- User testing validates improvements

---

## Conclusion

### Key Takeaways

1. **Audio mode already solves turn-taking elegantly** through single-agent design
2. **The challenge is NOT coordination complexity** (solved via simplicity)
3. **The opportunity is ENRICHMENT** - adding distinct voices without losing simplicity
4. **Research validates priority-based floor control** with explicit handoffs
5. **Audio mixing enables background reactions** without dialogue interruption

### Recommended Next Steps

1. **Validate user demand** - Do users want multiple voices in audio mode?
2. **Prototype Phase 1** - Test MC + Partner voice handoffs
3. **Measure improvements** - Does multi-voice improve engagement vs single MC?
4. **Iterate on UX** - Ensure natural feel, not robotic handoffs

### Open Questions

- **Is multi-agent audio worth the complexity?** Current single-MC approach is simple and works well
- **What are user expectations?** Do they want distinct voices or is MC narration sufficient?
- **Performance tradeoffs?** Will audio mixing add latency or quality degradation?

---

## Sources

Academic Research:
- [Who speaks next? Multi-party AI discussion in Murder Mystery games](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1582287/full)
- [Evaluating LLM-based Agents for Multi-Turn Conversations Survey](https://arxiv.org/pdf/2503.22458)
- [Survey of Agent Interoperability Protocols - MCP, ACP, A2A, ANP](https://arxiv.org/html/2505.02279v1)
- [Modular Speaker Architecture for Multi-Agent Communication](https://arxiv.org/html/2506.01095)
- [Interruption Handling for Conversational Robots](https://arxiv.org/html/2501.01568v1)

Floor Control:
- [Token-Passing Floor Control](https://www.usabilityfirst.com/glossary/token-passing-floor-control/)
- [Supporting Engagement and Floor Control in Hybrid Meetings](https://link.springer.com/chapter/10.1007/978-3-642-03320-9_26)
- [A Multimodal Analysis of Floor Control in Meetings](https://link.springer.com/chapter/10.1007/11965152_4)

Barge-In and Turn Detection:
- [Contextual Acoustic Barge-in Classification - Amazon Science](https://www.amazon.science/publications/contextual-acoustic-barge-in-classification-for-spoken-dialog-systems)
- [Turn Detection and Interruptions - LiveKit Docs](https://docs.livekit.io/agents/build/turns/)
- [Turn-taking and Backchannel Prediction with LLM Fusion - Amazon Science](https://www.amazon.science/publications/turn-taking-and-backchannel-prediction-with-acoustic-and-large-language-model-fusion)
- [Voice Activity Detection - Wikipedia](https://en.wikipedia.org/wiki/Voice_activity_detection)
- [Voice Activity Detection - Deepgram](https://deepgram.com/learn/voice-activity-detection)
- [Automatic Evaluation of Turn-taking Cues in Conversational Speech Synthesis](https://arxiv.org/abs/2305.17971)
- [Turn-end Estimation in Conversational Turn-taking: Roles of Context and Prosody](https://www.tandfonline.com/doi/full/10.1080/0163853X.2021.1986664)

Priority Systems:
- [Low-latency Queuing - Wikipedia](https://en.wikipedia.org/wiki/Low-latency_queuing)
- [QoS LLQ (Low Latency Queueing) on Cisco IOS](https://networklessons.com/quality-of-service/qos-llq-low-latency-queueing-cisco-ios)
- [Voice Priority Queue Scheduling System Models for VoIP](https://www.igi-global.com/article/voice-priority-queue-scheduling-system/76320)

Audio Ducking:
- [What is Audio Ducking - iZotope](https://www.izotope.com/en/learn/what-is-audio-ducking)
- [What Is Audio Ducking and How to Use It - eMastered](https://emastered.com/blog/audio-ducking)
- [Audio Ducking for Live Sound - HARMAN Professional](https://pro.harman.com/insights/harman-pro/what-is-ducking-and-how-can-it-help-you-sound-better-live/)

Event-Driven Architecture:
- [An Event Driven Model for Dialogue Systems](https://www.researchgate.net/publication/221488934_An_event_driven_model_for_dialogue_systems)
- [Event-Driven Architecture Patterns - Solace](https://solace.com/event-driven-architecture-patterns/)
- [Design Patterns for Event-Driven Systems - Medium](https://dbaltor.medium.com/design-patterns-for-event-driven-systems-aa409d789519)
- [Event-Driven Architecture - GeeksforGeeks](https://www.geeksforgeeks.org/event-driven-architecture-system-design/)
- [4 Event-Driven Architecture Patterns - Ably](https://ably.com/topic/event-driven-architecture-patterns)

Backchanneling:
- [What is Backchanneling? - Retell AI](https://www.retellai.com/blog/how-backchanneling-improves-user-experience-in-ai-powered-voice-agents)
- [What is Backchanneling in AI Voice Agents? - Vaanix](https://vaanix.ai/blog/what-is-backchanneling-in-ai-voice-agents)
- [Back-Channeling as a Conversational Strategy - Rime Labs](https://www.rime.ai/blog/back-channeling-as-a-conversational-strategy/)
- [Backchannel Behavior Influences Perceived Personality - Frontiers](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2022.835298/full)
- [Robotic Backchanneling in Online Conversation Facilitation](https://ieeexplore.ieee.org/document/10309362/)

Improv and Dialogue Systems:
- [You Are an AI. Yes, and I Also Do Improv Comedy - USC Viterbi](https://magazine.viterbi.usc.edu/fall-2020/features/you-are-an-ai-yes-and-i-also-do-improv-comedy/)
- [New Chatbot Project Turns Conversational AI into Improv Performance - Voicebot.ai](https://voicebot.ai/2020/07/17/new-chatbot-project-turns-conversational-ai-into-an-improv-performance/)
- [Improbotics - Theatre lab and AI improv pioneers](https://improbotics.org/)
- [DialogLab: Authoring, Simulating, and Testing Dynamic Human-AI Group Conversations](https://dl.acm.org/doi/10.1145/3746059.3747696)

State Machines:
- [State Machine Based Human-Bot Conversation Model](https://link.springer.com/chapter/10.1007/978-3-030-49435-3_13)
- [Conversational State Machines - Medium](https://solyarisoftware.medium.com/dialoghi-come-macchine-a-stati-41bb748fd5b0)
- [State Machine & Dialog Systems - Meta-Guide](https://meta-guide.com/dialog-systems/state-machine-dialog-systems)
- [Full-Duplex Spoken Dialogue Model](https://www.emergentmind.com/topics/full-duplex-spoken-dialogue-model)

Voice Assistants:
- [Managing Interruptions - Voiceflow](https://docs.voiceflow.com/docs/interruption-behavior)
- [Understand Context-Aware Interruption Handling - Yellow.ai](https://docs.yellow.ai/docs/cookbooks/voice-as-channel/usecases/interrupthandling)
- [Voice Pipeline Configuration - Vapi](https://docs.vapi.ai/customization/voice-pipeline-configuration)
- [The Next Evolution in Voice Assistants: AI-Powered Turn Detection](https://theten.ai/blog/voice-assistant-with-ten-turn-detection)

Multi-Speaker Systems:
- [Experiences of Multi-Speaker Dialogue System for Vehicular Information Retrieval](https://link.springer.com/chapter/10.1007/0-387-22979-5_4)
- [Multi-Party Conversational Agents: A Survey](https://arxiv.org/html/2505.18845v1)
- [How Agents Talk: Multi-Agent Communication Protocols - Medium](https://medium.com/software-architecture-in-the-age-of-ai/how-agents-talk-mapping-the-future-of-multi-agent-communication-protocols-6115ea083dba)

---

**End of Research Report**
