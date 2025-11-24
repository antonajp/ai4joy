"""Request-level performance tracking middleware with OpenTelemetry integration"""
import time
import uuid
from typing import Callable, Dict, List
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from opentelemetry import trace

from app.utils.logger import get_logger, set_trace_id
from app.services.monitoring import get_monitoring_service

logger = get_logger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request-level performance tracking.

    Features:
    - Track request duration
    - Add trace IDs to all requests
    - Log slow requests (>5s)
    - Collect performance statistics
    """

    def __init__(self, app: ASGIApp, slow_request_threshold: float = 5.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.request_stats: Dict[str, List[float]] = defaultdict(list)
        self.monitoring = get_monitoring_service()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance tracking and OpenTelemetry trace propagation"""
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Create a span for the HTTP request
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(
            f"HTTP {request.method} {request.url.path}",
            kind=trace.SpanKind.SERVER,
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.target": request.url.path,
            }
        ) as span:
            # Get trace ID from OpenTelemetry span
            span_context = span.get_span_context()
            if span_context.is_valid:
                trace_id = format(span_context.trace_id, '032x')
            else:
                # Fallback to UUID if span context is invalid
                trace_id = str(uuid.uuid4())

            request.state.trace_id = trace_id
            set_trace_id(trace_id)  # Set in context var for logger

            logger.debug(
                "Request started",
                trace_id=trace_id,
                method=request.method,
                path=request.url.path,
                timestamp=timestamp
            )

            try:
                response = await call_next(request)
                duration = time.time() - start_time

                # Add span attributes for response
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.duration_ms", duration * 1000)

                self.monitoring.record_request_duration(
                    duration=duration,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code
                )

                response.headers["X-Trace-ID"] = trace_id
                response.headers["X-Request-Duration"] = f"{duration:.3f}s"

                if duration > self.slow_request_threshold:
                    logger.warning(
                        "Slow request detected",
                        trace_id=trace_id,
                        method=request.method,
                        path=request.url.path,
                        duration=duration,
                        threshold=self.slow_request_threshold,
                        status_code=response.status_code
                    )
                    span.set_attribute("slow_request", True)
                else:
                    logger.info(
                        "Request completed",
                        trace_id=trace_id,
                        method=request.method,
                        path=request.url.path,
                        duration=duration,
                        status_code=response.status_code
                    )

                endpoint_key = f"{request.method}:{request.url.path}"
                self.request_stats[endpoint_key].append(duration)

                return response

            except Exception as e:
                duration = time.time() - start_time

                # Record exception in span
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

                logger.error(
                    "Request failed",
                    trace_id=trace_id,
                    method=request.method,
                    path=request.url.path,
                    duration=duration,
                    error=str(e),
                    error_type=type(e).__name__
                )

                self.monitoring.record_error(
                    error_type=type(e).__name__,
                    attributes={
                        "method": request.method,
                        "path": request.url.path,
                        "trace_id": trace_id
                    }
                )

                raise
            finally:
                # Clear trace ID from context
                set_trace_id(None)

    def get_performance_summary(self) -> Dict[str, Dict[str, float]]:
        """Get performance summary for all endpoints"""
        summary = {}

        for endpoint, durations in self.request_stats.items():
            if not durations:
                continue

            sorted_durations = sorted(durations)
            count = len(durations)

            summary[endpoint] = {
                "count": count,
                "mean": sum(durations) / count,
                "min": min(durations),
                "max": max(durations),
                "p50": sorted_durations[int(count * 0.5)] if count > 0 else 0,
                "p95": sorted_durations[int(count * 0.95)] if count > 0 else 0,
                "p99": sorted_durations[int(count * 0.99)] if count > 0 else 0,
            }

        return summary

    def reset_stats(self):
        """Reset performance statistics"""
        self.request_stats.clear()
        logger.info("Performance statistics reset")


def get_trace_id(request: Request) -> str:
    """Extract trace ID from request state"""
    return getattr(request.state, "trace_id", "unknown")
