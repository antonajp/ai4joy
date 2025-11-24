# Improv Olympics - GCP Deployment Guide

Complete guide for deploying the Improv Olympics multi-agent application to Google Cloud Platform.

## Quick Start

```bash
# 1. Set environment variables
export PROJECT_ID="your-gcp-project-id"
export BILLING_ACCOUNT_ID="your-billing-account-id"

# 2. Run setup
./scripts/setup.sh

# 3. MANUAL STEP: Create OAuth consent screen (see output from setup.sh)
# Visit: https://console.cloud.google.com/apis/credentials/consent
# Configure: App name, support email, developer contact

# 4. Configure OAuth/IAP in terraform.tfvars
# Set: iap_support_email and iap_allowed_users

# 5. Deploy infrastructure
cd infrastructure/terraform
terraform apply

# 6. Configure DNS at your registrar
# (Use nameservers from: terraform output dns_nameservers)

# 7. Wait for SSL certificate provisioning (15-30 minutes)

# 8. Test OAuth flow
# Visit: https://ai4joy.org (should redirect to Google Sign-In)

# 9. Build and deploy application
cd ../..
./scripts/deploy.sh
```

## Documentation Structure

This deployment includes comprehensive documentation:

### Core Documentation

1. **[GCP Deployment Architecture](docs/gcp-deployment-architecture.md)**
   - Complete infrastructure design
   - Service selection rationale
   - Cost analysis
   - Security configuration
   - Monitoring setup
   - WebSocket architecture (future)

2. **[Deployment Runbook](docs/deployment-runbook.md)**
   - Step-by-step deployment procedures
   - Rollback procedures
   - Troubleshooting guide
   - Incident response procedures
   - Maintenance tasks

3. **[IAP OAuth User Management Guide](docs/IAP_OAUTH_GUIDE.md)**
   - OAuth consent screen setup
   - Managing user access
   - Testing OAuth flow
   - Per-user rate limiting
   - Troubleshooting authentication issues

4. **[Terraform README](infrastructure/terraform/README.md)**
   - Terraform configuration guide
   - Variable documentation
   - Common operations
   - Security best practices

### Infrastructure as Code

- **Terraform Configuration**: `infrastructure/terraform/`
  - `main.tf`: Complete infrastructure definition
  - `variables.tf`: Configurable parameters
  - `outputs.tf`: Deployment outputs
  - `terraform.tfvars.example`: Example configuration

### CI/CD Pipeline

- **Cloud Build**: `cloudbuild.yaml`
  - Automated testing
  - Container building and scanning
  - Cloud Run deployment
  - Gradual rollout
  - Automated rollback on failure

- **Docker**: `Dockerfile`
  - Multi-stage build
  - Security hardening
  - Health checks

### Deployment Scripts

- **Setup**: `scripts/setup.sh`
  - Initial GCP project setup
  - API enablement
  - Bucket creation
  - Key generation

- **Deploy**: `scripts/deploy.sh`
  - Manual deployment option
  - Build-only or deploy-only modes
  - Custom tag support

- **Rollback**: `scripts/rollback.sh`
  - Quick rollback to previous revision
  - Interactive or scripted

- **Logs**: `scripts/logs.sh`
  - Tail logs in real-time
  - Read historical logs
  - Filter error logs

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │  Cloud DNS (ai4joy.org)  │
            └──────────────┬───────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │ Global HTTPS Load Balancer│
            │  - SSL Certificate        │
            │  - IAP OAuth (Auth)       │ ← OAuth 2.0 Authentication
            │  - Cloud Armor (DDoS)     │
            │  - Cloud CDN (future)     │
            └──────────────┬───────────┘
                           │
                       ┌───┴───┐
                       │  IAP  │  ← Identity-Aware Proxy
                       │ Check │     - Google Sign-In
                       └───┬───┘     - User verification
                           │
                           ▼
            ┌──────────────────────────┐
            │   Cloud Run Service      │
            │  - Auto-scaling (1-100)  │
            │  - 2 vCPU, 2 GiB RAM     │
            │  - Container: ADK app    │
            │  + IAP Headers           │ ← User ID from IAP
            └──────┬──────┬────────────┘
                   │      │
         ┌─────────┘      └──────────┐
         │                            │
         ▼                            ▼
┌────────────────┐         ┌──────────────────┐
│  VertexAI API  │         │    Firestore     │
│ - Gemini Pro   │         │ - Session state  │
│ - Gemini Flash │         │ - Conversation   │
└────────────────┘         │   history        │
                           │ - user_limits    │ ← Rate limiting
                           └──────────────────┘
