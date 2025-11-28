# Product Requirements Document: Real-Time Conversational Audio (Premium Feature)

**Document Version:** 1.0
**Author:** Product Team
**Date:** 2025-11-27
**Project:** Improv Olympics (ai4joy)
**Epic:** Premium Audio Experience
**Linear Ticket:** IQS-[TBD]

---

## Overview

Add real-time conversational audio capability to Improv Olympics, enabling premium tier users to practice improv through voice rather than text. Users speak into their microphone and hear MC, Partner, and Audience agents respond with synthesized voices in near-real-time (< 2s roundtrip latency). This transforms the platform from a text-based training tool into an immersive, voice-driven improv gym that more closely replicates live performance conditions.

This feature targets **premium tier subscribers only**, creating a clear value differential from standard (text-based) tier while leveraging Google ADK Live API for audio streaming and VertexAI for speech-to-text/text-to-speech processing.

---

## Critical Success Factors

- **CSF-1: Premium Conversion Driver** - 30% of active standard users upgrade to premium tier within 60 days of audio feature launch, demonstrating clear value proposition
- **CSF-2: Technical Reliability** - 95% of audio sessions complete without technical failures (dropped connections, audio glitches, timeout errors) over 30-day period
- **CSF-3: Latency Performance** - P95 total roundtrip latency (user speech end → agent audio playback start) stays below 2000ms measured across all premium sessions
- **CSF-4: User Satisfaction** - Premium users rate audio experience 4.0+ out of 5.0 in post-session surveys, with primary feedback focused on "immersiveness" and "realistic practice"
- **CSF-5: Cost Control** - Premium audio feature operates within $500/month additional GCP spend for first 50 premium users (avg $10/user/month), maintaining profitability at $29/month subscription price

---

## Functional Requirements

### FR-1: Premium Tier Gating
**Requirement:** System MUST enforce premium tier access control for all audio features
**Acceptance Criteria:**
- Standard tier users see audio feature as locked with upgrade CTA
- Premium tier check occurs at session initialization via Firestore user document `tier` field
- Unauthorized audio session attempts return HTTP 403 with clear upgrade message
- Feature flag `PREMIUM_AUDIO_ENABLED` controls global feature availability (env var)

### FR-2: WebSocket Audio Session Management
**Requirement:** System MUST establish bidirectional WebSocket connection for audio streaming
**Acceptance Criteria:**
- WebSocket endpoint at `/ws/audio/{session_id}` accepts authenticated connections
- Session initialization validates: (1) OAuth session cookie, (2) Premium tier status, (3) Active ADK session exists
- Connection maintains session state for duration of improv session (up to 30 minutes)
- Graceful disconnection on client close or server timeout (5 minutes idle)
- Automatic reconnection logic on client with session state restoration

### FR-3: Real-Time Audio Input (Speech-to-Text)
**Requirement:** System MUST capture user speech via microphone and transcribe to text in real-time
**Acceptance Criteria:**
- Client captures PCM16 mono audio at 16kHz sample rate from browser MediaRecorder API
- Audio chunks sent as base64-encoded binary over WebSocket at 100ms intervals
- ADK Live API integration performs streaming speech recognition
- Speech detection parameters: `voice_activity_timeout: 2.0s`, `speech_start_timeout: 10.0s`
- Transcribed text available to agent within 500ms of user stopping speech (P95)

### FR-4: Agent Voice Synthesis (Text-to-Speech)
**Requirement:** System MUST convert agent text responses to natural-sounding speech
**Acceptance Criteria:**
- Each agent has distinct voice configuration: MC (authoritative male), Partner (friendly neutral), Room/Audience (varied crowd voices)
- ADK Live API `voice_config` parameter specifies language (`en-US`) and voice persona
- Audio response chunks streamed back to client as base64 PCM16 mono 16kHz
- First audio chunk arrives within 1000ms of agent generating text (P95)
- Audio quality maintains clarity for improv dialogue (>80% intelligibility in user testing)

