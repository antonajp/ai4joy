# Improv Olympics - Main Terraform Configuration
# This file orchestrates the complete GCP infrastructure deployment

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  # Remote state in Cloud Storage (best practice)
  backend "gcs" {
    bucket = "coherent-answer-479115-e1-terraform-state"
    prefix = "terraform/state"
  }
}

# Configure the Google Cloud provider
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Get project metadata (needed for IAP service account)
data "google_project" "project" {
  project_id = var.project_id
}

# Enable required APIs
module "project_services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 14.0"

  project_id = var.project_id

  activate_apis = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "aiplatform.googleapis.com",
    "firestore.googleapis.com",
    "secretmanager.googleapis.com",
    "dns.googleapis.com",
    "compute.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
    "cloudprofiler.googleapis.com",
    "vpcaccess.googleapis.com",
    "certificatemanager.googleapis.com",
    "iap.googleapis.com",
    "cloudscheduler.googleapis.com",
  ]

  disable_services_on_destroy = false
}

# VPC Network for serverless VPC access
resource "google_compute_network" "improv_vpc" {
  name                    = "improv-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id

  depends_on = [module.project_services]
}

# Serverless VPC Access Connector
# Note: The connector will create its own /28 subnet automatically
resource "google_vpc_access_connector" "improv_connector" {
  name          = "improv-vpc-connector"
  region        = var.region
  project       = var.project_id
  network       = google_compute_network.improv_vpc.name
  ip_cidr_range = "10.0.1.0/28"
  min_instances = 2
  max_instances = 10
  machine_type  = "e2-micro"

  depends_on = [
    module.project_services
  ]
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "improv_app" {
  location      = var.region
  repository_id = "improv-app"
  description   = "Docker repository for Improv Olympics application"
  format        = "DOCKER"
  project       = var.project_id

  cleanup_policies {
    id     = "keep-last-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "2592000s" # 30 days
    }
  }

  depends_on = [module.project_services]
}

# Firestore database
resource "google_firestore_database" "improv_sessions" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [module.project_services]
}

# Cloud Storage bucket for Firestore backups
resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-backups"
  location      = var.region
  project       = var.project_id
  storage_class = "COLDLINE"

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }

  depends_on = [module.project_services]
}

# Cloud Storage bucket for Terraform state
resource "google_storage_bucket" "terraform_state" {
  name          = "coherent-answer-479115-e1-terraform-state"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [module.project_services]
}

# Service Accounts
resource "google_service_account" "app_runtime" {
  account_id   = "improv-app-runtime"
  display_name = "Improv Olympics Cloud Run Runtime"
  description  = "Service account for Cloud Run application runtime"
  project      = var.project_id

  depends_on = [module.project_services]
}

resource "google_service_account" "cloud_build" {
  account_id   = "cloud-build-deployer"
  display_name = "Cloud Build Deployer"
  description  = "Service account for CI/CD deployments"
  project      = var.project_id

  depends_on = [module.project_services]
}

# IAM Roles for App Runtime Service Account
resource "google_project_iam_member" "app_runtime_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.app_runtime.email}"
}

resource "google_project_iam_member" "app_runtime_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.app_runtime.email}"
}

resource "google_project_iam_member" "app_runtime_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.app_runtime.email}"
}

resource "google_project_iam_member" "app_runtime_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.app_runtime.email}"
}

resource "google_project_iam_member" "app_runtime_trace" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.app_runtime.email}"
}

# IAM Roles for Cloud Build Service Account
resource "google_project_iam_member" "cloud_build_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "cloud_build_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "cloud_build_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "cloud_build_storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

# OAuth and Session secrets (created via gcloud, referenced here)
data "google_secret_manager_secret" "oauth_client_id" {
  secret_id = "oauth-client-id"
  project   = var.project_id
}

data "google_secret_manager_secret" "oauth_client_secret" {
  secret_id = "oauth-client-secret"
  project   = var.project_id
}

data "google_secret_manager_secret" "session_secret_key" {
  secret_id = "session-secret-key"
  project   = var.project_id
}

