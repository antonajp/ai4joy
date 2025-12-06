# Multi-Agent Real-Time Voice Synthesis Research Report

**Date:** December 1, 2025
**Context:** Multi-agent improv application with concurrent voice streams (MC, Partner, Room/Audience agents)
**Current Stack:** Gemini native TTS via ADK Live API (single-agent limitation)

---

## Executive Summary

This research evaluates TTS services and coordination patterns for multi-agent voice applications requiring concurrent, real-time voice streams. Key findings:

1. **Best Multi-Voice TTS Services:** Cartesia Sonic, ElevenLabs Multi-Context WebSocket, and LiveKit orchestration frameworks
2. **Optimal Latency:** Cartesia Sonic (~40-95ms TTFB), ElevenLabs Flash v2.5 (~75ms), Gemini Live API (~280ms)
3. **Cost-Effective Options:** Deepgram Aura-2 ($30/million chars), Cartesia Sonic ($38/million chars) vs ElevenLabs ($150/million chars)
4. **Architecture Pattern:** WebSocket-based multi-context streaming with client-side audio mixing or LiveKit WebRTC orchestration

---

## 1. TTS Services Comparison

### 1.1 Ultra-Low Latency Providers

#### **Cartesia Sonic 3** ⭐ TOP CHOICE FOR REAL-TIME
- **Latency:** 40-95ms TTFB (Turbo mode: ~40ms, Standard: ~90ms)
- **Streaming:** WebSocket and SSE APIs with instant voice cloning (3 seconds of audio)
- **Features:**
  - 15 realistic voices out-of-the-box
  - Multi-language support (15+ languages)
  - Non-verbal expressiveness: laughter, breathing, emotional inflections
  - Fine-grained prosody control
- **Pricing:** ~$38 per million characters (~73% cheaper than ElevenLabs)
- **Best For:** Real-time conversational AI, voice agents with emotion
- **Multi-Voice Support:** Voice cloning preserves unique speaking style, accent, emotion
- **API:** Developer-friendly WebSocket/SSE with instant voice cloning

