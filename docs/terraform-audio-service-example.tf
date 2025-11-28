# Terraform Module: Audio Service (Cloud Run + WebSocket Support)
# Location: terraform/modules/audio-service/main.tf

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

variable "region" {
  description = "GCP region for Cloud Run service"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "ai4joy-audio-service"
}

variable "image" {
  description = "Container image URL from Artifact Registry"
  type        = string
  # Example: us-central1-docker.pkg.dev/PROJECT/ai4joy/audio-service:latest
}

variable "min_instances" {
  description = "Minimum number of instances (0 for cost savings, 1+ for warm start)"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of instances for autoscaling"
  type        = number
  default     = 50
}

variable "cpu" {
  description = "CPU allocation (1000m = 1 vCPU)"
  type        = string
  default     = "2000m"
}

variable "memory" {
  description = "Memory allocation"
  type        = string
  default     = "1Gi"
}

variable "concurrency" {
  description = "Max concurrent requests per instance"
  type        = number
  default     = 10
}

variable "timeout" {
  description = "Request timeout in seconds"
  type        = number
  default     = 3600  # 1 hour for WebSocket connections
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "vertex_ai_location" {
  description = "Vertex AI API location"
  type        = string
  default     = "us-central1"
}

variable "enable_iap" {
  description = "Enable Identity-Aware Proxy authentication"
  type        = bool
  default     = true
}

# Service Account for Cloud Run
resource "google_service_account" "audio_service" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name}"
  project      = var.project_id
}

# IAM Roles for Service Account
resource "google_project_iam_member" "audio_service_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.audio_service.email}"
}

resource "google_project_iam_member" "audio_service_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.audio_service.email}"
}

resource "google_project_iam_member" "audio_service_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.audio_service.email}"
}

resource "google_project_iam_member" "audio_service_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.audio_service.email}"
}

resource "google_project_iam_member" "audio_service_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.audio_service.email}"
}

# Cloud Run Service for Real-Time Audio
resource "google_cloud_run_v2_service" "audio_service" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.audio_service.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image

      # Resource limits
      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle = false  # Always allocate CPU (critical for WebSocket)
      }

      # Environment variables
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "VERTEX_AI_LOCATION"
        value = var.vertex_ai_location
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "WEBSOCKET_TIMEOUT"
        value = "3600"
      }

      env {
        name  = "WEBSOCKET_PING_INTERVAL"
        value = "30"  # Send keepalive every 30 seconds
      }

      # Secret Manager reference for ADK API credentials
      env {
        name = "ADK_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "adk-api-key"  # Created separately
            version = "latest"
          }
        }
      }

      # Health check endpoints
      startup_probe {
        http_get {
          path = "/ws/health"
          port = 8080
        }
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/ws/health"
          port = 8080
        }
        initial_delay_seconds = 30
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3
      }

      ports {
        container_port = 8080
        name           = "http1"
      }
    }

    # Concurrency and timeout settings
    max_instance_request_concurrency = var.concurrency
    timeout                          = "${var.timeout}s"

    # Labels for resource organization
    labels = {
      app         = "ai4joy"
      component   = "audio-service"
      environment = var.environment
      managed_by  = "terraform"
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = {
    app         = "ai4joy"
    component   = "audio-service"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# IAM Policy for Cloud Run (conditional IAP or public access)
resource "google_cloud_run_v2_service_iam_member" "audio_service_invoker" {
  count = var.enable_iap ? 0 : 1  # Only if not using IAP

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.audio_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"  # For public access (use IAP in production)
}

# Outputs
output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.audio_service.uri
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.audio_service.name
}

output "service_account_email" {
  description = "Service account email for the audio service"
  value       = google_service_account.audio_service.email
}
