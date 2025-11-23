# Improv Olympics - Terraform Infrastructure

This directory contains Terraform configuration for deploying the complete GCP infrastructure for the Improv Olympics application.

## Prerequisites

1. **Install Terraform** (>= 1.5.0):
   ```bash
   brew install terraform  # macOS
   # or download from https://www.terraform.io/downloads
   ```

2. **Install gcloud CLI**:
   ```bash
   brew install google-cloud-sdk  # macOS
   # or download from https://cloud.google.com/sdk/install
   ```

3. **Authenticate with GCP**:
   ```bash
   gcloud auth application-default login
   gcloud config set project improvOlympics
   ```

4. **Generate encryption key**:
   ```bash
   openssl rand -base64 32
   # Save this output for terraform.tfvars
   ```

## Initial Setup

1. **Create Terraform state bucket** (one-time, manual):
   ```bash
   gsutil mb -p improvOlympics -l us-central1 gs://improvOlympics-terraform-state
   gsutil versioning set on gs://improvOlympics-terraform-state
   ```

2. **Copy and configure variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Initialize Terraform**:
   ```bash
   terraform init
   ```

## Deployment

### Plan (Review Changes)
```bash
terraform plan
```

### Apply (Deploy Infrastructure)
```bash
terraform apply
```

This will create:
- VPC network and serverless VPC connector
- Artifact Registry repository
- Firestore database
- Cloud Storage buckets (backups, Terraform state)
- Service accounts and IAM roles
- Secret Manager secrets
- Cloud Run service
- Global HTTPS Load Balancer
- Cloud DNS zone and records
- SSL certificate (Google-managed)
- Cloud Armor security policy
- Monitoring and alerting policies
- Budget alerts
- Scheduled Firestore backups

### Destroy (Tear Down)
```bash
terraform destroy
```

**Warning**: This will delete all resources. Ensure you have backups!

## Post-Deployment Steps

After `terraform apply` completes:

1. **Configure DNS at domain registrar**:
   - Copy nameservers from output: `terraform output dns_nameservers`
   - Update NS records at your domain registrar (e.g., Google Domains, Namecheap)
   - Wait 24-48 hours for DNS propagation

2. **Wait for SSL certificate provisioning**:
   - Check status: `terraform output ssl_certificate_status`
   - Provisioning takes 15-30 minutes after DNS validation
   - Monitor: https://console.cloud.google.com/net-services/loadbalancing/advanced/sslCertificates

3. **Create notification channels** (for alerting):
   ```bash
   # Email channel
   gcloud alpha monitoring channels create \
     --display-name="Email Alerts" \
     --type=email \
     --channel-labels=email_address=alerts@ai4joy.org

   # Copy the channel ID and add to terraform.tfvars
   ```

4. **Build and deploy application**:
   ```bash
   # See cloudbuild.yaml or manual deployment section
   ```

## Directory Structure

```
infrastructure/terraform/
├── main.tf                    # Main Terraform configuration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── terraform.tfvars.example   # Example variables file
├── terraform.tfvars           # Your variables (gitignored)
├── README.md                  # This file
└── .terraform/                # Terraform state (auto-generated)
```

## Key Resources Created

| Resource Type | Name | Purpose |
|---------------|------|---------|
| VPC Network | `improv-vpc` | Serverless VPC access |
| VPC Connector | `improv-vpc-connector` | Cloud Run to VPC bridge |
| Artifact Registry | `improv-app` | Docker image repository |
| Firestore | `(default)` | Session state database |
| Cloud Run | `improv-olympics-app` | Application runtime |
| Service Account | `improv-app-runtime` | Cloud Run identity |
| Service Account | `cloud-build-deployer` | CI/CD identity |
| Load Balancer | `improv-lb` | Global HTTPS LB |
| SSL Certificate | `improv-cert` | ai4joy.org certificate |
| Static IP | `improv-static-ip` | Global static IP |
| DNS Zone | `ai4joy-org` | DNS management |
| Cloud Armor | `improv-security-policy` | DDoS protection |
| Storage Bucket | `improvOlympics-backups` | Firestore backups |
| Secret | `session-encryption-key` | Session encryption |
| Budget | `Improv Olympics Monthly Budget` | Cost alerts |

## Outputs

After deployment, view outputs:
```bash
terraform output
```

Key outputs:
- `static_ip_address`: IP for DNS A records
- `dns_nameservers`: Nameservers for domain registrar
- `load_balancer_url`: Production URL
- `artifact_registry_repository`: Docker image repository
- `deployment_commands`: Quick reference commands

## Common Operations

### Update Cloud Run Image
```bash
# Terraform manages infrastructure, not application code
# Use gcloud or Cloud Build for deployments:
gcloud run deploy improv-olympics-app \
  --image us-central1-docker.pkg.dev/improvOlympics/improv-app/improv-olympics:latest \
  --region us-central1
```

### View Logs
```bash
# Cloud Run logs
gcloud run services logs tail improv-olympics-app --region us-central1

# Terraform operations logs
terraform show
```

### Update Configuration
```bash
# Edit terraform.tfvars or variables.tf
# Then apply changes:
terraform plan
terraform apply
```

### Check State
```bash
# List all resources
terraform state list

# Show specific resource
terraform state show google_cloud_run_v2_service.improv_app
```

## Troubleshooting

### SSL Certificate Not Provisioning
- Verify DNS is configured: `dig ai4joy.org`
- Check certificate status: `terraform output ssl_certificate_status`
- Wait 15-30 minutes after DNS propagation
- Ensure domains match exactly (no trailing dots in DNS)

### Cloud Run Deployment Fails
- Check service account permissions: `terraform state show google_service_account.app_runtime`
- Verify APIs are enabled: `gcloud services list --enabled`
- Review Cloud Run logs: `gcloud run services logs read improv-olympics-app --region us-central1`

### Terraform State Lock
If Terraform state is locked:
```bash
# List locks
gsutil ls gs://improvOlympics-terraform-state/terraform/state/

# Force unlock (use with caution)
terraform force-unlock <LOCK_ID>
```

### Cost Overruns
- Check budget alerts in Cloud Console
- Review resource usage: `gcloud billing accounts list`
- Adjust `max_instances` in terraform.tfvars
- Consider disabling Memorystore if enabled

## Security Best Practices

1. **Never commit terraform.tfvars**: Contains sensitive values
2. **Use separate environments**: Create separate Terraform workspaces or directories for dev/staging/prod
3. **Restrict service account permissions**: Follow principle of least privilege
4. **Enable audit logging**: Already configured via Terraform
5. **Rotate secrets regularly**: Update `session_encryption_key` periodically
6. **Review IAM bindings**: `terraform state show google_project_iam_member.*`

## Cost Management

Estimated monthly costs (moderate usage):
- Base infrastructure: ~$15/month
- Cloud Run (variable): $50-300/month
- VertexAI API: $10-50/month
- Total: ~$105-425/month

To reduce costs:
- Decrease `min_instances` to 0 (increases cold starts)
- Set lower `max_instances` (risk of capacity limits)
- Disable `enable_memorystore` if not needed
- Use Firestore free tier (50K reads, 20K writes daily)

## Support

For issues or questions:
1. Check Terraform documentation: https://registry.terraform.io/providers/hashicorp/google/latest/docs
2. Review GCP documentation: https://cloud.google.com/docs
3. Check deployment logs: `gcloud run services logs read`
4. Contact GCP support: https://cloud.google.com/support

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-23 | Initial infrastructure |
