# Improv Olympics - Terraform Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "coherent-answer-479115-e1"
}

variable "region" {
  description = "Primary GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "billing_account_id" {
  description = "Billing account ID for budget alerts"
  type        = string
  # Set this via terraform.tfvars or environment variable
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances (keep warm)"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "cloud_run_cpu" {
  description = "CPU allocation for Cloud Run (e.g., '1', '2', '4')"
  type        = string
  default     = "2"
}

variable "cloud_run_memory" {
  description = "Memory allocation for Cloud Run (e.g., '512Mi', '1Gi', '2Gi')"
  type        = string
  default     = "2Gi"
}

# OAuth secrets are managed via Secret Manager (created via gcloud)
# No variables needed here - referenced as data sources in main.tf

variable "allowed_users" {
  description = "Comma-separated list of email addresses allowed to access the application (leave empty to allow all - not recommended)"
  type        = string
  default     = ""
  # Example: "user1@example.com,user2@example.com,user3@example.com"
}

variable "notification_channels" {
  description = "List of notification channel IDs for alerting"
  type        = list(string)
  default     = []
  # Create channels manually or via Terraform, then reference their IDs
}

variable "domain" {
  description = "Primary domain name"
  type        = string
  default     = "ai4joy.org"
}

variable "enable_memorystore" {
  description = "Enable Memorystore Redis for caching (adds ~$40/month cost)"
  type        = bool
  default     = false
}

variable "memorystore_size_gb" {
  description = "Memorystore Redis capacity in GB (if enabled)"
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "Number of days to retain logs in Cloud Logging"
  type        = number
  default     = 30
}

variable "backup_retention_days" {
  description = "Number of days to retain Firestore backups"
  type        = number
  default     = 30
}

variable "enable_cloud_cdn" {
  description = "Enable Cloud CDN for static content caching"
  type        = bool
  default     = false
  # Set to true when serving static assets
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    app         = "improv-olympics"
    environment = "production"
    managed_by  = "terraform"
  }
}

# Rate Limiting Variables
variable "user_daily_session_limit" {
  description = "Maximum sessions per user per day (cost protection)"
  type        = number
  default     = 10
}

variable "user_concurrent_session_limit" {
  description = "Maximum concurrent active sessions per user"
  type        = number
  default     = 3
}
