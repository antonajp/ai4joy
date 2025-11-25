"""Performance Tuning Configuration and Utilities"""
from dataclasses import dataclass


@dataclass
class PerformanceConfig:
    """
    Performance tuning parameters for ADK multi-agent orchestration

    These values are based on load testing results and capacity planning:
    - Target p95 latency: < 3s
    - Max concurrent users: 10
    - Session duration: ~5-10 minutes (15 turns)

    Tunable Parameters:
    - agent_timeout_seconds: Max time for agent execution
    - cache_ttl_seconds: Time-to-live for cached responses
    - max_context_tokens: Maximum context window size
    - batch_write_threshold: Minimum operations before batch write
    """

    agent_timeout_seconds: int = 30
    cache_ttl_seconds: int = 300
    max_context_tokens: int = 4000
    batch_write_threshold: int = 5
    max_concurrent_sessions_per_instance: int = 10
    firestore_batch_size: int = 500

    def validate(self) -> None:
        """Validate configuration values are within acceptable ranges"""
        if self.agent_timeout_seconds < 10:
            raise ValueError("agent_timeout_seconds must be >= 10")

        if self.agent_timeout_seconds > 60:
            raise ValueError("agent_timeout_seconds must be <= 60")

        if self.cache_ttl_seconds < 0:
            raise ValueError("cache_ttl_seconds must be >= 0")

        if self.max_context_tokens < 1000:
            raise ValueError("max_context_tokens must be >= 1000")

        if self.max_context_tokens > 32000:
            raise ValueError("max_context_tokens must be <= 32000")

        if self.batch_write_threshold < 1:
            raise ValueError("batch_write_threshold must be >= 1")

        if self.max_concurrent_sessions_per_instance < 1:
            raise ValueError("max_concurrent_sessions_per_instance must be >= 1")

        if self.firestore_batch_size < 1 or self.firestore_batch_size > 500:
            raise ValueError("firestore_batch_size must be between 1 and 500")

    @classmethod
    def from_env(cls, env_prefix: str = "PERF_") -> "PerformanceConfig":
        """
        Create PerformanceConfig from environment variables

        Environment variables:
        - PERF_AGENT_TIMEOUT: Agent execution timeout in seconds
        - PERF_CACHE_TTL: Cache time-to-live in seconds
        - PERF_MAX_CONTEXT_TOKENS: Maximum context window size
        - PERF_BATCH_WRITE_THRESHOLD: Minimum ops before batch write
        - PERF_MAX_CONCURRENT_SESSIONS: Max concurrent sessions per instance
        - PERF_FIRESTORE_BATCH_SIZE: Firestore batch operation size
        """
        import os

        return cls(
            agent_timeout_seconds=int(
                os.getenv(f"{env_prefix}AGENT_TIMEOUT", "30")
            ),
            cache_ttl_seconds=int(
                os.getenv(f"{env_prefix}CACHE_TTL", "300")
            ),
            max_context_tokens=int(
                os.getenv(f"{env_prefix}MAX_CONTEXT_TOKENS", "4000")
            ),
            batch_write_threshold=int(
                os.getenv(f"{env_prefix}BATCH_WRITE_THRESHOLD", "5")
            ),
            max_concurrent_sessions_per_instance=int(
                os.getenv(f"{env_prefix}MAX_CONCURRENT_SESSIONS", "10")
            ),
            firestore_batch_size=int(
                os.getenv(f"{env_prefix}FIRESTORE_BATCH_SIZE", "500")
            )
        )


class ContextCompactor:
    """
    Utility for compacting conversation context to stay within token limits

    Strategies:
    1. Keep most recent N turns (recency bias)
    2. Keep first turn (scene setup)
    3. Summarize middle turns if needed
    """

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.avg_tokens_per_turn = 150

    def compact_history(
        self,
        conversation_history: list,
        keep_recent: int = 3
    ) -> list:
        """
        Compact conversation history to fit within token limits

        Args:
            conversation_history: Full conversation history
            keep_recent: Number of recent turns to always keep

        Returns:
            Compacted conversation history
        """
        if not conversation_history:
            return []

        history_length = len(conversation_history)
        estimated_tokens = history_length * self.avg_tokens_per_turn

        if estimated_tokens <= self.max_tokens:
            return conversation_history

        max_turns = self.max_tokens // self.avg_tokens_per_turn

        if history_length <= max_turns:
            return conversation_history

        if history_length <= keep_recent + 1:
            return conversation_history

        first_turn = conversation_history[0]
        recent_turns = conversation_history[-keep_recent:]

        return [first_turn] + recent_turns

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text

        Rough approximation: 1 token ≈ 4 characters
        """
        return len(text) // 4


class FirestoreBatchWriter:
    """
    Utility for batching Firestore write operations

    Improves performance by reducing number of network round-trips
    """

    def __init__(self, db, batch_size: int = 500):
        self.db = db
        self.batch_size = batch_size
        self._pending_writes = []

    def add_write(self, doc_ref, data: dict) -> None:
        """Add write operation to batch"""
        self._pending_writes.append(("set", doc_ref, data))

        if len(self._pending_writes) >= self.batch_size:
            self.flush()

    def add_update(self, doc_ref, updates: dict) -> None:
        """Add update operation to batch"""
        self._pending_writes.append(("update", doc_ref, updates))

        if len(self._pending_writes) >= self.batch_size:
            self.flush()

    def flush(self) -> int:
        """Execute all pending writes in batch"""
        if not self._pending_writes:
            return 0

        batch = self.db.batch()
        for operation, doc_ref, data in self._pending_writes:
            if operation == "set":
                batch.set(doc_ref, data)
            elif operation == "update":
                batch.update(doc_ref, data)

        batch.commit()
        count = len(self._pending_writes)
        self._pending_writes = []

        return count


def get_performance_config() -> PerformanceConfig:
    """Get performance configuration instance"""
    config = PerformanceConfig.from_env()
    config.validate()
    return config