### FR-5: Multi-Agent Audio Orchestration
**Requirement:** System MUST coordinate audio responses from multiple agents (MC, Partner, Room)
**Acceptance Criteria:**
- Stage Manager agent receives speech transcription as user input
- Stage Manager routes to appropriate sub-agent (MC, Partner, Room) based on session phase
- Only one agent speaks at a time (no overlapping audio)
- Turn-taking logic prevents audio interruptions: user speech detected → cancel pending agent audio
- Room Agent ambient reactions (laughter, gasps) play asynchronously at lower volume (30% of main audio)

### FR-6: Post-Session Transcript Generation
**Requirement:** System MUST save complete audio session transcript for user review
**Acceptance Criteria:**
- Transcript includes: timestamp, speaker (User/MC/Partner/Room), text content
- Transcript stored in Firestore `sessions/{session_id}/transcript` subcollection
- Transcript available via GET `/api/v1/session/{id}/transcript` endpoint within 30s of session end
- Transcript format: JSON array with `[{timestamp, speaker, text, audio_duration_ms}]`
- UI displays transcript with playback controls (future enhancement placeholder)

### FR-7: Audio Session Error Handling
**Requirement:** System MUST gracefully handle audio failures and provide clear user feedback
**Acceptance Criteria:**
- Microphone permission denied → show browser permission instructions
- WebSocket connection loss → attempt reconnect 3x with exponential backoff, then prompt user
- ADK Live API timeout (> 5s no response) → display "Agent thinking..." indicator, fallback to text if > 10s
- Speech recognition failure → prompt user to repeat, log error to Cloud Logging
- TTS synthesis failure → display text response as fallback, alert user of audio issue

### FR-8: Browser Compatibility
**Requirement:** System MUST support audio features on major modern browsers
**Acceptance Criteria:**
- Chrome/Chromium >= 90 (primary support)
- Firefox >= 88 (secondary support)
- Safari >= 14 (secondary support, best effort)
- Mobile browsers: Chrome Android, Safari iOS (best effort, documented limitations)
- Feature detection on client: disable audio features if MediaRecorder API unavailable

### FR-9: Audio Quality Configuration
**Requirement:** System MUST allow users to adjust audio settings for their environment
**Acceptance Criteria:**
- User settings panel for: microphone input device selection, audio playback volume (0-100%)
- Noise suppression toggle (browser API if available)
- "Test microphone" button shows live input waveform visualization
- Settings persisted in browser localStorage, applied on session start

### FR-10: Cost Monitoring and Rate Limiting
**Requirement:** System MUST track audio usage and enforce usage limits to control costs
**Acceptance Criteria:**
- Premium users get 60 minutes of audio session time per month (reset on billing cycle)
- Firestore tracks `users/{user_id}/audio_usage_seconds` counter, incremented on session close
- Attempting to start audio session when quota exceeded returns HTTP 402 with upgrade/wait message
- Admin dashboard shows aggregate audio usage by user, total API costs from Cloud Billing API
- Alert triggers if monthly audio spend exceeds $600 (120% of budget)

---

## Non-Functional Requirements

### NFR-1: Latency Performance
**Requirement:** Audio roundtrip latency MUST meet < 2000ms P95 target for conversational flow
**Acceptance Criteria:**
- Measured metric: Time from user stops speaking → first audio chunk from agent arrives
- Instrumented via OpenTelemetry custom spans: `audio.roundtrip_latency_ms`
- Cloud Monitoring dashboard shows P50, P95, P99 latency over rolling 7-day window
- Performance regression alert if P95 exceeds 2500ms for >1 hour

### NFR-2: WebSocket Scalability
**Requirement:** System MUST support 50 concurrent premium audio sessions on Cloud Run
**Acceptance Criteria:**
- Cloud Run configured with min 2 instances, max 10 instances, concurrency=10 (5 audio sessions/instance assuming 2 containers)
- WebSocket connections use Cloud Run's HTTP/2 server push capabilities
- Load testing validates 50+ concurrent WebSocket connections with < 5% connection failure rate
- Auto-scaling triggers when CPU > 70% or memory > 80%

