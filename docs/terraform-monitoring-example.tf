# Terraform Module: Monitoring, Alerting, and SLOs for Audio Service
# Location: terraform/modules/monitoring/main.tf

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "audio_service_name" {
  description = "Cloud Run audio service name"
  type        = string
}

variable "notification_email" {
  description = "Email address for alert notifications"
  type        = string
}

variable "notification_slack_webhook" {
  description = "Slack webhook URL for alert notifications (optional)"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

# Notification Channel - Email
resource "google_monitoring_notification_channel" "email" {
  display_name = "Audio Service Alerts - Email"
  project      = var.project_id
  type         = "email"

  labels = {
    email_address = var.notification_email
  }

  enabled = true
}

# Notification Channel - Slack (optional)
resource "google_monitoring_notification_channel" "slack" {
  count        = var.notification_slack_webhook != "" ? 1 : 0
  display_name = "Audio Service Alerts - Slack"
  project      = var.project_id
  type         = "slack"

  labels = {
    url = var.notification_slack_webhook
  }

  enabled = true
}

# Custom Metrics Dashboard
resource "google_monitoring_dashboard" "audio_service_dashboard" {
  dashboard_json = jsonencode({
    displayName = "AI4Joy Audio Service - Real-Time Monitoring"
    mosaicLayout = {
      columns = 12
      tiles = [
        # WebSocket Connections (Active)
        {
          width  = 6
          height = 4
          widget = {
            title = "Active WebSocket Connections"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        },

        # Request Latency (p50, p95, p99)
        {
          xPos   = 6
          width  = 6
          height = 4
          widget = {
            title = "WebSocket Request Latency (ms)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_50"
                      }
                    }
                  }
                  plotType = "LINE"
                  legendTemplate = "p50"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_95"
                      }
                    }
                  }
                  plotType = "LINE"
                  legendTemplate = "p95"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_99"
                      }
                    }
                  }
                  plotType = "LINE"
                  legendTemplate = "p99"
                }
              ]
            }
          }
        },

        # Instance Count
        {
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run Instance Count"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/container/instance_count\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        },

        # CPU Utilization
        {
          xPos   = 6
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "CPU Utilization (%)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/container/cpu/utilizations\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              yAxis = {
                scale = "LINEAR"
              }
            }
          }
        },

        # Memory Utilization
        {
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "Memory Utilization (%)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/container/memory/utilizations\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        },

        # Error Rate (5xx responses)
        {
          xPos   = 6
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "Error Rate (5xx Responses)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/request_count\" metric.labels.response_code_class=\"5xx\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        }
      ]
    }
  })
}

# Alert Policy: High Error Rate
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "[${upper(var.environment)}] Audio Service - High Error Rate"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Error rate > 5% for 5 minutes"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/request_count\" metric.labels.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05  # 5% error rate

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.notification_slack_webhook != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )

  alert_strategy {
    auto_close = "1800s"  # 30 minutes
  }

  documentation {
    content = <<-EOT
      # Audio Service High Error Rate Alert

      **What's happening:**
      The audio service is experiencing a 5xx error rate above 5% for the last 5 minutes.

      **Impact:**
      Users may be unable to establish WebSocket connections or experience audio session failures.

      **Troubleshooting Steps:**
      1. Check Cloud Run logs: `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${var.audio_service_name}" --limit 50 --format json`
      2. Verify Vertex AI quota: Check for rate limiting errors in logs
      3. Check instance health: Review Cloud Monitoring dashboard for CPU/memory saturation
      4. Verify Secret Manager access: Ensure ADK API credentials are accessible
      5. Check upstream dependencies: Vertex AI service status

      **Escalation:**
      If error rate persists for >15 minutes, escalate to on-call engineer.
    EOT
    mime_type = "text/markdown"
  }
}

# Alert Policy: High Latency
resource "google_monitoring_alert_policy" "high_latency" {
  display_name = "[${upper(var.environment)}] Audio Service - High Latency"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "p95 latency > 2 seconds for 5 minutes"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 2000  # 2000ms = 2 seconds

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
      }
    }
  }

  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.notification_slack_webhook != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content = <<-EOT
      # Audio Service High Latency Alert

      **What's happening:**
      The p95 latency for WebSocket requests exceeds 2 seconds for the last 5 minutes.

      **Impact:**
      Users experience delayed audio responses and degraded conversational quality.

      **Troubleshooting Steps:**
      1. Check Cloud Profiler for performance bottlenecks
      2. Review Cloud Trace for distributed tracing insights
      3. Check instance count: May need to increase min_instances
      4. Verify Vertex AI response times: Check if upstream API is slow
      5. Review CPU/memory utilization: Scale up if saturated

      **Mitigation:**
      - Increase min_instances to 2-3 to reduce cold start impact
      - Scale CPU to 4 vCPU if sustained high utilization
      - Check for Vertex AI quota throttling
    EOT
    mime_type = "text/markdown"
  }
}

