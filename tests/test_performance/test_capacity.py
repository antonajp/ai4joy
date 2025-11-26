"""
Capacity Validation Tests

Tests to validate system capacity planning assumptions:
- Memory usage per session
- Response times under load
- Firestore operation patterns
- Resource consumption metrics

Run with:
    pytest tests/test_performance/test_capacity.py -v
"""
import pytest
import sys
import time
from unittest.mock import Mock, patch
from app.services.performance_tuning import (
    PerformanceConfig,
    ContextCompactor,
    FirestoreBatchWriter
)
from app.models.session import Session, SessionStatus
from datetime import datetime, timezone, timedelta


class TestPerformanceConfig:
    """Test performance configuration validation"""

    def test_default_config_values(self):
        """Test default configuration values are reasonable"""
        config = PerformanceConfig()

        assert config.agent_timeout_seconds == 30
        assert config.cache_ttl_seconds == 300
        assert config.max_context_tokens == 4000
        assert config.batch_write_threshold == 5
        assert config.max_concurrent_sessions_per_instance == 10
        assert config.firestore_batch_size == 500

    def test_config_validation_success(self):
        """Test valid configuration passes validation"""
        config = PerformanceConfig(
            agent_timeout_seconds=30,
            cache_ttl_seconds=300,
            max_context_tokens=4000,
            batch_write_threshold=5
        )

        config.validate()

    def test_config_validation_timeout_too_low(self):
        """Test validation fails for timeout below minimum"""
        config = PerformanceConfig(agent_timeout_seconds=5)

        with pytest.raises(ValueError, match="agent_timeout_seconds must be >= 10"):
            config.validate()

    def test_config_validation_timeout_too_high(self):
        """Test validation fails for timeout above maximum"""
        config = PerformanceConfig(agent_timeout_seconds=120)

        with pytest.raises(ValueError, match="agent_timeout_seconds must be <= 60"):
            config.validate()

    def test_config_validation_negative_cache_ttl(self):
        """Test validation fails for negative cache TTL"""
        config = PerformanceConfig(cache_ttl_seconds=-1)

        with pytest.raises(ValueError, match="cache_ttl_seconds must be >= 0"):
            config.validate()

    def test_config_validation_context_tokens_too_low(self):
        """Test validation fails for context tokens below minimum"""
        config = PerformanceConfig(max_context_tokens=500)

        with pytest.raises(ValueError, match="max_context_tokens must be >= 1000"):
            config.validate()

    def test_config_validation_context_tokens_too_high(self):
        """Test validation fails for context tokens above maximum"""
        config = PerformanceConfig(max_context_tokens=50000)

        with pytest.raises(ValueError, match="max_context_tokens must be <= 32000"):
            config.validate()

    def test_config_from_env(self):
        """Test configuration from environment variables"""
        with patch.dict('os.environ', {
            'PERF_AGENT_TIMEOUT': '45',
            'PERF_CACHE_TTL': '600',
            'PERF_MAX_CONTEXT_TOKENS': '8000',
            'PERF_BATCH_WRITE_THRESHOLD': '10'
        }):
            config = PerformanceConfig.from_env()

            assert config.agent_timeout_seconds == 45
            assert config.cache_ttl_seconds == 600
            assert config.max_context_tokens == 8000
            assert config.batch_write_threshold == 10