# Reserve global static IP address
resource "google_compute_global_address" "improv_ip" {
  name         = "improv-static-ip"
  project      = var.project_id
  address_type = "EXTERNAL"

  depends_on = [module.project_services]
}

# Cloud DNS managed zone
resource "google_dns_managed_zone" "ai4joy_org" {
  name        = "ai4joy-org"
  dns_name    = "ai4joy.org."
  description = "DNS zone for Improv Olympics application"
  project     = var.project_id

  depends_on = [module.project_services]
}

# DNS A record for apex domain
resource "google_dns_record_set" "apex" {
  name         = google_dns_managed_zone.ai4joy_org.dns_name
  managed_zone = google_dns_managed_zone.ai4joy_org.name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.improv_ip.address]
  project      = var.project_id
}

# DNS A record for www subdomain
resource "google_dns_record_set" "www" {
  name         = "www.${google_dns_managed_zone.ai4joy_org.dns_name}"
  managed_zone = google_dns_managed_zone.ai4joy_org.name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_compute_global_address.improv_ip.address]
  project      = var.project_id
}

# Cloud Run service
resource "google_cloud_run_v2_service" "improv_app" {
  name     = "improv-olympics-app"
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.app_runtime.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.improv_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/improv-app/improv-olympics:latest"

      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "REGION"
        value = var.region
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name = "OAUTH_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = data.google_secret_manager_secret.oauth_client_id.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "OAUTH_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = data.google_secret_manager_secret.oauth_client_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "SESSION_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = data.google_secret_manager_secret.session_secret_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "OAUTH_REDIRECT_URI"
        value = "https://ai4joy.org/auth/callback"
      }

      env {
        name  = "ALLOWED_USERS"
        value = var.allowed_users
      }

      ports {
        container_port = 8080
      }

      startup_probe {
        http_get {
          path = "/ready"
        }
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 30
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3
      }
    }

    timeout = "300s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    module.project_services,
    google_artifact_registry_repository.improv_app,
    google_service_account.app_runtime,
    google_vpc_access_connector.improv_connector
  ]

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image, # Managed by CI/CD
    ]
  }
}

# Cloud Run IAM - Allow public access (IAP disabled for non-org projects)
# Note: IAP requires GCP Organization, so allowing public access for now
# You can add authentication at the application level
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.improv_app.location
  name     = google_cloud_run_v2_service.improv_app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Serverless Network Endpoint Group for Load Balancer
resource "google_compute_region_network_endpoint_group" "improv_neg" {
  name                  = "improv-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  project               = var.project_id

  cloud_run {
    service = google_cloud_run_v2_service.improv_app.name
  }

  depends_on = [google_cloud_run_v2_service.improv_app]
}

# IAP OAuth Brand (OAuth Consent Screen)
# DISABLED: IAP requires GCP Organization which personal projects don't have
# To enable IAP, your project must be part of a GCP Organization
# For now, authentication can be handled at the application level
# resource "google_iap_brand" "improv_brand" {
#   support_email     = var.iap_support_email
#   application_title = "Improv Olympics"
#   project           = var.project_id
#
#   depends_on = [module.project_services]
# }

# IAP OAuth Client for Authentication
# DISABLED: Requires IAP Brand which needs GCP Organization
# resource "google_iap_client" "improv_oauth" {
#   display_name = "Improv Olympics IAP Client"
#   brand        = google_iap_brand.improv_brand.name
#
#   depends_on = [google_iap_brand.improv_brand]
# }

# Backend Service with Cloud Armor (IAP disabled for non-org projects)
resource "google_compute_backend_service" "improv_backend" {
  name                  = "improv-backend"
  project               = var.project_id
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP"
  port_name             = "http"
  # Note: timeout_sec is not supported for serverless backends
  # Cloud Run timeout is configured on the service itself

  backend {
    group = google_compute_region_network_endpoint_group.improv_neg.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }

  session_affinity = "GENERATED_COOKIE"

  # Identity-Aware Proxy (IAP) Configuration - DISABLED
  # IAP requires GCP Organization, so it's disabled for personal projects
  # Authentication should be handled at the application level
  # iap {
  #   oauth2_client_id     = google_iap_client.improv_oauth.client_id
  #   oauth2_client_secret = google_iap_client.improv_oauth.secret
  # }

  # Attach Cloud Armor security policy
  security_policy = google_compute_security_policy.improv_policy.id

  depends_on = [
    module.project_services,
    google_compute_security_policy.improv_policy
  ]
}