### NFR-3: Audio Data Security
**Requirement:** System MUST protect user audio data and comply with privacy requirements
**Acceptance Criteria:**
- Audio streams encrypted in transit (WSS - WebSocket Secure over TLS)
- Raw audio PCM data never persisted to disk or Cloud Storage
- Transcripts stored in Firestore with standard security rules (user can only access own transcripts)
- Audio processing occurs in VertexAI with Google's data residency guarantees (US region)
- No third-party audio analytics or tracking integrated

### NFR-4: Browser Performance
**Requirement:** Client-side audio processing MUST not degrade user experience
**Acceptance Criteria:**
- MediaRecorder CPU usage < 10% on reference device (MacBook Pro 2019, Chrome)
- Audio playback buffer prevents stuttering on connections with 100ms jitter
- Memory usage < 100MB for 30-minute audio session
- No memory leaks detected in 60-minute continuous session test

### NFR-5: Audio API Cost Efficiency
**Requirement:** Audio feature MUST operate within $10/user/month cost target
**Acceptance Criteria:**
- ADK Live API usage optimized: streaming STT/TTS reduces latency vs batch processing
- Voice Activity Detection (VAD) prevents unnecessary transcription of silence
- Agent responses limited to 500 characters max to control TTS costs
- Cost monitoring per-user: Firestore tracks `estimated_api_cost_cents` based on audio minutes
- Pricing page clearly states 60-minute monthly audio limit for $29/month premium tier

### NFR-6: Observability
**Requirement:** System MUST provide comprehensive monitoring of audio feature health
**Acceptance Criteria:**
- Cloud Monitoring dashboard "Premium Audio Health" with: active sessions, avg latency, error rate, API cost burn
- Cloud Logging captures: session start/end, transcription events, TTS requests, errors with request IDs
- OpenTelemetry traces link WebSocket connection → ADK agent execution → VertexAI API calls
- Alert rules: P95 latency > 2500ms, error rate > 5%, daily cost > $20

### NFR-7: Graceful Degradation
**Requirement:** System MUST fallback to text mode if audio features fail
**Acceptance Criteria:**
- Audio session initialization failure → automatic redirect to standard text session
- Mid-session audio failure (3 consecutive errors) → offer user choice: retry audio or continue in text
- Text fallback maintains full agent functionality (no loss of improv experience quality)
- User notified of fallback with clear explanation and option to report issue

### NFR-8: Disaster Recovery
**Requirement:** System MUST recover from audio service outages without data loss
**Acceptance Criteria:**
- In-progress audio session state persisted to Firestore every 30 seconds (ADK session snapshot)
- WebSocket reconnection restores session state from last snapshot
- VertexAI API outage → queue audio requests for 60s retry window, then fallback to text
- Post-incident: partial transcripts still saved, users notified of incomplete session

---

## Explicit Scope Exclusions

The following capabilities are **deliberately NOT included** in this initiative to maintain focus and control scope:

- **Multi-user voice sessions** - No support for multiple users speaking simultaneously (e.g., voice-based group improv). Future consideration for "Premium Pro" tier.
- **Custom voice training** - Users cannot upload voice samples to create personalized agent voices. Agents use predefined voice personas only.
- **Real-time live transcription UI** - Transcripts generated but not displayed during active session (post-session only). Live transcription increases complexity and is not required for MVP.
- **Voice analytics/coaching** - No analysis of user's vocal patterns, tone, pacing, or other performance metrics. Focus is conversational audio, not vocal coaching.
- **Audio recording download** - Users cannot download MP3/WAV files of their sessions. Transcripts are the retention artifact (text format preferred for coaching review).
- **Background music or sound effects** - No ambient music, scene sound effects, or audio atmosphere beyond agent voices and audience reactions.
- **Voice modulation/filters** - No pitch shifting, voice changing, or effects on user or agent audio.
- **Multi-language support** - English (`en-US`) only for MVP. Other languages require separate voice persona configuration and testing.
- **Offline audio mode** - No client-side audio processing or offline session support. Requires active internet connection.
- **Third-party integrations** - No Spotify, YouTube, or external audio service integrations for this phase.

