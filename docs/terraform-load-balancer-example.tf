# Terraform Module: Load Balancer with WebSocket Support
# Location: terraform/modules/load-balancer/main.tf

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

variable "domain_name" {
  description = "Domain name for SSL certificate"
  type        = string
  # Example: app.example.com
}

variable "api_service_name" {
  description = "Existing REST API Cloud Run service name"
  type        = string
}

variable "api_service_region" {
  description = "Region of existing API service"
  type        = string
  default     = "us-central1"
}

variable "audio_service_name" {
  description = "Audio WebSocket Cloud Run service name"
  type        = string
}

variable "audio_service_region" {
  description = "Region of audio service"
  type        = string
  default     = "us-central1"
}

variable "enable_cloud_armor" {
  description = "Enable Cloud Armor for DDoS protection"
  type        = bool
  default     = true
}

variable "enable_iap" {
  description = "Enable Identity-Aware Proxy"
  type        = bool
  default     = true
}

# Regional Network Endpoint Group for API Service
resource "google_compute_region_network_endpoint_group" "api_neg" {
  name                  = "api-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.api_service_region
  project               = var.project_id

  cloud_run {
    service = var.api_service_name
  }
}

# Regional Network Endpoint Group for Audio Service
resource "google_compute_region_network_endpoint_group" "audio_neg" {
  name                  = "audio-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.audio_service_region
  project               = var.project_id

  cloud_run {
    service = var.audio_service_name
  }
}

# Backend Service for REST API
resource "google_compute_backend_service" "api_backend" {
  name                  = "api-backend-service"
  project               = var.project_id
  protocol              = "HTTP2"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  timeout_sec           = 30
  enable_cdn            = false  # CDN typically not useful for APIs

  backend {
    group = google_compute_region_network_endpoint_group.api_neg.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0  # Log all requests (adjust for production)
  }

  dynamic "iap" {
    for_each = var.enable_iap ? [1] : []
    content {
      oauth2_client_id     = google_iap_client.iap_client[0].client_id
      oauth2_client_secret = google_iap_client.iap_client[0].secret
    }
  }
}

# Backend Service for WebSocket Audio
resource "google_compute_backend_service" "audio_backend" {
  name                  = "audio-backend-service"
  project               = var.project_id
  protocol              = "HTTP"  # HTTP/1.1 for WebSocket support
  load_balancing_scheme = "EXTERNAL_MANAGED"
  timeout_sec           = 3600    # 1 hour for WebSocket connections
  enable_cdn            = false   # CRITICAL: Do not enable CDN for WebSocket

  backend {
    group = google_compute_region_network_endpoint_group.audio_neg.id
  }

  session_affinity = "CLIENT_IP"  # Pin clients to same instance

  log_config {
    enable      = true
    sample_rate = 1.0
  }

  # Custom request/response headers for WebSocket
  custom_request_headers = [
    "X-Client-Region:{client_region}",
    "X-Client-City:{client_city}"
  ]

  dynamic "iap" {
    for_each = var.enable_iap ? [1] : []
    content {
      oauth2_client_id     = google_iap_client.iap_client[0].client_id
      oauth2_client_secret = google_iap_client.iap_client[0].secret
    }
  }
}

# URL Map for path-based routing
resource "google_compute_url_map" "default" {
  name            = "ai4joy-url-map"
  project         = var.project_id
  default_service = google_compute_backend_service.api_backend.id

  host_rule {
    hosts        = [var.domain_name]
    path_matcher = "main-paths"
  }

  path_matcher {
    name            = "main-paths"
    default_service = google_compute_backend_service.api_backend.id

    path_rule {
      paths   = ["/ws/audio/*", "/ws/health"]
      service = google_compute_backend_service.audio_backend.id
    }

    path_rule {
      paths   = ["/api/*", "/health", "/"]
      service = google_compute_backend_service.api_backend.id
    }
  }
}

# Google-managed SSL Certificate
resource "google_compute_managed_ssl_certificate" "default" {
  name    = "ai4joy-ssl-cert"
  project = var.project_id

  managed {
    domains = [var.domain_name]
  }

  lifecycle {
    create_before_destroy = true
  }
}

