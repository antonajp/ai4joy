# LiveKit Multi-Stream Room Architecture for Multi-Agent Voice Applications

**Research Date:** December 1, 2025
**Researcher:** Claude Code Research Agent
**Context:** Multi-agent improv application requiring simultaneous AI voice streaming (MC, Partner, Audience agents)

---

## Executive Summary

LiveKit is an excellent fit for multi-agent voice applications requiring simultaneous audio broadcasting. Unlike Google ADK's Live API, LiveKit's architecture natively supports **multiple AI agents publishing separate audio tracks to a single room**, with each participant (human or AI) capable of independent audio streaming. The platform combines WebRTC's low-latency transport with a comprehensive Agents framework specifically designed for AI voice applications.

**Key Findings:**
- ✅ Multiple AI agents can each publish separate audio tracks to a single LiveKit room
- ✅ LiveKit Agents framework provides production-ready AI voice orchestration
- ✅ Flexible client-side and server-side audio mixing options
- ✅ Built-in support for TTS integration (Google, ElevenLabs, Cartesia, etc.)
- ✅ Lower latency than traditional MCU architectures
- ✅ Open-source option for self-hosting to reduce costs

---

## 1. LiveKit Architecture for Multi-Agent Voice Applications

### 1.1 Core Architecture: SFU (Selective Forwarding Unit)

LiveKit uses an **SFU architecture** rather than an MCU (Multipoint Control Unit):

> "Similar to an MCU, a publisher need only transmit a single copy of their media streams, saving a client significant upstream bandwidth. However, an SFU trades downstream bandwidth efficiency for flexibility and scalability."

**Key Benefits for Multi-Agent Audio:**
- **Direct stream forwarding** without server-side decoding/re-encoding
- **Individual track control** - each AI agent publishes independently
- **Low latency** - minimal processing overhead
- **Flexible composition** - clients choose which tracks to render

### 1.2 Three Core Constructs

LiveKit's simple architecture consists of:

1. **Room**: A realtime session between one or more participants
2. **Participant**: Any entity (human or AI agent) in the room
3. **Track**: Audio, video, or data stream published by a participant

> "There is no limit on the number of participants in a room and each participant can publish audio, video, and data to the room."

### 1.3 Multi-Agent Publishing Model

Each AI agent in your improv application (MC, Partner, Audience) would:
- Join the room as a separate **participant**
- Publish its own **audio track** with synthesized speech
- Have a unique **identity** and **name** (e.g., "mc-agent", "partner-agent")
- Publish independently without interfering with other agents

**Example Scenario:**
```
Room: "improv-session-123"
├── Participant: "human-user" (subscribes to all agent tracks)
├── Participant: "mc-agent" (publishes MC voice track)
├── Participant: "partner-agent" (publishes Partner voice track)
└── Participant: "audience-agent" (publishes Audience reactions track)
```

---

## 2. How to Publish Multiple AI Audio Streams to a Single Room

### 2.1 LiveKit Agents Framework

LiveKit provides a dedicated **Agents Framework** designed specifically for AI voice applications:

> "The Agents framework allows you to add a Python or Node.js program to any LiveKit room as a full realtime participant."

**Key Features:**
- MCP (Model Context Protocol) support for tool integration
- Built-in test framework with judges
- Flexible STT, LLM, TTS provider integrations
- Automatic job scheduling and distribution
- Telephony integration support

### 2.2 Publishing Audio from AI Agents

Each AI agent publishes audio by:

1. **Creating an AudioSource**
   ```python
   from livekit import rtc

   # Create audio source (48kHz, mono recommended)
   audio_source = rtc.AudioSource(sample_rate=48000, num_channels=1)
   ```

2. **Publishing as a Track**
   ```python
   # Publish the audio source as a track
   track = rtc.LocalAudioTrack.create_audio_track("agent-voice", audio_source)
   await room.local_participant.publish_track(track)
   ```

3. **Pushing Audio Frames**
   ```python
   # Push PCM audio data to the source
   audio_frame = rtc.AudioFrame(data=pcm_data, sample_rate=48000, num_channels=1)
   await audio_source.capture_frame(audio_frame)
   ```

### 2.3 Agent Identity Configuration

Each agent gets a unique identity when joining:

```python
async def request_fnc(req: JobRequest):
    await req.accept(
        name="MC Agent",  # Display name
        identity="mc-agent",  # Unique identifier
        attributes={"role": "mc", "agent_type": "improv"}
    )
```