```

## Key Features

### Infrastructure
- Fully automated Terraform deployment
- Serverless Cloud Run (auto-scaling, pay-per-use)
- Global HTTPS Load Balancer with SSL
- Cloud Armor DDoS protection
- VPC networking for security

### State Management
- Firestore for session persistence
- Automated daily backups
- Point-in-time recovery

### Security
- OAuth 2.0 authentication via Identity-Aware Proxy (IAP)
- Google Sign-In for user authentication
- Per-user rate limiting (10 sessions/day, 3 concurrent)
- Workload Identity Federation (no API keys)
- Secret Manager for credentials
- Least privilege IAM
- Cloud Armor DDoS protection and rate limiting
- SSL/TLS encryption

### Observability
- Cloud Monitoring dashboards
- Structured logging with Cloud Logging
- Cloud Trace for distributed tracing
- Uptime checks and SLO alerts
- Budget alerts

### CI/CD
- Automated Cloud Build pipeline
- Container vulnerability scanning
- Smoke tests on deployment
- Gradual rollout (canary)
- Automated rollback on errors

## Cost Estimate

**Monthly costs** (moderate usage: 2000 sessions/month):
- Cloud Run: ~$75
- VertexAI (Gemini): ~$12
- Load Balancing: ~$8
- Firestore: ~$1
- Other services: ~$9
- **Total: ~$105/month**

**High usage** (10,000 sessions/month):
- **Total: ~$425/month**

See [Cost Analysis](docs/gcp-deployment-architecture.md#8-cost-analysis--optimization) for detailed breakdown and optimization strategies.

## Prerequisites

### Required
- GCP account with billing enabled
- Domain name (ai4joy.org)
- gcloud CLI (>= 400.0.0)
- Terraform (>= 1.5.0)
- Docker (>= 20.10.0)

### Recommended
- Git (for version control)
- jq (for JSON parsing in scripts)
- curl (for API testing)

## Deployment Steps

### 1. Initial Setup

```bash
# Clone repository
git clone https://github.com/{org}/improv-olympics.git
cd improv-olympics

# Set environment variables
export PROJECT_ID="improvOlympics"
export REGION="us-central1"
export BILLING_ACCOUNT_ID="$(gcloud billing accounts list --format='value(name)' --limit=1)"

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This creates:
- Terraform state bucket
- Build artifacts bucket
- Session encryption key (.env.local)
- Terraform configuration (terraform.tfvars)

### 2. Create OAuth Consent Screen (One-Time Manual Step)

**IMPORTANT:** This step must be completed before running `terraform apply`.

```bash
# Open OAuth consent screen configuration
open "https://console.cloud.google.com/apis/credentials/consent?project=${PROJECT_ID}"
```

**Configuration Steps:**

1. **User Type:**
   - Select "Internal" (if using Google Workspace) or "External"
   - Click "Create"

2. **App Information:**
   - App name: `Improv Olympics`
   - Support email: Your email (will be used in terraform.tfvars)
   - App logo: (optional)
   - Developer contact: Your email

3. **Scopes:**
   - Skip this section (click "Save and Continue")

4. **Test Users (External only):**
   - Skip for now (click "Save and Continue")

5. **Summary:**
   - Review and click "Back to Dashboard"