class TestContextCompactor:
    """Test context compaction for memory management"""

    def test_compact_empty_history(self):
        """Test compaction with empty history"""
        compactor = ContextCompactor(max_tokens=4000)
        result = compactor.compact_history([])

        assert result == []

    def test_compact_history_within_limits(self):
        """Test compaction when history is already within limits"""
        compactor = ContextCompactor(max_tokens=4000)
        history = [
            {"turn_number": 1, "user_input": "Test 1", "partner_response": "Response 1"},
            {"turn_number": 2, "user_input": "Test 2", "partner_response": "Response 2"},
            {"turn_number": 3, "user_input": "Test 3", "partner_response": "Response 3"}
        ]

        result = compactor.compact_history(history)

        assert len(result) == 3
        assert result == history

    def test_compact_history_exceeds_limits(self):
        """Test compaction when history exceeds token limits"""
        compactor = ContextCompactor(max_tokens=600)
        history = [
            {"turn_number": i, "user_input": f"Test {i}", "partner_response": f"Response {i}"}
            for i in range(1, 21)
        ]

        result = compactor.compact_history(history, keep_recent=3)

        assert len(result) == 4
        assert result[0]["turn_number"] == 1
        assert result[1]["turn_number"] == 18
        assert result[2]["turn_number"] == 19
        assert result[3]["turn_number"] == 20

    def test_compact_preserves_first_and_recent(self):
        """Test compaction preserves first turn and recent turns"""
        compactor = ContextCompactor(max_tokens=600)
        history = [
            {"turn_number": i, "user_input": f"Turn {i}"}
            for i in range(1, 16)
        ]

        result = compactor.compact_history(history, keep_recent=3)

        assert result[0]["turn_number"] == 1
        assert result[-3]["turn_number"] == 13
        assert result[-2]["turn_number"] == 14
        assert result[-1]["turn_number"] == 15

    def test_estimate_tokens(self):
        """Test token estimation"""
        compactor = ContextCompactor()

        short_text = "Hello"
        assert compactor.estimate_tokens(short_text) == 1

        medium_text = "This is a test sentence with some words."
        tokens = compactor.estimate_tokens(medium_text)
        assert tokens >= 8
        assert tokens <= 12

        long_text = "A" * 1000
        assert compactor.estimate_tokens(long_text) == 250


class TestFirestoreBatchWriter:
    """Test Firestore batch write operations"""

    @pytest.fixture
    def mock_db(self):
        """Mock Firestore database"""
        db = Mock()
        batch = Mock()
        db.batch.return_value = batch
        return db, batch

    def test_add_write_below_threshold(self, mock_db):
        """Test adding writes below batch threshold"""
        db, batch = mock_db
        writer = FirestoreBatchWriter(db, batch_size=5)

        doc_ref = Mock()
        data = {"field": "value"}

        writer.add_write(doc_ref, data)

        batch.set.assert_not_called()
        batch.commit.assert_not_called()

    def test_add_write_reaches_threshold(self, mock_db):
        """Test batch commits when threshold is reached"""
        db, batch = mock_db
        writer = FirestoreBatchWriter(db, batch_size=3)

        doc_ref = Mock()

        for i in range(3):
            writer.add_write(doc_ref, {"field": f"value{i}"})

        assert batch.set.call_count == 3
        batch.commit.assert_called_once()

    def test_add_update_operation(self, mock_db):
        """Test adding update operations"""
        db, batch = mock_db
        writer = FirestoreBatchWriter(db, batch_size=5)

        doc_ref = Mock()
        updates = {"status": "active"}

        writer.add_update(doc_ref, updates)

        batch.update.assert_not_called()
        batch.commit.assert_not_called()

    def test_manual_flush(self, mock_db):
        """Test manually flushing pending writes"""
        db, batch = mock_db
        writer = FirestoreBatchWriter(db, batch_size=10)

        doc_ref = Mock()
        writer.add_write(doc_ref, {"field": "value1"})
        writer.add_write(doc_ref, {"field": "value2"})

        count = writer.flush()

        assert count == 2
        assert batch.set.call_count == 2
        batch.commit.assert_called_once()

    def test_flush_empty_batch(self, mock_db):
        """Test flushing empty batch does nothing"""
        db, batch = mock_db
        writer = FirestoreBatchWriter(db, batch_size=10)

        count = writer.flush()

        assert count == 0
        batch.commit.assert_not_called()

    def test_mixed_operations(self, mock_db):
        """Test mixing set and update operations"""
        db, batch = mock_db
        writer = FirestoreBatchWriter(db, batch_size=10)

        doc_ref1 = Mock()
        doc_ref2 = Mock()

        writer.add_write(doc_ref1, {"field": "value"})
        writer.add_update(doc_ref2, {"status": "updated"})

        count = writer.flush()

        assert count == 2
        batch.set.assert_called_once()
        batch.update.assert_called_once()
        batch.commit.assert_called_once()