**Customization Options:**
- `name`: Participant display name (e.g., "MC Agent")
- `identity`: Unique identifier (e.g., "mc-agent-001")
- `metadata`: JSON string with custom data
- `attributes`: Key-value pairs for filtering/routing

### 2.4 Multiple Tracks Per Agent

Each agent can publish multiple tracks:

> "Each participant can publish and subscribe to as many tracks as makes sense for your application."

**Example Use Cases:**
- Main voice track + background music track
- Multiple character voices from one agent
- Voice + sound effects tracks

**Background Audio Example:**
```python
from livekit.agents.voice import BackgroundAudioPlayer

player = BackgroundAudioPlayer(
    ambient_sound=ambient_config,
    thinking_sound=thinking_config
)

await player.start(room=room, agent_session=session)
```

---

## 3. Client-Side vs Server-Side Mixing Options

### 3.1 Client-Side Mixing (Default)

**How It Works:**
- Each AI agent publishes a separate audio track
- Web client receives all tracks independently
- Browser's Web Audio API mixes tracks together

**Advantages:**
- Individual volume control per agent
- Spatial audio possibilities (panning agents left/right/center)
- No additional server processing
- Maximum flexibility

**LiveKit Implementation:**
```javascript
// Client-side with Web Audio API mixing
const roomOptions = {
  webAudioMix: true,  // Enable Web Audio mixing
  // OR provide custom AudioContext
  webAudioMix: {
    audioContext: customAudioContext
  }
};
```

**Bandwidth Consideration:**
> "A user subscribed to camera feeds of five others would pull down five individual video streams... you have complete control over every individual audio and video track."

For your 3-agent improv app, the client receives 3 separate audio streams.

### 3.2 Server-Side Mixing (Optional)

**How It Works:**
- Use LiveKit Egress to record/mix streams server-side
- Produce a single mixed audio output
- Reduce client bandwidth requirements

**Use Cases:**
- Recording sessions with pre-mixed audio
- Mobile clients with limited bandwidth
- Broadcasting to non-WebRTC destinations

**Implementation:**
```python
# Server-side mixing via Egress
from livekit import api

egress_request = api.RoomCompositeEgressRequest(
    room_name="improv-session-123",
    audio_only=True,
    file_outputs=[...],
    options=api.RoomCompositeOptions(
        audio_mixing=True  # Enable server-side mixing
    )
)
```

**Cost:**
- Audio-only egress: $0.004-$0.005 per minute

### 3.3 Hybrid Approach

**Best for Improv Application:**
1. **Client-side mixing** for live performance (low latency, spatial control)
2. **Server-side recording** for post-session playback (single mixed file)

### 3.4 Subscription Control

Fine-grained control over which tracks to receive:

```javascript
// Subscribe to specific agents only
room.on('trackPublished', (track, publication, participant) => {
  if (participant.identity === 'mc-agent' ||
      participant.identity === 'partner-agent') {
    track.subscribe();  // Only subscribe to these agents
  }
});
```

> "Implementations seeking fine-grained control can enable or disable tracks at their discretion."

---

## 4. Integration Complexity vs Google ADK Live API

### 4.1 Architecture Comparison

| Aspect | LiveKit | Google ADK Live API |
|--------|---------|---------------------|
| **Multi-Agent Support** | Native - each agent is a participant | Limited - designed for single agent |
| **Audio Track Publishing** | Multiple independent tracks | Single bidirectional stream |
| **Transport** | WebRTC (industry standard) | WebSocket-based |
| **Infrastructure Control** | Open-source, self-hostable | Google Cloud only |
| **TTS Integration** | 10+ providers (modular) | Gemini-focused |
| **Programming Language** | Python, Node.js, Go, Rust | Python (primarily) |
| **Turn Detection** | Custom transformer model | Built-in VAD |

### 4.2 Multi-Agent Audio: Key Difference

**Google ADK Live API:**
- Designed for **single AI agent** ↔ **single user** conversations
- Bidirectional audio stream (one agent at a time)
- Multi-agent would require complex workarounds

> "With bidi-streaming mode, you can provide end users with the experience of natural, human-like voice conversations, including the ability for the user to interrupt the agent's responses."

**LiveKit:**
- Designed for **N participants** in a room (including multiple AI agents)
- Each agent publishes independently
- Native support for simultaneous speakers

