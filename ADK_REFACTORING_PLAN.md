# ADK-First Refactoring Plan

## Executive Summary

This document outlines a comprehensive plan to refactor the Improv Olympics codebase to adopt an **ADK-first architecture**. The current implementation uses custom wrappers and bridges that duplicate functionality provided natively by Google's Agent Development Kit (ADK).

**Current State:** Mixed implementation with custom Firestore session management, bridged ADK sessions, and outdated import paths.

**Target State:** Native ADK implementation using `DatabaseSessionService`, `MemoryService`, built-in observability, and proper import paths.

---

## Phase Overview

| Phase | Name | Effort | Priority | Dependencies |
|-------|------|--------|----------|--------------|
| 1 | Fix Import Paths | Small | P0 - Critical | None |
| 2 | Consolidate Session Management | Large | P0 - Critical | Phase 1 |
| 3 | Integrate ADK Runner Properly | Medium | P0 - Critical | Phase 2 |
| 4 | Add Memory Service | Medium | P1 - High | Phase 2, 3 |
| 5 | Standardize Observability | Medium | P2 - Medium | Phase 3 |
| 6 | Add ADK Evaluation Framework | Small | P3 - Low | Phase 3 |
| 7 | Cleanup Legacy Code | Small | P2 - Medium | All above |

---

## Phase 1: Fix Import Paths

### Ticket: IQS-XX - Update ADK Import Paths to v1.19+ Standard

**Priority:** P0 - Critical (blocking production)
**Effort:** Small (1-2 hours)
**Risk:** Low

#### Problem
The codebase uses deprecated import paths that may break with future ADK versions:
```python
# Current (deprecated)
from google.adk import Agent

# Should be
from google.adk.agents import Agent
```

#### Files to Update

| File | Current Import | New Import |
|------|---------------|------------|
| `app/agents/stage_manager.py:2` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `app/agents/partner_agent.py:2` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `app/agents/room_agent.py:2` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `app/agents/mc_agent.py` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `app/agents/coach_agent.py` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `app/services/agent_cache.py:7` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `tests/test_adk_agents.py:7` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `tests/test_agents/test_stage_manager_phases.py:14` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `tests/test_agents/test_coach_agent.py:13` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `tests/test_agents/test_week6_edge_cases.py:13` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `tests/manual_adk_verification.py:12` | `from google.adk import Agent` | `from google.adk.agents import Agent` |
| `tests/test_performance/test_agent_caching.py:167,188` | `from google.adk import Agent` | `from google.adk.agents import Agent` |

#### Acceptance Criteria
- [ ] All `from google.adk import Agent` replaced with `from google.adk.agents import Agent`
- [ ] All unit tests pass
- [ ] Application starts without import errors
- [ ] Manual verification tests pass (`tests/manual_adk_verification.py`)

#### Test Commands
```bash
# Verify no old imports remain
grep -r "from google.adk import Agent" app/ tests/

# Run tests
pytest tests/test_adk_agents.py -v
pytest tests/test_agents/ -v
```

---

## Phase 2: Consolidate Session Management

### Ticket: IQS-XX - Replace Custom Session Management with ADK DatabaseSessionService

**Priority:** P0 - Critical
**Effort:** Large (1-2 days)
**Risk:** High (core functionality)

#### Problem
The current architecture has THREE layers of session management:

1. **`app/services/session_manager.py`** - Custom Firestore CRUD operations
2. **`app/services/adk_session_bridge.py`** - Bridges ADK InMemorySessionService to Firestore
3. **`app/services/turn_orchestrator.py`** - Creates new InMemorySessionService per request (!)

This is inefficient, error-prone, and doesn't leverage ADK's built-in persistence.

#### Current Anti-Pattern
```python
# turn_orchestrator.py - creates NEW session service each request
class TurnOrchestrator:
    def __init__(self, ...):
        self.adk_session_service = InMemorySessionService()  # Lost on each request!
```