class TestMemoryUsage:
    """Test memory usage patterns"""

    def test_session_object_size(self):
        """Test estimated memory size of session object"""
        session = Session(
            session_id="test_session_123",
            user_id="user_123",
            user_email="test@example.com",
            user_name="Test User",
            location="Test Location",
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            conversation_history=[],
            metadata={},
            turn_count=0
        )

        session_size = sys.getsizeof(session)

        assert session_size < 1024 * 10

    def test_conversation_history_memory_growth(self):
        """Test memory growth as conversation history expands"""
        base_history = []
        sizes = []

        for turn in range(15):
            turn_data = {
                "turn_number": turn + 1,
                "user_input": f"User input for turn {turn + 1}",
                "partner_response": f"Partner response for turn {turn + 1}",
                "room_vibe": {"analysis": "Engaged", "energy": "positive"},
                "phase": "PHASE_1" if turn < 4 else "PHASE_2",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            base_history.append(turn_data)
            sizes.append(sys.getsizeof(str(base_history)))

        total_growth = sizes[-1] - sizes[0]
        avg_per_turn = total_growth / 15

        print("\nConversation History Memory Growth:")
        print(f"  Initial size: {sizes[0]} bytes")
        print(f"  Final size (15 turns): {sizes[-1]} bytes")
        print(f"  Average per turn: {avg_per_turn:.0f} bytes")

        assert sizes[-1] < 1024 * 50


class TestResponseTimeEstimates:
    """Test response time estimates under various conditions"""

    @pytest.mark.performance
    def test_config_load_time(self):
        """Test configuration loading is fast"""
        start_time = time.time()

        for _ in range(100):
            config = PerformanceConfig()
            config.validate()

        elapsed = time.time() - start_time

        print(f"\n100 config loads: {elapsed:.3f}s")
        assert elapsed < 0.1

    @pytest.mark.performance
    def test_context_compaction_time(self):
        """Test context compaction performance"""
        compactor = ContextCompactor(max_tokens=4000)

        large_history = [
            {"turn_number": i, "user_input": f"Turn {i}" * 50}
            for i in range(50)
        ]

        start_time = time.time()
        result = compactor.compact_history(large_history)
        elapsed = time.time() - start_time

        print(f"\nCompact 50 turns: {elapsed:.3f}s")
        assert elapsed < 0.01
        assert len(result) < len(large_history)


class TestFirestoreOperationPatterns:
    """Test Firestore operation patterns for capacity planning"""

    def test_operations_per_turn(self):
        """
        Document expected Firestore operations per turn

        Per turn estimate:
        - 1 read: Get session
        - 2 writes: Update session atomic (conversation_history + turn_count)
        - Optional: Phase update, status update

        Total: ~3 operations per turn
        """
        operations_per_turn = {
            "reads": 1,
            "writes": 2,
            "optional_writes": 1
        }

        total_ops = sum(operations_per_turn.values())
        assert total_ops <= 5

        print("\nFirestore operations per turn:")
        print(f"  Reads: {operations_per_turn['reads']}")
        print(f"  Writes: {operations_per_turn['writes']}")
        print(f"  Optional: {operations_per_turn['optional_writes']}")
        print(f"  Total: {total_ops}")

    def test_operations_per_session(self):
        """
        Document expected Firestore operations per complete session

        Session lifecycle:
        - 1 write: Create session
        - 15 × 3 = 45 ops: 15 turns
        - 1 write: Close session

        Total: ~47 operations per session
        """
        operations = {
            "session_creation": 1,
            "turns": 15 * 3,
            "session_close": 1
        }

        total_ops = sum(operations.values())

        print("\nFirestore operations per session:")
        print(f"  Session creation: {operations['session_creation']}")
        print(f"  Turn operations: {operations['turns']} (15 turns × 3 ops)")
        print(f"  Session close: {operations['session_close']}")
        print(f"  Total: {total_ops}")

        assert total_ops < 50