> "To test audio capabilities in your app, you can simulate simultaneous speakers to the room. The `lk load-test --room test-room --audio-publishers 5` command simulates 5 concurrent speakers."

### 4.3 Integration Complexity

**LiveKit Advantages:**
- ✅ **Simpler for multi-agent**: Each agent is just another participant
- ✅ **Better separation**: Each agent's code runs independently
- ✅ **Flexible TTS**: Mix different TTS providers per agent
- ✅ **Built-in orchestration**: Agent dispatch and load balancing

**ADK Live API Advantages:**
- ✅ **Tighter Gemini integration**: Optimized for Gemini models
- ✅ **Simpler for single agent**: Less infrastructure overhead

### 4.4 Migration Path from ADK

If currently using Google ADK Live API:

1. **Replace single agent connection** with multiple LiveKit agents
2. **Convert WebSocket** to WebRTC client SDK
3. **Separate TTS calls** into individual agent participants
4. **Update client** to handle multiple audio tracks

**Estimated Migration Effort:**
- Backend: 2-3 days (restructure as separate agents)
- Frontend: 1-2 days (integrate LiveKit client SDK)
- Testing: 1 day (multi-agent coordination)

---

## 5. Cost and Latency Considerations

### 5.1 LiveKit Cloud Pricing

**Connection Fee:**
- **$0.0005/minute per participant** (scales down with volume)
- Includes AI agents and human users
- Free for upstream bandwidth (only pay for downstream)

**Bandwidth:**
- **$0.12/GB downstream** (reduced from $0.18)
- Upstream is **free**
- Audio-only bandwidth is minimal

**Egress (Recording/Mixing):**
- **$0.004-$0.005/minute** for audio-only
- Shared minutes included in plans (60-8,000)

**Example Cost for Improv Session:**
```
Scenario: 1 user + 3 AI agents, 30-minute session

Connection: 4 participants × 30 min × $0.0005 = $0.06
Bandwidth: ~10 MB (audio) × $0.12/GB = ~$0.001
Recording: 30 min × $0.005 = $0.15

Total: ~$0.21 per session
```

### 5.2 Self-Hosting Option

> "LiveKit is free if you self-host. The managed cloud version is paid, but includes a free tier... Both LiveKit's media server and Agents framework are completely open source."

**Self-Hosting Benefits:**
- **Free infrastructure** (only pay for compute/bandwidth)
- **Full control** over deployment
- **No per-minute fees**

**Self-Hosting Costs:**
- Server compute (e.g., $50-200/month for moderate usage)
- Bandwidth (typically cheaper than managed)
- Maintenance overhead

### 5.3 Latency Profile

**LiveKit Latency Characteristics:**

> "At its core, LiveKit uses WebRTC to enable low-latency, peer-to-peer, or server-routed communication. The SFU routes media streams directly from publishers to multiple subscribers without decoding or re-encoding, keeping latency low."

**Typical Latencies:**
- **WebRTC transport**: 50-150ms (depending on network)
- **SFU processing**: <10ms (minimal overhead)
- **Total end-to-end**: 100-200ms (lower than MCU architectures)

**Multi-Stream Impact:**
> "LiveKit supports thousands of concurrent users with minimal latency and consistent quality."

Multiple audio streams do **not** add significant latency since they're forwarded independently.

### 5.4 Latency Optimization Features

**Preemptive Generation:**
> "Preemptive generation allows the agent to begin generating a response before the user's end of turn is committed... helping reduce perceived response delay."

**Instant Connect:**
> "The instant connect feature reduces perceived connection time by capturing microphone input before the agent connection is established."

**WHIP Ingress:**
> "By default, WHIP ingress sessions forward incoming audio and video media unmodified from the source to LiveKit clients. This behavior allows the lowest possible end to end latency."

### 5.5 Cost Comparison: LiveKit vs ADK

| Cost Factor | LiveKit | Google ADK Live API |
|-------------|---------|---------------------|
| **Connection** | $0.0005/min/participant | Included in Gemini API costs |
| **Bandwidth** | $0.12/GB (downstream only) | Included |
| **TTS** | Pay per provider (e.g., $0.015/1K chars for ElevenLabs) | Included with Gemini |
| **Infrastructure** | Optional self-hosting (free) | Google Cloud only |
| **Multi-Agent** | Linear scaling (4× cost for 4 agents) | Not designed for multi-agent |

