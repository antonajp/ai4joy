"""
ADK Native OpenTelemetry Integration

This module configures OpenTelemetry to leverage ADK's built-in instrumentation.
ADK automatically creates spans for:
- invocation: Overall agent invocation
- agent_run: Individual agent execution
- call_llm: LLM API calls
- execute_tool: Tool executions

We configure the exporters to send telemetry to Google Cloud Platform.
"""
import os
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.resourcedetector.gcp_resource_detector import GoogleCloudResourceDetector

from app.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ADKObservability:
    """
    OpenTelemetry configuration for ADK native instrumentation.

    Sets up:
    - Cloud Trace exporter for distributed tracing
    - Cloud Monitoring exporter for metrics
    - Resource detection for GCP metadata
    - Environment variables for ADK instrumentation
    """

    def __init__(self, enabled: bool = None):
        self.enabled = enabled if enabled is not None else settings.otel_enabled
        self._tracer_provider: Optional[TracerProvider] = None
        self._meter_provider: Optional[MeterProvider] = None

        if self.enabled:
            self._setup_environment()
            self._initialize_providers()
            logger.info("ADK OpenTelemetry initialized",
                       service_name=settings.app_name,
                       gcp_project=settings.gcp_project_id)
        else:
            logger.info("ADK OpenTelemetry disabled")

    def _setup_environment(self):
        """Set environment variables for ADK OpenTelemetry instrumentation"""
        os.environ.setdefault("OTEL_SERVICE_NAME", "improv-olympics-agent")
        os.environ.setdefault("OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED", "true")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")

        logger.debug("OpenTelemetry environment configured",
                    service_name=os.environ.get("OTEL_SERVICE_NAME"),
                    logging_enabled=os.environ.get("OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED"))

    def _initialize_providers(self):
        """Initialize OpenTelemetry providers with GCP exporters"""
        # Detect GCP resources (project ID, instance ID, etc.)
        resource = Resource.create({
            "service.name": settings.app_name,
            "service.version": "1.0.0",
        })

        # Try to merge with GCP resource detector
        try:
            gcp_resource = GoogleCloudResourceDetector().detect()
            resource = resource.merge(gcp_resource)
            logger.debug("GCP resource detection successful")
        except Exception as e:
            logger.warning("GCP resource detection failed, using basic resource", error=str(e))

        # Setup Trace Provider with Cloud Trace exporter
        try:
            self._tracer_provider = TracerProvider(resource=resource)

            # Cloud Trace exporter
            cloud_trace_exporter = CloudTraceSpanExporter(
                project_id=settings.gcp_project_id
            )

            # Batch processor for efficient export
            span_processor = BatchSpanProcessor(
                cloud_trace_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000  # 5 seconds
            )

            self._tracer_provider.add_span_processor(span_processor)
            trace.set_tracer_provider(self._tracer_provider)

            logger.info("Cloud Trace exporter configured", project_id=settings.gcp_project_id)

        except Exception as e:
            logger.error("Failed to initialize Cloud Trace exporter", error=str(e))
            # Fall back to no-op provider
            trace.set_tracer_provider(TracerProvider(resource=resource))

        # Setup Metrics Provider (for custom metrics beyond ADK built-ins)
        try:
            # For now, we'll use periodic console export for metrics
            # In production, you could use Cloud Monitoring exporter
            from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

            metric_reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=60000  # 1 minute
            )

            self._meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader]
            )
            metrics.set_meter_provider(self._meter_provider)

            logger.debug("Metrics provider configured")

        except Exception as e:
            logger.error("Failed to initialize metrics provider", error=str(e))

    def get_tracer(self, name: str) -> trace.Tracer:
        """Get a tracer for creating custom spans"""
        return trace.get_tracer(name)

    def get_meter(self, name: str) -> metrics.Meter:
        """Get a meter for creating custom metrics"""
        return metrics.get_meter(name)

    def get_current_trace_context(self) -> Optional[str]:
        """
        Get current trace ID from OpenTelemetry context.
        Returns trace ID in format suitable for Cloud Logging correlation.
        """
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            trace_id = format(span.get_span_context().trace_id, '032x')
            # Cloud Logging format: projects/{project}/traces/{trace_id}
            return f"projects/{settings.gcp_project_id}/traces/{trace_id}"
        return None

    def get_trace_id(self) -> Optional[str]:
        """Get just the trace ID (without project prefix) for logging"""
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, '032x')
        return None

    def shutdown(self):
        """Shutdown providers gracefully (flush pending spans/metrics)"""
        if self._tracer_provider:
            try:
                self._tracer_provider.shutdown()
                logger.info("Tracer provider shutdown complete")
            except Exception as e:
                logger.error("Error shutting down tracer provider", error=str(e))

        if self._meter_provider:
            try:
                self._meter_provider.shutdown()
                logger.info("Meter provider shutdown complete")
            except Exception as e:
                logger.error("Error shutting down meter provider", error=str(e))


# Singleton instance
_adk_observability: Optional[ADKObservability] = None


def initialize_adk_observability(enabled: bool = None) -> ADKObservability:
    """
    Initialize the ADK observability singleton.
    Should be called once at application startup.
    """
    global _adk_observability
    if _adk_observability is None:
        _adk_observability = ADKObservability(enabled=enabled)
    return _adk_observability


def get_adk_observability() -> Optional[ADKObservability]:
    """Get the ADK observability instance (may be None if not initialized)"""
    return _adk_observability


def get_current_trace_id() -> Optional[str]:
    """
    Convenience function to get current trace ID.
    Returns None if observability not initialized or no active span.
    """
    obs = get_adk_observability()
    if obs:
        return obs.get_trace_id()
    return None
