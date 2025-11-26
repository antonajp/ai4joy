"""Tests for monitoring and observability features"""

import pytest
import time

from app.services.monitoring import MonitoringService, get_monitoring_service
from app.services.alerting import AlertingService, AlertSeverity
from app.utils.logger import CloudLogger, set_trace_id, get_trace_id
from app.middleware.performance import PerformanceMiddleware


class TestMonitoringService:
    """Tests for OpenTelemetry monitoring service"""

    def test_monitoring_service_initialization(self):
        """Test monitoring service initializes correctly"""
        monitoring = MonitoringService(service_name="test-service", enabled=True)
        assert monitoring.service_name == "test-service"
        assert monitoring.enabled is True
        assert monitoring.tracer is not None
        assert monitoring.meter is not None

    def test_monitoring_service_disabled(self):
        """Test monitoring service with disabled mode"""
        monitoring = MonitoringService(enabled=False)
        assert monitoring.enabled is False

    def test_record_turn_latency(self):
        """Test recording turn latency metric"""
        monitoring = MonitoringService(enabled=True)
        monitoring.record_turn_latency(1.5, {"session_id": "test-123"})

    def test_record_agent_latency(self):
        """Test recording agent latency metric"""
        monitoring = MonitoringService(enabled=True)
        monitoring.record_agent_latency(0.8, "partner", {"turn": 1})

    def test_record_cache_operations(self):
        """Test recording cache hit and miss metrics"""
        monitoring = MonitoringService(enabled=True)
        monitoring.record_cache_hit("session_cache")
        monitoring.record_cache_miss("session_cache")

    def test_record_error(self):
        """Test recording error metric"""
        monitoring = MonitoringService(enabled=True)
        monitoring.record_error("ValueError", {"context": "test"})

    def test_trace_operation_context_manager(self):
        """Test trace operation context manager"""
        monitoring = MonitoringService(enabled=True)

        with monitoring.trace_operation("test_operation", {"key": "value"}) as span:
            assert span is not None
            time.sleep(0.01)

    def test_measure_latency_context_manager(self):
        """Test measure latency context manager for turn"""
        monitoring = MonitoringService(enabled=True)

        with monitoring.measure_latency("turn", {"session_id": "test"}):
            time.sleep(0.01)

    def test_measure_latency_for_agent(self):
        """Test measure latency context manager for agent"""
        monitoring = MonitoringService(enabled=True)

        with monitoring.measure_latency("agent", {"agent": "partner"}):
            time.sleep(0.01)

    def test_get_trace_id(self):
        """Test getting current trace ID"""
        monitoring = MonitoringService(enabled=True)
        _trace_id = monitoring.get_trace_id()  # noqa: F841 - verifies method works

    def test_singleton_pattern(self):
        """Test get_monitoring_service returns singleton"""
        service1 = get_monitoring_service(enabled=False)
        service2 = get_monitoring_service(enabled=False)
        assert service1 is service2


class TestAlertingService:
    """Tests for alerting service"""

    def test_alerting_service_initialization(self):
        """Test alerting service initializes with thresholds"""
        alerting = AlertingService(
            latency_threshold=8.0,
            error_rate_threshold=0.05,
            cache_hit_rate_threshold=0.50,
        )
        assert alerting.latency_threshold == 8.0
        assert alerting.error_rate_threshold == 0.05
        assert alerting.cache_hit_rate_threshold == 0.50

    def test_check_latency_below_threshold(self):
        """Test latency check when below threshold"""
        alerting = AlertingService(latency_threshold=8.0)
        alert = alerting.check_latency(5.0, "turn_latency")
        assert alert is None

    def test_check_latency_above_threshold_warning(self):
        """Test latency check when above threshold triggers warning"""
        alerting = AlertingService(latency_threshold=8.0)
        alert = alerting.check_latency(9.0, "turn_latency")
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.metric == "turn_latency_p95"
        assert alert.current_value == 9.0

    def test_check_latency_above_threshold_critical(self):
        """Test latency check when far above threshold triggers critical"""
        alerting = AlertingService(latency_threshold=8.0)
        alert = alerting.check_latency(15.0, "turn_latency")
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL

    def test_check_error_rate_below_threshold(self):
        """Test error rate check when below threshold"""
        alerting = AlertingService(error_rate_threshold=0.05)
        alert = alerting.check_error_rate(total_requests=100, error_count=2)
        assert alert is None

    def test_check_error_rate_above_threshold(self):
        """Test error rate check when above threshold"""
        alerting = AlertingService(error_rate_threshold=0.05)
        alert = alerting.check_error_rate(total_requests=100, error_count=10)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.current_value == 0.10

    def test_check_error_rate_zero_requests(self):
        """Test error rate check with zero requests"""
        alerting = AlertingService(error_rate_threshold=0.05)
        alert = alerting.check_error_rate(total_requests=0, error_count=0)
        assert alert is None

    def test_check_cache_hit_rate_above_threshold(self):
        """Test cache hit rate check when above threshold"""
        alerting = AlertingService(cache_hit_rate_threshold=0.50)
        alert = alerting.check_cache_hit_rate(cache_hits=60, cache_total=100)
        assert alert is None

    def test_check_cache_hit_rate_below_threshold(self):
        """Test cache hit rate check when below threshold"""
        alerting = AlertingService(cache_hit_rate_threshold=0.50)
        alert = alerting.check_cache_hit_rate(cache_hits=30, cache_total=100)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.current_value == 0.30

    def test_check_cache_hit_rate_zero_operations(self):
        """Test cache hit rate check with zero operations"""
        alerting = AlertingService(cache_hit_rate_threshold=0.50)
        alert = alerting.check_cache_hit_rate(cache_hits=0, cache_total=0)
        assert alert is None

    def test_get_recent_alerts(self):
        """Test getting recent alerts"""
        alerting = AlertingService(latency_threshold=5.0)
        alerting.check_latency(10.0, "test1")
        alerting.check_latency(12.0, "test2")

        recent = alerting.get_recent_alerts(count=2)
        assert len(recent) == 2

    def test_get_alerts_by_severity(self):
        """Test filtering alerts by severity"""
        alerting = AlertingService(latency_threshold=5.0)
        alerting.check_latency(6.0, "test1")
        alerting.check_latency(10.0, "test2")

        warnings = alerting.get_alerts_by_severity(AlertSeverity.WARNING)
        assert len(warnings) > 0

    def test_get_alert_summary(self):
        """Test alert summary generation"""
        alerting = AlertingService(latency_threshold=5.0)
        alerting.check_latency(6.0, "test")

        summary = alerting.get_alert_summary()
        assert "total" in summary
        assert "warning" in summary
        assert "critical" in summary
        assert summary["total"] >= 1

    def test_clear_alerts(self):
        """Test clearing alerts"""
        alerting = AlertingService(latency_threshold=5.0)
        alerting.check_latency(10.0, "test")
        assert len(alerting.alerts) > 0

        alerting.clear_alerts()
        assert len(alerting.alerts) == 0