**For Multi-Agent Improv App:**
- **LiveKit is more cost-effective** if using competitive TTS providers
- **Self-hosting LiveKit** eliminates connection fees
- **ADK** may be cheaper for single-agent scenarios with Gemini TTS

---

## 6. TTS Integration Examples

### 6.1 Supported TTS Providers

LiveKit Agents framework supports **10+ TTS providers**:

| Provider | Latency | Voice Quality | Cost (approx) | Notes |
|----------|---------|---------------|---------------|-------|
| **ElevenLabs** | Low | Excellent | $0.15-0.30/1K chars | Best quality, SSML support |
| **Cartesia** | Very Low | Excellent | $0.05/1K chars | Optimized for realtime |
| **OpenAI TTS** | Low | Very Good | $0.015/1K chars | Good value |
| **Google TTS** | Medium | Good | $0.016/1K chars | Wide language support |
| **Azure TTS** | Medium | Good | $0.016/1K chars | Enterprise integration |
| **Deepgram** | Low | Good | $0.015/1K chars | Fast synthesis |

### 6.2 ElevenLabs Integration (Recommended for Quality)

**Installation:**
```bash
pip install livekit-plugins-elevenlabs
```

**Configuration:**
```python
from livekit.plugins import elevenlabs

# Configure ElevenLabs TTS
tts = elevenlabs.TTS(
    model="eleven_turbo_v2_5",  # Low-latency model
    api_key="your-api-key",
    voice="21m00Tcm4TlvDq8ikWAM",  # Rachel voice
    enable_ssml=True,  # For pronunciation control
    auto_mode=True  # Reduces latency
)

# Use in VoicePipelineAgent
agent = VoicePipelineAgent(
    tts=tts,
    # ... other config
)
```

**Advanced SSML for Pronunciation:**
```python
text = '''
<speak>
    Welcome to <phoneme alphabet="ipa" ph="ˈɪmprɑv">improv</phoneme> night!
</speak>
'''
```

### 6.3 Google TTS Integration

**Installation:**
```bash
pip install livekit-plugins-google
```

**Configuration:**
```python
from livekit.plugins import google

tts = google.TTS(
    language="en-US",
    voice="en-US-Neural2-F",
    credentials_info={...}  # GCP credentials
)
```

### 6.4 Multiple TTS Providers Per Agent

**Different voices for different agents:**
```python
# MC Agent - ElevenLabs professional voice
mc_tts = elevenlabs.TTS(voice="professional-male")

# Partner Agent - Cartesia conversational voice
partner_tts = cartesia.TTS(voice="friendly-female")

# Audience Agent - Google synthesized crowd
audience_tts = google.TTS(voice="en-US-Wavenet-A")
```

### 6.5 Aligned Transcription Feature

**ElevenLabs** supports aligned transcription forwarding:

> "ElevenLabs TTS supports aligned transcription forwarding, which improves transcription synchronization in your frontend. Set `use_tts_aligned_transcript=True` in your AgentSession configuration."

**Benefit:**
Synchronize text captions with spoken audio for better UX.

---

## 7. Code Examples for Multi-Agent Implementation

### 7.1 Basic Multi-Agent Setup

```python
from livekit import rtc, api
from livekit.agents import JobRequest, WorkerOptions, cli
from livekit.plugins import elevenlabs, cartesia, google

# MC Agent
async def mc_agent_entry(ctx: JobContext):
    await ctx.connect()

    # Configure MC with professional voice
    mc_tts = elevenlabs.TTS(voice="professional-male", model="eleven_turbo_v2_5")

    agent = VoicePipelineAgent(
        tts=mc_tts,
        chat_ctx=ChatContext(
            instructions="You are the MC of an improv show. Introduce acts and engage the audience."
        )
    )

    agent.start(ctx.room)
    await agent.say("Welcome to tonight's improv show!")

# Partner Agent
async def partner_agent_entry(ctx: JobContext):
    await ctx.connect()

    # Configure Partner with conversational voice
    partner_tts = cartesia.TTS(voice="friendly-female")

    agent = VoicePipelineAgent(
        tts=partner_tts,
        chat_ctx=ChatContext(
            instructions="You are an improv partner. React to the MC and user inputs creatively."
        )
    )

    agent.start(ctx.room)

# Audience Agent
async def audience_agent_entry(ctx: JobContext):
    await ctx.connect()

    # Configure Audience with varied voices
    audience_tts = google.TTS(voice="en-US-Wavenet-A")

    agent = VoicePipelineAgent(
        tts=audience_tts,
        chat_ctx=ChatContext(
            instructions="You are the audience. Provide reactions, laughter, and applause."
        )
    )

    agent.start(ctx.room)
    await agent.say("*applause*")

# Worker configuration for MC
mc_worker = Worker(
    WorkerOptions(
        entrypoint_fnc=mc_agent_entry,
        request_fnc=lambda req: req.accept(name="MC Agent", identity="mc-agent")
    )
)

# Similar for partner and audience workers
```

