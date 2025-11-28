# Real-Time Conversational Audio Architecture Analysis
## Improv Olympics - Google ADK Implementation

**Version**: 1.0
**Date**: 2025-11-27
**Status**: Planning Phase

---

## Executive Summary

This document provides a comprehensive technical architecture analysis for adding real-time conversational audio capabilities to the Improv Olympics application using Google ADK's Live API. The analysis covers architectural decisions, implementation phases, ADK-specific patterns, and risk mitigation strategies.

### Key Recommendations

1. **Same Repository Approach**: Keep audio implementation in the same repository with modular separation
2. **Dual-Mode Architecture**: Support both text and audio modes with shared agent logic
3. **WebSocket Layer**: Add WebSocket endpoints alongside existing REST API
4. **ADK Live API Integration**: Use `InMemoryRunner` with Live API speech settings for real-time streaming
5. **Phased Implementation**: 5-phase rollout with incremental feature delivery

---

## Table of Contents

1. [Current Architecture Analysis](#1-current-architecture-analysis)
2. [Target Architecture for Real-Time Audio](#2-target-architecture-for-real-time-audio)
3. [ADK Version & API Compatibility](#3-adk-version--api-compatibility)
4. [Architectural Decisions](#4-architectural-decisions)
5. [Implementation Phases](#5-implementation-phases)
6. [Technical Design Details](#6-technical-design-details)
7. [Risk Assessment & Mitigations](#7-risk-assessment--mitigations)
8. [Performance & Cost Considerations](#8-performance--cost-considerations)
9. [Testing Strategy](#9-testing-strategy)
10. [Appendix: Code Examples](#10-appendix-code-examples)

---

## 1. Current Architecture Analysis

### 1.1 Existing Components

**Backend Stack:**
- FastAPI 0.118.0+ with REST endpoints
- ADK 1.19.0+ with text-based agents
- Singleton `Runner` with `run_async()` for turn-based execution
- `DatabaseSessionService` for SQLite-backed session persistence
- Firestore for rate limiting and session metadata
- OAuth 2.0 session middleware (httponly cookies)
- OpenTelemetry observability with Cloud Trace

**Agent Architecture:**
```python
# Current pattern (text-based)
Agent(
    name="mc_agent",
    model=settings.vertexai_flash_model,  # gemini-2.0-flash
    instruction=MC_SYSTEM_PROMPT,
    tools=[ImprovGamesToolset]
)

# Execution pattern (turn-based)
async for event in runner.run_async(
    user_id=user_id,
    session_id=session_id,
    new_message=new_message
):
    # Process text responses
```

**Session Management:**
- `SessionManager` handles Firestore session state
- `DatabaseSessionService` manages ADK conversation history (SQLite)
- Turn-based execution with atomic Firestore updates
- State includes: phase, turn_count, conversation_history

**Current Limitations for Real-Time Audio:**
1. REST-only architecture (no WebSocket support)
2. Turn-based execution model (not streaming)
3. No audio input/output handling
4. No speech configuration in agents
5. Session state assumes synchronous turns

---

## 2. Target Architecture for Real-Time Audio

### 2.1 Live API Capabilities

Google ADK Live API provides:
- **Bidirectional Streaming**: Simultaneous audio input and output
- **Automatic Speech Detection**: End-of-speech detection with configurable sensitivity
- **Speech Synthesis**: Multiple voice options, language selection
- **Low Latency**: Sub-second response times for interactive conversation
- **Multi-Modal Input**: Audio, text, and images in the same stream

### 2.2 Reference Implementation Patterns

Based on `realtime-conversational-agent` sample:

```python
# Live API with speech configuration
from google.genai import types

live_config = {
    "speech_config": {
        "voice_config": {
            "prebuilt_voice_config": {
                "voice_name": "Aoede"  # Or Puck, Charon, Kore, Fenrir, Kore
            }
        },
        "language": "en-US"
    },
    "response_modalities": ["AUDIO"],
    "input_audio_transcription": True  # Get text transcription of user audio
}

# WebSocket streaming pattern
async def websocket_handler(websocket: WebSocket):
    await websocket.accept()

    # Bidirectional streaming
    async def send_audio():
        async for chunk in client.stream():
            await websocket.send_bytes(chunk.audio)

    async def receive_audio():
        while True:
            data = await websocket.receive_bytes()
            await client.send_audio(data)

    await asyncio.gather(send_audio(), receive_audio())
```

### 2.3 Proposed Dual-Mode Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Improv Olympics Backend                      │
│                                                                   │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │   REST API       │              │  WebSocket API   │         │
│  │   (Text Mode)    │              │  (Audio Mode)    │         │
│  │                  │              │                  │         │
│  │ POST /session/   │              │ WS /audio/       │         │
│  │   {id}/turn      │              │   {session_id}   │         │
│  └────────┬─────────┘              └────────┬─────────┘         │
│           │                                 │                    │
│           └────────────┬────────────────────┘                    │
│                        │                                         │
│              ┌─────────▼──────────┐                              │
│              │  Shared Agent Core │                              │
│              │                    │                              │
│              │  - MC Agent        │                              │
│              │  - Partner Agent   │                              │
│              │  - Room Agent      │                              │
│              │  - Coach Agent     │                              │
│              │  - Stage Manager   │                              │
│              └─────────┬──────────┘                              │
│                        │                                         │
│              ┌─────────▼──────────┐                              │
│              │   Session Layer    │                              │
│              │                    │                              │
│              │ - DatabaseSession  │ (ADK SQLite)                 │
│              │ - SessionManager   │ (Firestore metadata)         │
│              │ - MemoryService    │ (ADK RAG)                    │
│              └─────────┬──────────┘                              │
│                        │                                         │
│              ┌─────────▼──────────┐                              │
│              │  ADK Runner        │                              │
│              │                    │                              │
│              │ Text: run_async()  │                              │
│              │ Audio: Live API    │                              │
│              └─────────┬──────────┘                              │
│                        │                                         │
└────────────────────────┼─────────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  Vertex AI   │
                  │  Gemini 2.0  │
                  └──────────────┘
```

---

## 3. ADK Version & API Compatibility

### 3.1 Current ADK Version Analysis

**Installed**: `google-adk>=1.19.0`

**Key ADK Components Available:**
- ✅ `google.adk.agents.Agent` - Agent definition
- ✅ `google.adk.runners.Runner` - Execution engine with `run_async()`
- ✅ `google.adk.sessions.DatabaseSessionService` - Session persistence
- ✅ `google.adk.memory.VertexAiRagMemoryService` - Cross-session memory
- ⚠️  **Live API**: Need to verify if ADK 1.19.0+ supports Live API or requires direct `google-genai` integration

### 3.2 Live API Integration Options

**Option A: ADK Native Live API (if supported)**
```python
# If ADK 1.19.0+ has native Live API support
from google.adk.live import LiveRunner

live_runner = LiveRunner(
    agent=agent,
    speech_config=speech_config,
    session_service=session_service
)

async for event in live_runner.stream(session_id=session_id):
    # Handle audio events
```

**Option B: Direct google-genai Live API** (more likely for ADK 1.19.0)
```python
# Use google-genai Live API directly alongside ADK agents
from google.genai import live

# Reuse agent instruction and tools, but execute via Live API
live_client = live.LiveClient(
    model="gemini-2.0-flash",
    config=live_config
)

# Manual session management coordination with ADK DatabaseSessionService
```

### 3.3 Required Investigation

Before implementation, verify:

1. **ADK Live API Support**: Check ADK 1.19.0+ release notes for Live API integration
2. **Speech Configuration**: How to pass `speech_config` to ADK agents
3. **Streaming Events**: Event format differences between `run_async()` and Live API
4. **Session Compatibility**: Can `DatabaseSessionService` handle real-time streaming sessions?

**Action Item**: Research ADK documentation and test Live API compatibility in sandbox environment.

---

## 4. Architectural Decisions

### 4.1 Decision 1: Same Repository vs Separate Repository

**Recommendation**: ✅ **Same Repository** with modular separation

**Rationale:**

| Aspect | Same Repo | Separate Repo |
|--------|-----------|---------------|
| Code Reuse | ✅ Share agents, session logic, models | ❌ Duplicate or use shared libraries |
| Maintenance | ✅ Single deployment pipeline | ❌ Coordinate two pipelines |
| Testing | ✅ Unified test suite | ❌ Two test suites |
| Version Sync | ✅ Guaranteed compatibility | ❌ Version drift risk |
| Initial Complexity | ⚠️  Moderate refactoring needed | ✅ Clean slate |
| Future Scaling | ✅ Can split later if needed | ❌ Harder to merge back |

**Implementation Pattern:**
```
app/
├── routers/
│   ├── sessions.py          # Text REST endpoints
│   └── audio_sessions.py    # WebSocket audio endpoints
├── services/
│   ├── turn_orchestrator.py         # Text turn execution
│   ├── audio_stream_orchestrator.py # Audio stream execution
│   └── agent_factory.py             # Shared agent creation
├── agents/
│   ├── mc_agent.py          # Shared agent logic
│   └── partner_agent.py     # Works in both modes
└── models/
    ├── text_session.py      # Text-specific models
    └── audio_session.py     # Audio-specific models
```

### 4.2 Decision 2: Agent Reuse Strategy

**Recommendation**: ✅ **Shared Agent Instructions with Mode-Specific Execution**

**Pattern:**
```python
# agents/mc_agent.py (shared)
MC_SYSTEM_PROMPT = """You are the MC for Improv Olympics..."""

def create_mc_agent(mode: str = "text") -> Agent:
    """Create MC agent for text or audio mode"""
    agent = Agent(
        name="mc_agent",
        instruction=MC_SYSTEM_PROMPT,
        tools=[ImprovGamesToolset],
        model=settings.vertexai_flash_model
    )
    return agent

# services/audio_stream_orchestrator.py
async def execute_audio_stream(session_id: str, websocket: WebSocket):
    # Get shared agent
    mc_agent = create_mc_agent(mode="audio")

    # Execute with Live API (not run_async)
    live_client = create_live_client(agent=mc_agent)
    await stream_audio(live_client, websocket, session_id)
```

**Benefits:**
- Same personality and rules across modes
- Maintain consistency in coaching, sentiment analysis
- Single source of truth for improv principles
- Easier A/B testing of prompt changes

**Mode-Specific Differences:**
- **Audio Mode**: May need additional instructions for pacing, verbal cues
- **Text Mode**: Can use markdown, structured formatting
- **Audio Voice Selection**: Different agents could have different voices (MC = enthusiastic, Coach = calm)

### 4.3 Decision 3: WebSocket Architecture

**Recommendation**: ✅ **Add WebSocket alongside REST, not replace**

**Implementation:**
```python
# app/main.py
from fastapi import FastAPI, WebSocket

app = FastAPI()

# Existing REST endpoints
app.include_router(sessions.router)  # Text mode

# New WebSocket endpoint
@app.websocket("/ws/audio/{session_id}")
async def audio_session_websocket(websocket: WebSocket, session_id: str):
    # WebSocket handler for audio streaming
    await audio_stream_orchestrator.handle_websocket(websocket, session_id)
```

**Coexistence Strategy:**
- REST endpoints remain unchanged
- WebSocket shares same authentication middleware (OAuth session cookies)
- Session state synchronized between modes (Firestore + DatabaseSessionService)
- User can switch modes mid-session (future enhancement)

### 4.4 Decision 4: Session State Management

**Recommendation**: ✅ **Hybrid State Model**

**Current (Text Mode):**
```python
# Turn-based updates
await session_manager.update_session_atomic(
    session_id=session_id,
    turn_data=turn_data,
    new_phase=new_phase,
    new_status=new_status
)
```

**Audio Mode Addition:**
```python
# Real-time state updates for audio
class AudioSessionState:
    session_id: str
    audio_chunks_received: int
    audio_chunks_sent: int
    transcription_buffer: List[str]
    current_speaker: str  # "user" | "agent"
    speech_start_time: datetime

    # Sync with Firestore periodically, not per-chunk
    async def sync_to_firestore(self):
        # Batch update every N seconds or on significant events
        pass
```

**Key Differences:**
- **Text Mode**: Atomic updates per turn (every message)
- **Audio Mode**: Streaming state with periodic snapshots
- **Shared State**: Phase, turn_count, conversation_history remain compatible

### 4.5 Decision 5: Deployment Strategy

**Recommendation**: ✅ **Single Cloud Run Service with Both Modes**

**Rationale:**
- Cloud Run supports WebSocket connections (with proper configuration)
- Same instance can handle REST and WebSocket (FastAPI supports both)
- Simplified deployment and scaling
- Shared session service and database connections

**Configuration:**
```yaml
# cloudbuild.yaml additions
env:
  - ENABLE_AUDIO_MODE=true
  - MAX_WEBSOCKET_CONNECTIONS=100
  - AUDIO_STREAM_TIMEOUT=300  # 5 minutes per audio session
```

**Alternative** (if Cloud Run WebSocket limits are hit):
- Separate Cloud Run service for audio
- Share Firestore, DatabaseSessionService, and ADK agents
- Coordinate session state via Firestore

---

## 5. Implementation Phases

### Phase 1: ADK Live API Research & Proof of Concept (1-2 weeks)

**Objectives:**
- Verify ADK 1.19.0+ Live API compatibility
- Create minimal WebSocket echo server
- Test audio streaming with Gemini Live API
- Validate session persistence with DatabaseSessionService

**Deliverables:**
1. **Research Document**: ADK Live API capabilities and limitations
2. **PoC Code**: Simple audio echo WebSocket endpoint
3. **Test Results**: Audio latency, transcription accuracy
4. **Decision**: Finalize ADK integration approach (Option A or B from §3.2)

**Tasks:**
```bash
# 1. Create PoC branch
git checkout -b IQS-XX-audio-poc

# 2. Add WebSocket test endpoint
# app/routers/audio_poc.py
@app.websocket("/ws/test")
async def test_websocket(websocket: WebSocket):
    await websocket.accept()
    # Test audio streaming

# 3. Test with simple client
# tests/test_audio_poc.py
async def test_audio_stream():
    # Send audio, receive audio, verify transcription
```

**Success Criteria:**
- [ ] Audio successfully streamed bidirectionally
- [ ] Transcription received in real-time
- [ ] Session state persisted to DatabaseSessionService
- [ ] Latency < 1 second for simple responses

---

### Phase 2: Core Audio Infrastructure (2-3 weeks)

**Objectives:**
- Implement production WebSocket handler
- Add authentication to WebSocket endpoint
- Create `AudioStreamOrchestrator` service
- Integrate with existing session management

**Architecture:**
```
app/services/audio_stream_orchestrator.py
├── AudioStreamOrchestrator
│   ├── handle_websocket() -> Entry point
│   ├── initialize_live_session() -> Create Live API client
│   ├── stream_audio_to_client() -> Send agent audio
│   ├── receive_audio_from_user() -> Process user audio
│   └── sync_session_state() -> Update Firestore/DatabaseService
```

**Key Files:**
```python
# app/routers/audio_sessions.py
@router.websocket("/ws/audio/{session_id}")
async def audio_session_stream(
    websocket: WebSocket,
    session_id: str,
    # How to pass OAuth session cookie in WebSocket?
    # Options: Query param token, upgrade from HTTP request
):
    # Authenticate user
    user_info = await authenticate_websocket(websocket)

    # Verify session ownership
    session = await session_manager.get_session(session_id)
    if session.user_id != user_info["user_id"]:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    # Execute audio stream
    orchestrator = AudioStreamOrchestrator(session_manager)
    await orchestrator.handle_websocket(websocket, session, user_info)
```

**Authentication Pattern:**
```python
# WebSocket authentication options:

# Option A: Token in query params (generated from OAuth session)
# GET /ws/audio/{session_id}?token=<short-lived-jwt>

# Option B: Cookie in WebSocket upgrade handshake
# Use Starlette's cookie parser on upgrade request

# Recommendation: Option A for WebSocket-specific auth
async def create_websocket_token(user_id: str) -> str:
    # Create short-lived JWT (5 min expiry)
    # Signed with SESSION_SECRET_KEY
    # Validated in websocket handler
```

**Tasks:**
1. Create `AudioStreamOrchestrator` service
2. Implement WebSocket authentication flow
3. Add Live API client initialization
4. Test with simple agent (MC welcome message)
5. Add error handling and reconnection logic

**Success Criteria:**
- [ ] WebSocket connection authenticated via OAuth-derived token
- [ ] Audio streaming works end-to-end
- [ ] Session state synchronized with Firestore
- [ ] Graceful handling of disconnections

---

### Phase 3: Agent Integration (2-3 weeks)

**Objectives:**
- Integrate MC Agent with audio streaming
- Add Partner Agent audio responses
- Implement Room Agent audio feedback
- Configure voice selection per agent

**Voice Selection Strategy:**
```python
AGENT_VOICE_CONFIG = {
    "mc_agent": {
        "voice_name": "Aoede",  # Enthusiastic, energetic
        "language": "en-US"
    },
    "partner_agent": {
        "voice_name": "Puck",  # Playful, versatile
        "language": "en-US"
    },
    "coach_agent": {
        "voice_name": "Kore",  # Calm, supportive
        "language": "en-US"
    },
    "room_agent": {
        # Room might not speak, just provide text sentiment
        # Or use crowd-like voice for audience reactions
        "voice_name": "Charon",
        "language": "en-US"
    }
}
```

**Multi-Agent Coordination:**
```python
# Challenge: Stage Manager orchestrates 3+ agents in text mode
# In audio mode, need sequential audio responses

async def execute_audio_turn(session, user_audio_input):
    # 1. Partner responds (audio)
    partner_response = await partner_agent.respond_audio(user_audio_input)
    await send_audio(partner_response, label="PARTNER")

    # 2. Room provides vibe (could be text overlay or brief audio)
    room_vibe = await room_agent.analyze(user_audio_input, partner_response)
    await send_metadata(room_vibe)  # Send as JSON, not audio

    # 3. Coach provides feedback (audio, if turn >= 15)
    if should_coach_provide_feedback(turn_number):
        coach_feedback = await coach_agent.provide_feedback_audio()
        await send_audio(coach_feedback, label="COACH")
```

**Tasks:**
1. Extend `create_*_agent()` functions to support Live API configuration
2. Implement audio-specific prompts (pacing, verbal cues)
3. Test multi-agent audio sequencing
4. Add audio response labeling (PARTNER, COACH, etc.)

**Success Criteria:**
- [ ] All agents produce audio responses
- [ ] Voice selection reflects agent personality
- [ ] Multi-agent coordination works in audio mode
- [ ] Responses are naturally paced for speech

---

### Phase 4: Production Features (2-3 weeks)

**Objectives:**
- Add speech detection configuration
- Implement reconnection and recovery
- Add audio session metrics and observability
- Optimize for Cloud Run deployment

**Speech Detection Configuration:**
```python
# Adjust sensitivity for improv context
# Users may pause for thinking, don't cut them off too quickly
live_config = {
    "speech_config": {
        "end_of_speech_sensitivity": "MEDIUM",  # Balance responsiveness vs interruption
        "silence_duration_ms": 2000,  # 2 seconds of silence before considering speech ended
        "input_audio_transcription": True
    }
}
```

**Reconnection Strategy:**
```python
# Handle network interruptions gracefully
class AudioSessionState:
    last_sync_time: datetime
    audio_buffer: List[AudioChunk]

    async def recover_from_disconnection(self):
        # Restore session state from DatabaseSessionService
        # Replay missed audio chunks if within buffer window
        # Resume conversation context
```

**Observability:**
```python
# Extend OpenTelemetry for audio metrics
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("audio_stream_session") as span:
    span.set_attribute("session_id", session_id)
    span.set_attribute("audio_chunks_received", chunks_received)
    span.set_attribute("audio_chunks_sent", chunks_sent)
    span.set_attribute("stream_duration_seconds", duration)
```

**Tasks:**
1. Implement reconnection logic with state recovery
2. Add audio-specific Cloud Trace spans
3. Create audio session dashboard (Cloud Monitoring)
4. Test with poor network conditions
5. Optimize Cloud Run configuration for WebSocket

**Success Criteria:**
- [ ] Reconnections preserve conversation context
- [ ] Audio metrics visible in Cloud Monitoring
- [ ] Speech detection tuned for natural conversation
- [ ] WebSocket connections scale to 100+ concurrent users

---

### Phase 5: Testing & Deployment (1-2 weeks)

**Objectives:**
- Comprehensive testing of audio mode
- Deploy to staging environment
- Beta testing with real users
- Production deployment

**Testing Strategy:**
1. **Unit Tests**: Audio session state, WebSocket handlers
2. **Integration Tests**: End-to-end audio streaming
3. **Load Tests**: Concurrent WebSocket connections
4. **User Acceptance Tests**: Real improv sessions with audio

**Deployment Checklist:**
```bash
# 1. Update Cloud Run configuration
gcloud run services update improv-olympics \
  --region us-central1 \
  --cpu-boost \  # Faster cold starts for WebSocket
  --max-instances 10 \
  --timeout 300  # 5 min for audio sessions

# 2. Add environment variables
ENABLE_AUDIO_MODE=true
MAX_WEBSOCKET_CONNECTIONS=100

# 3. Update firewall rules (if needed)
# Ensure WebSocket upgrade requests allowed

# 4. Deploy with gradual rollout
# 25% -> 50% -> 100% traffic
```

**Success Criteria:**
- [ ] All tests passing (unit, integration, load)
- [ ] Beta users successfully complete audio sessions
- [ ] No regressions in text mode
- [ ] Monitoring confirms <1s audio latency

---

## 6. Technical Design Details

### 6.1 WebSocket Protocol Design

**Message Types:**
```python
# Client -> Server
{
    "type": "audio_chunk",
    "data": "<base64-encoded-pcm>",
    "sequence": 123,
    "timestamp": "2025-11-27T12:00:00Z"
}

{
    "type": "text_input",  # Fallback if audio fails
    "text": "User's typed message",
    "timestamp": "2025-11-27T12:00:00Z"
}

# Server -> Client
{
    "type": "audio_response",
    "agent": "PARTNER",
    "data": "<base64-encoded-audio>",
    "transcription": "Optional text transcription",
    "timestamp": "2025-11-27T12:00:00Z"
}

{
    "type": "metadata",
    "event": "speech_started" | "speech_ended" | "transcription",
    "data": {...}
}

{
    "type": "room_vibe",
    "analysis": "Audience is engaged...",
    "mood_metrics": {...}
}

{
    "type": "error",
    "code": "AUDIO_ERROR",
    "message": "Failed to process audio",
    "recoverable": true
}
```

### 6.2 Session State Synchronization

**Problem**: Real-time audio creates many state changes (chunks, transcriptions), but Firestore updates should be atomic and infrequent.

**Solution**: Hybrid state with periodic syncing

```python
class AudioSessionStateManager:
    def __init__(self, session_id: str, session_manager: SessionManager):
        self.session_id = session_id
        self.session_manager = session_manager
        self.in_memory_state = {
            "audio_chunks_received": 0,
            "audio_chunks_sent": 0,
            "transcription_buffer": [],
            "last_sync": datetime.now(timezone.utc)
        }

    async def increment_chunk_count(self, direction: str):
        """Update in-memory counter, sync periodically"""
        if direction == "received":
            self.in_memory_state["audio_chunks_received"] += 1
        else:
            self.in_memory_state["audio_chunks_sent"] += 1

        # Sync every 30 seconds or every 100 chunks
        if self._should_sync():
            await self.sync_to_firestore()

    def _should_sync(self) -> bool:
        chunks_total = (
            self.in_memory_state["audio_chunks_received"] +
            self.in_memory_state["audio_chunks_sent"]
        )
        time_since_sync = datetime.now(timezone.utc) - self.in_memory_state["last_sync"]

        return chunks_total >= 100 or time_since_sync.total_seconds() >= 30

    async def sync_to_firestore(self):
        """Periodic sync to Firestore for durability"""
        await self.session_manager.update_audio_session_metrics(
            session_id=self.session_id,
            audio_chunks_received=self.in_memory_state["audio_chunks_received"],
            audio_chunks_sent=self.in_memory_state["audio_chunks_sent"]
        )
        self.in_memory_state["last_sync"] = datetime.now(timezone.utc)
```

### 6.3 Error Handling & Recovery

**Error Categories:**

1. **Network Errors** (recoverable)
   - WebSocket disconnection
   - Audio packet loss
   - **Recovery**: Reconnection with state restoration

2. **Audio Processing Errors** (degradable)
   - Speech recognition failure
   - Audio codec issues
   - **Recovery**: Fall back to text mode, request user to repeat

3. **Agent Errors** (same as text mode)
   - VertexAI timeout
   - Rate limit exceeded
   - **Recovery**: Existing retry logic, exponential backoff

**Implementation:**
```python
async def handle_audio_stream_error(error: Exception, session_id: str):
    if isinstance(error, WebSocketDisconnect):
        logger.warning("WebSocket disconnected", session_id=session_id)
        # Clean up resources, mark session as "interrupted"
        await cleanup_audio_session(session_id)

    elif isinstance(error, AudioProcessingError):
        logger.error("Audio processing failed", session_id=session_id, error=str(error))
        # Send error message to client
        await websocket.send_json({
            "type": "error",
            "message": "Audio processing failed. Please try speaking again or switch to text mode.",
            "recoverable": True
        })

    elif isinstance(error, asyncio.TimeoutError):
        logger.error("Agent timeout in audio mode", session_id=session_id)
        # Same as text mode timeout handling
        await websocket.send_json({
            "type": "error",
            "message": "Agent response timed out. Please try again.",
            "recoverable": True
        })
```

### 6.4 Rate Limiting for Audio Mode

**Challenge**: Audio sessions consume more resources (WebSocket, Live API calls, longer sessions)

**Strategy**: Separate rate limits for audio

```python
# config.py additions
rate_limit_daily_audio_sessions: int = 5  # Lower than text (10)
rate_limit_concurrent_audio_sessions: int = 1  # Only 1 audio session at a time

# services/rate_limiter.py
async def check_audio_session_limit(user_id: str):
    """Separate quota for audio sessions"""
    daily_audio_count = await get_daily_audio_session_count(user_id)
    concurrent_audio = await get_concurrent_audio_sessions(user_id)

    if daily_audio_count >= settings.rate_limit_daily_audio_sessions:
        raise RateLimitExceeded("Daily audio session limit reached")

    if concurrent_audio >= settings.rate_limit_concurrent_audio_sessions:
        raise RateLimitExceeded("Only one audio session allowed at a time")
```

---

## 7. Risk Assessment & Mitigations

### 7.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| ADK 1.19.0 lacks native Live API support | Medium | High | Use direct `google-genai` Live API, coordinate with ADK manually |
| WebSocket stability on Cloud Run | Low | Medium | Enable Cloud Run WebSocket support, test under load, implement reconnection |
| Audio latency > 2 seconds | Medium | High | Use Gemini 2.0 Flash (lowest latency model), optimize audio chunk size |
| DatabaseSessionService incompatible with streaming | Low | High | Create separate audio session table if needed, sync to DatabaseSessionService periodically |
| Speech detection too sensitive/insensitive | Medium | Low | Make detection parameters configurable, gather user feedback |

### 7.2 Cost Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Live API costs 2-3x text API | High | Medium | Implement stricter rate limits for audio, monitor costs closely |
| WebSocket connections increase Cloud Run costs | Medium | Low | Set max instance limits, implement connection timeout (5 min) |
| Long audio sessions exhaust quota | Low | Medium | Hard limit on audio session duration (15 minutes), warn users |

### 7.3 User Experience Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Poor audio quality on user's device | Medium | Medium | Provide audio quality diagnostics, fallback to text mode |
| Multi-agent coordination feels unnatural in audio | Medium | High | Careful prompt engineering for audio pacing, beta testing |
| Users prefer text mode | Low | Low | Keep both modes available, don't force audio |

---

## 8. Performance & Cost Considerations

### 8.1 Expected Latency

**Target**: <1 second from user speech end to agent audio start

**Latency Breakdown:**
- Speech detection (user stops speaking): 200-500ms
- Audio encoding/network: 50-100ms
- Gemini Live API processing: 300-700ms
- Audio response generation: 200-400ms
- Audio decoding/playback: 50-100ms

**Total**: ~800-1800ms (under 2 seconds)

**Optimization Strategies:**
1. Use Gemini 2.0 Flash (lowest latency)
2. Minimize audio chunk size (lower buffering)
3. Pre-warm WebSocket connections (reduce cold start)
4. Use Cloud Run CPU boost for faster cold starts

### 8.2 Cost Projections

**Text Mode (Current):**
- Gemini Flash API: $0.075 per 1M input tokens, $0.30 per 1M output tokens
- Average session: ~5,000 tokens total = $0.0019 per session
- 10 users × 10 sessions/day = 100 sessions/day = $5.70/month

**Audio Mode (Estimated):**
- Gemini Live API: ~2-3x text API costs (based on OpenAI Realtime pricing as reference)
- Average audio session: 10 minutes = ~$0.006-0.01 per session
- Conservative estimate: 5 users × 5 audio sessions/day = 25 sessions/day = $4.50-7.50/month

**Total Projected Cost:**
- Text mode: $5.70/month
- Audio mode: $7.50/month
- **Total**: ~$13.20/month (well under $200 budget)

**Note**: Actual Live API pricing may differ; monitor during PoC phase.

### 8.3 Scalability Limits

**Cloud Run WebSocket Limits:**
- Max concurrent connections per instance: 1000 (Cloud Run default)
- Max instances: Configurable (suggest 10 for pilot)
- Connection timeout: 5 minutes recommended (vs Cloud Run max 60 minutes)

**Recommended Capacity Planning:**
- 50 users (pilot)
- 5 audio sessions/day per user = 250 audio sessions/day
- Average session duration: 10 minutes
- Peak concurrent sessions: ~10-15 (assuming 3-hour peak window)

**Cloud Run Configuration:**
```yaml
resources:
  limits:
    cpu: 2
    memory: 2Gi
autoscaling:
  minScale: 1  # Keep 1 instance warm
  maxScale: 10
  targetConcurrentRequests: 50  # Conservative for WebSocket
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Scope**: Individual components in isolation

```python
# tests/test_audio/test_audio_stream_orchestrator.py
@pytest.mark.asyncio
async def test_audio_chunk_processing():
    orchestrator = AudioStreamOrchestrator(session_manager)

    # Mock audio chunk
    audio_data = base64.b64encode(b"fake_pcm_data")

    # Process chunk
    result = await orchestrator.process_audio_chunk(
        session_id="test_session",
        audio_data=audio_data
    )

    assert result["status"] == "processed"

@pytest.mark.asyncio
async def test_speech_detection_timeout():
    # Verify timeout if user doesn't speak for X seconds
    pass

@pytest.mark.asyncio
async def test_session_state_sync():
    # Verify Firestore sync happens every N chunks
    pass
```

### 9.2 Integration Tests

**Scope**: End-to-end audio streaming

```python
# tests/integration/test_audio_session_e2e.py
@pytest.mark.asyncio
async def test_full_audio_session():
    # 1. Authenticate and create session
    session_id = await create_test_session()

    # 2. Connect WebSocket
    async with connect_websocket(session_id) as ws:
        # 3. Send audio chunk
        await ws.send_bytes(test_audio_chunk)

        # 4. Receive agent audio response
        response = await ws.receive_json()
        assert response["type"] == "audio_response"
        assert response["agent"] == "PARTNER"

        # 5. Verify transcription
        assert "transcription" in response

        # 6. Verify session state updated
        session = await get_session(session_id)
        assert session.audio_chunks_received > 0
```

### 9.3 Load Tests

**Tool**: Locust (already in requirements.txt)

```python
# tests/load/locustfile_audio.py
from locust import User, task, between
import asyncio
import websockets

class AudioUser(User):
    wait_time = between(1, 3)

    @task
    def audio_session(self):
        # Simulate audio session
        asyncio.run(self._run_audio_session())

    async def _run_audio_session(self):
        uri = f"ws://{self.host}/ws/audio/test_session?token={self.token}"
        async with websockets.connect(uri) as ws:
            # Send 100 audio chunks
            for i in range(100):
                await ws.send(test_audio_chunk)
                await ws.recv()  # Wait for response
```

**Load Test Scenarios:**
1. **Baseline**: 10 concurrent audio users, 5 minute sessions
2. **Stress**: 50 concurrent users (max pilot capacity)
3. **Spike**: Sudden increase from 5 to 30 users

**Success Criteria:**
- P95 latency < 2 seconds
- 0% WebSocket disconnections
- No Cloud Run instance crashes

### 9.4 User Acceptance Testing

**Beta Testers**: 5-10 early adopters

**Test Scenarios:**
1. **Happy Path**: Complete 10-minute improv session via audio
2. **Network Interruption**: Disconnect WiFi mid-session, reconnect
3. **Audio Quality**: Test on mobile, desktop, headphones, built-in mic
4. **Multi-Agent**: Verify Coach feedback is audible and helpful
5. **Fallback**: Switch from audio to text mode mid-session

**Feedback Questions:**
- Was audio latency acceptable? (<2 seconds)
- Did agents sound natural and conversational?
- Were multi-agent responses clearly distinguished?
- Any technical issues or errors?
- Would you use audio mode over text mode?

---

## 10. Appendix: Code Examples

### 10.1 Complete WebSocket Handler Example

```python
# app/routers/audio_sessions.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.services.audio_stream_orchestrator import AudioStreamOrchestrator
from app.services.session_manager import SessionManager, get_session_manager
from app.middleware.oauth_auth import validate_websocket_token
from app.utils.logger import get_logger

router = APIRouter(prefix="/ws", tags=["audio"])
logger = get_logger(__name__)

@router.websocket("/audio/{session_id}")
async def audio_session_stream(
    websocket: WebSocket,
    session_id: str,
    token: str,  # Short-lived JWT from query param
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    WebSocket endpoint for real-time audio streaming.

    Authentication: OAuth-derived JWT token in query param
    Audio Format: PCM 16-bit, 16kHz, mono
    Protocol: Bidirectional audio chunks + metadata
    """
    try:
        # 1. Validate token and extract user info
        user_info = await validate_websocket_token(token)
        user_id = user_info["user_id"]

        logger.info("WebSocket connection initiated", session_id=session_id, user_id=user_id)

        # 2. Verify session exists and user owns it
        session = await session_manager.get_session(session_id)
        if not session:
            await websocket.close(code=1008, reason="Session not found")
            return

        if session.user_id != user_id:
            await websocket.close(code=1008, reason="Unauthorized")
            return

        # 3. Accept WebSocket connection
        await websocket.accept()
        logger.info("WebSocket accepted", session_id=session_id, user_id=user_id)

        # 4. Initialize audio stream orchestrator
        orchestrator = AudioStreamOrchestrator(
            session_manager=session_manager,
            session=session,
            user_info=user_info
        )

        # 5. Execute audio stream (blocks until session ends or disconnect)
        await orchestrator.handle_websocket(websocket, session_id)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", session_id=session_id)
        # Cleanup handled by orchestrator

    except Exception as e:
        logger.error(
            "WebSocket error",
            session_id=session_id,
            error=str(e),
            error_type=type(e).__name__
        )
        await websocket.close(code=1011, reason=f"Server error: {str(e)}")
```

### 10.2 AudioStreamOrchestrator Implementation Skeleton

```python
# app/services/audio_stream_orchestrator.py
from typing import Optional
import asyncio
from fastapi import WebSocket
from google.genai import live
from google.genai import types

from app.models.session import Session
from app.services.session_manager import SessionManager
from app.agents import create_mc_agent, create_partner_agent, create_coach_agent
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

class AudioStreamOrchestrator:
    """
    Orchestrates real-time audio streaming for improv sessions.

    Responsibilities:
    - Manage Live API client connection
    - Handle bidirectional audio streaming
    - Coordinate multi-agent responses
    - Sync session state periodically
    """

    def __init__(
        self,
        session_manager: SessionManager,
        session: Session,
        user_info: dict
    ):
        self.session_manager = session_manager
        self.session = session
        self.user_info = user_info
        self.live_client: Optional[live.LiveClient] = None
        self.audio_chunks_received = 0
        self.audio_chunks_sent = 0

    async def handle_websocket(self, websocket: WebSocket, session_id: str):
        """Main WebSocket handler for audio streaming"""
        try:
            # Initialize Live API client
            await self._initialize_live_client()

            # Run bidirectional streaming
            await asyncio.gather(
                self._stream_audio_to_client(websocket),
                self._receive_audio_from_user(websocket),
                self._periodic_state_sync(session_id)
            )

        except Exception as e:
            logger.error("Audio stream error", session_id=session_id, error=str(e))
            raise
        finally:
            await self._cleanup()

    async def _initialize_live_client(self):
        """Initialize Google Live API client with speech configuration"""
        # Determine which agent voice to use based on session phase
        # For now, use Partner agent voice as primary

        voice_config = {
            "voice_name": "Puck",  # Playful improv partner
            "language": "en-US"
        }

        live_config = {
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": voice_config
                },
                "end_of_speech_sensitivity": "MEDIUM",
                "silence_duration_ms": 2000  # 2 seconds for thinking pauses
            },
            "response_modalities": ["AUDIO"],
            "input_audio_transcription": True
        }

        # TODO: Verify ADK 1.19.0 Live API integration pattern
        # This may need adjustment based on actual ADK API
        self.live_client = live.LiveClient(
            model=settings.vertexai_flash_model,
            config=live_config
        )

        logger.info("Live API client initialized", voice=voice_config["voice_name"])

    async def _stream_audio_to_client(self, websocket: WebSocket):
        """Send agent audio responses to client"""
        async for chunk in self.live_client.stream():
            if chunk.type == "audio":
                await websocket.send_json({
                    "type": "audio_response",
                    "agent": "PARTNER",  # TODO: Determine from context
                    "data": chunk.audio_base64,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                self.audio_chunks_sent += 1

            elif chunk.type == "transcription":
                # Send transcription for debugging/accessibility
                await websocket.send_json({
                    "type": "metadata",
                    "event": "transcription",
                    "text": chunk.text
                })

    async def _receive_audio_from_user(self, websocket: WebSocket):
        """Receive user audio and send to Live API"""
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Audio chunk
                    audio_data = message["bytes"]
                    await self.live_client.send_audio(audio_data)
                    self.audio_chunks_received += 1

                elif "text" in message:
                    # JSON control message
                    control = json.loads(message["text"])
                    await self._handle_control_message(control)

    async def _handle_control_message(self, control: dict):
        """Handle client control messages (e.g., end session, switch agent)"""
        if control.get("type") == "end_session":
            logger.info("User requested session end")
            # Close Live API connection
            await self.live_client.close()

    async def _periodic_state_sync(self, session_id: str):
        """Sync session state to Firestore every 30 seconds"""
        while True:
            await asyncio.sleep(30)
            await self.session_manager.update_audio_session_metrics(
                session_id=session_id,
                audio_chunks_received=self.audio_chunks_received,
                audio_chunks_sent=self.audio_chunks_sent
            )
            logger.debug("Audio session state synced", session_id=session_id)

    async def _cleanup(self):
        """Cleanup Live API client and resources"""
        if self.live_client:
            await self.live_client.close()
        logger.info("Audio stream cleaned up")
```

### 10.3 OAuth Token Generation for WebSocket

```python
# app/middleware/oauth_auth.py additions

import jwt
from datetime import datetime, timedelta, timezone

async def create_websocket_token(user_id: str, user_email: str) -> str:
    """
    Create short-lived JWT for WebSocket authentication.

    This token is derived from the OAuth session but is separate
    from the httponly session cookie (which can't be sent via WebSocket easily).

    Args:
        user_id: Authenticated user ID from OAuth session
        user_email: User email from OAuth session

    Returns:
        JWT token valid for 5 minutes
    """
    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)

    payload = {
        "user_id": user_id,
        "user_email": user_email,
        "exp": expiry,
        "iat": datetime.now(timezone.utc),
        "aud": "improv-olympics-websocket"
    }

    token = jwt.encode(
        payload,
        settings.session_secret_key,
        algorithm="HS256"
    )

    return token

async def validate_websocket_token(token: str) -> dict:
    """
    Validate WebSocket JWT token.

    Args:
        token: JWT token from WebSocket query param

    Returns:
        User info dict with user_id and user_email

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.session_secret_key,
            algorithms=["HS256"],
            audience="improv-olympics-websocket"
        )

        return {
            "user_id": payload["user_id"],
            "user_email": payload["user_email"]
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="WebSocket token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid WebSocket token")

# Add endpoint to get WebSocket token from authenticated session
@router.get("/auth/websocket-token")
async def get_websocket_token(request: Request) -> dict:
    """
    Get short-lived WebSocket token for authenticated user.

    Requires valid OAuth session cookie.
    Returns JWT token to use in WebSocket connection.
    """
    user_info = get_authenticated_user(request)  # Validates OAuth session

    token = await create_websocket_token(
        user_id=user_info["user_id"],
        user_email=user_info["user_email"]
    )

    return {
        "token": token,
        "expires_in": 300,  # 5 minutes
        "websocket_url_template": f"/ws/audio/{{session_id}}?token={token}"
    }
```

---

## Conclusion

This architecture analysis provides a comprehensive roadmap for implementing real-time conversational audio in the Improv Olympics application using Google ADK Live API. The recommended approach is:

1. **Keep in same repository** with modular separation
2. **Reuse agent instructions** across text and audio modes
3. **Add WebSocket endpoints** alongside existing REST API
4. **Use hybrid session state** with periodic Firestore syncing
5. **Deploy to single Cloud Run service** with both modes enabled
6. **Implement in 5 phases** over 8-13 weeks

**Next Steps:**
1. Research ADK 1.19.0+ Live API compatibility (Phase 1)
2. Create proof-of-concept audio streaming endpoint
3. Validate latency and cost assumptions
4. Create Linear ticket for full implementation

**Key Success Factors:**
- Maintain consistency between text and audio agent personalities
- Ensure <2 second audio latency for natural conversation
- Keep costs under budget ($13/month projected)
- Provide seamless fallback to text mode if audio fails

This design preserves the existing ADK-first architecture while extending it to support real-time audio streaming, setting the foundation for a multimodal improv learning experience.
