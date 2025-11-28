# Real-time Conversational Audio Feature - Planning Summary

**Created**: 2025-11-27
**Status**: Planning Complete - Ready for Phase 0
**Linear Project**: ai4joy

## Executive Summary

This document summarizes the planning phase for adding real-time conversational audio capabilities to the Improv Olympics AI application, transforming it from a text-based to voice-driven premium experience.

## Key Decisions

### Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Git Repository** | Same repo | Share agent code, instructions, models |
| **Cloud Run** | Separate service | Different concurrency/scaling for WebSocket |
| **GCP Project** | Same project | Share Firestore, IAM, monitoring |
| **Agent Instructions** | Shared | Same prompts work for both text and audio modes |
| **Coach Agent** | Text-only | Intentional - allows copying/retention of feedback |

### Implementation Phases

| Phase | Ticket | Duration | Scope |
|-------|--------|----------|-------|
| **0** | [IQS-57](https://linear.app/iqsubagents/issue/IQS-57) | 1-2 weeks | ADK Live API Research & PoC |
| **1** | [IQS-58](https://linear.app/iqsubagents/issue/IQS-58) | 4 weeks | MC Agent Voice (WebSocket, premium gating) |
| **2** | [IQS-59](https://linear.app/iqsubagents/issue/IQS-59) | 6 weeks | Partner Agent & Multi-Agent Coordination |
| **3** | [IQS-60](https://linear.app/iqsubagents/issue/IQS-60) | 4 weeks | Room Agent & Full Immersive Experience |

**Total Timeline**: 15-17 weeks (Phase 0 → Phase 3)

### Voice Configuration

| Agent | Voice | Persona |
|-------|-------|---------|
| MC | Aoede | Enthusiastic host |
| Partner | Puck | Playful scene partner |
| Coach | Text-only | Instructional (no audio) |
| Room | Charon or ambient | Background reactions |

## Documentation Created

The following documents were created during planning:

### Requirements & PRD
- `/docs/premium-audio-prd.md` - Comprehensive Product Requirements Document

### Technical Architecture
- `/docs/REALTIME_AUDIO_ARCHITECTURE.md` - Technical architecture analysis

### UX Design
- `/docs/audio-ux-review.md` - UX review and recommendations

### Deployment & Infrastructure
- `/docs/gcp-audio-deployment-guide.md` - GCP deployment guide
- `/docs/gcp-architecture-decision-matrix.md` - Architecture options comparison
- `/docs/terraform-audio-service-example.tf` - Cloud Run audio service
- `/docs/terraform-load-balancer-example.tf` - Load balancer config
- `/docs/terraform-monitoring-example.tf` - Monitoring setup

## Critical Risk: ADK Live API

**Phase 0 must validate** that `google-adk>=1.19.0` supports the Live API for real-time audio. The ADK sample uses patterns that may differ from our version.

### Questions to Answer in Phase 0

1. Does `Runner` support Live API streaming, or need `InMemoryRunner`?
2. How to configure speech synthesis (voice, language) in ADK?
3. Is `DatabaseSessionService` compatible with streaming sessions?
4. Can we use `google-genai` Live API alongside ADK if needed?

### Go/No-Go Decision

After Phase 0:
- **GO**: Proceed to Phase 1 with validated approach
- **NO-GO**: Reassess architecture or defer audio feature

## Success Metrics

| Metric | Target |
|--------|--------|
| Premium conversion | 30% |
| Audio latency (P95) | < 2 seconds |
| User satisfaction | 4.0+ rating |
| Cost per user | < $10/month |
| Concurrent sessions | 50 users |

## Cost Projections

| Component | Monthly Cost |
|-----------|--------------|
| Cloud Run - Audio Service | $1,770 |
| Vertex AI - ADK/Live API | $8,275 |
| Load Balancer | $58 |
| Firestore + Logging | $427 |
| **Total (1000 sessions)** | **$10,530** |

## Next Steps

1. **Start Phase 0**: Begin ADK Live API research with IQS-57
2. **Validate feasibility**: Build minimal PoC, measure latency
3. **Make Go/No-Go decision**: Based on Phase 0 findings
4. **Proceed to Phase 1**: If GO, implement MC agent audio

## Related Documents

- [ADK Realtime Sample](https://github.com/google/adk-samples/tree/main/python/agents/realtime-conversational-agent)
- [ADK Documentation](https://google.github.io/adk-python/)
- [Vertex AI Live API](https://cloud.google.com/vertex-ai/docs/generative-ai/live-api)

---

**Planning completed by**: Claude Code TDD Workflow
**Specialist agents used**: PRD Writer, Agentic ML Architect, UX Design Reviewer, QA Tester, GCP Admin Deployer
