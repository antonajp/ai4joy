# Integration Test Requirements

**Status**: Documentation Only - Implementation Requires Real Infrastructure
**Created**: 2025-11-24
**Branch**: IQS-46

## Overview

This document specifies the integration tests that should be implemented once real ADK and Firestore infrastructure is available. Current tests use mocks; these tests would validate actual system behavior.

---

## 1. Real ADK Integration Test

**File**: `tests/integration/test_real_adk_execution.py`

**Purpose**: Validate that the turn orchestrator correctly executes real ADK agents and parses their responses.

### Prerequisites
- VertexAI credentials configured
- GCP project with ADK enabled
- Test quota allocation

### Test Cases

#### TC-REAL-ADK-01: Basic Turn Execution
```python
async def test_real_adk_turn_execution():
    """Execute a single turn with real ADK agents"""
    # Setup
    session = create_test_session(location="Mars Colony")
    orchestrator = TurnOrchestrator(session_manager)

    # Execute
    response = await orchestrator.execute_turn(
        session=session,
        user_input="Hello, I'm an astronaut!",
        turn_number=1
    )

    # Assert
    assert response["partner_response"]  # Not empty
    assert len(response["partner_response"]) > 20  # Substantial response
    assert response["room_vibe"]["analysis"]  # Has room analysis
    assert response["current_phase"] == 1  # Phase 1 for turn 1
    assert response["coach_feedback"] is None  # No coach before turn 15
```

#### TC-REAL-ADK-02: Phase Transition at Turn 5
```python
async def test_real_phase_transition():
    """Verify partner behavior changes between Phase 1 and Phase 2"""
    session = create_test_session()
    orchestrator = TurnOrchestrator(session_manager)

    # Execute turns 1-6
    responses = []
    for turn in range(1, 7):
        response = await orchestrator.execute_turn(
            session=session,
            user_input=f"Turn {turn} input",
            turn_number=turn
        )
        responses.append(response)

    # Assert phase transitions
    assert all(r["current_phase"] == 1 for r in responses[:4])  # Turns 1-4
    assert all(r["current_phase"] == 2 for r in responses[4:])  # Turns 5-6

    # Assert behavioral differences (qualitative check)
    # Phase 2 responses should be less "perfect" - may require manual review
```

#### TC-REAL-ADK-03: Coach Feedback at Turn 15
```python
async def test_real_coach_feedback():
    """Verify coach agent provides feedback at turn 15+"""
    session = create_test_session()
    orchestrator = TurnOrchestrator(session_manager)

    # Fast-forward to turn 15
    for turn in range(1, 16):
        response = await orchestrator.execute_turn(
            session=session,
            user_input=f"Improv line {turn}",
            turn_number=turn
        )

    # Assert coach feedback present
    assert response["coach_feedback"] is not None
    assert len(response["coach_feedback"]) > 50  # Substantial feedback
    # Check for coaching keywords (optional)
    feedback_lower = response["coach_feedback"].lower()
    assert any(word in feedback_lower for word in ["good", "try", "principle", "improve"])
```

#### TC-REAL-ADK-04: Response Parsing with Real Output
```python
async def test_real_response_parsing():
    """Validate parsing logic works with actual ADK agent responses"""
    session = create_test_session()
    orchestrator = TurnOrchestrator(session_manager)

    response = await orchestrator.execute_turn(
        session=session,
        user_input="Let's start an improv scene!",
        turn_number=1
    )

    # Validate parsing succeeded
    assert response["partner_response"]  # Partner section parsed
    assert response["room_vibe"]["analysis"]  # Room section parsed
    assert "timestamp" in response
    assert "turn_number" in response
```

#### TC-REAL-ADK-05: Timeout Handling
```python
async def test_real_adk_timeout():
    """Verify timeout mechanism works with real agents"""
    session = create_test_session()
    orchestrator = TurnOrchestrator(session_manager)

    # Execute with very short timeout (should fail)
    with pytest.raises(asyncio.TimeoutError):
        await orchestrator._run_agent_async(
            runner=create_runner(),
            prompt="Test prompt",
            timeout=0.001  # 1ms timeout (guaranteed to fail)
        )
```

