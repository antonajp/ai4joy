"""Structured logging for Cloud Logging integration with OpenTelemetry trace correlation"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

from opentelemetry import trace

trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


class CloudLogger:
    """
    Structured logger for GCP Cloud Logging with JSON formatting.
    Logs are compatible with Chrome DevTools console and Cloud Logging.

    Enhanced with:
    - Automatic trace ID injection for request correlation
    - Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Convenience methods for agent and cache operations
    """

    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(self._get_formatter())
            self.logger.addHandler(handler)

    def _get_formatter(self) -> logging.Formatter:
        """Get JSON formatter for structured logging"""
        return logging.Formatter(
            '{"severity": "%(levelname)s", "timestamp": "%(asctime)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )

    def _log_structured(self, level: str, message: str, **kwargs):
        """Log structured data with optional context fields and trace ID from OpenTelemetry"""
        log_entry = {
            "severity": level,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": message,
        }

        # Try to get trace ID from OpenTelemetry context first
        trace_id = self._get_trace_id_from_otel()
        if not trace_id:
            # Fall back to manual trace ID from context var
            trace_id = trace_id_var.get()

        if trace_id:
            log_entry["trace_id"] = trace_id
            # Also add logging.googleapis.com/trace for Cloud Logging correlation
            # Format: projects/{project}/traces/{trace_id}
            if not trace_id.startswith("projects/"):
                from app.config import get_settings
                settings = get_settings()
                log_entry["logging.googleapis.com/trace"] = f"projects/{settings.gcp_project_id}/traces/{trace_id}"

        if kwargs:
            log_entry.update(kwargs)

        getattr(self.logger, level.lower())(json.dumps(log_entry))

    def _get_trace_id_from_otel(self) -> Optional[str]:
        """Get trace ID from OpenTelemetry current span context"""
        try:
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                return format(span.get_span_context().trace_id, '032x')
        except Exception:
            pass
        return None

    def info(self, message: str, **kwargs):
        """Log info message with optional context"""
        self._log_structured("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional context"""
        self._log_structured("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with optional context"""
        self._log_structured("ERROR", message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with optional context"""
        self._log_structured("DEBUG", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message with optional context"""
        self._log_structured("CRITICAL", message, **kwargs)

    def log_agent_execution(
        self,
        agent_name: str,
        operation: str,
        duration: Optional[float] = None,
        success: bool = True,
        **kwargs
    ):
        """
        Convenience method for logging agent execution.

        Args:
            agent_name: Name of the agent (e.g., "partner", "coach", "room")
            operation: Operation being performed (e.g., "generate_response")
            duration: Execution duration in seconds
            success: Whether operation succeeded
            **kwargs: Additional context
        """
        log_data = {
            "agent": agent_name,
            "operation": operation,
            "success": success,
            **kwargs
        }

        if duration is not None:
            log_data["duration_seconds"] = duration

        if success:
            self.info(f"Agent {agent_name} completed {operation}", **log_data)
        else:
            self.error(f"Agent {agent_name} failed {operation}", **log_data)

    def log_cache_operation(
        self,
        operation: str,
        cache_type: str,
        hit: bool,
        key: Optional[str] = None,
        **kwargs
    ):
        """
        Convenience method for logging cache operations.

        Args:
            operation: Operation type (e.g., "get", "set", "delete")
            cache_type: Type of cache (e.g., "session", "response")
            hit: Whether cache hit occurred (for get operations)
            key: Cache key (optional, may contain sensitive data)
            **kwargs: Additional context
        """
        log_data = {
            "cache_type": cache_type,
            "operation": operation,
            "cache_hit": hit,
            **kwargs
        }

        if key:
            log_data["cache_key"] = key

        self.debug(
            f"Cache {operation} - {'hit' if hit else 'miss'}",
            **log_data
        )


def get_logger(name: str, level: str = "INFO") -> CloudLogger:
    """Get or create logger instance"""
    return CloudLogger(name, level)


def set_trace_id(trace_id: Optional[str]):
    """Set trace ID in context for current request"""
    trace_id_var.set(trace_id)


def get_trace_id() -> Optional[str]:
    """Get current trace ID from context"""
    return trace_id_var.get()
