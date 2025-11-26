"""OpenTelemetry instrumentation service for metrics and tracing

Note: This service provides custom metrics and tracing beyond what ADK provides.
ADK automatically instruments:
- invocation: Overall agent invocation
- agent_run: Individual agent execution
- call_llm: LLM API calls
- execute_tool: Tool executions

This service adds custom metrics for cache operations and custom spans for
application-specific operations not covered by ADK.
"""

import asyncio
import time
import functools
from typing import Callable, Optional
from contextlib import contextmanager

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from app.utils.logger import get_logger

logger = get_logger(__name__)


class MonitoringService:
    """
    Service for custom OpenTelemetry instrumentation.

    Provides custom metrics and tracing beyond ADK's built-in instrumentation:
    - Custom metrics: cache operations, custom business metrics
    - Custom spans: application-specific operations
    - Decorators: @trace_operation, @measure_latency for easy instrumentation

    Note: Uses the global OpenTelemetry providers initialized by ADK observability.
    """

    def __init__(self, service_name: str = "improv-olympics", enabled: bool = True):
        self.service_name = service_name
        self.enabled = enabled

        if not self.enabled:
            logger.info("Monitoring disabled, using no-op providers")
            self.tracer = trace.get_tracer(__name__)
            self.meter = metrics.get_meter(__name__)
            self._setup_noop_metrics()
            return

        # Use globally configured tracer and meter from ADK observability
        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)

        self._setup_metrics()
        logger.info("Monitoring service initialized", service_name=service_name)

    def _setup_metrics(self):
        """Setup metrics for turn latency, agent latency, cache operations, errors"""
        self.turn_latency_histogram = self.meter.create_histogram(
            name="turn_latency_seconds",
            description="Turn execution latency in seconds",
            unit="s",
        )

        self.agent_latency_histogram = self.meter.create_histogram(
            name="agent_latency_seconds",
            description="Individual agent execution latency in seconds",
            unit="s",
        )

        self.cache_hit_counter = self.meter.create_counter(
            name="cache_hits_total", description="Total number of cache hits", unit="1"
        )

        self.cache_miss_counter = self.meter.create_counter(
            name="cache_misses_total",
            description="Total number of cache misses",
            unit="1",
        )

        self.error_counter = self.meter.create_counter(
            name="errors_total", description="Total number of errors", unit="1"
        )

        self.request_duration_histogram = self.meter.create_histogram(
            name="request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s",
        )

    def _setup_noop_metrics(self):
        """Setup no-op metrics when monitoring is disabled"""
        self.turn_latency_histogram = None
        self.agent_latency_histogram = None
        self.cache_hit_counter = None
        self.cache_miss_counter = None
        self.error_counter = None
        self.request_duration_histogram = None

    def record_turn_latency(self, duration: float, attributes: Optional[dict] = None):
        """Record turn execution latency"""
        if not self.enabled or not self.turn_latency_histogram:
            return
        self.turn_latency_histogram.record(duration, attributes=attributes or {})
        logger.debug("Turn latency recorded", duration=duration, attributes=attributes)

    def record_agent_latency(
        self, duration: float, agent_name: str, attributes: Optional[dict] = None
    ):
        """Record individual agent execution latency"""
        if not self.enabled or not self.agent_latency_histogram:
            return
        attrs = {"agent": agent_name}
        if attributes:
            attrs.update(attributes)
        self.agent_latency_histogram.record(duration, attributes=attrs)
        logger.debug("Agent latency recorded", agent=agent_name, duration=duration)

    def record_cache_hit(self, cache_type: str = "default"):
        """Record cache hit"""
        if not self.enabled or not self.cache_hit_counter:
            return
        self.cache_hit_counter.add(1, {"cache_type": cache_type})
        logger.debug("Cache hit recorded", cache_type=cache_type)

    def record_cache_miss(self, cache_type: str = "default"):
        """Record cache miss"""
        if not self.enabled or not self.cache_miss_counter:
            return
        self.cache_miss_counter.add(1, {"cache_type": cache_type})
        logger.debug("Cache miss recorded", cache_type=cache_type)

    def record_error(
        self, error_type: str = "unknown", attributes: Optional[dict] = None
    ):
        """Record error occurrence"""
        if not self.enabled or not self.error_counter:
            return
        attrs = {"error_type": error_type}
        if attributes:
            attrs.update(attributes)
        self.error_counter.add(1, attrs)
        logger.error("Error recorded", error_type=error_type, attributes=attributes)

    def record_request_duration(
        self, duration: float, method: str, path: str, status_code: int
    ):
        """Record HTTP request duration"""
        if not self.enabled or not self.request_duration_histogram:
            return
        self.request_duration_histogram.record(
            duration,
            attributes={"method": method, "path": path, "status_code": status_code},
        )

    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Optional[dict] = None):
        """
        Context manager for tracing operations with automatic span management.

        Usage:
            with monitoring.trace_operation("execute_turn", {"turn": 1}):
                # operation code here
                pass
        """
        if not self.enabled:
            yield None
            return

        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    @contextmanager
    def measure_latency(self, metric_name: str, attributes: Optional[dict] = None):
        """
        Context manager for measuring operation latency.

        Usage:
            with monitoring.measure_latency("turn_execution", {"turn": 1}):
                # operation to measure
                pass
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if metric_name == "turn":
                self.record_turn_latency(duration, attributes)
            elif metric_name == "agent":
                agent_name = (
                    attributes.get("agent", "unknown") if attributes else "unknown"
                )
                self.record_agent_latency(duration, agent_name, attributes)

    def get_trace_id(self) -> Optional[str]:
        """Get current trace ID for request correlation"""
        if not self.enabled:
            return None

        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, "032x")
        return None


_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service(enabled: bool = True) -> MonitoringService:
    """Get or create singleton monitoring service instance"""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService(enabled=enabled)
    return _monitoring_service


def trace_operation(operation_name: str):
    """
    Decorator for tracing function/method execution.

    Usage:
        @trace_operation("execute_turn")
        async def execute_turn(session, user_input):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitoring = get_monitoring_service()
            with monitoring.trace_operation(operation_name):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitoring = get_monitoring_service()
            with monitoring.trace_operation(operation_name):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def measure_latency(metric_name: str, **metric_attributes):
    """
    Decorator for measuring function/method execution latency.

    Usage:
        @measure_latency("turn", turn_number=1)
        async def execute_turn(session, user_input):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitoring = get_monitoring_service()
            with monitoring.measure_latency(metric_name, metric_attributes):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitoring = get_monitoring_service()
            with monitoring.measure_latency(metric_name, metric_attributes):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