### Success Criteria
- All 5 test cases pass with real ADK
- No response parsing errors
- Phase transitions occur correctly
- Coach appears at turn 15+
- Timeout mechanism prevents hangs

---

## 2. Real Firestore Integration Test

**File**: `tests/integration/test_real_firestore_persistence.py`

**Purpose**: Validate session state persistence and transaction safety with real Firestore.

### Prerequisites
- Firestore test database configured
- Service account credentials
- Test collection: `test_sessions`

### Test Cases

#### TC-FIRESTORE-01: Session Creation and Retrieval
```python
async def test_create_and_retrieve_session():
    """Create session in Firestore and retrieve it"""
    manager = SessionManager()

    # Create
    session = await manager.create_session(
        user_id="test_user_123",
        user_email="test@example.com",
        session_data=SessionCreate(location="Test Location")
    )

    # Retrieve
    retrieved = await manager.get_session(session.session_id)

    # Assert
    assert retrieved is not None
    assert retrieved.session_id == session.session_id
    assert retrieved.user_id == "test_user_123"
    assert retrieved.location == "Test Location"
    assert retrieved.turn_count == 0

    # Cleanup
    await manager.close_session(session.session_id)
```

#### TC-FIRESTORE-02: Atomic Turn Update
```python
async def test_atomic_session_update():
    """Verify turn updates are atomic"""
    manager = SessionManager()
    session = await manager.create_session(...)

    # Prepare turn data
    turn_data = {
        "turn_number": 1,
        "user_input": "Hello",
        "partner_response": "Hi there!",
        "room_vibe": {"energy": "positive"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Atomic update
    await manager.update_session_atomic(
        session_id=session.session_id,
        turn_data=turn_data,
        new_phase="PHASE_1",
        new_status=SessionStatus.ACTIVE
    )

    # Retrieve and verify all fields updated
    updated = await manager.get_session(session.session_id)
    assert updated.turn_count == 1
    assert len(updated.conversation_history) == 1
    assert updated.current_phase == "PHASE_1"
    assert updated.status == SessionStatus.ACTIVE

    # Cleanup
    await manager.close_session(session.session_id)
```

#### TC-FIRESTORE-03: Concurrent Update Safety
```python
async def test_concurrent_turn_updates():
    """Verify transaction safety with concurrent updates"""
    manager = SessionManager()
    session = await manager.create_session(...)

    # Attempt concurrent updates (should be serialized by Firestore)
    async def update_turn(turn_num):
        turn_data = {
            "turn_number": turn_num,
            "user_input": f"Input {turn_num}",
            "partner_response": f"Response {turn_num}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await manager.update_session_atomic(
            session_id=session.session_id,
            turn_data=turn_data
        )

    # Execute 5 concurrent updates
    await asyncio.gather(*[update_turn(i) for i in range(1, 6)])

    # Verify final state
    final = await manager.get_session(session.session_id)
    assert final.turn_count == 5
    assert len(final.conversation_history) == 5

    # Cleanup
    await manager.close_session(session.session_id)
```

#### TC-FIRESTORE-04: Session Expiration
```python
async def test_session_expiration():
    """Verify expired sessions are not retrieved"""
    manager = SessionManager()

    # Create session with 1-second expiration
    session = await manager.create_session(...)
    # Manually set expiration in past
    doc_ref = manager.collection.document(session.session_id)
    doc_ref.update({
        "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    })

    # Attempt retrieval
    retrieved = await manager.get_session(session.session_id)

    # Assert expired session returns None
    assert retrieved is None
```

#### TC-FIRESTORE-05: Turn Sequence Validation
```python
async def test_turn_sequence_enforcement():
    """Verify turn sequence is enforced"""
    manager = SessionManager()
    session = await manager.create_session(...)

    # Add turn 1
    await manager.update_session_atomic(
        session_id=session.session_id,
        turn_data={"turn_number": 1, "user_input": "First"}
    )

    # Attempt to add turn 3 (skipping turn 2) - should fail or be handled
    # Implementation depends on whether we add turn sequence validation
    # Current implementation doesn't check, but should be added
```