### 7.2 Multi-Agent Dispatch

```python
from livekit import api

# Create room and dispatch all agents
async def create_improv_session(room_name: str):
    # Create room
    room_api = api.RoomServiceClient()
    room = await room_api.create_room(api.CreateRoomRequest(name=room_name))

    # Dispatch MC agent
    await room_api.create_dispatch(api.CreateDispatchRequest(
        room=room_name,
        agent_name="mc-agent-worker",
        metadata='{"role": "mc"}'
    ))

    # Dispatch Partner agent
    await room_api.create_dispatch(api.CreateDispatchRequest(
        room=room_name,
        agent_name="partner-agent-worker",
        metadata='{"role": "partner"}'
    ))

    # Dispatch Audience agent
    await room_api.create_dispatch(api.CreateDispatchRequest(
        room=room_name,
        agent_name="audience-agent-worker",
        metadata='{"role": "audience"}'
    ))

    return room
```

### 7.3 Client-Side Track Subscription

```javascript
import { Room, RoomEvent, Track } from 'livekit-client';

const room = new Room({
  webAudioMix: true,  // Enable client-side mixing
});

// Connect to room
await room.connect(url, token);

// Handle agent audio tracks
room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
  if (track.kind === Track.Kind.Audio) {
    // Create audio element for each agent
    const audioElement = track.attach();

    // Apply spatial audio based on agent role
    if (participant.identity === 'mc-agent') {
      audioElement.style.position = 'center';
      audioElement.volume = 1.0;
    } else if (participant.identity === 'partner-agent') {
      audioElement.style.position = 'left';
      audioElement.volume = 0.9;
    } else if (participant.identity === 'audience-agent') {
      audioElement.style.position = 'right';
      audioElement.volume = 0.7;
    }

    document.body.appendChild(audioElement);
  }
});

// Active speaker detection for visual feedback
room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
  speakers.forEach(speaker => {
    console.log(`${speaker.identity} is speaking`);
    // Update UI to highlight active agent
  });
});
```

### 7.4 Background Audio for Ambient Effects

```python
from livekit.agents.voice import BackgroundAudioPlayer, BuiltinAudioClip

async def add_background_music(ctx: JobContext):
    # Add ambient improv show music
    player = BackgroundAudioPlayer(
        ambient_sound="/path/to/improv-theme.mp3",
        thinking_sound=BuiltinAudioClip.AMBIENT_DRONE  # For transitions
    )

    await player.start(
        room=ctx.room,
        agent_session=session,
        track_publish_options=rtc.TrackPublishOptions(
            name="background-music",
            source=rtc.TrackSource.SOURCE_MICROPHONE
        )
    )
```

### 7.5 Agent Handoff Pattern

```python
from livekit.agents import Agent, AgentSession

async def improv_handoff_example(ctx: JobContext):
    session = AgentSession()

    # Start with MC introducing
    mc_agent = Agent(
        instructions="Introduce the improv session and hand off to partner."
    )
    session.add_agent(mc_agent)

    # Define handoff function
    @mc_agent.on_function_call("handoff_to_partner")
    async def handoff(args):
        # Remove MC from active
        session.remove_agent(mc_agent)

        # Add Partner agent
        partner_agent = Agent(
            instructions="Continue the improv scene."
        )
        session.add_agent(partner_agent)

        return {"success": True, "message": "Handed off to Partner"}

    await session.start()
```

---

## 8. Recommended Architecture for Multi-Agent Improv App

