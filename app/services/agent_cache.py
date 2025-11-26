"""Agent Instance Caching Service for Performance Optimization"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from threading import Lock

from google.adk.agents import Agent

from app.agents.stage_manager import create_stage_manager, get_partner_agent_for_turn
from app.agents.room_agent import create_room_agent
from app.agents.coach_agent import create_coach_agent
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AgentCacheStats:
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.lock = Lock()

    def record_hit(self):
        with self.lock:
            self.hits += 1

    def record_miss(self):
        with self.lock:
            self.misses += 1

    def record_eviction(self):
        with self.lock:
            self.evictions += 1

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "total_requests": total,
                "hit_rate_pct": round(hit_rate, 2),
            }

    def reset(self):
        with self.lock:
            self.hits = 0
            self.misses = 0
            self.evictions = 0


class CachedAgent:
    def __init__(self, agent: Agent, phase: Optional[int] = None):
        self.agent = agent
        self.phase = phase
        self.created_at = datetime.now(timezone.utc)
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count = 0

    def access(self) -> Agent:
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1
        return self.agent

    def is_expired(self, ttl_seconds: int) -> bool:
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > ttl_seconds


class AgentCache:
    def __init__(self, ttl_minutes: int = 5):
        self.ttl_seconds = ttl_minutes * 60
        self._stage_manager_cache: Dict[int, CachedAgent] = {}
        self._partner_cache: Dict[int, CachedAgent] = {}
        self._room_cache: Optional[CachedAgent] = None
        self._coach_cache: Optional[CachedAgent] = None
        self._cache_lock = Lock()
        self.stats = AgentCacheStats()

        logger.info("AgentCache initialized", ttl_minutes=ttl_minutes)

    def get_stage_manager(self, turn_count: int) -> Agent:
        phase = 1 if turn_count < 4 else 2
        cache_key = phase

        with self._cache_lock:
            cached = self._stage_manager_cache.get(cache_key)

            if cached and not cached.is_expired(self.ttl_seconds):
                self.stats.record_hit()
                logger.debug(
                    "Stage Manager cache hit",
                    turn_count=turn_count,
                    phase=phase,
                    access_count=cached.access_count + 1,
                )
                return cached.access()

            if cached and cached.is_expired(self.ttl_seconds):
                self.stats.record_eviction()
                logger.debug("Stage Manager cache entry expired", phase=phase)

            self.stats.record_miss()
            logger.debug("Stage Manager cache miss", turn_count=turn_count, phase=phase)

            agent = create_stage_manager(turn_count=turn_count)
            self._stage_manager_cache[cache_key] = CachedAgent(agent, phase=phase)

            return agent

    def get_partner_agent(self, turn_count: int) -> Agent:
        phase = 1 if turn_count < 4 else 2

        with self._cache_lock:
            cached = self._partner_cache.get(phase)

            if cached and not cached.is_expired(self.ttl_seconds):
                self.stats.record_hit()
                logger.debug(
                    "Partner Agent cache hit",
                    phase=phase,
                    access_count=cached.access_count + 1,
                )
                return cached.access()

            if cached and cached.is_expired(self.ttl_seconds):
                self.stats.record_eviction()
                logger.debug("Partner Agent cache entry expired", phase=phase)

            self.stats.record_miss()
            logger.debug("Partner Agent cache miss", phase=phase)

            agent = get_partner_agent_for_turn(turn_count=turn_count)
            self._partner_cache[phase] = CachedAgent(agent, phase=phase)

            return agent

    def get_room_agent(self) -> Agent:
        with self._cache_lock:
            if self._room_cache and not self._room_cache.is_expired(self.ttl_seconds):
                self.stats.record_hit()
                logger.debug(
                    "Room Agent cache hit",
                    access_count=self._room_cache.access_count + 1,
                )
                return self._room_cache.access()

            if self._room_cache and self._room_cache.is_expired(self.ttl_seconds):
                self.stats.record_eviction()
                logger.debug("Room Agent cache entry expired")

            self.stats.record_miss()
            logger.debug("Room Agent cache miss")

            agent = create_room_agent()
            self._room_cache = CachedAgent(agent)

            return agent

    def get_coach_agent(self) -> Agent:
        with self._cache_lock:
            if self._coach_cache and not self._coach_cache.is_expired(self.ttl_seconds):
                self.stats.record_hit()
                logger.debug(
                    "Coach Agent cache hit",
                    access_count=self._coach_cache.access_count + 1,
                )
                return self._coach_cache.access()

            if self._coach_cache and self._coach_cache.is_expired(self.ttl_seconds):
                self.stats.record_eviction()
                logger.debug("Coach Agent cache entry expired")

            self.stats.record_miss()
            logger.debug("Coach Agent cache miss")

            agent = create_coach_agent()
            self._coach_cache = CachedAgent(agent)

            return agent

    def invalidate_cache(self, agent_type: Optional[str] = None):
        with self._cache_lock:
            if agent_type is None:
                count = (
                    len(self._stage_manager_cache)
                    + len(self._partner_cache)
                    + (1 if self._room_cache else 0)
                    + (1 if self._coach_cache else 0)
                )
                self._stage_manager_cache.clear()
                self._partner_cache.clear()
                self._room_cache = None
                self._coach_cache = None
                logger.info("All agent caches invalidated", entries_cleared=count)
            elif agent_type == "stage_manager":
                count = len(self._stage_manager_cache)
                self._stage_manager_cache.clear()
                logger.info("Stage Manager cache invalidated", entries_cleared=count)
            elif agent_type == "partner":
                count = len(self._partner_cache)
                self._partner_cache.clear()
                logger.info("Partner Agent cache invalidated", entries_cleared=count)
            elif agent_type == "room":
                self._room_cache = None
                logger.info("Room Agent cache invalidated")
            elif agent_type == "coach":
                self._coach_cache = None
                logger.info("Coach Agent cache invalidated")
            else:
                logger.warning(
                    "Unknown agent type for invalidation", agent_type=agent_type
                )

    def get_cache_stats(self) -> Dict[str, Any]:
        stats = self.stats.get_stats()

        with self._cache_lock:
            total_cached = (
                len(self._stage_manager_cache)
                + len(self._partner_cache)
                + (1 if self._room_cache else 0)
                + (1 if self._coach_cache else 0)
            )

            cache_sizes = {
                "stage_manager_entries": len(self._stage_manager_cache),
                "partner_entries": len(self._partner_cache),
                "room_cached": self._room_cache is not None,
                "coach_cached": self._coach_cache is not None,
                "total_cached_agents": total_cached,
            }

            phase_breakdown = {}
            for phase, cached_agent in self._stage_manager_cache.items():
                phase_breakdown[f"phase_{phase}_accesses"] = cached_agent.access_count
                phase_breakdown[f"phase_{phase}_age_seconds"] = int(
                    (
                        datetime.now(timezone.utc) - cached_agent.created_at
                    ).total_seconds()
                )

        return {
            **stats,
            **cache_sizes,
            "phase_details": phase_breakdown,
            "ttl_seconds": self.ttl_seconds,
        }


_agent_cache_instance: Optional[AgentCache] = None
_instance_lock = Lock()


def get_agent_cache(ttl_minutes: int = 5) -> AgentCache:
    global _agent_cache_instance

    if _agent_cache_instance is None:
        with _instance_lock:
            if _agent_cache_instance is None:
                _agent_cache_instance = AgentCache(ttl_minutes=ttl_minutes)

    return _agent_cache_instance


def reset_agent_cache():
    global _agent_cache_instance
    with _instance_lock:
        if _agent_cache_instance:
            _agent_cache_instance.invalidate_cache()
        _agent_cache_instance = None