### Success Criteria
- All 5 test cases pass with real Firestore
- Transactions ensure atomic updates
- Concurrent updates handled correctly
- Session expiration works
- Data persists correctly

---

## 3. End-to-End Integration Test

**File**: `tests/integration/test_e2e_turn_flow.py`

**Purpose**: Validate complete turn flow from API endpoint to Firestore persistence.

### Prerequisites
- Running FastAPI application
- Real ADK credentials
- Real Firestore database
- IAP authentication headers (or mock)

### Test Cases

#### TC-E2E-01: Complete 15-Turn Session
```python
async def test_complete_session_flow():
    """Execute a full 15-turn session end-to-end"""
    # Create session via API
    response = await client.post("/api/v1/session/start", json={
        "location": "Spaceship Bridge"
    })
    session_id = response.json()["session_id"]

    # Execute 15 turns
    for turn_num in range(1, 16):
        turn_response = await client.post(
            f"/api/v1/session/{session_id}/turn",
            json={
                "user_input": f"Improv line {turn_num}",
                "turn_number": turn_num
            }
        )
        assert turn_response.status_code == 200
        data = turn_response.json()

        # Validate response structure
        assert "partner_response" in data
        assert "room_vibe" in data
        assert "current_phase" in data

        # Check phase transitions
        if turn_num <= 4:
            assert data["current_phase"] == 1
        else:
            assert data["current_phase"] == 2

        # Check coach feedback at turn 15
        if turn_num >= 15:
            assert data["coach_feedback"] is not None

    # Close session
    await client.post(f"/api/v1/session/{session_id}/close")
```

#### TC-E2E-02: Error Handling
```python
async def test_e2e_error_scenarios():
    """Validate error handling throughout the stack"""
    # Test: Invalid session ID
    response = await client.post("/api/v1/session/invalid_id/turn", ...)
    assert response.status_code == 404

    # Test: Out-of-sequence turn number
    session_id = await create_session()
    response = await client.post(f"/api/v1/session/{session_id}/turn", json={
        "user_input": "Hello",
        "turn_number": 5  # Skipped turns 1-4
    })
    assert response.status_code == 400
```

### Success Criteria
- 15-turn session completes successfully
- All phases transition correctly
- Coach appears at turn 15
- Error scenarios handled gracefully
- Data persists in Firestore

---

## Implementation Plan

### Phase 1: Setup (2 hours)
1. Configure test GCP project
2. Set up Firestore test database
3. Configure VertexAI test credentials
4. Create test fixtures and helpers

### Phase 2: ADK Tests (3 hours)
1. Implement TC-REAL-ADK-01 through TC-REAL-ADK-05
2. Run tests and debug issues
3. Document any ADK-specific quirks

### Phase 3: Firestore Tests (2 hours)
1. Implement TC-FIRESTORE-01 through TC-FIRESTORE-05
2. Verify transaction behavior
3. Test concurrent access patterns

### Phase 4: E2E Tests (3 hours)
1. Implement TC-E2E-01 and TC-E2E-02
2. Set up test authentication
3. Run full system validation

**Total Estimated Time**: 10 hours

---

## Acceptance Criteria

- [ ] All ADK integration tests pass (5/5)
- [ ] All Firestore integration tests pass (5/5)
- [ ] All E2E integration tests pass (2/2)
- [ ] Tests can run in CI/CD pipeline
- [ ] Test cleanup leaves no orphaned data
- [ ] Tests documented and maintainable

---

## Notes

**Why Not Implemented Now**:
- Requires real GCP infrastructure (costs money)
- Needs production-like environment setup
- Current mocked tests validate logic sufficiently
- Integration tests are better suited for staging/pre-prod environments

**When to Implement**:
- Before first production deployment
- As part of staging environment setup
- When setting up CI/CD pipeline
- During performance testing phase

**Alternative Approaches**:
- Use ADK emulator if available
- Use Firestore emulator for local testing
- Implement as part of smoke tests in staging