#### Target Architecture
```python
# Use ADK's DatabaseSessionService with Cloud SQL or Firestore
from google.adk.sessions import DatabaseSessionService

# Single shared instance (singleton)
_session_service = None

def get_session_service() -> DatabaseSessionService:
    global _session_service
    if _session_service is None:
        _session_service = DatabaseSessionService(
            db_url=settings.database_url  # PostgreSQL/SQLite
        )
    return _session_service
```

#### Implementation Steps

1. **Add database for ADK sessions**
   - Option A: Use existing Firestore (requires custom adapter)
   - Option B: Add Cloud SQL PostgreSQL (recommended by ADK)
   - Option C: Use SQLite for simple deployments

2. **Create new `app/services/adk_session_service.py`**
   ```python
   from google.adk.sessions import DatabaseSessionService
   from app.config import get_settings

   settings = get_settings()
   _session_service: DatabaseSessionService = None

   def get_adk_session_service() -> DatabaseSessionService:
       global _session_service
       if _session_service is None:
           _session_service = DatabaseSessionService(
               db_url=settings.adk_database_url
           )
       return _session_service
   ```

3. **Migrate session data model**
   - ADK sessions have: `id`, `app_name`, `user_id`, `state`, `events`, `last_update_time`
   - Our sessions have additional: `location`, `user_email`, `user_name`, `expires_at`, `conversation_history`
   - Store app-specific data in `state` dict

4. **Update `turn_orchestrator.py`**
   - Remove `self.adk_session_service = InMemorySessionService()`
   - Use shared `get_adk_session_service()`
   - Store conversation history in ADK session state

5. **Update `session_manager.py`**
   - Keep Firestore for rate limiting and user metadata
   - Delegate session state/events to ADK session service
   - Or: migrate everything to ADK

6. **Deprecate `adk_session_bridge.py`**
   - No longer needed with native ADK persistence

#### Files to Modify
- `app/services/turn_orchestrator.py` - Use shared session service
- `app/services/session_manager.py` - Delegate to ADK or keep for metadata only
- `app/services/adk_session_bridge.py` - DELETE after migration
- `app/config.py` - Add `adk_database_url` setting
- `app/routers/sessions.py` - Update session creation/retrieval

#### Database Schema (ADK auto-creates)
```sql
-- ADK DatabaseSessionService creates these tables:
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    app_name TEXT,
    user_id TEXT,
    state JSON,
    last_update_time TIMESTAMP
);

CREATE TABLE events (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    event_data JSON,
    timestamp TIMESTAMP
);
```

#### Migration Strategy
1. Deploy new DatabaseSessionService alongside existing
2. New sessions use ADK service
3. Existing sessions continue with Firestore (read-only)
4. After N days, remove Firestore session code

#### Acceptance Criteria
- [ ] DatabaseSessionService configured and working
- [ ] Sessions persist across Cloud Run instance restarts
- [ ] Turn orchestrator uses shared session service
- [ ] All session-related tests pass
- [ ] No data loss during migration

---

## Phase 3: Integrate ADK Runner Properly

### Ticket: IQS-XX - Implement Singleton Runner Pattern with Proper Session Integration

**Priority:** P0 - Critical
**Effort:** Medium (4-8 hours)
**Risk:** Medium

#### Problem
Current implementation creates new Runner instance per turn:
```python
# Current - inefficient
async def execute_turn(self, session, user_input, turn_number):
    stage_manager = create_stage_manager(turn_number)
    runner = Runner(
        agent=stage_manager,
        app_name=settings.app_name,
        session_service=self.adk_session_service  # New each time!
    )
```

#### Target Implementation
```python
# Singleton runner with shared services
class TurnOrchestrator:
    _runner: Runner = None

    @classmethod
    def get_runner(cls) -> Runner:
        if cls._runner is None:
            cls._runner = Runner(
                agent=create_stage_manager(),
                app_name=settings.app_name,
                session_service=get_adk_session_service(),
                memory_service=get_memory_service(),  # Phase 4
            )
        return cls._runner

    async def execute_turn(self, session, user_input, turn_number):
        runner = self.get_runner()

        # Runner handles session automatically
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.session_id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )
        ):
            # Process events...
```