**Sources:**
- [Cartesia TTS Documentation](https://docs.cartesia.ai/build-with-cartesia/models/tts)
- [Cartesia vs ElevenLabs Comparison](https://www.getlisten2it.com/tts-comparison/cartesia-vs-elevenlabs)
- [TTS Voice AI Model Guide 2025](https://layercode.com/blog/tts-voice-ai-model-guide)

---

#### **ElevenLabs** ⭐ BEST MULTI-SPEAKER API
- **Latency:** Flash v2.5: 75-150ms TTFA
- **Streaming:** Multi-Context WebSocket API for concurrent streams
- **Features:**
  - **Multi-Context WebSocket:** Multiple independent audio generation streams over single connection
  - **Multi-Voice Support:** Voice switching within single response with minimal overhead
  - **Eleven v3 Multi-Speaker:** Natural multi-speaker dialogue with dramatic delivery
  - 70+ languages, 3,000+ voices
  - Professional and instant voice cloning
- **Concurrency:** ~5 concurrent streams can support 100+ simultaneous broadcasts
- **Pricing:** ~$150 per million characters
- **Best For:** Multi-character storytelling, emotional agents, language tutoring
- **API:** Multi-context WebSocket for concurrent voice streams

**Sources:**
- [ElevenLabs Multi-Context WebSocket](https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-multi-stream-input)
- [ElevenLabs Multi-Voice Support](https://elevenlabs.io/docs/agents-platform/customization/voice/multi-voice-support)
- [ElevenLabs Models Documentation](https://elevenlabs.io/docs/models)

---

#### **Google Gemini TTS**
- **Latency:** Gemini Flash ~280ms TTFT (not as fast as Cartesia/ElevenLabs)
- **Streaming:** True streaming synthesis with progressive audio generation
- **Features:**
  - **Multi-Speaker Configuration:** `multiSpeakerVoiceConfig` with `speakerVoiceConfigs`
  - 30 built-in voices (Puck, Charon, Kore, Fenrir, Aoede, etc.)
  - 24 supported languages
  - Natural language control over style, accent, pace, tone, emotion
  - **Chirp 3 HD voices:** Low-latency real-time streaming (newer than Neural2)
- **Multi-Speaker Support:** Can assign different voices to different speakers (e.g., "Joe" = Kore, "Jane" = Puck)
- **Pricing:** Google Cloud TTS Neural2: $16/million chars, Standard: $4/million chars
- **Limitation:** Multi-speaker TTS API is separate from Live API (not available for interactive conversations)
- **Best For:** Podcast generation, audiobook narration, scripted multi-speaker content

**Current Challenge:** Gemini Live API (used in ADK) is designed for single interactive agent. Multi-speaker TTS requires separate Gemini TTS API which is batch-oriented, not real-time streaming for conversations.

**Sources:**
- [Gemini TTS Documentation](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts)
- [Gemini API Speech Generation](https://ai.google.dev/gemini-api/docs/speech-generation)
- [Real-Time Voice Detection with Vector TTS in Gemini Live API](https://www.qed42.com/insights/real-time-voice-detection-with-vector-tts-in-gemini-live-api)
- [Gemini ADK Feature Request #487](https://github.com/google/adk-docs/issues/487)

---

### 1.2 Enterprise-Grade Providers

#### **Azure Speech Services**
- **Latency:** 100-200ms TTFA (90th percentile: 135ms)
- **Streaming:** WebSocket and REST APIs with concurrent request scaling
- **Features:**
  - Neural TTS voices (140+ languages)
  - Custom Neural Voice creation
  - SSML for fine-tuning
  - Concurrent request scaling (default 200 TPS, scalable)
- **Pricing:** Neural TTS: $16/million chars, Custom Neural: $24/million chars
- **Concurrency:** Default 200 TPS (transactions per second), can increase via support request
- **Example:** 1,000 concurrent calls = ~100 TPS requirement
- **Best For:** Enterprise applications requiring reliability and global language support

**Sources:**
- [Azure Speech Services Pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/)
- [Azure Speech Service Quotas](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits)

---

#### **Deepgram Aura-2**
- **Latency:** Competitive (specific benchmarks not disclosed)
- **Pricing:** $30 per million characters (73% cheaper than ElevenLabs)
- **Features:** Lower latency and natural-sounding voices
- **Best For:** Cost-sensitive applications requiring good quality

**Sources:**
- [How to Choose STT and TTS for Voice Agents](https://softcery.com/lab/how-to-choose-stt-tts-for-ai-voice-agents-in-2025-a-comprehensive-guide)

---

### 1.3 Budget-Friendly Options

#### **Speechmatics**
- **Pricing:** $0.011 per 1K characters (~$11/million chars) - up to 27x cheaper than ElevenLabs
- **Best For:** High-volume applications with tight budgets

#### **Google Cloud TTS (Standard/Neural2)**
- **Pricing:** Standard: $4/million chars, Neural2: $16/million chars
- **Free Tier:** 1 million characters/month (WaveNet voices)
- **Features:**
  - WebSocket-based streaming (GoogleTTSService) for lowest latency
  - Chirp 3 HD voices for real-time communication
  - 100+ languages
- **Best For:** Enterprise applications requiring global language support and cost control

**Sources:**
- [Best TTS APIs in 2025](https://www.speechmatics.com/company/articles-and-news/best-tts-apis-in-2025-top-12-text-to-speech-services-for-developers)
- [Google Cloud TTS Documentation](https://cloud.google.com/text-to-speech)

---

### 1.4 Specialized Providers

#### **PlayHT 2.0 Turbo**
- **Latency:** 70ms to start streaming (users receive within 200-400ms with network costs)
- **Streaming:** gRPC and WebSocket support with input text streaming
- **Features:**
  - Seamless integration with LLM token streams
  - Voice conditioning seconds parameter for consistency
  - Seed parameter for reproducibility
- **Voice Consistency:** Good but not always consistent; some voices can sound synthetic in long-form
- **Best For:** LLM integration, fast prototyping

**Sources:**
- [PlayHT Python SDK](https://github.com/playht/pyht)
- [PlayHT Text to Speech Review](https://www.videosdk.live/developer-hub/tts/playht-text-to-speech)

---

#### **Resemble AI**
- **Latency:** Competitive (specific benchmarks not disclosed)
- **Streaming:** WebSocket API for real-time streaming (Business plan only)
- **Features:**
  - Rapid Voice Clone (10s-1min audio, ~1min processing)
  - Professional Voice Clone (10min audio, ~1hr processing)
  - Custom voice API for programmatic control
  - Speech-to-speech functionality
- **Best For:** High-quality voice cloning with emotional nuances

**Sources:**
- [Resemble AI LiveKit Plugin](https://pypi.org/project/livekit-plugins-resemble/1.2.6/)
- [Resemble AI Custom Voice API](https://www.resemble.ai/api/)

---

## 2. Multi-Voice Coordination Patterns

### 2.1 Architecture Approaches

#### **1. Multi-Context WebSocket (ElevenLabs Pattern)**
```
Application
    ↓
Single WebSocket Connection
    ↓
Multiple Contexts (MC Agent, Partner Agent, Room Agent)
    ↓
Concurrent Audio Stream Generation
    ↓
Client-Side Audio Mixing
```

**Pros:**
- Single connection reduces overhead
- Independent stream management
- Built-in concurrency support (5 concurrent streams → 100+ broadcasts)

**Cons:**
- Limited to ElevenLabs ecosystem
- Client-side mixing complexity

**Best For:** Applications needing multiple concurrent voices from single provider

**Sources:**
- [ElevenLabs Multi-Context WebSocket](https://elevenlabs.io/docs/api-reference/multi-context-text-to-speech/v-1-text-to-speech-voice-id-multi-stream-input)

---

#### **2. LiveKit WebRTC Orchestration** ⭐ RECOMMENDED FOR MULTI-AGENT
```
Multiple AI Agents (MC, Partner, Room)
    ↓
LiveKit Agents Framework (Python)
    ↓
WebRTC Media Server
    ↓
Client Browser (Low Latency)
```

**Pros:**
- Built for multi-agent voice conversations
- WebRTC handles network unpredictability
- Manages agent handoffs, shared state, interruptions
- VAD (Voice Activity Detection) built-in
- Provider-agnostic (works with any TTS API)

**Cons:**
- More complex setup than single WebSocket
- Requires LiveKit infrastructure

**Best For:** Complex multi-agent applications requiring agent coordination, state management

**Sources:**
- [Building Multi-Agent Conversations with WebRTC & LiveKit](https://dev.to/cloudx/building-multi-agent-conversations-with-webrtc-livekit-48f1)
- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)

---

#### **3. Hybrid WebRTC + WebSocket (OpenAI Pattern)**
```
Client Browser
    ↓ (WebRTC)
Relay Server
    ↓ (WebSocket)
Multiple TTS APIs (one per agent)
    ↓
Server-Side Mixing → Client
```

**Pros:**
- WebRTC handles unpredictable client networks
- WebSocket simplifies AI model interfacing
- Can use different TTS providers per agent

**Cons:**
- Additional relay server required
- More complex architecture

**Best For:** Applications needing different TTS providers per agent

**Sources:**
- [Real-Time Voice Agent Architecture](https://softcery.com/lab/ai-voice-agents-real-time-vs-turn-based-tts-stt-architecture)

---

#### **4. Google ADK Bidi-Streaming (Current Limitation)**
```
Client Browser
    ↓ (WebSocket)
FastAPI Server (ADK)
    ↓
Single Gemini Live API Session
    ↓
Single Agent Output Only
```

**Current Limitation:** Gemini Live API supports single agent. For multi-speaker, need to switch to Gemini TTS API (batch-oriented) which doesn't support real-time streaming conversations.

**ADK Auto-Transcription:** For multi-agent scenarios (agents with sub_agents), ADK automatically enables audio transcription for agent transfer functionality.

**Sources:**
- [Google ADK Custom Streaming WebSocket](https://google.github.io/adk-docs/streaming/custom-streaming-ws/)
- [Google ADK Bidi-Streaming](https://google.github.io/adk-docs/streaming/)

---

### 2.2 Audio Mixing Strategies

#### **Client-Side Mixing**
```javascript
// Mix multiple audio streams in browser
const audioContext = new AudioContext();
const gainNodes = [
  audioContext.createGain(), // MC Agent
  audioContext.createGain(), // Partner Agent
  audioContext.createGain()  // Room Agent
];

// Mix to destination
gainNodes.forEach(gain => gain.connect(audioContext.destination));
```

**Pros:** Low server cost, flexible volume control per stream
**Cons:** Client CPU usage, browser compatibility issues

---

#### **Server-Side Mixing**
```python
# Mix audio frames before sending to client
def mix_audio_frames(frames_list):
    mixed = np.zeros_like(frames_list[0])
    for frames in frames_list:
        mixed += frames
    return mixed / len(frames_list)  # Normalize
```

**Pros:** Consistent quality, single stream to client
**Cons:** Server CPU usage, added latency

**Sources:**
- [Software Mixing of Multiple Audio Streams](https://dsp.stackexchange.com/questions/72826/software-mixing-of-multiple-audio-streams-from-network)

---

### 2.3 Synchronization Patterns

#### **Master-Slave Synchronization**
- Choose master audio source (e.g., MC Agent)
- Perform cross-correlations between master and other sources
- Align secondary sources to master

**Sources:**
- [Synchronizing Multiple Real-Time Audio Streams](https://dsp.stackexchange.com/questions/61403/how-to-synchronize-multiple-real-time-audio-streams-before-mixing-them)

---

#### **Circular Buffer Pattern**
```python
# For each agent's audio stream
circular_buffer = CircularBuffer(size=optimal_latency)

# When D/A buffer runs empty:
for agent in agents:
    frame = agent.circular_buffer.read()
    mixed_frame = mix(frames)

da_buffer.write(mixed_frame)
```

**Latency vs Dropout Tradeoff:** Lower latency = higher dropout rate. Should be adaptive based on network conditions.

**Sources:**
- [Software Mixing of Multiple Audio Streams](https://dsp.stackexchange.com/questions/72826/software-mixing-of-multiple-audio-streams-from-network)

---

## 3. Voice Consistency & Identity Management

### 3.1 Voice Cloning Requirements

#### **Instant Voice Cloning (IVC)**
- **Cartesia:** 3 seconds of audio
- **ElevenLabs:** Small audio sample, quick processing
- **PlayHT:** Rapid processing
- **Resemble AI:** 10 seconds - 1 minute, ~1 minute processing

#### **Professional Voice Cloning (PVC)**
- **ElevenLabs:** More data and fine-tuning, multi-step API process
- **Resemble AI:** 10 minutes audio, ~1 hour processing, captures emotional nuances

---

### 3.2 Voice Identity Persistence

#### **Voice ID Management**
```python
# Cartesia example
voice_id = "cosyvoice-v3-plus-myvoice-xxxxxxxx"

# ElevenLabs example
voice_id = "21m00Tcm4TlvDq8ikWAM"  # Unique ID persists across sessions

# Session usage
tts_api.synthesize(
    text="Hello from MC Agent",
    voice_id=voice_id,
    session_id="improv_session_123"
)
```

**Key Providers:**
- **ElevenLabs:** Unique voice IDs, persistent across sessions
- **Cartesia:** Format `{model_name}-{prefix}-{unique_identifier}`
- **Alibaba CosyVoice:** Voice ID for cloning, use in WebSocket API
- **Hume AI:** Reference by name or ID in TTS requests

**Sources:**
- [ElevenLabs Voice Cloning](https://elevenlabs.io/docs/cookbooks/voices/instant-voice-cloning)
- [Alibaba CosyVoice API](https://www.alibabacloud.com/help/en/model-studio/cosyvoice-clone-api)
- [Hume AI Voice Cloning](https://dev.hume.ai/docs/voice/voice-cloning)

---

### 3.3 Voice Consistency Parameters

#### **PlayHT Parameters:**
- `voice_conditioning_seconds`: Control how much reference audio to pass as guide
- `seed`: Audio generation seed for reproducibility (default: random)

#### **Cartesia Parameters:**
- Voice cloning preserves: speaking style, accent, background, emotion, vocal characteristics

**Sources:**
- [PlayHT Python SDK](https://github.com/playht/pyht)

---

## 4. Cost Analysis for Production Usage

### 4.1 Pricing Comparison (Per Million Characters)

| Provider | Standard Pricing | Notes |
|----------|-----------------|-------|
| **Speechmatics** | $11 | 27x cheaper than ElevenLabs |
| **Deepgram Aura-2** | $30 | Good quality-to-cost ratio |
| **Cartesia Sonic** | $38 | 73% cheaper than ElevenLabs, ultra-low latency |
| **Azure Neural TTS** | $16 | Enterprise reliability |
| **Google Neural2** | $16 | Global language support |
| **Google Standard** | $4 | Budget option |
| **ElevenLabs** | $150 | Premium quality, highest cost |

**Free Tiers:**
- **Google Cloud TTS:** 1M chars/month (WaveNet)
- **Azure:** 500K chars/month (Neural)
- **Amazon Polly:** 5M chars/month first year (Standard)
- **ElevenLabs:** ~10K chars/month

**Sources:**
- [TTS API Pricing Comparison 2025](https://www.speechmatics.com/company/articles-and-news/best-tts-apis-in-2025-top-12-text-to-speech-services-for-developers)
- [Cartesia vs ElevenLabs Pricing](https://fish.audio/vs/elevenlabs-versus-cartesia/)

---

### 4.2 Usage Scenarios

#### **Scenario: 3-Agent Improv Show**
**Assumptions:**
- 3 agents (MC, Partner, Room) speaking concurrently
- 30-minute show = 1,800 seconds
- Average 150 words/minute per agent when speaking
- ~5 characters per word
- Each agent speaks 50% of the time

**Calculation:**
- Per agent: 30 min × 150 words/min × 0.5 = 2,250 words
- Per agent: 2,250 words × 5 chars/word = 11,250 characters
- Total (3 agents): 33,750 characters per show

**Monthly Cost (100 shows/month = 3.375M characters):**

| Provider | Cost per 100 Shows |
|----------|-------------------|
| Speechmatics | $37 |
| Deepgram | $101 |
| Cartesia | $128 |
| Azure/Google Neural | $54 |
| Google Standard | $13.50 |
| ElevenLabs | $506 |

**Recommendation:** For production with 100+ shows/month:
- **Budget:** Google Standard ($13.50/month)
- **Best Value:** Cartesia ($128/month) - best latency-to-cost ratio
- **Enterprise:** Azure/Google Neural ($54/month) - reliability + good cost

---

### 4.3 Concurrency Cost Considerations

#### **ElevenLabs Concurrency**
- 5 concurrent streams → 100 simultaneous broadcasts
- Concurrency limit depends on subscription tier
- For multi-agent: Need sufficient concurrency for parallel synthesis

#### **Azure TTS Scaling**
- Default 200 TPS (transactions per second)
- Example: 1,000 concurrent calls ≈ 100 TPS
- Scaling via support request (no direct cost impact, pay-as-you-go)

**Key Insight:** Concurrency limits affect responsiveness, not cost (pay for usage only).

**Sources:**
- [ElevenLabs Multi-Context WebSocket](https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-multi-stream-input)
- [Azure Speech Service Quotas](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits)

---

## 5. Recommended Architecture for Multi-Agent Voice

### 5.1 Option A: ElevenLabs Multi-Context (Simplest)

```
┌─────────────────────────────────────────────────┐
│          Browser Client                         │
│  ┌──────────┬──────────┬──────────┐            │
│  │ MC Audio │Partner Au│ Room Aud │            │
│  └────┬─────┴────┬─────┴────┬─────┘            │
│       └──────────┴──────────┘                   │
│         Client-Side Mixer                       │
│              │                                   │
└──────────────┼───────────────────────────────────┘
               │ WebSocket
┌──────────────┼───────────────────────────────────┐
│              ↓                                   │
│   ElevenLabs Multi-Context WebSocket API        │
│  ┌────────────┬────────────┬────────────┐       │
│  │ Context 1  │ Context 2  │ Context 3  │       │
│  │ (MC-Aoede) │ (Partner)  │(Room-Charon│       │
│  └────────────┴────────────┴────────────┘       │
└──────────────────────────────────────────────────┘
```

**Pros:**
- Single WebSocket connection
- Built-in multi-speaker support
- Natural multi-speaker dialogue with Eleven v3
- Minimal backend complexity

**Cons:**
- Higher cost ($150/million chars)
- Vendor lock-in

**Best For:** Quick implementation, premium quality required

---

### 5.2 Option B: LiveKit + Cartesia (Recommended for Production) ⭐

```
┌─────────────────────────────────────────────────┐
│          Browser Client (WebRTC)                │
└──────────────┬───────────────────────────────────┘
               │
┌──────────────┼───────────────────────────────────┐
│              ↓                                   │
│      LiveKit Media Server                        │
│              ↑                                   │
│      ┌───────┼────────┐                         │
│      │       │        │                         │
│  ┌───▼───┬───▼───┬───▼───┐                     │
│  │ Agent │ Agent │ Agent │  LiveKit Agents     │
│  │  MC   │Partner│ Room  │  Framework (Python) │
│  └───┬───┴───┬───┴───┬───┘                     │
│      │       │       │                          │
│      ↓       ↓       ↓                          │
│  ┌───────────────────────┐                     │
│  │  Cartesia Sonic API   │                     │
│  │  (WebSocket per agent)│                     │
│  └───────────────────────┘                     │
└──────────────────────────────────────────────────┘
```

**Pros:**
- Ultra-low latency (40-95ms)
- Cost-effective ($38/million chars)
- Built-in agent coordination
- WebRTC network resilience
- Emotional voice synthesis (laughter, breathing)
- Provider-agnostic (can switch TTS if needed)

**Cons:**
- More complex setup
- Requires LiveKit infrastructure

**Implementation:**
```python
# LiveKit Agents Framework
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice import VoicePipelineAgent
from livekit.plugins import cartesia

async def entrypoint(ctx: JobContext):
    # MC Agent with Aoede-like voice
    mc_agent = VoicePipelineAgent(
        vad=ctx.vad,
        stt=ctx.stt,
        llm=ctx.llm,
        tts=cartesia.TTS(voice_id="mc_aoede_clone"),
    )

    # Partner Agent with different voice
    partner_agent = VoicePipelineAgent(
        vad=ctx.vad,
        stt=ctx.stt,
        llm=ctx.llm,
        tts=cartesia.TTS(voice_id="partner_voice_clone"),
    )

    # Room/Audience Agent with Charon-like voice
    room_agent = VoicePipelineAgent(
        vad=ctx.vad,
        stt=ctx.stt,
        llm=ctx.llm,
        tts=cartesia.TTS(voice_id="room_charon_clone"),
    )

    # Start all agents
    await mc_agent.start(ctx.room)
    await partner_agent.start(ctx.room)
    await room_agent.start(ctx.room)
```

**Best For:** Production multi-agent applications requiring low latency, cost efficiency, and scalability

**Sources:**
- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
- [Building Multi-Agent Conversations with LiveKit](https://dev.to/cloudx/building-multi-agent-conversations-with-webrtc-livekit-48f1)

---

### 5.3 Option C: Gemini Multi-Speaker TTS (Batch-Oriented)

```
┌─────────────────────────────────────────────────┐
│          Application                            │
│  ┌──────────────────────────────────┐           │
│  │ Script with Speaker Assignments │           │
│  └──────────────┬───────────────────┘           │
└─────────────────┼─────────────────────────────────┘
                  │
┌─────────────────┼─────────────────────────────────┐
│                 ↓                                 │
│   Gemini TTS API (Multi-Speaker Config)          │
│  ┌────────────────────────────────────┐          │
│  │ multiSpeakerVoiceConfig:           │          │
│  │   - Joe: Kore voice                │          │
│  │   - Jane: Puck voice               │          │
│  │   - Narrator: Aoede voice          │          │
│  └────────────────────────────────────┘          │
│                 ↓                                 │
│         Generated Audio File                     │
└───────────────────────────────────────────────────┘
```

**Pros:**
- Natural language control (style, accent, pace, tone, emotion)
- 30 built-in voices
- 24 languages
- Cost-effective ($16/million chars Neural2)

**Cons:**
- **NOT real-time streaming for conversations**
- Batch-oriented (generates complete audio file)
- Cannot be used with Gemini Live API for interactive agents
- Latency not suitable for conversational AI

**Best For:** Podcast generation, audiobook narration, scripted multi-speaker content (NOT for improv)

**Limitation for Your Use Case:** Gemini's multi-speaker TTS is designed for scripted content, not real-time conversational agents. The Live API (used in ADK) supports only single agent output.

**Sources:**
- [Gemini TTS Documentation](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts)
- [Gemini API Speech Generation](https://ai.google.dev/gemini-api/docs/speech-generation)

---

## 6. Implementation Recommendations

### 6.1 Short-Term (Quick Prototype)

**Use ElevenLabs Multi-Context WebSocket:**
1. Create voice clones for MC (Aoede-like), Partner, Room (Charon-like)
2. Establish single WebSocket connection
3. Create 3 contexts (one per agent)
4. Implement client-side audio mixing
5. Test concurrent speech scenarios

**Estimated Implementation Time:** 2-3 days
**Monthly Cost (100 shows):** $506

---

### 6.2 Medium-Term (Production MVP) ⭐ RECOMMENDED

**Use LiveKit Agents Framework + Cartesia:**
1. Set up LiveKit infrastructure (cloud or self-hosted)
2. Clone voices using Cartesia (3 seconds of audio each)
3. Implement 3 agents using LiveKit Agents Framework
4. Configure WebRTC streaming to client
5. Add agent coordination logic (turn-taking, interruptions)
6. Implement monitoring and error handling

**Estimated Implementation Time:** 1-2 weeks
**Monthly Cost (100 shows):** $128 + LiveKit hosting (~$50-100)

**Migration Path from Current ADK:**
- Replace Gemini Live API with LiveKit agents
- Use Cartesia for TTS (similar latency to Gemini Live)
- Keep LLM logic (can use Gemini or other LLMs via LiveKit)
- Gain multi-agent coordination capabilities

---

### 6.3 Long-Term (Optimization)

**Hybrid Approach:**
1. Use Cartesia Sonic for MC and Partner (low latency required)
2. Use cheaper TTS (Google Standard $4/million) for ambient Room/Audience reactions
3. Implement intelligent caching for common phrases
4. Add voice emotion control based on scene context
5. Build analytics for voice performance optimization

**Potential Monthly Cost (100 shows):** $80-120

---

## 7. Key Findings Summary

### 7.1 Can Gemini TTS be used outside ADK Live API?
**YES**, but:
- Gemini TTS API is separate from Live API
- Multi-speaker support exists but is **batch-oriented** (not real-time streaming)
- NOT suitable for conversational AI or improv scenarios
- Live API (ADK) only supports single agent output currently

### 7.2 Which services support concurrent streaming?
1. **ElevenLabs Multi-Context WebSocket** - Built-in support for multiple concurrent streams
2. **LiveKit + Any TTS Provider** - Framework-level multi-agent support
3. **Cartesia WebSocket** - Provider-agnostic, can run multiple connections
4. **Azure Speech Services** - Scalable concurrent requests (200 TPS default)

### 7.3 Best services for multi-voice real-time applications?
1. **Cartesia Sonic** - Best latency-to-cost ratio (40-95ms, $38/million)
2. **ElevenLabs Multi-Context** - Best built-in multi-speaker API ($150/million)
3. **LiveKit Framework** - Best orchestration (provider-agnostic)

### 7.4 Voice consistency across sessions?
**All major providers support persistent voice IDs:**
- Voice cloning creates unique ID (persists indefinitely)
- Reference same ID across sessions for consistency
- Professional cloning (longer audio samples) provides better consistency than instant cloning

### 7.5 Costs for high-volume multi-voice TTS?
**For 3 agents, 100 shows/month (3.375M characters):**
- Budget: $13-38 (Google Standard, Speechmatics, Deepgram)
- Balanced: $54-128 (Azure/Google Neural, Cartesia)
- Premium: $506 (ElevenLabs)

---

## 8. Final Recommendation

### For Your Multi-Agent Improv Application:

**Recommended Solution: LiveKit Agents Framework + Cartesia Sonic**

**Why:**
1. **Real-time streaming:** 40-95ms latency (comparable to Gemini Live)
2. **Cost-effective:** $128/month for 100 shows (vs $506 for ElevenLabs)
3. **Multi-agent support:** Built-in agent coordination, state management, handoffs
4. **Emotional voices:** Laughter, breathing, emotional inflections (perfect for improv)
5. **Scalable:** Can handle concurrent agents without complex custom logic
6. **Flexible:** Can switch TTS providers if needed (provider-agnostic)

**Migration from Current ADK Setup:**
- Replace Gemini Live API → LiveKit Agents Framework
- Replace Gemini TTS → Cartesia Sonic TTS
- Keep LLM logic (can use Gemini 2.0 Flash via LiveKit)
- Gain multi-agent voice coordination out-of-the-box

**Alternative (If Budget is Tight):**
Use LiveKit + Google Cloud TTS (Chirp 3 HD):
- Lower cost: ~$54/month
- Good latency with Chirp 3 HD
- Enterprise reliability
- 30+ voices available

**Not Recommended:**
- Gemini Multi-Speaker TTS: Batch-oriented, not suitable for real-time improv
- Pure Gemini Live API: Single-agent limitation, no multi-voice support

---

## 9. Additional Resources

### Documentation Links
- [LiveKit Agents Framework](https://docs.livekit.io/agents/)
- [Cartesia TTS Documentation](https://docs.cartesia.ai/build-with-cartesia/models/tts)
- [ElevenLabs Multi-Context WebSocket](https://elevenlabs.io/docs/api-reference/multi-context-text-to-speech/v-1-text-to-speech-voice-id-multi-stream-input)
- [Google ADK Bidi-Streaming](https://google.github.io/adk-docs/streaming/)

### Benchmarking Resources
- [TTS Latency vs Quality Benchmark](https://podcastle.ai/blog/tts-latency-vs-quality-benchmark/)
- [Real-Time vs Turn-Based Voice Agent Architecture](https://softcery.com/lab/ai-voice-agents-real-time-vs-turn-based-tts-stt-architecture)

### Implementation Examples
- [Building Multi-Agent Conversations with LiveKit](https://dev.to/cloudx/building-multi-agent-conversations-with-webrtc-livekit-48f1)
- [Real-Time Voice Interactions with WebSocket](https://dev.to/ag2ai/real-time-voice-interactions-with-the-websocket-audio-adapter-4keb)
- [Google ADK Custom Audio Bidi-Streaming](https://google.github.io/adk-docs/streaming/custom-streaming-ws/)

---

## Research Sources

### Latency & Performance
- [Streaming TTS Benchmark: Async vs Elevenlabs vs Cartesia](https://podcastle.ai/blog/tts-latency-vs-quality-benchmark/)
- [Best TTS APIs in 2025](https://www.speechmatics.com/company/articles-and-news/best-tts-apis-in-2025-top-12-text-to-speech-services-for-developers)
- [ElevenLabs vs Cartesia Comparison](https://elevenlabs.io/blog/elevenlabs-vs-cartesia)
- [Text-to-Speech voice AI model guide 2025](https://layercode.com/blog/tts-voice-ai-model-guide)

### Multi-Speaker & Coordination
- [Gemini-TTS Multi-Speaker Documentation](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts)
- [ElevenLabs Multi-Voice Support](https://elevenlabs.io/docs/agents-platform/customization/voice/multi-voice-support)
- [The Voice AI Stack for Building Agents](https://www.assemblyai.com/blog/the-voice-ai-stack-for-building-agents)
- [Real-Time Voice Agent Architecture](https://softcery.com/lab/ai-voice-agents-real-time-vs-turn-based-tts-stt-architecture)
- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)

### Pricing & Cost Analysis
- [Azure Speech Services Pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/)
- [TTS API Pricing Comparison 2025](https://www.speechmatics.com/company/articles-and-news/best-tts-apis-in-2025-top-12-text-to-speech-services-for-developers)
- [Cartesia vs ElevenLabs Pricing](https://fish.audio/vs/elevenlabs-versus-cartesia/)

### Voice Cloning & Identity
- [ElevenLabs Voice Cloning API](https://elevenlabs.io/docs/cookbooks/voices/instant-voice-cloning)
- [Cartesia Voice Cloning](https://docs.cartesia.ai/build-with-cartesia/models/tts)
- [Resemble AI Custom Voice API](https://www.resemble.ai/api/)
- [Hume AI Voice Cloning](https://dev.hume.ai/docs/voice/voice-cloning)

### Audio Mixing & Synchronization
- [Software Mixing of Multiple Audio Streams](https://dsp.stackexchange.com/questions/72826/software-mixing-of-multiple-audio-streams-from-network)
- [Synchronizing Multiple Real-Time Audio Streams](https://dsp.stackexchange.com/questions/61403/how-to-synchronize-multiple-real-time-audio-streams-before-mixing-them)
- [RealtimeTTS GitHub](https://github.com/KoljaB/RealtimeTTS)

---

**Report Compiled:** December 1, 2025
**Research Agent:** Claude Code Research Specialist
**Project:** ai4joy Multi-Agent Improv Application