**Why is this manual?**
- Google allows only ONE OAuth brand per project
- Must be created via console before Terraform can reference it
- See [IAP OAuth Guide](docs/IAP_OAUTH_GUIDE.md#initial-oauth-setup) for details

### 3. Review and Customize Configuration

```bash
# Review Terraform variables
cat infrastructure/terraform/terraform.tfvars

# Customize OAuth/IAP settings (REQUIRED)
vim infrastructure/terraform/terraform.tfvars
```

**Required OAuth/IAP Configuration:**

```terraform
# OAuth / IAP Configuration - REQUIRED FOR MVP
iap_support_email = "your-email@example.com"  # Must match OAuth consent screen

iap_allowed_users = [
  "user:your-email@example.com",
  "user:pilot1@example.com",
  # Add pilot testers:
  # "user:tester@example.com",
  # "group:improv-testers@ai4joy.org",  # Recommended
]

# Per-user rate limits (cost protection)
user_daily_session_limit       = 10  # Max sessions per user per day
user_concurrent_session_limit  = 3   # Max concurrent sessions per user
```

**Optional Customizations:**
- `min_instances`: 0 for dev (slower), 1+ for prod (faster)
- `max_instances`: Set based on expected traffic (default: 100)
- `cloud_run_cpu` / `cloud_run_memory`: Adjust for workload
- `notification_channels`: Add after creating channels

### 4. Deploy Infrastructure

```bash
cd infrastructure/terraform

# Preview changes (verify IAP resources)
terraform plan | grep -A 5 "google_iap"

# Deploy (takes 10-15 minutes)
terraform apply

# Save outputs (including IAP OAuth details)
terraform output > ../../deployment-outputs.txt

# Verify IAP configuration
terraform output iap_oauth_client_id
terraform output iap_allowed_users
```

### 5. Configure DNS

```bash
# Get nameservers
terraform output dns_nameservers

# Example output:
# ns-cloud-a1.googledomains.com.
# ns-cloud-a2.googledomains.com.
# ns-cloud-a3.googledomains.com.
# ns-cloud-a4.googledomains.com.
```

**Action required:**
1. Log in to your domain registrar (e.g., Google Domains)
2. Update nameservers for ai4joy.org
3. Wait for propagation (15 minutes - 48 hours)

### 6. Wait for SSL Certificate

```bash
# Check certificate status
watch -n 30 'gcloud compute ssl-certificates describe improv-cert --global --format="value(managed.status)"'

# Wait for: ACTIVE
```

Expected: 15-30 minutes after DNS propagation

### 7. Test OAuth Authentication Flow

**Before deploying the application**, verify that OAuth/IAP is working:

```bash
# Test 1: Health check (should work without auth)
curl https://ai4joy.org/health
# Expected: {"status": "healthy"} or connection error (if SSL not ready)

# Test 2: Main application (should redirect to Google Sign-In)
# Open in incognito browser window:
open "https://ai4joy.org"

# Expected behavior:
# 1. Redirect to Google Sign-In page
# 2. Sign in with authorized user (from iap_allowed_users)
# 3. Redirect back to application
# 4. Application loads (may show error if app not deployed yet)

# Test 3: Verify IAP is enabled
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=improv-backend

# Expected: Shows iap_allowed_users with roles/iap.httpsResourceAccessor
```

**Troubleshooting OAuth:**
- If OAuth consent screen shows "error", verify you created OAuth brand in Step 2
- If 403 Forbidden, check that your email is in `iap_allowed_users`
- If redirect loop, wait for SSL certificate to be ACTIVE
- See [IAP OAuth Guide](docs/IAP_OAUTH_GUIDE.md#troubleshooting) for detailed help

### 8. Build and Deploy Application

#### Option A: Cloud Build (Recommended for Production)

```bash
# Set up GitHub integration (one-time)
gcloud builds connections create github improv-olympics-github \
  --region=us-central1

# Create trigger
gcloud builds triggers create github \
  --name=deploy-production \
  --repository=projects/improvOlympics/locations/us-central1/connections/improv-olympics-github/repositories/improv-olympics \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml

# Trigger initial build
gcloud builds submit --config=cloudbuild.yaml
```

#### Option B: Manual Deployment

```bash
cd ../..  # Back to project root
./scripts/deploy.sh
```

### 9. Verify Deployment with OAuth

```bash
# Test health endpoint (no auth required)
curl https://ai4joy.org/health
# Expected: {"status": "healthy"}

# Test ready endpoint (no auth required)
curl https://ai4joy.org/ready
# Expected: {"status": "ready"}

# Test authenticated API access (requires browser session)
# 1. Sign in via browser: https://ai4joy.org
# 2. Open browser DevTools → Network tab
# 3. Copy session cookie
# 4. Use cookie in curl:

curl -X POST https://ai4joy.org/api/v1/session \
  -H "Content-Type: application/json" \
  -H "Cookie: YOUR_SESSION_COOKIE" \
  -d '{"user_id":"test-user","location":"Test Location"}'
# Expected: {"session_id": "...", ...}

# Test unauthenticated API (should fail)
curl -X POST https://ai4joy.org/api/v1/session \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test-user","location":"Test Location"}'
# Expected: 302 redirect to Google Sign-In
```

**OAuth-Specific Verification:**

```bash
# Check application logs for IAP headers
gcloud run services logs read improv-olympics-app \
  --region=us-central1 \
  --limit=10

# Look for IAP headers in logs:
# X-Goog-Authenticated-User-Email: accounts.google.com:user@example.com
# X-Goog-Authenticated-User-ID: accounts.google.com:1234567890
```

### 10. Manage OAuth/IAP User Access

Add or remove users from IAP access:

```bash
# Add individual user
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=improv-backend \
  --member='user:newpilot@example.com' \
  --role='roles/iap.httpsResourceAccessor'

# Add Google Group (recommended)
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=improv-backend \
  --member='group:improv-testers@ai4joy.org' \
  --role='roles/iap.httpsResourceAccessor'

# Remove user
gcloud iap web remove-iam-policy-binding \
  --resource-type=backend-services \
  --service=improv-backend \
  --member='user:remove@example.com' \
  --role='roles/iap.httpsResourceAccessor'

# List current access
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=improv-backend
```

See [IAP OAuth Guide](docs/IAP_OAUTH_GUIDE.md) for detailed user management procedures.

### 11. Set Up Monitoring

```bash
# Create email notification channel
gcloud alpha monitoring channels create \
  --display-name="Email Alerts" \
  --type=email \
  --channel-labels=email_address=alerts@ai4joy.org

# Get channel ID
CHANNEL_ID=$(gcloud alpha monitoring channels list --format='value(name)' --limit=1)

# Add to terraform.tfvars
echo "notification_channels = [\"${CHANNEL_ID}\"]" >> infrastructure/terraform/terraform.tfvars

# Re-apply to connect alerts
cd infrastructure/terraform
terraform apply
```

### 12. Access Dashboards

```bash
# Cloud Monitoring
open "https://console.cloud.google.com/monitoring?project=improvOlympics"

# Cloud Run Service
open "https://console.cloud.google.com/run/detail/us-central1/improv-olympics-app?project=improvOlympics"

# Cloud Logging
open "https://console.cloud.google.com/logs?project=improvOlympics"
```

## Post-Deployment

### Daily Operations

```bash
# View logs
./scripts/logs.sh tail

# Check service status
gcloud run services describe improv-olympics-app --region=us-central1

# Monitor costs
gcloud billing accounts get-cost-table --billing-account=${BILLING_ACCOUNT_ID}
```

### Application Updates

For production deployments:
1. Create feature branch
2. Make changes and test locally
3. Create pull request
4. Merge to main → Cloud Build auto-deploys

For emergency fixes:
```bash
./scripts/deploy.sh --tag hotfix-v1.2.3
```

### Rollback

If deployment fails or causes issues:
```bash
./scripts/rollback.sh
```

## Troubleshooting

See [Deployment Runbook - Troubleshooting](docs/deployment-runbook.md#troubleshooting) for detailed procedures.

### Common Issues

**SSL Certificate Not Provisioning**
- Verify DNS: `dig ai4joy.org`
- Check nameservers match Cloud DNS
- Wait up to 48 hours for DNS propagation

**Service Unavailable (503)**
- Check Cloud Run logs: `./scripts/logs.sh errors 50`
- Verify service account permissions
- Check VertexAI API status: https://status.cloud.google.com/

**High Latency**
- Increase min_instances to reduce cold starts
- Check VertexAI API latency in Cloud Monitoring
- Review Firestore query patterns

## Security Best Practices

1. **Never commit secrets**
   - .env.local is gitignored
   - Use Secret Manager for all credentials

2. **Least privilege IAM**
   - Service accounts have minimal required permissions
   - Review IAM regularly

3. **Keep dependencies updated**
   - Run `pip install --upgrade -r requirements.txt` monthly
   - Monitor security advisories

4. **Enable audit logging**
   - Already configured via Terraform
   - Review logs for suspicious activity

5. **Rotate secrets regularly**
   - Rotate session_encryption_key quarterly
   - Follow [Maintenance Procedures](docs/deployment-runbook.md#maintenance-procedures)

## Support

### Documentation
- [GCP Deployment Architecture](docs/gcp-deployment-architecture.md)
- [Deployment Runbook](docs/deployment-runbook.md)
- [Terraform README](infrastructure/terraform/README.md)

### Resources
- [GCP Documentation](https://cloud.google.com/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [VertexAI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

### Getting Help
1. Check troubleshooting section in Deployment Runbook
2. Review Cloud Logging for error messages
3. Contact GCP Support (if Premium Support enabled)
4. File issue in GitHub repository

## Contributing

When making infrastructure changes:
1. Test in separate GCP project first
2. Update Terraform configuration
3. Update documentation
4. Run `terraform fmt` and `terraform validate`
5. Create pull request with detailed description

## License

See LICENSE file for details.

---

**Deployment Guide Version:** 1.0
**Last Updated:** 2025-11-23
**Maintained by:** ai4joy.org team