# IAP Web Backend Service IAM Policy (Who can access via IAP)
# DISABLED: IAP requires GCP Organization
# resource "google_iap_web_backend_service_iam_binding" "improv_iap_access" {
#   project             = var.project_id
#   web_backend_service = google_compute_backend_service.improv_backend.name
#   role                = "roles/iap.httpsResourceAccessor"
#
#   # Grant access to pilot users (configure in variables)
#   members = var.iap_allowed_users
#
#   depends_on = [google_compute_backend_service.improv_backend]
# }

# URL Map
resource "google_compute_url_map" "improv_lb" {
  name            = "improv-lb"
  project         = var.project_id
  default_service = google_compute_backend_service.improv_backend.id
}

# Managed SSL Certificate
resource "google_compute_managed_ssl_certificate" "improv_cert" {
  name    = "improv-cert"
  project = var.project_id

  managed {
    domains = [
      "ai4joy.org",
      "www.ai4joy.org"
    ]
  }

  depends_on = [module.project_services]

  lifecycle {
    create_before_destroy = true
  }
}

# HTTPS Target Proxy
resource "google_compute_target_https_proxy" "improv_https_proxy" {
  name             = "improv-https-proxy"
  project          = var.project_id
  url_map          = google_compute_url_map.improv_lb.id
  ssl_certificates = [google_compute_managed_ssl_certificate.improv_cert.id]
}

# Global Forwarding Rule (HTTPS)
resource "google_compute_global_forwarding_rule" "improv_https" {
  name                  = "improv-https-rule"
  project               = var.project_id
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.improv_https_proxy.id
  ip_address            = google_compute_global_address.improv_ip.id
}

# HTTP to HTTPS Redirect
resource "google_compute_url_map" "improv_http_redirect" {
  name    = "improv-http-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "improv_http_proxy" {
  name    = "improv-http-proxy"
  project = var.project_id
  url_map = google_compute_url_map.improv_http_redirect.id
}

resource "google_compute_global_forwarding_rule" "improv_http" {
  name                  = "improv-http-rule"
  project               = var.project_id
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.improv_http_proxy.id
  ip_address            = google_compute_global_address.improv_ip.id
}

# Cloud Armor Security Policy
resource "google_compute_security_policy" "improv_policy" {
  name    = "improv-security-policy"
  project = var.project_id

  # Default rule
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rule"
  }

  # Allow health check endpoints without IAP authentication
  # Note: IAP is configured at backend service level, but we need to ensure
  # health checks can reach these endpoints from Google's infrastructure
  rule {
    action   = "allow"
    priority = "500"
    match {
      expr {
        expression = "request.path.matches('/health') || request.path.matches('/ready')"
      }
    }
    description = "Allow health check endpoints without authentication"
  }

  # Rate limiting rule
  rule {
    action   = "rate_based_ban"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      ban_duration_sec = 600
    }
    description = "Rate limit: 100 requests per minute per IP"
  }

  # Block requests without User-Agent (except health checks)
  rule {
    action   = "deny(403)"
    priority = "2000"
    match {
      expr {
        expression = "!has(request.headers['user-agent']) && !request.path.matches('/health') && !request.path.matches('/ready')"
      }
    }
    description = "Block requests without User-Agent (except health checks)"
  }

  depends_on = [module.project_services]
}

# Monitoring: Budget Alert
# DISABLED: Requires special quota project configuration
# You can set up budgets manually in the GCP Console:
# https://console.cloud.google.com/billing/budgets
# resource "google_billing_budget" "improv_budget" {
#   billing_account = var.billing_account_id
#   display_name    = "Improv Olympics Monthly Budget"
#
#   budget_filter {
#     projects = ["projects/${var.project_id}"]
#   }
#
#   amount {
#     specified_amount {
#       currency_code = "USD"
#       units         = "150"
#     }
#   }
#
#   threshold_rules {
#     threshold_percent = 0.5
#   }
#
#   threshold_rules {
#     threshold_percent = 0.9
#   }
#
#   threshold_rules {
#     threshold_percent = 1.0
#   }
#
#   all_updates_rule {
#     pubsub_topic = google_pubsub_topic.budget_alerts.id
#   }
# }

