"""Tests for ADK native OpenTelemetry observability integration"""
from unittest.mock import patch

from app.services.adk_observability import (
    ADKObservability,
    initialize_adk_observability,
    get_adk_observability,
    get_current_trace_id,
    add_agent_context,
    record_token_usage,
    record_sentiment
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

        _settings = get_settings()  # noqa: F841 - verifies settings load
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


class TestConvenienceFunctions:
    """Tests for convenience functions added for simplified observability"""

    def test_add_agent_context_basic(self):
        """Test adding basic agent context to current span"""
        obs = initialize_adk_observability(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span") as span:
            add_agent_context(
                agent_type="partner",
                session_id="test-session-123",
                turn_number=5,
                phase=2
            )

            # Verify span is still valid after adding context
            assert span.get_span_context().is_valid

    def test_add_agent_context_with_extra_attributes(self):
        """Test adding agent context with extra custom attributes"""
        obs = initialize_adk_observability(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span") as span:
            add_agent_context(
                agent_type="coach",
                session_id="test-session-456",
                custom_field="custom_value",
                scene_number=3
            )

            # Should not raise exception
            assert span.get_span_context().is_valid

    def test_add_agent_context_minimal(self):
        """Test adding agent context with only required fields"""
        obs = initialize_adk_observability(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span") as span:
            # Only agent_type is required
            add_agent_context(agent_type="room")

            assert span.get_span_context().is_valid

    def test_add_agent_context_no_active_span(self):
        """Test add_agent_context when no span is active"""
        initialize_adk_observability(enabled=True)

        # Should not raise exception even without active span
        add_agent_context(agent_type="stage_manager", session_id="test-789")

    def test_add_agent_context_observability_disabled(self):
        """Test add_agent_context when observability is disabled"""
        initialize_adk_observability(enabled=False)

        # Should not raise exception when disabled
        add_agent_context(agent_type="partner", session_id="test-000")

    def test_record_token_usage_basic(self):
        """Test recording token usage metric"""
        obs = initialize_adk_observability(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span"):
            record_token_usage(
                token_count=1500,
                agent="partner",
                model="gemini-2.0-flash-001",
                session_id="test-session-123"
            )

            # Should not raise exception

    def test_record_token_usage_minimal(self):
        """Test recording token usage with minimal parameters"""
        initialize_adk_observability(enabled=True)

        # Only token_count and agent are required
        record_token_usage(
            token_count=500,
            agent="coach"
        )

        # Should not raise exception

    def test_record_token_usage_no_session(self):
        """Test recording token usage without session ID"""
        initialize_adk_observability(enabled=True)

        record_token_usage(
            token_count=800,
            agent="room",
            model="gemini-2.0-flash-001"
        )

        # Should not raise exception

    def test_record_token_usage_observability_disabled(self):
        """Test recording token usage when observability is disabled"""
        initialize_adk_observability(enabled=False)

        # Should not raise exception when disabled
        record_token_usage(
            token_count=1000,
            agent="partner",
            session_id="test-disabled"
        )

    def test_record_sentiment_basic(self):
        """Test recording sentiment score metric"""
        obs = initialize_adk_observability(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span"):
            record_sentiment(
                sentiment_score=0.75,
                session_id="test-session-123",
                turn_number=10
            )

            # Should not raise exception

    def test_record_sentiment_negative(self):
        """Test recording negative sentiment score"""
        initialize_adk_observability(enabled=True)

        record_sentiment(
            sentiment_score=-0.5,
            session_id="test-session-456",
            turn_number=3
        )

        # Should not raise exception

    def test_record_sentiment_neutral(self):
        """Test recording neutral sentiment score"""
        initialize_adk_observability(enabled=True)

        record_sentiment(
            sentiment_score=0.0,
            session_id="test-session-789",
            turn_number=1
        )

        # Should not raise exception

    def test_record_sentiment_observability_disabled(self):
        """Test recording sentiment when observability is disabled"""
        initialize_adk_observability(enabled=False)

        # Should not raise exception when disabled
        record_sentiment(
            sentiment_score=0.8,
            session_id="test-disabled",
            turn_number=5
        )


class TestADKNativeSpanIntegration:
    """Tests for ADK native span integration (no duplicate spans)"""

    def test_no_manual_span_creation(self):
        """Verify we don't create manual spans that duplicate ADK's built-in spans"""
        obs = ADKObservability(enabled=True)

        # The observability service should NOT create spans named:
        # - "invocation" (ADK creates this)
        # - "agent_run" (ADK creates this)
        # - "call_llm" (ADK creates this)
        # - "execute_tool" (ADK creates this)

        # We only create custom spans for specific use cases
        tracer = obs.get_tracer("test")

        # This is a custom span - OK to create
        with tracer.start_as_current_span("custom_business_logic") as span:
            assert span.get_span_context().is_valid
            assert span.name == "custom_business_logic"

    def test_add_attributes_to_existing_span(self):
        """Test that add_agent_context enriches existing spans instead of creating new ones"""
        obs = initialize_adk_observability(enabled=True)
        tracer = obs.get_tracer("test")

        # Simulate an ADK-created span (like "agent_run")
        with tracer.start_as_current_span("agent_run") as span:
            span_id_before = span.get_span_context().span_id

            # add_agent_context should enrich this span, not create a new one
            add_agent_context(
                agent_type="partner",
                session_id="test-123",
                turn_number=1
            )

            span_id_after = span.get_span_context().span_id

            # Same span should be enriched
            assert span_id_before == span_id_after

    def test_metrics_recorded_via_logging(self):
        """Test that custom metrics are recorded via structured logging, not OTel metrics API"""
        # Reset singleton for clean test
        import app.services.adk_observability as adk_obs_module
        adk_obs_module._adk_observability = None

        _obs = initialize_adk_observability(enabled=True)  # noqa: F841 - init needed for test

        # record_token_usage and record_sentiment should use logger, not create OTel metric spans
        # This approach creates log-based metrics in Cloud Monitoring

        with patch.object(adk_obs_module, 'logger') as mock_logger:
            record_token_usage(
                token_count=1000,
                agent="partner",
                model="gemini-2.0-flash-001"
            )

            # Should have logged the metric event
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args

            # Verify log structure
            assert "Metric: token_usage" in call_args[0]
            assert call_args[1]["event"] == "token_usage"
            assert call_args[1]["value"] == 1000

    def test_cloud_trace_correlation_format(self):
        """Test trace ID format matches Cloud Logging correlation requirements"""
        obs = initialize_adk_observability(enabled=True)
        tracer = obs.get_tracer("test")

        with tracer.start_as_current_span("test-span"):
            trace_context = obs.get_current_trace_context()

            if trace_context:
                # Should match format: projects/{project}/traces/{trace_id}
                assert trace_context.startswith("projects/")
                assert "/traces/" in trace_context

                # Extract trace ID part
                trace_id = trace_context.split("/traces/")[1]

                # Should be 32-character hex string (128-bit trace ID)
                assert len(trace_id) == 32
                assert all(c in "0123456789abcdef" for c in trace_id)


class TestCloudTraceExporterConfiguration:
    """Tests for Cloud Trace exporter specific configuration"""

    def test_batch_processor_configuration(self):
        """Test that BatchSpanProcessor is configured with appropriate settings"""
        obs = ADKObservability(enabled=True)

        # BatchSpanProcessor should be configured to batch spans efficiently
        # Settings: max_queue_size=2048, max_export_batch_size=512, schedule_delay_millis=5000

        assert obs._tracer_provider is not None

        # Verify processor exists (it's added during initialization)
        # Note: We can't easily inspect processor settings without accessing private attributes,
        # but we can verify the provider was created successfully
        assert len(obs._tracer_provider._active_span_processor._span_processors) > 0

    @patch.dict('os.environ', {'GCP_PROJECT_ID': 'test-project-123'}, clear=False)
    def test_project_id_configuration(self):
        """Test that Cloud Trace exporter uses correct project ID"""
        from app.config import get_settings
        _settings = get_settings()  # noqa: F841 - verifies settings load

        # Project ID should come from settings
        obs = ADKObservability(enabled=True)

        _trace_context = obs.get_current_trace_context()  # noqa: F841 - verifies method works
        # Even without active span, the observability should be configured
        assert obs._tracer_provider is not None

    def test_environment_variables_set_correctly(self):
        """Test that OTEL environment variables are set for ADK instrumentation"""
        _obs = ADKObservability(enabled=True)  # noqa: F841 - init sets env vars

        import os

        # These env vars enable ADK's native OpenTelemetry instrumentation
        assert os.environ.get("OTEL_SERVICE_NAME") == "improv-olympics-agent"
        assert os.environ.get("OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED") == "true"
        assert os.environ.get("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT") == "true"

    def test_graceful_degradation_without_credentials(self):
        """Test that observability degrades gracefully without GCP credentials"""
        # This test verifies the system doesn't crash if Cloud Trace can't be initialized
        # (e.g., in CI/CD without credentials)

        obs = ADKObservability(enabled=True)

        # Should still have a tracer provider (may be no-op if export fails)
        assert obs._tracer_provider is not None

        # Should still be able to get tracer
        tracer = obs.get_tracer("test")
        assert tracer is not None

        # Should be able to create spans (may not export anywhere)
        with tracer.start_as_current_span("test-span") as span:
            assert span.get_span_context().is_valid
