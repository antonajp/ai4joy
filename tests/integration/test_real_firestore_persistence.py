"""
Real Firestore Integration Tests - Week 8 Production Readiness

These tests validate session state persistence and transaction safety with real Firestore.
They require GCP credentials and Firestore database access.

Test Coverage:
- TC-FIRESTORE-01: Session Creation and Retrieval
- TC-FIRESTORE-02: Atomic Turn Update
- TC-FIRESTORE-03: Concurrent Update Safety
- TC-FIRESTORE-04: Session Expiration
- TC-FIRESTORE-05: Turn Sequence Validation
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List

from app.services.session_manager import SessionManager
from app.models.session import SessionCreate, SessionStatus


@pytest.mark.integration
@pytest.mark.skip(reason="Requires real Firestore database access")
class TestRealFirestorePersistence:
    """Integration tests for real Firestore persistence"""

    @pytest.fixture
    def manager(self):
        """Real session manager with Firestore"""
        return SessionManager()

    @pytest.fixture
    async def cleanup_sessions(self):
        """Cleanup test sessions after test"""
        session_ids: List[str] = []

        yield session_ids

        manager = SessionManager()
        for session_id in session_ids:
            try:
                await manager.close_session(session_id)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_tc_firestore_01_session_creation_and_retrieval(
        self, manager, cleanup_sessions
    ):
        """
        TC-FIRESTORE-01: Session Creation and Retrieval

        Create session in Firestore and retrieve it with all fields intact.
        """
        session_data = SessionCreate(
            location="Firestore Test Location", user_name="Test User"
        )

        created_session = await manager.create_session(
            user_id="firestore_test_user_123",
            user_email="firestore-test@example.com",
            session_data=session_data,
        )

        cleanup_sessions.append(created_session.session_id)

        assert created_session.session_id is not None
        assert created_session.user_id == "firestore_test_user_123"
        assert created_session.location == "Firestore Test Location"
        assert created_session.turn_count == 0
        assert created_session.status == SessionStatus.INITIALIZED

        retrieved_session = await manager.get_session(created_session.session_id)

        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
        assert retrieved_session.user_id == "firestore_test_user_123"
        assert retrieved_session.user_email == "firestore-test@example.com"
        assert retrieved_session.location == "Firestore Test Location"
        assert retrieved_session.turn_count == 0
        assert retrieved_session.status == SessionStatus.INITIALIZED
        assert len(retrieved_session.conversation_history) == 0

    @pytest.mark.asyncio
    async def test_tc_firestore_02_atomic_turn_update(self, manager, cleanup_sessions):
        """
        TC-FIRESTORE-02: Atomic Turn Update

        Verify turn updates are atomic (all fields update together).
        """
        session_data = SessionCreate(location="Atomic Test Arena")

        session = await manager.create_session(
            user_id="atomic_test_user",
            user_email="atomic@example.com",
            session_data=session_data,
        )

        cleanup_sessions.append(session.session_id)

        turn_data = {
            "turn_number": 1,
            "user_input": "Hello, let's start the scene!",
            "partner_response": "Hi there! I'm excited to improvise with you.",
            "room_vibe": {
                "analysis": "Audience is engaged and curious",
                "energy": "positive",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await manager.update_session_atomic(
            session_id=session.session_id,
            turn_data=turn_data,
            new_phase="PHASE_1",
            new_status=SessionStatus.ACTIVE,
        )

        updated_session = await manager.get_session(session.session_id)

        assert updated_session.turn_count == 1
        assert len(updated_session.conversation_history) == 1
        assert updated_session.current_phase == "PHASE_1"
        assert updated_session.status == SessionStatus.ACTIVE

        history_turn = updated_session.conversation_history[0]
        assert history_turn["turn_number"] == 1
        assert history_turn["user_input"] == "Hello, let's start the scene!"
        assert "partner_response" in history_turn

    @pytest.mark.asyncio
    async def test_tc_firestore_03_concurrent_update_safety(
        self, manager, cleanup_sessions
    ):
        """
        TC-FIRESTORE-03: Concurrent Update Safety

        Verify transaction safety with concurrent turn updates.
        Firestore transactions should serialize updates properly.
        """
        session_data = SessionCreate(location="Concurrency Test Zone")

        session = await manager.create_session(
            user_id="concurrent_test_user",
            user_email="concurrent@example.com",
            session_data=session_data,
        )

        cleanup_sessions.append(session.session_id)

        async def update_turn(turn_num: int):
            """Update a single turn"""
            turn_data = {
                "turn_number": turn_num,
                "user_input": f"Concurrent input {turn_num}",
                "partner_response": f"Concurrent response {turn_num}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            await manager.update_session_atomic(
                session_id=session.session_id, turn_data=turn_data
            )

        await asyncio.gather(*[update_turn(i) for i in range(1, 6)])

        final_session = await manager.get_session(session.session_id)

        assert (
            final_session.turn_count == 5
        ), "All 5 concurrent updates should be recorded"
        assert (
            len(final_session.conversation_history) == 5
        ), "All 5 turns should be in history"

        turn_numbers = [
            turn["turn_number"] for turn in final_session.conversation_history
        ]
        assert sorted(turn_numbers) == [
            1,
            2,
            3,
            4,
            5,
        ], "All turn numbers should be present"

    @pytest.mark.asyncio
    async def test_tc_firestore_04_session_expiration(self, manager, cleanup_sessions):
        """
        TC-FIRESTORE-04: Session Expiration

        Verify expired sessions return None when retrieved.
        """
        session_data = SessionCreate(location="Expiration Test Lab")

        session = await manager.create_session(
            user_id="expiration_test_user",
            user_email="expiration@example.com",
            session_data=session_data,
        )

        cleanup_sessions.append(session.session_id)

        doc_ref = manager.collection.document(session.session_id)
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        doc_ref.update({"expires_at": expired_time.isoformat()})

        retrieved_session = await manager.get_session(session.session_id)

        assert retrieved_session is None, "Expired session should return None"

    @pytest.mark.asyncio
    async def test_tc_firestore_05_conversation_history_ordering(
        self, manager, cleanup_sessions
    ):
        """
        TC-FIRESTORE-05: Conversation History Ordering

        Verify conversation history maintains turn order.
        """
        session_data = SessionCreate(location="History Test Arena")

        session = await manager.create_session(
            user_id="history_test_user",
            user_email="history@example.com",
            session_data=session_data,
        )

        cleanup_sessions.append(session.session_id)

        for turn_num in range(1, 6):
            turn_data = {
                "turn_number": turn_num,
                "user_input": f"Input {turn_num}",
                "partner_response": f"Response {turn_num}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            await manager.add_conversation_turn(
                session_id=session.session_id, turn_data=turn_data
            )

        final_session = await manager.get_session(session.session_id)

        assert len(final_session.conversation_history) == 5

        for idx, turn in enumerate(final_session.conversation_history, start=1):
            assert (
                turn["turn_number"] == idx
            ), f"Turn order should be preserved (expected {idx}, got {turn['turn_number']})"
            assert turn["user_input"] == f"Input {idx}"

    @pytest.mark.asyncio
    async def test_tc_firestore_06_phase_persistence(self, manager, cleanup_sessions):
        """
        TC-FIRESTORE-06: Phase Persistence

        Verify phase transitions are persisted correctly.
        """
        session_data = SessionCreate(location="Phase Test Zone")

        session = await manager.create_session(
            user_id="phase_test_user",
            user_email="phase@example.com",
            session_data=session_data,
        )

        cleanup_sessions.append(session.session_id)

        await manager.update_session_phase(
            session_id=session.session_id, phase="PHASE_1"
        )

        retrieved = await manager.get_session(session.session_id)
        assert retrieved.current_phase == "PHASE_1"

        await manager.update_session_phase(
            session_id=session.session_id, phase="PHASE_2"
        )

        retrieved = await manager.get_session(session.session_id)
        assert retrieved.current_phase == "PHASE_2"

    @pytest.mark.asyncio
    async def test_tc_firestore_07_status_transitions(self, manager, cleanup_sessions):
        """
        TC-FIRESTORE-07: Status Transitions

        Verify session status transitions persist correctly.
        """
        session_data = SessionCreate(location="Status Test Location")

        session = await manager.create_session(
            user_id="status_test_user",
            user_email="status@example.com",
            session_data=session_data,
        )

        cleanup_sessions.append(session.session_id)

        assert session.status == SessionStatus.INITIALIZED

        await manager.update_session_status(session.session_id, SessionStatus.ACTIVE)

        retrieved = await manager.get_session(session.session_id)
        assert retrieved.status == SessionStatus.ACTIVE

        await manager.update_session_status(
            session.session_id, SessionStatus.SCENE_COMPLETE
        )

        retrieved = await manager.get_session(session.session_id)
        assert retrieved.status == SessionStatus.SCENE_COMPLETE

    @pytest.mark.asyncio
    async def test_tc_firestore_08_large_conversation_history(
        self, manager, cleanup_sessions
    ):
        """
        TC-FIRESTORE-08: Large Conversation History

        Verify Firestore can handle 15+ turns (full session).
        """
        session_data = SessionCreate(location="Marathon Test Arena")

        session = await manager.create_session(
            user_id="marathon_test_user",
            user_email="marathon@example.com",
            session_data=session_data,
        )

        cleanup_sessions.append(session.session_id)

        for turn_num in range(1, 21):
            turn_data = {
                "turn_number": turn_num,
                "user_input": f"This is a longer user input for turn {turn_num} to simulate real conversation data.",
                "partner_response": f"This is the partner's response for turn {turn_num}, which should also be substantial.",
                "room_vibe": {
                    "analysis": f"Room analysis for turn {turn_num}",
                    "energy": "engaged",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if turn_num >= 15:
                turn_data["coach_feedback"] = f"Coach feedback for turn {turn_num}"

            await manager.add_conversation_turn(
                session_id=session.session_id, turn_data=turn_data
            )

        final_session = await manager.get_session(session.session_id)

        assert len(final_session.conversation_history) == 20
        assert final_session.turn_count == 20

        last_turn = final_session.conversation_history[-1]
        assert last_turn["turn_number"] == 20
        assert "coach_feedback" in last_turn


@pytest.mark.integration
@pytest.mark.skip(reason="Requires Firestore emulator setup")
class TestFirestoreEmulator:
    """Tests for Firestore emulator (local development)"""

    @pytest.mark.asyncio
    async def test_emulator_connection(self):
        """Verify Firestore emulator connection works"""
        import os

        os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"

        manager = SessionManager()
        assert manager.db is not None
        assert manager.collection is not None