# Pub/Sub topic for budget alerts
# DISABLED: Only needed for billing budget which is disabled
# resource "google_pubsub_topic" "budget_alerts" {
#   name    = "budget-alerts"
#   project = var.project_id
#
#   depends_on = [module.project_services]
# }

# Cloud Scheduler job for Firestore backups
resource "google_cloud_scheduler_job" "firestore_backup" {
  name        = "firestore-daily-backup"
  description = "Daily Firestore export to Cloud Storage"
  schedule    = "0 2 * * *" # 2 AM UTC
  time_zone   = "UTC"
  region      = var.region
  project     = var.project_id

  http_target {
    http_method = "POST"
    uri         = "https://firestore.googleapis.com/v1/projects/${var.project_id}/databases/(default):exportDocuments"

    body = base64encode(jsonencode({
      outputUriPrefix = "gs://${google_storage_bucket.backups.name}/firestore/${formatdate("YYYY-MM-DD", timestamp())}"
    }))

    oauth_token {
      service_account_email = google_service_account.app_runtime.email
    }
  }

  depends_on = [
    module.project_services,
    google_storage_bucket.backups
  ]
}

# Log-based metric for scene turn latency
resource "google_logging_metric" "scene_turn_latency" {
  name    = "scene_turn_latency"
  project = var.project_id
  filter  = "jsonPayload.event=\"scene_turn\""

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    unit         = "ms"
    display_name = "Scene Turn Latency"

    labels {
      key         = "agent"
      value_type  = "STRING"
      description = "Agent type"
    }
  }

  value_extractor = "EXTRACT(jsonPayload.latency_ms)"

  label_extractors = {
    agent = "EXTRACT(jsonPayload.agent)"
  }

  bucket_options {
    exponential_buckets {
      num_finite_buckets = 64
      growth_factor      = 2
      scale              = 0.01
    }
  }

  depends_on = [module.project_services]
}

# Alerting: High error rate
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Error rate > 5% for 5 minutes"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.label.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.notification_channels

  alert_strategy {
    auto_close = "1800s"
  }

  depends_on = [module.project_services]
}

# Alerting: Service unavailable
resource "google_monitoring_uptime_check_config" "service_health" {
  display_name = "Improv Olympics Health Check"
  project      = var.project_id
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "ai4joy.org"
    }
  }

  depends_on = [module.project_services]
}

resource "google_monitoring_alert_policy" "service_unavailable" {
  display_name = "Service Unavailable"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Uptime check failure"

    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\""
      duration        = "120s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_FRACTION_TRUE"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.label.host"]
      }
    }
  }

  notification_channels = var.notification_channels

  alert_strategy {
    auto_close = "1800s"
  }

  depends_on = [
    module.project_services,
    google_monitoring_uptime_check_config.service_health
  ]
}

# ============================================================================
# WEEK 9: PRODUCTION OBSERVABILITY - LOG-BASED METRICS & DASHBOARD
# ============================================================================

# Log-based metric for token usage per request
resource "google_logging_metric" "token_usage" {
  name    = "token_usage"
  project = var.project_id
  filter  = "jsonPayload.token_count != null"

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    unit         = "1"
    display_name = "Token Usage Per Request"

    labels {
      key         = "agent"
      value_type  = "STRING"
      description = "Agent type that consumed tokens"
    }

    labels {
      key         = "model"
      value_type  = "STRING"
      description = "Model used (e.g., gemini-2.0-flash-001)"
    }
  }

  value_extractor = "EXTRACT(jsonPayload.token_count)"

  label_extractors = {
    agent = "EXTRACT(jsonPayload.agent)"
    model = "EXTRACT(jsonPayload.model)"
  }

  bucket_options {
    exponential_buckets {
      num_finite_buckets = 64
      growth_factor      = 2
      scale              = 1
    }
  }

  depends_on = [module.project_services]
}

