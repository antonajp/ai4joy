# Improv Olympics - Terraform Variables Example
# Copy this file to terraform.tfvars and fill in your values

# Required: GCP Project ID
project_id = "coherent-answer-479115-e1"

# Required: Billing account ID for budget alerts
# Find yours: gcloud billing accounts list
billing_account_id = "01A9DB-10D578-9E9D47"

# Required: Session encryption key (generate with: openssl rand -base64 32)
session_encryption_key = "gmPYuhXN3dQgh7PWATlVFZ33Le01JV+N6wOMacyyYYs="

# Optional: Customize region
region = "us-central1"

# Optional: Environment name
environment = "prod"

# Optional: Domain (if different from default)
domain = "ai4joy.org"

# Optional: Cloud Run scaling
min_instances = 1
max_instances = 10

# Optional: Cloud Run resources
cloud_run_cpu    = "2"
cloud_run_memory = "2Gi"

# Optional: Enable Memorystore Redis (adds ~$40/month)
enable_memorystore  = false
memorystore_size_gb = 1

# Optional: Notification channels for alerting
# Create notification channels first, then add their IDs here
notification_channels = [
  # "projects/improvOlympics/notificationChannels/1234567890",
]

# Optional: Resource labels
labels = {
  app         = "improv-olympics"
  environment = "production"
  managed_by  = "terraform"
  team        = "ai4joy"
}

# Optional: Log and backup retention
log_retention_days    = 30
backup_retention_days = 30

# Optional: Enable Cloud CDN (if serving static assets)
enable_cloud_cdn = false

# ==============================================================================
# OAuth / Identity-Aware Proxy (IAP) Configuration - REQUIRED FOR MVP
# ==============================================================================

# Required: Support email for OAuth consent screen (must be project owner/editor)
iap_support_email = "antona.jp@gmail.com"

# Required: List of users/groups allowed to access the application
# Add pilot testers here to grant access
iap_allowed_users = [
  "user:antona.jp@gmail.com",
  "user:jp@iqaccel.com",
  # "group:improv-testers@ai4joy.org",  # Recommended: use Google Group
  # "domain:ai4joy.org",  # Grant access to entire Workspace domain
]

# Optional: Per-user rate limits (cost protection)
user_daily_session_limit       = 10  # Max sessions per user per day
user_concurrent_session_limit  = 3   # Max concurrent sessions per user