# Alert Policy: Instance Saturation
resource "google_monitoring_alert_policy" "instance_saturation" {
  display_name = "[${upper(var.environment)}] Audio Service - Instance Saturation"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Instances near max capacity for 10 minutes"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/container/instance_count\""
      duration        = "600s"
      comparison      = "COMPARISON_GT"
      threshold_value = 40  # 80% of max_instances (50)

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.notification_slack_webhook != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )

  alert_strategy {
    auto_close = "3600s"
  }

  documentation {
    content = <<-EOT
      # Audio Service Instance Saturation Alert

      **What's happening:**
      The service is running near maximum instance capacity (>40 instances).

      **Impact:**
      - New WebSocket connections may be throttled or rejected
      - Users experience "service unavailable" errors
      - Approaching max_instances limit (50)

      **Immediate Actions:**
      1. Increase max_instances: `terraform apply -var="max_instances=100"`
      2. Monitor instance count closely
      3. Check for abnormal traffic patterns (DDoS?)
      4. Review Cloud Armor logs for blocked requests

      **Long-term Solutions:**
      - Optimize concurrency per instance (currently 10-20)
      - Implement connection pooling or session queuing
      - Consider multi-region deployment for global scale
    EOT
    mime_type = "text/markdown"
  }
}

# Alert Policy: Cold Start Rate
resource "google_monitoring_alert_policy" "cold_start_rate" {
  display_name = "[${upper(var.environment)}] Audio Service - High Cold Start Rate"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Cold starts > 10/minute for 5 minutes"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.audio_service_name}\" metric.type=\"run.googleapis.com/container/startup_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10  # 10 cold starts per minute

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_COUNT"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content = <<-EOT
      # Audio Service High Cold Start Rate

      **What's happening:**
      The service is experiencing frequent cold starts (>10/minute).

      **Impact:**
      - First WebSocket connections take 3-5 seconds longer
      - Poor user experience during scale-up events

      **Actions:**
      1. Increase min_instances from 1 to 2-3
      2. Review traffic patterns: Are there sudden spikes?
      3. Consider using Cloud Scheduler to ping /ws/health every 5 minutes

      **Configuration:**
      ```bash
      terraform apply -var="min_instances=2"
      ```
    EOT
    mime_type = "text/markdown"
  }
}

# Log-based Metric: WebSocket Connection Duration
resource "google_logging_metric" "websocket_duration" {
  name    = "audio_service_websocket_duration"
  project = var.project_id
  filter  = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="${var.audio_service_name}"
    jsonPayload.message=~"WebSocket connection closed"
  EOT

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "DISTRIBUTION"
    unit        = "s"

    labels {
      key         = "disconnect_reason"
      value_type  = "STRING"
      description = "Reason for WebSocket disconnection"
    }
  }

  value_extractor = "EXTRACT(jsonPayload.duration)"

  label_extractors = {
    "disconnect_reason" = "EXTRACT(jsonPayload.disconnect_reason)"
  }
}

# Log-based Metric: Vertex AI API Errors
resource "google_logging_metric" "vertex_ai_errors" {
  name    = "audio_service_vertex_ai_errors"
  project = var.project_id
  filter  = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="${var.audio_service_name}"
    jsonPayload.message=~"Vertex AI API error"
  EOT

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"

    labels {
      key         = "error_type"
      value_type  = "STRING"
      description = "Type of Vertex AI error"
    }
  }

  label_extractors = {
    "error_type" = "EXTRACT(jsonPayload.error_type)"
  }
}

# SLO: Availability (99.5% uptime)
resource "google_monitoring_slo" "availability" {
  service      = google_monitoring_custom_service.audio_service.service_id
  slo_id       = "audio-service-availability-slo"
  display_name = "99.5% Availability"

  goal                = 0.995  # 99.5%
  rolling_period_days = 30

  request_based_sli {
    good_total_ratio {
      total_service_filter = <<-EOT
        resource.type="cloud_run_revision"
        resource.labels.service_name="${var.audio_service_name}"
        metric.type="run.googleapis.com/request_count"
      EOT

      good_service_filter = <<-EOT
        resource.type="cloud_run_revision"
        resource.labels.service_name="${var.audio_service_name}"
        metric.type="run.googleapis.com/request_count"
        metric.labels.response_code_class!="5xx"
      EOT
    }
  }
}

# SLO: Latency (95% requests < 1 second)
resource "google_monitoring_slo" "latency" {
  service      = google_monitoring_custom_service.audio_service.service_id
  slo_id       = "audio-service-latency-slo"
  display_name = "95% requests < 1s latency"

  goal                = 0.95
  rolling_period_days = 30

  request_based_sli {
    distribution_cut {
      distribution_filter = <<-EOT
        resource.type="cloud_run_revision"
        resource.labels.service_name="${var.audio_service_name}"
        metric.type="run.googleapis.com/request_latencies"
      EOT

      range {
        min = 0
        max = 1000  # 1000ms = 1 second
      }
    }
  }
}

# Custom Service for SLOs
resource "google_monitoring_custom_service" "audio_service" {
  service_id   = "audio-service-custom"
  display_name = "Audio WebSocket Service"
  project      = var.project_id
}

# Outputs
output "dashboard_url" {
  description = "URL to the Cloud Monitoring dashboard"
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.audio_service_dashboard.id}?project=${var.project_id}"
}

output "notification_channel_email" {
  description = "Email notification channel ID"
  value       = google_monitoring_notification_channel.email.id
}

output "slo_availability_id" {
  description = "SLO ID for availability tracking"
  value       = google_monitoring_slo.availability.slo_id
}

output "slo_latency_id" {
  description = "SLO ID for latency tracking"
  value       = google_monitoring_slo.latency.slo_id
}