### 8.1 Proposed System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        LiveKit Cloud / Self-Hosted          │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ MC Agent    │  │Partner Agent│  │Audience Agent│          │
│  │ Worker      │  │ Worker      │  │ Worker       │          │
│  │             │  │             │  │              │          │
│  │ ElevenLabs  │  │ Cartesia    │  │ Google TTS   │          │
│  │ TTS         │  │ TTS         │  │              │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘          │
│         │                │                │                   │
│         └────────────────┴────────────────┘                   │
│                          │                                    │
│                   ┌──────▼──────┐                            │
│                   │ LiveKit SFU │                            │
│                   │  (Room)     │                            │
│                   └──────┬──────┘                            │
└──────────────────────────┼─────────────────────────────────┘
                           │
                           │ WebRTC
                           │
                   ┌───────▼────────┐
                   │  Web Client    │
                   │                │
                   │  ┌──────────┐  │
                   │  │ MC Audio │  │
                   │  ├──────────┤  │
                   │  │Partner Au│  │
                   │  ├──────────┤  │
                   │  │Audience A│  │
                   │  └──────────┘  │
                   │                │
                   │ Web Audio API  │
                   │   Mixing       │
                   └────────────────┘
```

### 8.2 Technology Stack

**Backend (Agent Workers):**
- **Language**: Python 3.10+
- **Framework**: LiveKit Agents SDK
- **TTS Providers**:
  - MC: ElevenLabs (professional voice)
  - Partner: Cartesia (conversational, low latency)
  - Audience: Google TTS (varied voices, cost-effective)
- **LLM**: OpenAI GPT-4 or Anthropic Claude (for agent intelligence)
- **STT**: Deepgram Nova-2 (for user input)

**Frontend (Web Client):**
- **SDK**: livekit-client (JavaScript/TypeScript)
- **Framework**: React or Vue.js
- **Audio**: Web Audio API for mixing/spatial effects
- **UI**: Real-time agent activity visualization

**Infrastructure:**
- **Option A**: LiveKit Cloud (managed, $0.0005/min/participant)
- **Option B**: Self-hosted on AWS/GCP (free software, pay for compute)

### 8.3 Deployment Strategy

**Phase 1: Prototype (Week 1-2)**
- Deploy single room with 3 agent workers
- Use LiveKit Cloud free tier
- Basic client with simple audio playback

**Phase 2: Enhancement (Week 3-4)**
- Add spatial audio positioning
- Implement agent coordination logic
- Add visual feedback for active speakers

**Phase 3: Production (Week 5-6)**
- Evaluate self-hosting vs cloud costs
- Optimize TTS provider selection
- Add recording/playback features
- Implement load balancing

### 8.4 Key Implementation Decisions

**1. Client-Side Mixing (Recommended)**
- Lower latency for live improv
- Individual volume/pan control per agent
- Better user experience

**2. Separate Agent Workers**
- Independent scaling per agent type
- Different TTS providers optimized per role
- Easier debugging and monitoring

**3. Agent Coordination via Metadata**
- Use participant metadata for turn-taking
- Implement custom signaling for handoffs
- Store improv context in room metadata

**4. Recording for Playback**
- Server-side egress for mixed recording
- Save individual agent tracks separately
- Post-production editing capabilities

---

## 9. Comparison Matrix: LiveKit vs Google ADK Live API

| Criterion | LiveKit | Google ADK Live API | Winner |
|-----------|---------|---------------------|--------|
| **Multi-Agent Support** | Native - unlimited participants | Single agent design | ✅ LiveKit |
| **Separate Audio Tracks** | Yes - each agent publishes independently | No - single bidirectional stream | ✅ LiveKit |
| **Latency** | 100-200ms (WebRTC/SFU) | ~150-300ms (WebSocket) | ✅ LiveKit |
| **TTS Flexibility** | 10+ providers, mix and match | Gemini-focused | ✅ LiveKit |
| **Self-Hosting** | Yes - fully open source | No - Google Cloud only | ✅ LiveKit |
| **Cost for Multi-Agent** | $0.0005/min × 4 = $0.002/min | Not designed for multi-agent | ✅ LiveKit |
| **Client SDKs** | All platforms (Web, iOS, Android, etc.) | Python, limited client support | ✅ LiveKit |
| **Gemini Integration** | Supported via plugin | Native | ⚖️ Tie |
| **Turn Detection** | Custom transformer model | Built-in VAD | ⚖️ Tie |
| **Learning Curve** | Moderate (WebRTC knowledge helpful) | Low (simpler for single agent) | ⚖️ ADK |
| **Production Readiness** | Powers ChatGPT Advanced Voice Mode | Production-ready reference impl | ⚖️ Tie |
| **Interruption Handling** | Built-in with semantic turn detection | Native support | ⚖️ Tie |

**Overall Recommendation for Multi-Agent Improv App:** **LiveKit**

---

## 10. Next Steps & Implementation Roadmap

### Week 1: Setup & Proof of Concept
- [ ] Set up LiveKit Cloud account (or self-hosted server)
- [ ] Install LiveKit Agents SDK: `pip install livekit-agents[openai,elevenlabs,deepgram]`
- [ ] Create first agent worker (MC)
- [ ] Test basic audio publishing to room
- [ ] Build minimal web client with livekit-client

### Week 2: Multi-Agent Development
- [ ] Implement Partner and Audience agent workers
- [ ] Configure different TTS voices per agent
- [ ] Set up agent dispatch system
- [ ] Test simultaneous audio streaming from 3 agents
- [ ] Implement client-side audio mixing

### Week 3: Coordination & Intelligence
- [ ] Add agent coordination logic (turn-taking)
- [ ] Implement improv scene context sharing via metadata
- [ ] Add active speaker detection UI
- [ ] Configure LLM prompts for each agent role
- [ ] Test agent interruption handling

### Week 4: Polish & Optimization
- [ ] Add spatial audio positioning (MC center, Partner left, Audience right)
- [ ] Implement volume balancing
- [ ] Add background music/effects track
- [ ] Optimize TTS latency (enable auto_mode, preemptive generation)
- [ ] Add visual feedback for agent activity

### Week 5: Production Features
- [ ] Set up server-side recording (Egress)
- [ ] Implement session playback
- [ ] Add user authentication and room management
- [ ] Configure monitoring and logging
- [ ] Load testing with multiple concurrent rooms

### Week 6: Deployment
- [ ] Evaluate costs: LiveKit Cloud vs self-hosting
- [ ] Deploy to production (cloud or self-hosted)
- [ ] Set up CI/CD pipeline
- [ ] Document agent configuration
- [ ] Create user documentation

---

## 11. Key Takeaways

1. **LiveKit is purpose-built for multi-agent voice applications**
   - Each AI agent joins as a participant and publishes audio independently
   - No architectural limitations on simultaneous speakers

2. **Superior to ADK Live API for multi-agent scenarios**
   - ADK is designed for single agent ↔ single user
   - LiveKit natively supports N agents + M users in one room

3. **Flexible TTS integration**
   - Mix and match providers (ElevenLabs for MC, Cartesia for Partner, Google for Audience)
   - Easy to swap providers without major code changes

4. **Low latency and high scalability**
   - WebRTC + SFU architecture keeps latency under 200ms
   - Scales to thousands of concurrent users
   - Powers ChatGPT's Advanced Voice Mode

5. **Client-side mixing offers best UX for improv**
   - Individual volume/pan control per agent
   - Spatial audio possibilities
   - Lower latency than server-side mixing

6. **Cost-effective with self-hosting option**
   - LiveKit Cloud: $0.002/min for 4 participants
   - Self-hosted: Free software, pay only for infrastructure
   - Much cheaper than per-token pricing for multi-agent

7. **Production-ready with extensive tooling**
   - Built-in agent dispatch and load balancing
   - Comprehensive SDKs for all platforms
   - Active speaker detection, turn handling, interruption support

8. **Migration from ADK is straightforward**
   - Convert single agent to multiple LiveKit participants
   - Replace WebSocket with WebRTC client SDK
   - Separate TTS calls into individual agents
   - Estimated effort: 4-6 days

---

## 12. Additional Resources

### Official Documentation
- [LiveKit Agents Framework](https://docs.livekit.io/agents/)
- [Building Voice Agents](https://docs.livekit.io/agents/build/)
- [Agent Speech and Audio](https://docs.livekit.io/agents/build/audio/)
- [Rooms, Participants, and Tracks](https://docs.livekit.io/home/get-started/api-primitives/)
- [LiveKit Client SDKs](https://docs.livekit.io/home/client/)

### Integration Guides
- [ElevenLabs TTS Plugin](https://docs.livekit.io/agents/integrations/tts/elevenlabs/)
- [Google AI Integration](https://docs.livekit.io/agents/integrations/google/)
- [Text-to-Speech Models](https://docs.livekit.io/agents/models/tts/)

### Tutorials & Examples
- [Building Multi-Agent Conversations with WebRTC & LiveKit](https://dev.to/cloudx/building-multi-agent-conversations-with-webrtc-livekit-48f1)
- [Voice AI Quickstart](https://docs.livekit.io/agents/quickstart/)
- [LiveKit Agents GitHub Repository](https://github.com/livekit/agents)
- [Python SDKs](https://github.com/livekit/python-sdks)

### Performance & Pricing
- [LiveKit Pricing](https://livekit.io/pricing)
- [Understanding LiveKit Cloud Pricing](https://kb.livekit.io/articles/3947254704-understanding-livekit-cloud-pricing)
- [Benchmarking](https://docs.livekit.io/home/self-hosting/benchmark/)
- [Quotas and Limits](https://docs.livekit.io/home/cloud/quotas-and-limits/)

### Community & Support
- [LiveKit Discord Community](https://livekit.io/discord)
- [LiveKit GitHub Discussions](https://github.com/livekit/livekit/discussions)
- [LiveKit Blog](https://blog.livekit.io/)

---

## Sources

1. [Realtime media | LiveKit docs](https://docs.livekit.io/home/client/tracks/)
2. [LiveKit SFU | LiveKit docs](https://docs.livekit.io/reference/internals/livekit-sfu/)
3. [Rooms, participants, and tracks | LiveKit docs](https://docs.livekit.io/home/get-started/api-primitives/)
4. [Subscribing to tracks | LiveKit docs](https://docs.livekit.io/home/client/tracks/subscribe/)
5. [Camera & microphone | LiveKit docs](https://docs.livekit.io/home/client/tracks/publish/)
6. [GitHub - livekit/agents](https://github.com/livekit/agents)
7. [LiveKit Agents | LiveKit docs](https://docs.livekit.io/agents/)
8. [Building voice agents | LiveKit docs](https://docs.livekit.io/agents/build/)
9. [AI voice agents | LiveKit Docs](https://docs.livekit.io/agents/voice-agent/)
10. [Voice AI quickstart | LiveKit docs](https://docs.livekit.io/agents/start/voice-ai/)
11. [GitHub - livekit/node-sdks](https://github.com/livekit/node-sdks)
12. [GitHub - livekit/python-sdks](https://github.com/livekit/python-sdks)
13. [Processing raw media tracks | LiveKit docs](https://docs.livekit.io/home/client/tracks/raw-tracks/)
14. [ElevenLabs integration guide | LiveKit Docs](https://docs.livekit.io/agents/integrations/elevenlabs/)
15. [ElevenLabs TTS plugin guide | LiveKit docs](https://docs.livekit.io/agents/integrations/tts/elevenlabs/)
16. [Text-to-speech (TTS) models | LiveKit docs](https://docs.livekit.io/agents/integrations/tts/)
17. [Agent speech and audio | LiveKit docs](https://docs.livekit.io/agents/build/audio/)
18. [Building Multi-Agent Conversations with WebRTC & LiveKit](https://dev.to/cloudx/building-multi-agent-conversations-with-webrtc-livekit-48f1)
19. [Benchmarking | LiveKit docs](https://docs.livekit.io/home/self-hosting/benchmark/)
20. [LiveKit Can Handle Millions of Concurrent Calls](https://medium.com/@BeingOttoman/livekit-can-handle-millions-of-concurrent-calls-crazy-1f2517165e04)
21. [RoomCompositeOptions | LiveKit JS Server SDK](https://docs.livekit.io/reference/server-sdk-js/interfaces/RoomCompositeOptions.html)
22. [Managing participants | LiveKit docs](https://docs.livekit.io/home/server/managing-participants/)
23. [Google AI and LiveKit | LiveKit docs](https://docs.livekit.io/agents/integrations/google/)
24. [Bidi-streaming (live) in ADK](https://google.github.io/adk-docs/streaming/)
25. [RealTime AI Agents frameworks comparison](https://medium.com/@ggarciabernardo/realtime-ai-agents-frameworks-bb466ccb2a09)
26. [livekit.agents.voice.background_audio API documentation](https://docs.livekit.io/reference/python/v1/livekit/agents/voice/background_audio.html)
27. [Pricing | LiveKit](https://livekit.io/pricing)
28. [Understanding LiveKit Cloud Pricing](https://kb.livekit.io/articles/3947254704-understanding-livekit-cloud-pricing)
29. [Job lifecycle | LiveKit docs](https://docs.livekit.io/agents/server/job/)
30. [Participant attributes and metadata | LiveKit docs](https://docs.livekit.io/home/client/state/participant-attributes/)
