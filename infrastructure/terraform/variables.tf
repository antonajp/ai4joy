# Improv Olympics - Terraform Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "improvOlympics"
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
  default     = 100
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

variable "session_encryption_key" {
  description = "Encryption key for session data (should be passed securely)"
  type        = string
  sensitive   = true
  # Generate with: openssl rand -base64 32
  # Pass via: TF_VAR_session_encryption_key or terraform.tfvars
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