class TestCloudLogger:
    """Tests for enhanced CloudLogger with trace IDs"""

    def test_trace_id_injection(self):
        """Test trace ID is injected into log messages"""
        set_trace_id("trace-123")

        logger = CloudLogger("test-logger")
        logger.info("Test message", extra_field="value")

        current_trace = get_trace_id()
        assert current_trace == "trace-123"

        set_trace_id(None)

    def test_log_agent_execution_success(self):
        """Test logging successful agent execution"""
        logger = CloudLogger("test-logger")
        logger.log_agent_execution(
            agent_name="partner",
            operation="generate_response",
            duration=1.5,
            success=True,
            turn=1,
        )

    def test_log_agent_execution_failure(self):
        """Test logging failed agent execution"""
        logger = CloudLogger("test-logger")
        logger.log_agent_execution(
            agent_name="coach",
            operation="analyze_scene",
            duration=0.5,
            success=False,
            error="Timeout",
        )

    def test_log_cache_operation_hit(self):
        """Test logging cache hit"""
        logger = CloudLogger("test-logger")
        logger.log_cache_operation(
            operation="get", cache_type="session", hit=True, key="session:123"
        )

    def test_log_cache_operation_miss(self):
        """Test logging cache miss"""
        logger = CloudLogger("test-logger")
        logger.log_cache_operation(
            operation="get", cache_type="session", hit=False, key="session:456"
        )


class TestPerformanceMiddleware:
    """Tests for performance tracking middleware"""

    @pytest.mark.asyncio
    async def test_performance_middleware_tracks_duration(self):
        """Test middleware tracks request duration"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        _middleware = PerformanceMiddleware(
            app, slow_request_threshold=1.0
        )  # noqa: F841 - tests instantiation
        app.add_middleware(PerformanceMiddleware, slow_request_threshold=1.0)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert "X-Trace-ID" in response.headers
        assert "X-Request-Duration" in response.headers

    def test_performance_summary(self):
        """Test performance summary generation"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = PerformanceMiddleware(app)

        middleware.request_stats["GET:/test"].append(0.5)
        middleware.request_stats["GET:/test"].append(1.0)
        middleware.request_stats["GET:/test"].append(1.5)

        summary = middleware.get_performance_summary()
        assert "GET:/test" in summary
        assert summary["GET:/test"]["count"] == 3
        assert summary["GET:/test"]["mean"] == 1.0
        assert summary["GET:/test"]["min"] == 0.5
        assert summary["GET:/test"]["max"] == 1.5

    def test_reset_stats(self):
        """Test resetting performance statistics"""
        from fastapi import FastAPI

        app = FastAPI()
        middleware = PerformanceMiddleware(app)

        middleware.request_stats["GET:/test"].append(1.0)
        assert len(middleware.request_stats) > 0

        middleware.reset_stats()
        assert len(middleware.request_stats) == 0


class TestTraceIDPropagation:
    """Tests for trace ID propagation across components"""

    def test_trace_id_propagation(self):
        """Test trace ID propagates through logger context"""
        trace_id = "test-trace-123"
        set_trace_id(trace_id)

        assert get_trace_id() == trace_id

        logger = CloudLogger("test")
        logger.info("Test message")

        set_trace_id(None)
        assert get_trace_id() is None