---

## Dependencies & Assumptions

### Technical Dependencies
- **Google ADK Live API** - Requires ADK v1.19.0+ with Live API support for streaming audio (dependency confirmed in requirements.txt)
- **VertexAI Speech APIs** - Speech-to-Text and Text-to-Speech APIs enabled in GCP project with sufficient quota (default: 10 concurrent requests)
- **Cloud Run WebSocket Support** - Cloud Run supports long-lived WebSocket connections (documented feature, no additional config required)
- **Browser MediaRecorder API** - Assumes 95%+ of premium users on modern browsers with microphone access
- **OAuth Session Management** - Existing OAuth middleware extended to support WebSocket authentication (session cookie validation)

### Infrastructure Assumptions
- **Cloud Run scaling** - Assumes Cloud Run can auto-scale to 10 instances within 30 seconds during traffic spike (GCP documented behavior)
- **Firestore write capacity** - Assumes Firestore can handle 100 writes/second for transcript persistence (well within free tier limits)
- **Network latency** - Assumes user network RTT < 200ms to GCP us-central1 (95th percentile for US users)
- **VertexAI SLA** - Assumes VertexAI Speech APIs maintain 99.9% availability per published SLA

### Product Assumptions
- **Premium conversion rate** - Assumes 30% of active standard users will upgrade for audio (based on competitor benchmarks)
- **User hardware** - Assumes users have functional microphone (built-in laptop mic or headset)
- **Session duration** - Assumes typical audio session is 10-15 minutes (matches current text session patterns)
- **Monthly usage** - Assumes premium users consume 40 minutes/month on average (60-minute cap allows headroom)

### Business Assumptions
- **Pricing acceptance** - Assumes $29/month premium tier pricing is acceptable for target market (improv students, coaches)
- **Competitive landscape** - Assumes no major competitor launches similar voice-driven improv AI tool in next 6 months
- **Legal/compliance** - Assumes no COPPA or GDPR blockers for storing voice transcripts (legal review required before launch)

---

## Open Questions

### High-Priority (Blocking)
1. **Voice persona selection** - Should users be able to choose from multiple voice options per agent (e.g., "MC Voice A" vs "MC Voice B"), or is single default voice sufficient for MVP?
   - **Impact:** Affects UI complexity and ADK configuration
   - **Owner:** Product + UX
   - **Decision Needed By:** Phase 1 kickoff

2. **Interrupt handling** - What should happen if user starts speaking while agent is mid-sentence? Cancel agent audio immediately, or let agent finish current thought?
   - **Impact:** Affects conversation flow naturalness and ADK Live API configuration
   - **Owner:** Product + Engineering
   - **Decision Needed By:** Phase 1 design review

3. **Accessibility compliance** - Are we required to provide audio transcripts under ADA/WCAG guidelines since Coach remains text-only?
   - **Impact:** May require live captioning (excluded from current scope)
   - **Owner:** Legal + Compliance
   - **Decision Needed By:** Before beta launch

### Medium-Priority (Non-blocking)
4. **Audio session analytics** - What metrics do we want beyond latency/errors? (e.g., user talk time %, agent response length, interruption frequency)
   - **Impact:** Informs product iteration and coaching insights
   - **Owner:** Product Analytics
   - **Decision Needed By:** Phase 2

5. **Transcript sharing** - Should users be able to share transcripts with coaches/friends (public links, exports)?
   - **Impact:** Requires additional privacy controls and sharing UI
   - **Owner:** Product
   - **Decision Needed By:** Phase 3