# Log-based metric for sentiment scores
resource "google_logging_metric" "sentiment_score" {
  name    = "sentiment_score"
  project = var.project_id
  filter  = "jsonPayload.sentiment_score != null"

  metric_descriptor {
    metric_kind  = "GAUGE"
    value_type   = "DOUBLE"
    unit         = "1"
    display_name = "Sentiment Score"

    labels {
      key         = "session_id"
      value_type  = "STRING"
      description = "Session identifier"
    }

    labels {
      key         = "turn"
      value_type  = "STRING"
      description = "Turn number in session"
    }
  }

  value_extractor = "EXTRACT(jsonPayload.sentiment_score)"

  label_extractors = {
    session_id = "EXTRACT(jsonPayload.session_id)"
    turn       = "EXTRACT(jsonPayload.turn)"
  }

  depends_on = [module.project_services]
}

# Log-based metric for agent type distribution
resource "google_logging_metric" "agent_invocations" {
  name    = "agent_invocations"
  project = var.project_id
  filter  = "jsonPayload.agent != null AND jsonPayload.operation=\"generate_response\""

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "Agent Invocations"

    labels {
      key         = "agent"
      value_type  = "STRING"
      description = "Agent type (partner, coach, room, stage_manager)"
    }

    labels {
      key         = "success"
      value_type  = "STRING"
      description = "Whether agent execution succeeded"
    }
  }

  value_extractor = "EXTRACT(1)"

  label_extractors = {
    agent   = "EXTRACT(jsonPayload.agent)"
    success = "EXTRACT(jsonPayload.success)"
  }

  depends_on = [module.project_services]
}

# Cloud Monitoring Dashboard
resource "google_monitoring_dashboard" "improv_dashboard" {
  dashboard_json = jsonencode({
    displayName = "Improv Olympics - Production Monitoring"
    mosaicLayout = {
      columns = 12
      tiles = [
        # Widget 1: Request Rate
        {
          width  = 6
          height = 4
          widget = {
            title = "Request Rate (requests/second)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Requests/s"
                scale = "LINEAR"
              }
            }
          }
        },
        # Widget 2: Latency Percentiles (p50, p95, p99)
        {
          xPos   = 6
          width  = 6
          height = 4
          widget = {
            title = "Request Latency Percentiles"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_50"
                      }
                    }
                  }
                  plotType       = "LINE"
                  targetAxis     = "Y1"
                  legendTemplate = "p50"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_95"
                      }
                    }
                  }
                  plotType       = "LINE"
                  targetAxis     = "Y1"
                  legendTemplate = "p95"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_99"
                      }
                    }
                  }
                  plotType       = "LINE"
                  targetAxis     = "Y1"
                  legendTemplate = "p99"
                }
              ]
              yAxis = {
                label = "Latency (ms)"
                scale = "LINEAR"
              }
            }
          }
        },
        # Widget 3: Error Rate (5xx responses)
        {
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Error Rate (5xx responses)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.label.response_code_class=\"5xx\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
                plotType = "LINE"
              }]
              yAxis = {
                label = "Errors/s"
                scale = "LINEAR"
              }
            }
          }
        },
        # Widget 4: Agent Execution Time (scene_turn_latency)
        {
          xPos   = 6
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Agent Execution Time by Type"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"logging.googleapis.com/user/scene_turn_latency\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_DELTA"
                      crossSeriesReducer = "REDUCE_PERCENTILE_95"
                      groupByFields      = ["metric.label.agent"]
                    }
                  }
                }
                plotType = "LINE"
              }]
              yAxis = {
                label = "Latency (ms)"
                scale = "LINEAR"
              }
            }
          }
        },
        # Widget 5: Token Usage Distribution
        {
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "Token Usage by Agent"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"logging.googleapis.com/user/token_usage\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_DELTA"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.label.agent"]
                    }
                  }
                }
                plotType = "STACKED_AREA"
              }]
              yAxis = {
                label = "Tokens"
                scale = "LINEAR"
              }
            }
          }
        },
        # Widget 6: Sentiment Score Distribution
        {
          xPos   = 6
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "Sentiment Score Over Time"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"logging.googleapis.com/user/sentiment_score\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              yAxis = {
                label = "Sentiment (-1 to 1)"
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })

  project = var.project_id

  depends_on = [
    module.project_services,
    google_logging_metric.scene_turn_latency,
    google_logging_metric.token_usage,
    google_logging_metric.sentiment_score,
    google_logging_metric.agent_invocations
  ]
}

