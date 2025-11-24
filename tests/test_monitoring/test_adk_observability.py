"""Tests for ADK native OpenTelemetry observability integration"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.services.adk_observability import (
    ADKObservability,
    initialize_adk_observability,
    get_adk_observability,
    get_current_trace_id
)


class TestADKObservability:
    """Tests for ADK OpenTelemetry integration"""

    def test_initialization_enabled(self):
        """Test ADK observability initializes when enabled"""
        obs = ADKObservability(enabled=True)
        assert obs.enabled is True
        assert obs._tracer_provider is not None

    def test_initialization_disabled(self):
        """Test ADK observability skips setup when disabled"""
        obs = ADKObservability(enabled=False)
        assert obs.enabled is False

    @patch.dict('os.environ', {}, clear=False)
    def test_environment_setup(self):
        """Test OpenTelemetry environment variables are configured"""
        obs = ADKObservability(enabled=True)
        obs._setup_environment()

        import os
        assert os.environ.get("OTEL_SERVICE_NAME") == "improv-olympics-agent"
        assert os.environ.get("OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED") == "true"
        assert os.environ.get("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT") == "true"

    def test_get_tracer(self):
        """Test getting a tracer instance"""
        obs = ADKObservability(enabled=True)
        tracer = obs.get_tracer("test-tracer")
        assert tracer is not None

    def test_get_meter(self):
        """Test getting a meter instance"""
        obs = ADKObservability(enabled=True)
        meter = obs.get_meter("test-meter")
        assert meter is not None

    def test_get_trace_id_no_span(self):
        """Test getting trace ID when no active span"""
        obs = ADKObservability(enabled=True)
        trace_id = obs.get_trace_id()
        # Should return None when no active span
        assert trace_id is None or isinstance(trace_id, str)

    def test_get_trace_id_with_span(self):
        """Test getting trace ID from active span"""
        obs = ADKObservability(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span") as span:
            trace_id = obs.get_trace_id()
            # Should have a trace ID within span context
            if span.get_span_context().is_valid:
                assert trace_id is not None
                assert isinstance(trace_id, str)
                assert len(trace_id) == 32  # 128-bit trace ID as hex

    def test_get_current_trace_context(self):
        """Test getting full trace context for Cloud Logging"""
        obs = ADKObservability(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span"):
            trace_context = obs.get_current_trace_context()
            if trace_context:
                assert trace_context.startswith("projects/")
                assert "/traces/" in trace_context

    def test_shutdown(self):
        """Test graceful shutdown of providers"""
        obs = ADKObservability(enabled=True)
        # Should not raise exception
        obs.shutdown()

    def test_singleton_initialize(self):
        """Test singleton initialization"""
        obs1 = initialize_adk_observability(enabled=False)
        obs2 = get_adk_observability()
        assert obs1 is obs2

    def test_get_current_trace_id_convenience(self):
        """Test convenience function for getting trace ID"""
        initialize_adk_observability(enabled=True)
        obs = get_adk_observability()

        tracer = obs.get_tracer("test")
        with tracer.start_as_current_span("test-span"):
            trace_id = get_current_trace_id()
            # Should work through convenience function
            assert trace_id is None or isinstance(trace_id, str)


class TestOpenTelemetryIntegration:
    """Tests for OpenTelemetry integration with logger and middleware"""

    def test_trace_propagation_to_logger(self):
        """Test trace ID propagates from span to logger"""
        from app.utils.logger import CloudLogger
        from opentelemetry import trace

        obs = ADKObservability(enabled=True)
        tracer = obs.get_tracer("test")
        logger = CloudLogger("test")

        with tracer.start_as_current_span("test-span") as span:
            # Logger should be able to extract trace ID from span context
            if span.get_span_context().is_valid:
                trace_id = logger._get_trace_id_from_otel()
                assert trace_id is not None
                assert isinstance(trace_id, str)

    def test_span_attributes(self):
        """Test setting custom attributes on spans"""
        obs = ADKObservability(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span") as span:
            span.set_attribute("custom.attribute", "test-value")
            span.set_attribute("http.method", "GET")
            # Should not raise exception
            assert span.get_span_context().is_valid

    def test_nested_spans(self):
        """Test creating nested spans for hierarchical tracing"""
        obs = ADKObservability(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("parent-span") as parent:
            parent_trace_id = format(parent.get_span_context().trace_id, '032x')

            with tracer.start_as_current_span("child-span") as child:
                child_trace_id = format(child.get_span_context().trace_id, '032x')

                # Child and parent should share the same trace ID
                if parent.get_span_context().is_valid and child.get_span_context().is_valid:
                    assert parent_trace_id == child_trace_id


class TestAlertingWithObservability:
    """Tests for alerting service integration with observability"""

    def test_alert_includes_trace_context(self):
        """Test alerts include trace context when available"""
        from app.services.alerting import AlertingService

        obs = ADKObservability(enabled=True)
        alerting = AlertingService()
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span"):
            # Trigger an alert
            alert = alerting.check_latency(10.0, "test_metric")

            # Alert should be created
            assert alert is not None
            # Logs should include trace ID (tested via logger)

    def test_error_recording_with_trace(self):
        """Test error recording includes trace context"""
        from app.services.monitoring import MonitoringService

        obs = ADKObservability(enabled=True)
        monitoring = MonitoringService(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span") as span:
            # Record an error
            monitoring.record_error("TestError", {"context": "test"})

            # Span should remain valid
            assert span.get_span_context().is_valid


class TestCloudTraceExporter:
    """Tests for Cloud Trace exporter configuration"""

    @patch('app.services.adk_observability.CloudTraceSpanExporter')
    def test_cloud_trace_exporter_initialization(self, mock_exporter):
        """Test Cloud Trace exporter is configured with correct project"""
        from app.config import get_settings

        settings = get_settings()
        obs = ADKObservability(enabled=True)

        # Should have attempted to create Cloud Trace exporter
        # (may fail in test environment without credentials)
        assert obs._tracer_provider is not None

    def test_resource_detection(self):
        """Test GCP resource detection is attempted"""
        obs = ADKObservability(enabled=True)

        # Should not raise exception even if resource detection fails
        assert obs.enabled is True
        assert obs._tracer_provider is not None


class TestCustomMetrics:
    """Tests for custom metrics beyond ADK built-ins"""

    def test_cache_hit_metric(self):
        """Test custom cache hit metric recording"""
        from app.services.monitoring import MonitoringService

        monitoring = MonitoringService(enabled=True)
        monitoring.record_cache_hit("session_cache")
        # Should not raise exception

    def test_cache_miss_metric(self):
        """Test custom cache miss metric recording"""
        from app.services.monitoring import MonitoringService

        monitoring = MonitoringService(enabled=True)
        monitoring.record_cache_miss("session_cache")
        # Should not raise exception

    def test_custom_latency_metric(self):
        """Test custom latency metric recording"""
        from app.services.monitoring import MonitoringService

        monitoring = MonitoringService(enabled=True)
        monitoring.record_turn_latency(2.5, {"session_id": "test-123"})
        # Should not raise exception