6. **Mobile experience** - What is priority for mobile browser support (iOS Safari, Chrome Android)? Desktop-first MVP acceptable?
   - **Impact:** Mobile WebSocket/MediaRecorder compatibility testing and potential fallback UX
   - **Owner:** Product + UX
   - **Decision Needed By:** Phase 1 scope finalization

---

## Phased Implementation Strategy

### Phase 1: MC Agent Voice (Foundation) - 4 weeks
**Goal:** Prove audio pipeline with simplest use case - MC introduces games and explains rules

**Deliverables:**
- WebSocket `/ws/audio/{session_id}` endpoint with OAuth authentication
- ADK Live API integration for streaming STT + TTS
- MC Agent voice persona configured (authoritative male voice)
- Premium tier gating in session initialization
- Basic error handling (mic permissions, connection loss)
- Post-session transcript storage and retrieval API
- Cloud Monitoring dashboard for audio metrics

**Success Criteria:**
- 10 beta testers complete 5 MC-only audio sessions each
- P95 latency < 2000ms for MC responses
- Zero session-breaking bugs reported
- $50 total GCP cost for beta period (10 users * 5 sessions * 10 min)

**Risks:**
- ADK Live API learning curve → Mitigate with Google ADK support engagement
- WebSocket deployment on Cloud Run untested → Mitigate with early spike/POC

### Phase 2: Partner Agent Voice (Core Value) - 6 weeks
**Goal:** Enable conversational scene work - the primary value proposition of premium audio

**Deliverables:**
- Partner Agent voice persona configured (friendly neutral, phase-aware tone)
- Multi-agent audio orchestration via Stage Manager
- Turn-taking logic (user speech detection cancels agent audio)
- Enhanced error handling (speech recognition failure, TTS timeout)
- Audio quality configuration panel (mic selection, volume, test)
- Cost monitoring and 60-minute monthly quota enforcement

**Success Criteria:**
- 25 beta users complete 10 scene sessions each
- User satisfaction rating 4.0+ out of 5.0 for "realism"
- 30% of standard users who demo audio feature upgrade to premium
- P95 latency remains < 2000ms with Partner Agent complexity
- Total spend < $300 for beta period (25 users * 10 sessions * 12 min avg)

**Risks:**
- Partner Agent complexity degrades latency → Mitigate with response length limits (500 char)
- Turn-taking logic causes awkward pauses → Mitigate with VAD tuning

### Phase 3: Room/Audience Ambient Audio (Immersion) - 4 weeks
**Goal:** Add ambient audience reactions to increase immersion

**Deliverables:**
- Room Agent audio reactions (laughter, applause, gasps)
- Asynchronous audio playback at 30% volume (no blocking)
- Crowd voice variety (multiple TTS voices for audience simulation)
- Transcript includes audience reactions as `[LAUGHTER]`, `[APPLAUSE]` markers
- Browser performance optimization for multi-stream playback

**Success Criteria:**
- 50 active premium users test audience feature
- User feedback highlights "immersiveness" improvement
- No degradation in P95 latency from Phase 2
- Browser CPU usage remains < 15% during sessions

**Risks:**
- Audience audio distracts from scene work → Mitigate with volume controls
- Performance impact on lower-end devices → Mitigate with quality settings

---

## Risk Analysis & Mitigation

### Technical Risks

**RISK-1: ADK Live API Latency Exceeds Target**
**Likelihood:** Medium | **Impact:** High
**Mitigation:**
- Conduct early latency benchmarking in Phase 1 with ADK support team
- Optimize network path: ensure Cloud Run in same region as VertexAI endpoints (us-central1)
- Implement client-side audio buffering to smooth jitter
- Fallback: Increase P95 target to 2500ms if user testing shows acceptable experience

**RISK-2: WebSocket Connection Stability on Mobile**
**Likelihood:** High | **Impact:** Medium
**Mitigation:**
- Document desktop-first support for MVP (mobile as best-effort)
- Implement aggressive WebSocket reconnection logic with session state restoration
- Provide clear user guidance: "Best experience on desktop Chrome"
- Future: Investigate WebRTC as alternative transport if WebSocket proves unreliable

