"""Test Suite for Agent Caching Performance Optimization"""

import pytest
import time
from datetime import datetime, timezone, timedelta

from app.services.agent_cache import (
    AgentCache,
    CachedAgent,
    get_agent_cache,
    reset_agent_cache,
)


class TestAgentCaching:
    @pytest.fixture(autouse=True)
    def reset_cache(self):
        reset_agent_cache()
        yield
        reset_agent_cache()

    @pytest.fixture
    def cache(self):
        return AgentCache(ttl_minutes=5)

    def test_cache_initialization(self, cache):
        assert cache.ttl_seconds == 300
        assert len(cache._stage_manager_cache) == 0
        assert len(cache._partner_cache) == 0
        assert cache._room_cache is None
        assert cache._coach_cache is None

    def test_stage_manager_cache_miss_then_hit(self, cache):
        agent1 = cache.get_stage_manager(turn_count=0)
        assert agent1 is not None

        stats = cache.stats.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

        agent2 = cache.get_stage_manager(turn_count=1)
        assert agent2 is agent1

        stats = cache.stats.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_stage_manager_phase_specific_caching(self, cache):
        phase1_agent = cache.get_stage_manager(turn_count=0)
        phase1_agent_again = cache.get_stage_manager(turn_count=2)
        assert phase1_agent is phase1_agent_again

        phase2_agent = cache.get_stage_manager(turn_count=4)
        assert phase2_agent is not phase1_agent

        stats = cache.stats.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2

    def test_partner_agent_cache_by_phase(self, cache):
        phase1_partner = cache.get_partner_agent(turn_count=0)
        phase1_again = cache.get_partner_agent(turn_count=3)
        assert phase1_partner is phase1_again

        phase2_partner = cache.get_partner_agent(turn_count=4)
        assert phase2_partner is not phase1_partner

        stats = cache.stats.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2

    def test_room_agent_caching(self, cache):
        room1 = cache.get_room_agent()
        room2 = cache.get_room_agent()
        room3 = cache.get_room_agent()

        assert room1 is room2 is room3

        stats = cache.stats.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1

    def test_coach_agent_caching(self, cache):
        coach1 = cache.get_coach_agent()
        coach2 = cache.get_coach_agent()

        assert coach1 is coach2

        stats = cache.stats.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_cache_expiration(self, cache):
        cache.ttl_seconds = 1

        _agent = cache.get_stage_manager(turn_count=0)  # noqa: F841 - populates cache
        stats_before = cache.stats.get_stats()
        assert stats_before["misses"] == 1

        time.sleep(1.5)

        _agent2 = cache.get_stage_manager(turn_count=0)  # noqa: F841 - tests expiration

        stats_after = cache.stats.get_stats()
        assert stats_after["misses"] == 2
        assert stats_after["evictions"] == 1

    def test_cache_invalidation_all(self, cache):
        cache.get_stage_manager(turn_count=0)
        cache.get_partner_agent(turn_count=0)
        cache.get_room_agent()
        cache.get_coach_agent()

        assert len(cache._stage_manager_cache) > 0
        assert len(cache._partner_cache) > 0
        assert cache._room_cache is not None
        assert cache._coach_cache is not None

        cache.invalidate_cache()

        assert len(cache._stage_manager_cache) == 0
        assert len(cache._partner_cache) == 0
        assert cache._room_cache is None
        assert cache._coach_cache is None

    def test_cache_invalidation_specific_type(self, cache):
        cache.get_stage_manager(turn_count=0)
        cache.get_partner_agent(turn_count=0)
        cache.get_room_agent()

        cache.invalidate_cache(agent_type="stage_manager")

        assert len(cache._stage_manager_cache) == 0
        assert len(cache._partner_cache) > 0
        assert cache._room_cache is not None

    def test_cache_stats_tracking(self, cache):
        cache.get_stage_manager(turn_count=0)
        cache.get_stage_manager(turn_count=1)
        cache.get_stage_manager(turn_count=1)

        cache.get_partner_agent(turn_count=0)
        cache.get_partner_agent(turn_count=0)

        stats = cache.get_cache_stats()

        assert stats["hits"] == 3
        assert stats["misses"] == 2
        assert stats["total_requests"] == 5
        assert stats["hit_rate_pct"] == 60.0
        assert stats["stage_manager_entries"] == 1
        assert stats["partner_entries"] == 1

    def test_cache_stats_reset(self, cache):
        cache.get_stage_manager(turn_count=0)
        cache.get_stage_manager(turn_count=0)

        stats_before = cache.stats.get_stats()
        assert stats_before["hits"] > 0

        cache.stats.reset()

        stats_after = cache.stats.get_stats()
        assert stats_after["hits"] == 0
        assert stats_after["misses"] == 0

    def test_cached_agent_access_tracking(self):
        from google.adk.agents import Agent

        mock_agent = Agent(
            name="test_agent", model="gemini-1.5-flash", instruction="Test agent"
        )

        cached = CachedAgent(mock_agent, phase=1)

        assert cached.access_count == 0

        agent = cached.access()
        assert cached.access_count == 1
        assert agent is mock_agent

        cached.access()
        cached.access()
        assert cached.access_count == 3

    def test_cached_agent_expiration(self):
        from google.adk.agents import Agent

        mock_agent = Agent(
            name="test_agent", model="gemini-1.5-flash", instruction="Test agent"
        )

        cached = CachedAgent(mock_agent)

        assert not cached.is_expired(ttl_seconds=5)

        cached.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)

        assert cached.is_expired(ttl_seconds=5)

    def test_global_cache_singleton(self):
        cache1 = get_agent_cache()
        cache2 = get_agent_cache()

        assert cache1 is cache2

    def test_cache_hit_rate_target(self, cache):
        for i in range(10):
            cache.get_stage_manager(turn_count=i % 4)

        stats = cache.get_cache_stats()

        assert stats["total_requests"] == 10
        assert stats["hit_rate_pct"] >= 70.0

    def test_concurrent_cache_access(self, cache):
        import concurrent.futures

        def access_cache(turn_count):
            return cache.get_stage_manager(turn_count=turn_count)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(access_cache, i % 4) for i in range(20)]
            results = [f.result() for f in futures]

        assert len(results) == 20
        assert all(r is not None for r in results)

        stats = cache.get_cache_stats()
        assert stats["hit_rate_pct"] >= 75.0

    def test_cache_performance_improvement(self):
        cache = AgentCache(ttl_minutes=5)

        start = time.time()
        agent1 = cache.get_stage_manager(turn_count=0)
        first_call_time = time.time() - start

        start = time.time()
        agent2 = cache.get_stage_manager(turn_count=1)
        cached_call_time = time.time() - start

        assert agent1 is agent2
        assert cached_call_time < first_call_time * 0.5

    def test_cache_different_phases_stored_separately(self, cache):
        cache.get_stage_manager(turn_count=0)
        cache.get_stage_manager(turn_count=5)

        assert len(cache._stage_manager_cache) == 2

        stats = cache.get_cache_stats()
        assert stats["stage_manager_entries"] == 2
        assert stats["misses"] == 2
        assert stats["hits"] == 0