# SSL Policy (Modern TLS configuration)
resource "google_compute_ssl_policy" "modern_tls" {
  name            = "modern-tls-policy"
  project         = var.project_id
  profile         = "MODERN"
  min_tls_version = "TLS_1_2"
}

# HTTPS Proxy
resource "google_compute_target_https_proxy" "default" {
  name             = "ai4joy-https-proxy"
  project          = var.project_id
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
  ssl_policy       = google_compute_ssl_policy.modern_tls.id
}

# Global Forwarding Rule (HTTPS)
resource "google_compute_global_forwarding_rule" "https" {
  name                  = "ai4joy-https-forwarding-rule"
  project               = var.project_id
  target                = google_compute_target_https_proxy.default.id
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.default.address
}

# HTTP to HTTPS Redirect
resource "google_compute_url_map" "http_redirect" {
  name    = "ai4joy-http-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "http_redirect" {
  name    = "ai4joy-http-proxy"
  project = var.project_id
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "ai4joy-http-forwarding-rule"
  project               = var.project_id
  target                = google_compute_target_http_proxy.http_redirect.id
  port_range            = "80"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.default.address
}

# Static IP Address
resource "google_compute_global_address" "default" {
  name    = "ai4joy-lb-ip"
  project = var.project_id
}

# Cloud Armor Security Policy (DDoS + Rate Limiting)
resource "google_compute_security_policy" "cloud_armor" {
  count   = var.enable_cloud_armor ? 1 : 0
  name    = "ai4joy-security-policy"
  project = var.project_id

  # Default rule: Allow traffic
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }

  # Rate limiting for WebSocket connections
  rule {
    action   = "rate_based_ban"
    priority = 1000
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
        count        = 100  # 100 WebSocket upgrade requests
        interval_sec = 60   # per minute
      }

      ban_duration_sec = 600  # 10-minute ban for violators
    }
    description = "Rate limit WebSocket upgrades to 100/min per IP"
  }

  # Pre-configured WAF rules (OWASP Top 10)
  rule {
    action   = "deny(403)"
    priority = 2000
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-v33-stable')"
      }
    }
    description = "SQL injection protection"
  }

  rule {
    action   = "deny(403)"
    priority = 3000
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-v33-stable')"
      }
    }
    description = "XSS protection"
  }

  # Geo-blocking example (optional)
  # rule {
  #   action   = "deny(403)"
  #   priority = 4000
  #   match {
  #     expr {
  #       expression = "origin.region_code == 'CN' || origin.region_code == 'RU'"
  #     }
  #   }
  #   description = "Block traffic from specific countries"
  # }

  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
    }
  }
}

# Attach Cloud Armor to backend services
resource "google_compute_backend_service_security_policy" "api_armor" {
  count          = var.enable_cloud_armor ? 1 : 0
  backend_service = google_compute_backend_service.api_backend.name
  security_policy = google_compute_security_policy.cloud_armor[0].name
}

resource "google_compute_backend_service_security_policy" "audio_armor" {
  count          = var.enable_cloud_armor ? 1 : 0
  backend_service = google_compute_backend_service.audio_backend.name
  security_policy = google_compute_security_policy.cloud_armor[0].name
}

# IAP Configuration (if enabled)
resource "google_iap_client" "iap_client" {
  count        = var.enable_iap ? 1 : 0
  display_name = "AI4Joy IAP Client"
  brand        = "projects/${data.google_project.project.number}/brands/${data.google_project.project.number}"
}

data "google_project" "project" {
  project_id = var.project_id
}

# Outputs
output "load_balancer_ip" {
  description = "Static IP address for the load balancer"
  value       = google_compute_global_address.default.address
}

output "api_backend_service" {
  description = "API backend service name"
  value       = google_compute_backend_service.api_backend.name
}

output "audio_backend_service" {
  description = "Audio backend service name"
  value       = google_compute_backend_service.audio_backend.name
}

output "ssl_certificate_name" {
  description = "Managed SSL certificate name"
  value       = google_compute_managed_ssl_certificate.default.name
}

output "url_map_name" {
  description = "URL map name for routing configuration"
  value       = google_compute_url_map.default.name
}