**RISK-3: Cloud Run Cold Starts Impact First-Session Latency**
**Likelihood:** Medium | **Impact:** Medium
**Mitigation:**
- Configure minimum 2 Cloud Run instances (always-warm) for premium audio service
- Implement WebSocket connection pre-warming: establish connection before session start
- Monitor cold start metrics, alert if > 5% of sessions affected

**RISK-4: VertexAI Speech API Quota Exhaustion**
**Likelihood:** Low | **Impact:** High
**Mitigation:**
- Request quota increase to 50 concurrent requests before Phase 2 launch
- Implement request queueing with 60s timeout
- Alert at 80% quota utilization
- Graceful degradation to text mode if quota exceeded

### Business Risks

**RISK-5: Premium Conversion Below 30% Target**
**Likelihood:** Medium | **Impact:** High
**Mitigation:**
- Offer free trial: 10 minutes of audio for all users to demo value
- A/B test pricing: $19/month vs $29/month tiers
- Gather qualitative feedback: why aren't users upgrading?
- Pivot: Consider audio as add-on ($9/month) instead of full tier upgrade

**RISK-6: Audio Costs Exceed $10/User/Month**
**Likelihood:** Medium | **Impact:** High
**Mitigation:**
- Enforce strict 60-minute monthly quota
- Optimize agent response length (shorter = cheaper TTS)
- Monitor per-user costs weekly, adjust quota if trending over budget
- Future: Introduce higher-tier "Premium Pro" with unlimited audio at $49/month

**RISK-7: Competitor Launches Similar Feature First**
**Likelihood:** Low | **Impact:** Medium
**Mitigation:**
- Accelerate Phase 1+2 timeline (target 8 weeks vs 10 weeks)
- Differentiate on quality: ADK-powered agents + improv expertise
- Monitor competitor landscape monthly
- Maintain focus on core improv pedagogy (not just tech novelty)

### Product Risks

**RISK-8: Users Prefer Text for Coach Feedback**
**Likelihood:** Low | **Impact:** Low
**Mitigation:**
- Validate assumption: survey users on audio vs text preference for coaching
- Keep Coach Agent text-only as designed (intentional for retention)
- Phase 4 consideration: Offer audio coaching as separate opt-in feature

**RISK-9: Accessibility Complaints (No Live Captions)**
**Likelihood:** Medium | **Impact:** Medium
**Mitigation:**
- Provide post-session transcripts within 30 seconds (near-real-time)
- Document accessibility limitations clearly in product marketing
- Phase 4 scope: Live captioning as premium accessibility feature
- Legal review before public beta to assess ADA compliance requirements

---

## Success Metrics & KPIs

### Product Metrics (Measured Monthly)
- **Premium conversion rate:** Target 30% of active standard users upgrade within 60 days of audio launch
- **Audio session completion rate:** Target 90% of started audio sessions complete without errors
- **User satisfaction (NPS):** Target 4.0+ out of 5.0 for premium audio experience
- **Retention rate:** Target 80% of premium users renew monthly subscription (vs 70% baseline)

### Technical Metrics (Measured Daily)
- **P95 roundtrip latency:** Target < 2000ms (alert if > 2500ms)
- **WebSocket connection success rate:** Target 98%+ (alert if < 95%)
- **Audio transcription accuracy:** Target 90%+ word accuracy (manual sampling)
- **Error rate:** Target < 2% of sessions encounter errors (alert if > 5%)

### Cost Metrics (Measured Weekly)
- **Cost per premium user per month:** Target < $10 (alert if > $12)
- **Total monthly audio spend:** Target < $500 for 50 users (alert if > $600)
- **Average session duration:** Target 12 minutes (monitor for quota gaming)

### Business Metrics (Measured Quarterly)
- **Premium tier revenue:** Target $1,450/month at 50 premium users ($29 * 50)
- **Customer acquisition cost (CAC):** Track marketing spend to acquire premium subscribers
- **Lifetime value (LTV):** Target LTV:CAC ratio of 3:1 for premium tier

