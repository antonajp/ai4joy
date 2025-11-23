# Improv Olympics - Terraform Outputs

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "Primary GCP region"
  value       = var.region
}

output "static_ip_address" {
  description = "Global static IP address for load balancer"
  value       = google_compute_global_address.improv_ip.address
}

output "dns_nameservers" {
  description = "DNS nameservers for ai4joy.org (configure at domain registrar)"
  value       = google_dns_managed_zone.ai4joy_org.name_servers
}

output "cloud_run_service_url" {
  description = "Cloud Run service URL (internal)"
  value       = google_cloud_run_v2_service.improv_app.uri
}

output "load_balancer_url" {
  description = "Production URL via Load Balancer"
  value       = "https://${var.domain}"
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository for Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/improv-app"
}

output "app_runtime_service_account" {
  description = "Service account email for Cloud Run runtime"
  value       = google_service_account.app_runtime.email
}

output "cloud_build_service_account" {
  description = "Service account email for Cloud Build"
  value       = google_service_account.cloud_build.email
}

output "firestore_database" {
  description = "Firestore database name"
  value       = google_firestore_database.improv_sessions.name
}

output "backup_bucket" {
  description = "Cloud Storage bucket for backups"
  value       = google_storage_bucket.backups.url
}

output "ssl_certificate_status" {
  description = "SSL certificate provisioning status"
  value       = google_compute_managed_ssl_certificate.improv_cert.managed[0].status
}

output "vpc_connector_id" {
  description = "VPC Access Connector ID"
  value       = google_vpc_access_connector.improv_connector.id
}

output "monitoring_dashboard_url" {
  description = "Cloud Monitoring console URL"
  value       = "https://console.cloud.google.com/monitoring/dashboards?project=${var.project_id}"
}

output "cloud_run_logs_url" {
  description = "Cloud Run logs URL"
  value       = "https://console.cloud.google.com/run/detail/${var.region}/${google_cloud_run_v2_service.improv_app.name}/logs?project=${var.project_id}"
}

output "deployment_commands" {
  description = "Quick reference commands for deployment"
  value = {
    build_image = "gcloud builds submit --tag ${var.region}-docker.pkg.dev/${var.project_id}/improv-app/improv-olympics:latest"
    deploy      = "gcloud run deploy ${google_cloud_run_v2_service.improv_app.name} --image ${var.region}-docker.pkg.dev/${var.project_id}/improv-app/improv-olympics:latest --region ${var.region}"
    view_logs   = "gcloud run services logs read ${google_cloud_run_v2_service.improv_app.name} --region ${var.region} --limit 50"
    tail_logs   = "gcloud run services logs tail ${google_cloud_run_v2_service.improv_app.name} --region ${var.region}"
  }
}

output "next_steps" {
  description = "Next steps after infrastructure deployment"
  value = <<-EOT
    Infrastructure deployed successfully!

    Next steps:
    1. Configure DNS at your registrar with these nameservers:
       ${join("\n       ", google_dns_managed_zone.ai4joy_org.name_servers)}

    2. Wait 15-30 minutes for SSL certificate provisioning.
       Check status: https://console.cloud.google.com/net-services/loadbalancing/advanced/sslCertificates/details/improv-cert?project=${var.project_id}

    3. Build and deploy your application:
       ${var.region}-docker.pkg.dev/${var.project_id}/improv-app/improv-olympics:latest

    4. Test the deployment:
       curl -k https://${var.domain}/health

    5. Set up notification channels for alerting:
       https://console.cloud.google.com/monitoring/alerting/notifications?project=${var.project_id}

    6. Review monitoring dashboard:
       https://console.cloud.google.com/monitoring/dashboards?project=${var.project_id}
  EOT
}
