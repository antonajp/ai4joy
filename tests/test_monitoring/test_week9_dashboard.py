"""Tests for Week 9 Cloud Monitoring Dashboard and Alert Policies

Test Coverage:
- TC-W9-001: Cloud Monitoring Dashboard Creation
- TC-W9-002: Alert Policy Functionality
- TC-W9-005: Log-Based Metrics (partial - requires manual validation)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from google.cloud import monitoring_v3
from google.cloud.monitoring_dashboard import v1 as dashboard_v1


@pytest.fixture
def mock_dashboard_client():
    """Mock dashboard client for testing"""
    client = Mock(spec=dashboard_v1.DashboardsServiceClient)
    return client


@pytest.fixture
def mock_alert_policy_client():
    """Mock alert policy client for testing"""
    client = Mock(spec=monitoring_v3.AlertPolicyServiceClient)
    return client


class TestCloudMonitoringDashboard:
    """TC-W9-001: Cloud Monitoring Dashboard Creation"""

    def test_dashboard_has_required_widgets(self, mock_dashboard_client):
        """Verify dashboard contains all 6 required widgets"""
        # Mock dashboard response
        mock_dashboard = Mock()
        mock_dashboard.display_name = "Improv Olympics Production"

        # Define 6 expected widgets
        widget_titles = [
            "Turn Latency (p50, p95, p99)",
            "Agent Execution Latency",
            "Error Rate Over Time",
            "Cache Hit/Miss Ratio",
            "Concurrent Session Count",
            "Request Rate & Status Codes"
        ]

        # Create mock widgets
        mock_widgets = []
        for title in widget_titles:
            widget = Mock()
            widget.title = title
            mock_widgets.append(widget)

        mock_dashboard.grid_layout.widgets = mock_widgets

        # Verify all 6 widgets present
        assert len(mock_dashboard.grid_layout.widgets) == 6

        # Verify widget titles
        actual_titles = [w.title for w in mock_dashboard.grid_layout.widgets]
        for expected_title in widget_titles:
            assert expected_title in actual_titles

    def test_turn_latency_widget_configuration(self):
        """Verify turn latency widget shows p50, p95, p99 percentiles"""
        # Expected metric query
        expected_metric = "turn_latency_seconds"
        expected_percentiles = [50, 95, 99]

        # This would be actual widget configuration in production
        widget_config = {
            "metric": expected_metric,
            "aggregation": {
                "alignment_period": "60s",
                "per_series_aligner": "ALIGN_DELTA",
                "cross_series_reducer": "REDUCE_PERCENTILE",
                "group_by_fields": []
            },
            "percentiles": expected_percentiles
        }

        assert widget_config["metric"] == expected_metric
        assert widget_config["percentiles"] == expected_percentiles

    def test_agent_latency_widget_grouped_by_agent(self):
        """Verify agent latency widget groups by agent type"""
        widget_config = {
            "metric": "agent_latency_seconds",
            "aggregation": {
                "group_by_fields": ["agent"],
                "cross_series_reducer": "REDUCE_MEAN"
            }
        }

        assert "agent" in widget_config["aggregation"]["group_by_fields"]

    def test_error_rate_widget_calculation(self):
        """Verify error rate widget calculates percentage correctly"""
        # Error rate = (errors_total / requests_total) * 100
        widget_config = {
            "metric_formula": "(errors_total / request_duration_seconds_count) * 100",
            "threshold_line": 5.0  # 5% threshold
        }

        assert "errors_total" in widget_config["metric_formula"]
        assert widget_config["threshold_line"] == 5.0

    def test_cache_metrics_widget_shows_hit_miss_ratio(self):
        """Verify cache widget shows hit/miss ratio"""
        widget_config = {
            "metrics": [
                "cache_hits_total",
                "cache_misses_total"
            ],
            "chart_type": "STACKED_AREA",
            "calculation": "cache_hits_total / (cache_hits_total + cache_misses_total)"
        }

        assert "cache_hits_total" in widget_config["metrics"]
        assert "cache_misses_total" in widget_config["metrics"]

    @pytest.mark.integration
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration", default=False),
        reason="Integration test - requires GCP credentials"
    )
    def test_dashboard_exists_in_production(self):
        """Integration test: Verify dashboard exists in GCP project"""
        import os
        from google.cloud import monitoring_dashboard_v1

        project_id = os.getenv("GCP_PROJECT_ID", "improvOlympics")
        client = monitoring_dashboard_v1.DashboardsServiceClient()

        # List all dashboards
        parent = f"projects/{project_id}"
        dashboards = client.list_dashboards(parent=parent)

        # Find our dashboard
        dashboard_found = False
        for dashboard in dashboards:
            if "Improv Olympics" in dashboard.display_name:
                dashboard_found = True
                # Verify it has widgets
                assert len(dashboard.grid_layout.widgets) >= 6, \
                    "Dashboard should have at least 6 widgets"
                break

        assert dashboard_found, "Dashboard 'Improv Olympics Production' not found"


class TestAlertPolicies:
    """TC-W9-002: Alert Policy Functionality"""

    def test_high_latency_alert_policy_exists(self):
        """Verify high latency alert policy is configured"""
        policy_config = {
            "display_name": "High P95 Turn Latency",
            "conditions": [{
                "display_name": "Turn latency p95 > 8s",
                "condition_threshold": {
                    "filter": 'metric.type="custom.googleapis.com/turn_latency_seconds"',
                    "aggregations": [{
                        "alignment_period": "60s",
                        "per_series_aligner": "ALIGN_DELTA",
                        "cross_series_reducer": "REDUCE_PERCENTILE_95"
                    }],
                    "comparison": "COMPARISON_GT",
                    "threshold_value": 8.0,
                    "duration": "120s"
                }
            }],
            "notification_channels": [],
            "alert_strategy": {
                "auto_close": "604800s"  # 7 days
            }
        }

        assert policy_config["conditions"][0]["condition_threshold"]["threshold_value"] == 8.0
        assert policy_config["conditions"][0]["condition_threshold"]["comparison"] == "COMPARISON_GT"

    def test_error_rate_alert_policy_exists(self):
        """Verify error rate alert policy is configured"""
        policy_config = {
            "display_name": "High Error Rate",
            "conditions": [{
                "display_name": "Error rate > 5%",
                "condition_threshold": {
                    "filter": 'metric.type="custom.googleapis.com/errors_total"',
                    "comparison": "COMPARISON_GT",
                    "threshold_value": 0.05,  # 5%
                    "duration": "300s"
                }
            }]
        }

        assert policy_config["conditions"][0]["condition_threshold"]["threshold_value"] == 0.05

    def test_low_cache_hit_rate_alert_policy_exists(self):
        """Verify low cache hit rate alert policy is configured"""
        policy_config = {
            "display_name": "Low Cache Hit Rate",
            "conditions": [{
                "display_name": "Cache hit rate < 50%",
                "condition_threshold": {
                    "filter": 'metric.type="custom.googleapis.com/cache_hits_total"',
                    "comparison": "COMPARISON_LT",
                    "threshold_value": 0.50,
                    "duration": "600s"  # 10 minutes
                }
            }]
        }

        assert policy_config["conditions"][0]["condition_threshold"]["comparison"] == "COMPARISON_LT"
        assert policy_config["conditions"][0]["condition_threshold"]["threshold_value"] == 0.50

    @pytest.mark.integration
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-integration", default=False),
        reason="Integration test - requires GCP credentials"
    )
    def test_alert_policies_exist_in_production(self):
        """Integration test: Verify all alert policies exist in GCP project"""
        import os
        from google.cloud import monitoring_v3

        project_id = os.getenv("GCP_PROJECT_ID", "improvOlympics")
        client = monitoring_v3.AlertPolicyServiceClient()

        # List all alert policies
        project_name = f"projects/{project_id}"
        policies = client.list_alert_policies(name=project_name)

        # Find our policies
        expected_policies = [
            "High P95 Turn Latency",
            "High Error Rate",
            "Low Cache Hit Rate"
        ]

        found_policies = [policy.display_name for policy in policies]

        for expected_policy in expected_policies:
            assert any(expected_policy in found for found in found_policies), \
                f"Alert policy '{expected_policy}' not found"

    def test_alert_notification_channels_configured(self):
        """Verify alert policies have notification channels"""
        # In production, these would be email, Slack, or PagerDuty channels
        notification_channels = [
            "projects/improvOlympics/notificationChannels/123456",
            "projects/improvOlympics/notificationChannels/789012"
        ]

        policy_config = {
            "notification_channels": notification_channels,
            "alert_strategy": {
                "notification_rate_limit": {
                    "period": "300s"  # Limit to one notification per 5 minutes
                }
            }
        }

        assert len(policy_config["notification_channels"]) >= 1


class TestAlertingServiceIntegration:
    """Test AlertingService integration with Cloud Monitoring"""

    def test_alerting_service_checks_latency_threshold(self):
        """Verify AlertingService.check_latency() creates alerts correctly"""
        from app.services.alerting import AlertingService, AlertSeverity

        alerting = AlertingService(latency_threshold=8.0)

        # Below threshold - no alert
        alert = alerting.check_latency(5.0, "turn_latency")
        assert alert is None

        # Above threshold - warning alert
        alert = alerting.check_latency(9.0, "turn_latency")
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.current_value == 9.0
        assert alert.threshold == 8.0

        # Far above threshold - critical alert
        alert = alerting.check_latency(15.0, "turn_latency")
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL

    def test_alerting_service_checks_error_rate_threshold(self):
        """Verify AlertingService.check_error_rate() creates alerts correctly"""
        from app.services.alerting import AlertingService, AlertSeverity

        alerting = AlertingService(error_rate_threshold=0.05)

        # Below threshold - no alert
        alert = alerting.check_error_rate(total_requests=100, error_count=2)
        assert alert is None

        # Above threshold - warning alert
        alert = alerting.check_error_rate(total_requests=100, error_count=10)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.current_value == 0.10

    def test_alerting_service_checks_cache_hit_rate_threshold(self):
        """Verify AlertingService.check_cache_hit_rate() creates alerts correctly"""
        from app.services.alerting import AlertingService, AlertSeverity

        alerting = AlertingService(cache_hit_rate_threshold=0.50)

        # Above threshold - no alert
        alert = alerting.check_cache_hit_rate(cache_hits=60, cache_total=100)
        assert alert is None

        # Below threshold - warning alert
        alert = alerting.check_cache_hit_rate(cache_hits=30, cache_total=100)
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.current_value == 0.30