---

## Appendix: Reference Architecture

### High-Level Audio Flow
```
User Browser
    │
    ├─► [Microphone Capture] → PCM16 audio chunks (100ms)
    │
    ▼
[WebSocket /ws/audio/{session_id}]
    │
    ├─► [OAuth Session Validation] → Premium tier check
    │
    ▼
[Cloud Run - FastAPI + ADK Live API]
    │
    ├─► [ADK Live API - STT] → Transcribe speech to text
    │   └─► [VertexAI Speech-to-Text API]
    │
    ├─► [Stage Manager Agent] → Route to sub-agent
    │   ├─► MC Agent (Phase 1)
    │   ├─► Partner Agent (Phase 2)
    │   └─► Room Agent (Phase 3)
    │
    ├─► [ADK Live API - TTS] → Synthesize agent response
    │   └─► [VertexAI Text-to-Speech API]
    │
    ▼
[WebSocket Audio Stream] → Base64 PCM16 chunks
    │
    ▼
User Browser
    │
    └─► [Audio Playback] → Hear agent response

[Post-Session]
    │
    ├─► [Firestore Transcript Storage]
    └─► [GET /api/v1/session/{id}/transcript]
```

### Technology Stack (Premium Audio Additions)
- **WebSocket Transport:** FastAPI WebSocketRoute with OAuth middleware
- **Audio Codec:** PCM16 mono 16kHz (standard for VertexAI)
- **Streaming Protocol:** Base64-encoded binary over WebSocket JSON frames
- **Speech-to-Text:** VertexAI Speech-to-Text API (streaming recognition)
- **Text-to-Speech:** VertexAI Text-to-Speech API (WaveNet or Journey voices)
- **ADK Integration:** `google.adk.live_api` module for streaming orchestration
- **Client Library:** Native browser MediaRecorder API + AudioContext

### File Organization (Same Repo Approach)
```
ai4joy/
├── app/
│   ├── routers/
│   │   ├── audio_sessions.py       # NEW: WebSocket audio endpoints
│   │   └── sessions.py             # Existing text sessions
│   ├── services/
│   │   ├── audio_service.py        # NEW: ADK Live API wrapper
│   │   ├── tier_manager.py         # NEW: Premium tier validation
│   │   └── session_manager.py      # Updated for audio sessions
│   ├── agents/
│   │   ├── stage_manager.py        # Updated for audio orchestration
│   │   ├── mc_agent.py             # Voice config added
│   │   ├── partner_agent.py        # Voice config added
│   │   └── room_agent.py           # Voice config added (Phase 3)
│   └── middleware/
│       └── premium_auth.py         # NEW: Premium tier middleware
├── static/
│   └── js/
│       └── audio-client.js         # NEW: WebSocket audio client
├── infrastructure/
│   └── terraform/
│       ├── main.tf                 # Updated: Cloud Run WebSocket config
│       └── variables.tf            # NEW: PREMIUM_AUDIO_ENABLED flag
└── tests/
    ├── test_audio_sessions.py      # NEW: Audio integration tests
    └── test_tier_gating.py         # NEW: Premium tier tests
```

---

## Document Control

**Approval Required From:**
- Engineering Lead: Architecture review, feasibility confirmation
- Product Manager: Business case, pricing strategy, success metrics
- Finance: Cost model validation, budget approval
- Legal/Compliance: Privacy review, accessibility compliance (before beta)

**Next Steps:**
1. Engineering spike: ADK Live API latency benchmarking (1 week)
2. UX design: Audio session UI mockups (1 week)
3. Legal review: Voice transcript storage and privacy (concurrent)
4. Linear ticket creation: IQS-XXX (Phase 1 epic)
5. Kickoff meeting: Week of 2025-12-02

**Document History:**
- v1.0 (2025-11-27): Initial PRD based on stakeholder input and Google ADK reference implementation