#### Key Changes
1. Make Runner a singleton or application-scoped instance
2. Agent can be recreated per turn (for phase changes) but Runner persists
3. Session service is shared across all requests
4. Remove manual session creation in `_run_agent_async`

#### Files to Modify
- `app/services/turn_orchestrator.py` - Singleton Runner pattern
- `app/main.py` - Initialize Runner on startup
- `app/routers/sessions.py` - Use shared orchestrator

#### Acceptance Criteria
- [ ] Single Runner instance serves all requests
- [ ] Session continuity works across multiple turns
- [ ] Performance improved (no Runner recreation)
- [ ] Memory usage stable under load

---

## Phase 4: Add Memory Service

### Ticket: IQS-XX - Integrate ADK MemoryService for Cross-Session Learning

**Priority:** P1 - High
**Effort:** Medium (4-8 hours)
**Risk:** Low (additive feature)

#### Problem
Currently, each session starts fresh with no memory of past interactions. Users can't build on previous sessions.

#### Opportunity
ADK's `MemoryService` enables:
- Storing insights from past sessions
- Retrieving relevant memories via vector search
- Building personalized agent responses

#### Implementation

1. **Add VertexAI Memory Bank configuration**
   ```python
   from google.adk.memory import VertexAiMemoryBankService

   memory_service = VertexAiMemoryBankService(
       project=settings.gcp_project_id,
       location=settings.gcp_location,
       agent_engine_id=settings.agent_engine_id  # Optional
   )
   ```

2. **Connect to Runner**
   ```python
   runner = Runner(
       agent=stage_manager,
       app_name=settings.app_name,
       session_service=session_service,
       memory_service=memory_service  # NEW
   )
   ```

3. **Auto-save sessions to memory**
   ```python
   # After session ends, save insights to memory
   await memory_service.add_session_to_memory(session)
   ```

4. **Search memories in prompts**
   ```python
   # Retrieve relevant past interactions
   memories = await memory_service.search_memory(
       app_name=settings.app_name,
       user_id=user_id,
       query="improv techniques they've practiced"
   )
   ```

#### Use Cases
- "Remember when the user struggled with 'Yes, and...' last session"
- "This user prefers sci-fi scenes"
- "User has completed 10 sessions, gradually improve difficulty"

#### Files to Modify
- `app/services/adk_memory_service.py` - NEW
- `app/services/turn_orchestrator.py` - Connect memory service
- `app/routers/sessions.py` - Save to memory on session close
- `app/config.py` - Add memory service settings

#### Acceptance Criteria
- [ ] Memory service configured and connected
- [ ] Session insights automatically saved after completion
- [ ] Agent can retrieve relevant memories
- [ ] No performance regression

---

## Phase 5: Standardize Observability

### Ticket: IQS-XX - Leverage ADK Native Observability Instead of Custom OpenTelemetry

**Priority:** P2 - Medium
**Effort:** Medium (4-8 hours)
**Risk:** Low

#### Problem
`app/services/adk_observability.py` manually configures OpenTelemetry, but ADK has built-in instrumentation that auto-creates spans for:
- `invocation` - Overall agent invocation
- `agent_run` - Individual agent execution
- `call_llm` - LLM API calls
- `execute_tool` - Tool executions

#### Current Implementation
```python
# Custom manual setup
class ADKObservability:
    def _initialize_providers(self):
        self._tracer_provider = TracerProvider(resource=resource)
        cloud_trace_exporter = CloudTraceSpanExporter(...)
        # ... manual configuration
```

#### Target Implementation
```python
# Let ADK handle tracing, just configure exporter
import os

# ADK reads these environment variables
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://cloudtrace.googleapis.com"
os.environ["GOOGLE_CLOUD_PROJECT"] = settings.gcp_project_id

# ADK automatically instruments agents
```

#### Changes
1. Simplify `adk_observability.py` to just configure exporters
2. Remove manual span creation that duplicates ADK
3. Keep custom attributes/metrics that ADK doesn't provide
4. Verify Cloud Trace shows ADK-native spans

#### Files to Modify
- `app/services/adk_observability.py` - Simplify
- `app/main.py` - Configure environment variables
- Remove custom span creation throughout codebase

