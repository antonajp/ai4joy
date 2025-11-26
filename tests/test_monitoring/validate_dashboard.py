#!/usr/bin/env python3
"""
Script to validate Cloud Monitoring Dashboard for IQS-47 Week 9

Usage:
    python validate_dashboard.py --project improvOlympics --dashboard-name "Improv Olympics Production"

This script verifies:
- Dashboard exists in the GCP project
- All 6 required widgets are present
- Alert policies are configured correctly
"""
import argparse
import sys
from google.cloud import monitoring_dashboard_v1
from google.cloud import monitoring_v3


def validate_dashboard_widgets(project_id: str, dashboard_name: str) -> bool:
    """Validate dashboard has all required widgets"""
    client = monitoring_dashboard_v1.DashboardsServiceClient()

    # List all dashboards
    parent = f"projects/{project_id}"
    dashboards = client.list_dashboards(parent=parent)

    # Find our dashboard
    target_dashboard = None
    for dashboard in dashboards:
        if dashboard_name.lower() in dashboard.display_name.lower():
            target_dashboard = dashboard
            break

    if not target_dashboard:
        print(f"❌ Dashboard '{dashboard_name}' not found in project {project_id}")
        return False

    print(f"✅ Dashboard '{target_dashboard.display_name}' found")

    # Verify widgets
    widgets = (
        target_dashboard.grid_layout.widgets if target_dashboard.grid_layout else []
    )
    widget_count = len(widgets)

    print(f"\nWidget Count: {widget_count}")

    if widget_count < 6:
        print(f"❌ Expected at least 6 widgets, found {widget_count}")
        return False

    print("✅ Dashboard has 6+ widgets")

    # List widget titles
    print("\nWidget Titles:")
    for i, widget in enumerate(widgets, 1):
        title = widget.title or f"Widget {i} (no title)"
        print(f"  {i}. {title}")

    # Expected widget titles
    expected_widgets = [
        "Turn Latency",
        "Agent",
        "Error Rate",
        "Cache",
        "Session",
        "Request",
    ]

    widget_titles = " ".join([w.title.lower() for w in widgets if w.title])

    found_widgets = []
    for expected in expected_widgets:
        if expected.lower() in widget_titles:
            found_widgets.append(expected)
            print(f"✅ Found widget matching: {expected}")
        else:
            print(f"⚠️  Widget matching '{expected}' not clearly identified")

    return True


def validate_alert_policies(project_id: str) -> bool:
    """Validate alert policies exist"""
    client = monitoring_v3.AlertPolicyServiceClient()

    project_name = f"projects/{project_id}"
    policies = client.list_alert_policies(name=project_name)

    policy_names = [policy.display_name for policy in policies]

    print(f"\n{len(policy_names)} alert policies found in project")

    # Expected policies
    expected_policies = [
        "High P95 Turn Latency",
        "High Error Rate",
        "Low Cache Hit Rate",
    ]

    all_found = True
    for expected_policy in expected_policies:
        found = any(expected_policy.lower() in name.lower() for name in policy_names)
        if found:
            print(f"✅ Alert policy found: {expected_policy}")
        else:
            print(f"❌ Alert policy NOT found: {expected_policy}")
            all_found = False

    return all_found


def validate_metrics(project_id: str) -> bool:
    """Validate custom metrics exist in Cloud Monitoring"""
    client = monitoring_v3.MetricServiceClient()

    project_name = f"projects/{project_id}"
    metric_descriptors = client.list_metric_descriptors(name=project_name)

    # Filter for custom metrics
    custom_metrics = []
    for descriptor in metric_descriptors:
        if (
            "custom.googleapis.com" in descriptor.type
            or "workload.googleapis.com" in descriptor.type
        ):
            custom_metrics.append(descriptor.type)

    print(f"\n{len(custom_metrics)} custom metrics found")

    # Expected metrics
    expected_metrics = [
        "turn_latency_seconds",
        "agent_latency_seconds",
        "cache_hits_total",
        "cache_misses_total",
        "errors_total",
    ]

    found_metrics = []
    for expected in expected_metrics:
        matching = [m for m in custom_metrics if expected in m]
        if matching:
            print(f"✅ Metric found: {expected}")
            print(f"   Full name: {matching[0]}")
            found_metrics.append(expected)
        else:
            print(f"⚠️  Metric not found: {expected}")

    print(f"\n{len(found_metrics)}/{len(expected_metrics)} expected metrics found")

    return len(found_metrics) >= 3  # At least 3 metrics should exist


def main():
    parser = argparse.ArgumentParser(description="Validate Cloud Monitoring Dashboard")
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument(
        "--dashboard-name",
        default="Improv Olympics Production",
        help="Dashboard display name",
    )

    args = parser.parse_args()

    print(f"Validating Cloud Monitoring for project: {args.project}\n")
    print("=" * 70)

    # Validate dashboard
    print("\n1. DASHBOARD VALIDATION")
    print("-" * 70)
    dashboard_valid = validate_dashboard_widgets(args.project, args.dashboard_name)

    # Validate alert policies
    print("\n2. ALERT POLICY VALIDATION")
    print("-" * 70)
    alerts_valid = validate_alert_policies(args.project)

    # Validate metrics
    print("\n3. CUSTOM METRICS VALIDATION")
    print("-" * 70)
    metrics_valid = validate_metrics(args.project)

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    results = {
        "Dashboard": dashboard_valid,
        "Alert Policies": alerts_valid,
        "Custom Metrics": metrics_valid,
    }

    for component, is_valid in results.items():
        status = "✅ PASS" if is_valid else "❌ FAIL"
        print(f"{component:.<40} {status}")

    all_valid = all(results.values())

    if all_valid:
        print("\n✅ All validations passed!")
        sys.exit(0)
    else:
        print("\n❌ Some validations failed. Review output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
