# Multi-Agent Audio Broadcasting Research

**Date**: 2025-12-01
**Branch**: `research/multi-agent-audio-broadcasting`
**Status**: Complete

## Executive Summary

This research explores how to enable **multiple AI agents (MC, Partner, Audience) to simultaneously broadcast voice** to a web client in the ai4joy improv application. The previous attempt (pre-IQS-63) proved difficult due to Google ADK Live API limitations.

### Key Finding

**The IQS-63 simplified architecture (single unified MC agent) is architecturally correct** given current platform constraints. However, if true multi-agent voice is required, **LiveKit Agents Framework** offers the most viable path forward.

## Research Documents

| Document | Focus Area | Key Finding |
|----------|------------|-------------|
| [ADK Live API Analysis](#adk-findings) | Google ADK capabilities | Single-agent streaming only; no native multi-voice support |
| [LiveKit Architecture](livekit-multi-agent-voice-architecture.md) | WebRTC multi-stream rooms | Best solution for multi-agent voice (native support) |
| [WebRTC Patterns](#webrtc-findings) | Multi-peer audio streaming | WebSocket + Web Audio API is simpler than full WebRTC |
| [Audio Mixing & Orchestration](#mixing-findings) | Real-time audio coordination | Client-side mixing via Web Audio API is industry standard |
| [Voice Synthesis Coordination](multi-agent-voice-synthesis-research.md) | TTS services comparison | Cartesia Sonic offers best latency/cost ratio |
| [Turn-Taking Protocols](multi_agent_turn_taking_orchestration.md) | Conversation orchestration | Push-to-talk + unified agent solves turn-taking elegantly |

---

## Architecture Comparison

### Current Architecture (IQS-63) ✅ Recommended

```
Browser                          Server (FastAPI)
┌─────────────────┐              ┌─────────────────────────┐
│  WebSocket      │◄────WSS─────►│  AudioStreamOrchestrator│
│  + Web Audio    │              │  └─ Single MC Agent     │
│  + Mood Visuals │              │     └─ ADK Live API     │
└─────────────────┘              └─────────────────────────┘
```

**Pros**: Simple, low latency (~1s), cost-effective ($0.20/session)
**Cons**: Single voice only, MC handles all roles

### Alternative: LiveKit Multi-Agent (If Required)

```
Browser (WebRTC)                 LiveKit Server              AI Agents
┌─────────────────┐              ┌──────────────┐           ┌─────────────┐
│  3 Audio Tracks │◄──WebRTC────►│  SFU Room    │◄─────────►│  MC Agent   │
│  + Web Audio    │              │  (routing)   │           │  Partner    │
│  + Spatial Mix  │              └──────────────┘           │  Audience   │
└─────────────────┘                                         └─────────────┘
```

**Pros**: True multi-voice, distinct characters, spatial audio
**Cons**: Complex migration, 3x cost (~$0.60/session), additional infrastructure

---

## Key Findings by Topic

### ADK Live API Findings {#adk-findings}

| Capability | Supported? | Notes |
|------------|------------|-------|
| Single agent streaming | ✅ Yes | Core design pattern |
| Multiple concurrent agents | ❌ No | Each `run_live()` binds to ONE agent |
| Agent-level voice config | ❌ No | Voice is session-level via `RunConfig` |
| Audio stream multiplexing | ❌ No | No native mixing support |
| Agent switching mid-stream | ⚠️ Partial | Requires stream restart (2-3s latency) |

**Conclusion**: ADK Live API is fundamentally single-agent. Multi-voice requires platform change.

### WebRTC Findings {#webrtc-findings}

| Architecture | Best For | Latency | Complexity |
|--------------|----------|---------|------------|
| WebSocket + Web Audio | Server→Browser streaming | 100-300ms | Low |
| WebRTC SFU (LiveKit) | Multi-peer with mixing | 200-500ms | Medium |
| WebRTC MCU | Large conferences | 500-1000ms | High |

**Conclusion**: Current WebSocket approach is optimal for server-originated audio. WebRTC only adds value if you need peer-to-peer or multi-track from server.

### Audio Mixing Findings {#mixing-findings}

| Approach | Server CPU | Latency | Flexibility |
|----------|------------|---------|-------------|
| Client-side (Web Audio API) | None | Low | High (user controls volume) |
| Server-side (FFmpeg/GStreamer) | High | Higher | Low (pre-mixed) |

**Conclusion**: Client-side mixing is industry standard. Your `AudioMixer` class is ready for future client-side implementation.

### TTS Services Comparison

| Service | TTFB | 90th %ile | Cost/1K chars | Best For |
|---------|------|-----------|---------------|----------|
| **Cartesia Sonic** | 40ms | 95ms | $0.05 | Ultra-low latency |
| ElevenLabs Flash | 75ms | 150ms | $0.18 | Natural voices |
| Google (Gemini Live) | 100ms | 200ms | Varies | Current integration |
| Azure Neural | 150ms | 250ms | $0.16 | Enterprise |

**Conclusion**: Current Google TTS is adequate. Consider Cartesia if latency becomes critical.

---

## Recommendations

### Short-Term (Keep Current)

1. **Keep IQS-63 architecture** - It's correct for ADK constraints
2. **Enhance mood visualization** - Expand MC phrase detection
3. **Document multi-voice readiness** - AudioMixer is ready when needed

### Medium-Term (If User Demand)

4. **Evaluate LiveKit** - Run proof-of-concept with 3 agents
5. **Consider Cartesia TTS** - For 60% latency reduction
6. **Implement client-side mixing** - If multiple voices requested

### Long-Term (Platform Migration)

7. **Migrate to LiveKit Agents** - If multi-voice is critical requirement
8. **Multi-TTS provider strategy** - Different voices per agent
9. **Spatial audio** - Position agents in stereo field

---

## Cost Analysis

| Architecture | API Cost | Infra Cost | Total/Session |
|--------------|----------|------------|---------------|
| Current (Single MC) | $0.20 | $0 | **$0.20** |
| LiveKit + Cartesia | $0.45 | ~$0.15 | **$0.60** |
| LiveKit + ElevenLabs | $0.90 | ~$0.15 | **$1.05** |

---

## Next Steps

1. Review this research with stakeholders
2. Decide if multi-voice is a critical user need
3. If yes, prototype LiveKit integration
4. If no, continue optimizing current architecture

---

## Source Files

- `livekit-multi-agent-voice-architecture.md` - LiveKit deep dive
- `multi-agent-voice-synthesis-research.md` - TTS comparison
- `multi_agent_turn_taking_orchestration.md` - Turn-taking protocols

## Related Code

- `app/audio/audio_orchestrator.py` - Current audio implementation
- `app/audio/audio_mixer.py` - Ready for client-side mixing
- `app/audio/room_tts.py` - Room agent TTS (currently unused)
- `app/agents/mc_agent.py` - Unified MC agent

---

**Research conducted by**: Hive Mind Swarm
**Coordination**: Claude Code
**Date**: 2025-12-01