#### Acceptance Criteria
- [ ] ADK native spans appear in Cloud Trace
- [ ] Custom metrics still work
- [ ] Less code to maintain
- [ ] No duplicate spans

---

## Phase 6: Add ADK Evaluation Framework

### Ticket: IQS-XX - Implement ADK Evaluation for Agent Quality Testing

**Priority:** P3 - Low
**Effort:** Small (2-4 hours)
**Risk:** Low (additive)

#### Opportunity
ADK provides evaluation framework for:
- Testing response quality
- Validating agent behavior
- Regression testing for prompts

#### Implementation
```bash
# Create evaluation test cases
adk eval create --test-file tests/eval/improv_scenarios.json

# Run evaluations
adk eval run --agent stage_manager
```

#### Test Case Structure
```json
{
  "test_cases": [
    {
      "name": "phase_1_supportive_response",
      "input": "Let's explore this abandoned spaceship!",
      "expected": {
        "contains": ["Yes", "and"],
        "sentiment": "positive",
        "no_blocking": true
      }
    },
    {
      "name": "phase_2_fallible_response",
      "input": "Quick, we need to fix the engine!",
      "expected": {
        "realistic_friction": true,
        "still_collaborative": true
      }
    }
  ]
}
```

#### Files to Create
- `tests/eval/improv_scenarios.json` - Test cases
- `tests/eval/evaluation_config.yaml` - Evaluation config
- CI integration for automated evaluation

#### Acceptance Criteria
- [ ] Evaluation test cases defined
- [ ] Can run evaluations via CLI
- [ ] CI/CD integration
- [ ] Baseline metrics established

---

## Phase 7: Cleanup Legacy Code

### Ticket: IQS-XX - Remove Deprecated Code and Update Documentation

**Priority:** P2 - Medium
**Effort:** Small (2-4 hours)
**Risk:** Low

#### Files to Delete/Deprecate

| File | Action | Reason |
|------|--------|--------|
| `app/services/adk_agent.py` | DELETE | Uses raw VertexAI SDK, not ADK. Confusing name. |
| `app/services/adk_session_bridge.py` | DELETE | Replaced by DatabaseSessionService in Phase 2 |

#### Files to Update

| File | Update |
|------|--------|
| `tests/manual_adk_verification.py` | Update assertions for new import paths |
| `QA_REPORT_WEEK5_ADK_REWRITE.md` | Update to reflect new architecture |
| `WEEK7_IMPLEMENTATION_SUMMARY.md` | Update Runner documentation |
| `README.md` | Update architecture diagram |

#### Code Cleanup
- Remove unused imports
- Update type hints for new ADK classes
- Remove TODO comments for completed items

#### Acceptance Criteria
- [ ] No deprecated files remain
- [ ] Documentation reflects current architecture
- [ ] No unused imports
- [ ] All tests pass

---

## Implementation Order

```
Phase 1 (Import Paths)
    │
    ▼
Phase 2 (Session Management) ──────┐
    │                               │
    ▼                               │
Phase 3 (Runner Integration) ◄─────┘
    │
    ├──────────────┬──────────────┐
    ▼              ▼              ▼
Phase 4        Phase 5        Phase 6
(Memory)    (Observability)  (Evaluation)
    │              │              │
    └──────────────┴──────────────┘
                   │
                   ▼
              Phase 7
            (Cleanup)
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Data loss during session migration | Run parallel systems, migrate gradually |
| Performance regression | Benchmark before/after each phase |
| Breaking changes in ADK | Pin to specific version, test thoroughly |
| Cloud SQL costs | Start with SQLite, upgrade if needed |

---

## Success Metrics

- **Performance:** Turn execution time < 3s (currently ~5s)
- **Reliability:** 99.9% success rate on turn execution
- **Maintainability:** 30% reduction in session-related code
- **Features:** Cross-session memory enables personalization

---

## Next Steps

1. Create Linear tickets for each phase
2. Prioritize Phase 1-3 as P0 blockers
3. Assign owners and set sprint goals
4. Begin Phase 1 immediately (import path fixes)