# ============================================================================
# WEEK 9: ADDITIONAL ALERT POLICIES
# ============================================================================

# Alert: High p95 latency (> 10s for 5 minutes)
resource "google_monitoring_alert_policy" "high_latency_p95" {
  display_name = "High P95 Latency"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "P95 latency > 10 seconds for 5 minutes"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10000 # milliseconds

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
      }
    }
  }

  notification_channels = var.notification_channels

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "P95 request latency has exceeded 10 seconds for 5 consecutive minutes. This may indicate performance degradation. Check Cloud Trace for slow requests and review agent execution times in the dashboard."
    mime_type = "text/markdown"
  }

  depends_on = [module.project_services]
}

# Alert: Session spike (> 100 new sessions per hour)
resource "google_monitoring_alert_policy" "session_spike" {
  display_name = "High Session Creation Rate"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "More than 100 new sessions per hour"

    condition_threshold {
      filter = join(" AND ", [
        "resource.type=\"cloud_run_revision\"",
        "metric.type=\"run.googleapis.com/request_count\"",
        "metric.label.response_code_class=\"2xx\"",
        "resource.labels.service_name=\"improv-olympics-app\""
      ])
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1.67 # ~100 requests per hour = 1.67 requests per minute

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.notification_channels

  alert_strategy {
    auto_close = "3600s"
  }

  documentation {
    content   = "Session creation rate has exceeded 100 sessions per hour. This may indicate increased traffic or potential abuse. Review request patterns in Cloud Logging and check rate limiting rules in Cloud Armor."
    mime_type = "text/markdown"
  }

  depends_on = [module.project_services]
}

# Alert: Firestore write failures
resource "google_monitoring_alert_policy" "firestore_write_failures" {
  display_name = "Firestore Write Failures"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Firestore write error rate > 5% for 5 minutes"

    condition_threshold {
      filter = join(" AND ", [
        "resource.type=\"datastore_request\"",
        "metric.type=\"datastore.googleapis.com/api/request_count\"",
        "metric.label.response_code!=\"OK\""
      ])
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = var.notification_channels

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "Firestore write operations are experiencing elevated failure rates (>5% for 5 minutes). Check Firestore quotas, IAM permissions, and application logs for error details. Verify the app runtime service account has `roles/datastore.user` permission."
    mime_type = "text/markdown"
  }

  depends_on = [module.project_services]
}

# ============================================================================
# BUDGET ALERTS - MANUAL SETUP REQUIRED
# ============================================================================
# NOTE: Budget alerts require GCP Organization billing permissions which are
# not available for personal projects. These must be configured manually:
#
# 1. Navigate to: https://console.cloud.google.com/billing/budgets
# 2. Click "CREATE BUDGET"
# 3. Set budget name: "Improv Olympics Monthly Budget"
# 4. Set amount: $150 USD
# 5. Add threshold rules at: 50%, 90%, 100%
# 6. Configure email notifications to project owners
#
# Terraform resource (requires billing account permissions):
# resource "google_billing_budget" "improv_budget" {
#   billing_account = var.billing_account_id
#   display_name    = "Improv Olympics Monthly Budget"
#
#   budget_filter {
#     projects = ["projects/${var.project_id}"]
#   }
#
#   amount {
#     specified_amount {
#       currency_code = "USD"
#       units         = "150"
#     }
#   }
#
#   threshold_rules {
#     threshold_percent = 0.5
#   }
#
#   threshold_rules {
#     threshold_percent = 0.9
#   }
#
#   threshold_rules {
#     threshold_percent = 1.0
#   }
# }
# ============================================================================
