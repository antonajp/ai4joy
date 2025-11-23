# Improv Olympics - Deployment Runbook

This runbook provides step-by-step procedures for deploying, operating, and troubleshooting the Improv Olympics application on GCP.

## Table of Contents

1. [Initial Deployment](#initial-deployment)
2. [Application Updates](#application-updates)
3. [Rollback Procedures](#rollback-procedures)
4. [Troubleshooting](#troubleshooting)
5. [Monitoring & Alerts](#monitoring--alerts)
6. [Incident Response](#incident-response)
7. [Maintenance Procedures](#maintenance-procedures)

---

## Initial Deployment

### Prerequisites Checklist

- [ ] GCP account with billing enabled
- [ ] Domain registered (ai4joy.org)
- [ ] gcloud CLI installed (>= 400.0.0)
- [ ] Terraform installed (>= 1.5.0)
- [ ] Docker installed (>= 20.10.0)
- [ ] Git repository access
- [ ] Billing account ID available

### Step 1: Clone Repository

```bash
git clone https://github.com/{org}/improv-olympics.git
cd improv-olympics
```

### Step 2: Run Setup Script

```bash
# Set environment variables
export PROJECT_ID="improvOlympics"
export REGION="us-central1"
export BILLING_ACCOUNT_ID="XXXXXX-YYYYYY-ZZZZZZ"  # Get from: gcloud billing accounts list

# Run setup
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**What this does:**
- Authenticates with GCP
- Enables essential APIs
- Creates Terraform state bucket
- Generates session encryption key
- Creates terraform.tfvars
- Initializes Terraform

**Expected duration:** 5-10 minutes

### Step 3: Review Terraform Configuration

```bash
cd infrastructure/terraform

# Review variables
cat terraform.tfvars

# Customize as needed (optional)
vim terraform.tfvars
```

**Key variables to review:**
- `billing_account_id`: Your billing account
- `min_instances`: Set to 1 for production (avoid cold starts)
- `max_instances`: Set based on expected load
- `notification_channels`: Add after creating channels

### Step 4: Deploy Infrastructure with Terraform

```bash
# Preview changes
terraform plan

# Review the plan carefully, then apply
terraform apply
```

**Expected duration:** 10-15 minutes

**What gets created:**
- VPC network and serverless connector
- Artifact Registry repository
- Firestore database
- Cloud Storage buckets
- Service accounts with IAM bindings
- Secret Manager secrets
- Cloud Run service (placeholder)
- Global HTTPS Load Balancer
- Cloud DNS zone
- SSL certificate (provisioning starts)
- Cloud Armor security policy
- Monitoring and alerting policies
- Budget alerts

### Step 5: Configure DNS at Domain Registrar

```bash
# Get nameservers
terraform output dns_nameservers
```

**Action required:**
1. Log in to your domain registrar (e.g., Google Domains, Namecheap)
2. Navigate to DNS settings for ai4joy.org
3. Replace existing nameservers with the ones from Terraform output
4. Save changes

**Expected duration:** 24-48 hours for full DNS propagation (but often faster)

### Step 6: Wait for SSL Certificate Provisioning

```bash
# Check certificate status
terraform output ssl_certificate_status

# Or check in Cloud Console
gcloud compute ssl-certificates describe improv-cert --global
```

**Status progression:**
- `PROVISIONING`: Still being provisioned (wait)
- `ACTIVE`: Ready to use (proceed)
- `FAILED`: Check DNS configuration

**Expected duration:** 15-30 minutes after DNS validation

### Step 7: Build and Deploy Application

#### Option A: Using Cloud Build (Recommended)

```bash
# Set up Cloud Build trigger (one-time)
gcloud builds triggers create github \
  --name=deploy-production \
  --repo-name=improv-olympics \
  --repo-owner={your-org} \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml

# Trigger build
gcloud builds submit --config=cloudbuild.yaml
```

#### Option B: Manual Deployment

```bash
# From project root
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

**Expected duration:** 15-20 minutes (first build is slower)

### Step 8: Verify Deployment

```bash
# Get service URL
terraform output load_balancer_url

# Test health endpoint
curl https://ai4joy.org/health

# Expected response: {"status": "healthy"}

# Test ready endpoint
curl https://ai4joy.org/ready

# Expected response: {"status": "ready"}
```

### Step 9: Create Notification Channels

```bash
# Email notification channel
gcloud alpha monitoring channels create \
  --display-name="Email Alerts" \
  --type=email \
  --channel-labels=email_address=alerts@ai4joy.org

# Get channel ID
gcloud alpha monitoring channels list

# Add to terraform.tfvars
# notification_channels = ["projects/improvOlympics/notificationChannels/1234567890"]

# Re-apply Terraform to connect alerts
cd infrastructure/terraform
terraform apply
```

### Step 10: Verify Monitoring

1. **Cloud Monitoring Dashboard:**
   - Visit: https://console.cloud.google.com/monitoring/dashboards?project=improvOlympics
   - Verify metrics are flowing

2. **Cloud Logging:**
   - Visit: https://console.cloud.google.com/logs?project=improvOlympics
   - Filter: `resource.type="cloud_run_revision"`
   - Verify application logs appear

3. **Uptime Checks:**
   - Visit: https://console.cloud.google.com/monitoring/uptime?project=improvOlympics
   - Verify health check is passing

---

## Application Updates

### Standard Update (via CI/CD)

**For production deployments to main branch:**

```bash
# 1. Make changes in feature branch
git checkout -b feature/new-agent-behavior

# 2. Test locally
python -m pytest tests/

# 3. Commit and push
git add .
git commit -m "Add new agent behavior"
git push origin feature/new-agent-behavior

# 4. Create pull request and merge to main

# 5. Cloud Build automatically deploys
# Monitor: https://console.cloud.google.com/cloud-build/builds?project=improvOlympics
```

**Deployment stages (automatic):**
1. Run unit tests
2. Lint code
3. Build Docker image
4. Scan for vulnerabilities
5. Push to Artifact Registry
6. Deploy to Cloud Run
7. Run smoke tests
8. Gradual rollout (90% new, 10% old)
9. Monitor for errors (5 minutes)
10. Complete rollout (100% new)

**Expected duration:** 25-35 minutes

### Manual Update (emergency/testing)

```bash
# Build and deploy
./scripts/deploy.sh

# Or just build
./scripts/deploy.sh --build-only

# Or just deploy existing image
./scripts/deploy.sh --deploy-only --tag v1.2.3
```

### Canary Deployment (manual testing)

```bash
# Deploy new revision
gcloud run deploy improv-olympics-app \
  --image us-central1-docker.pkg.dev/improvOlympics/improv-app/improv-olympics:new-version \
  --region us-central1 \
  --no-traffic

# Route 10% traffic to new revision
NEW_REVISION=$(gcloud run revisions list --service=improv-olympics-app --region=us-central1 --format='value(metadata.name)' --limit=1)
OLD_REVISION=$(gcloud run revisions list --service=improv-olympics-app --region=us-central1 --format='value(metadata.name)' --limit=2 | tail -n 1)

gcloud run services update-traffic improv-olympics-app \
  --region us-central1 \
  --to-revisions=$NEW_REVISION=10,$OLD_REVISION=90

# Monitor for 30 minutes, then increase to 50%
gcloud run services update-traffic improv-olympics-app \
  --region us-central1 \
  --to-revisions=$NEW_REVISION=50,$OLD_REVISION=50

# Monitor, then complete rollout
gcloud run services update-traffic improv-olympics-app \
  --region us-central1 \
  --to-latest
```

---

## Rollback Procedures

### Quick Rollback (Automated Script)

```bash
# Interactive rollback
./scripts/rollback.sh

# Or specify revision
REVISION=improv-olympics-app-00042-xyz ./scripts/rollback.sh
```

### Manual Rollback

```bash
# 1. List recent revisions
gcloud run revisions list \
  --service=improv-olympics-app \
  --region=us-central1 \
  --limit=5

# 2. Identify last stable revision
# Example: improv-olympics-app-00042-abc

# 3. Route 100% traffic to stable revision
gcloud run services update-traffic improv-olympics-app \
  --region=us-central1 \
  --to-revisions=improv-olympics-app-00042-abc=100

# 4. Verify health
curl https://ai4joy.org/health
```

### Rollback Verification

After rollback, verify:
- [ ] Health endpoint returns 200 OK
- [ ] Error rate < 1% in Cloud Monitoring
- [ ] Response latency p95 < 3s
- [ ] No critical alerts firing
- [ ] Test session creation succeeds

**Expected duration:** 2-5 minutes

---

## Troubleshooting

### Service Unavailable (503)

**Symptoms:**
- Load balancer returns 503 Service Unavailable
- curl https://ai4joy.org fails

**Diagnosis:**
```bash
# Check Cloud Run service status
gcloud run services describe improv-olympics-app --region=us-central1

# Check backend service health
gcloud compute backend-services get-health improv-backend --global

# Check Cloud Run logs
./scripts/logs.sh errors 100
```

**Common causes:**
1. **No healthy instances**: Check Cloud Run logs for startup errors
2. **Backend service misconfigured**: Verify NEG in backend service
3. **SSL certificate not active**: Check certificate status
4. **Firewall blocking health checks**: Verify Cloud Armor rules

**Resolution:**
```bash
# If Cloud Run is failing to start
gcloud run services logs read improv-olympics-app --region=us-central1 --limit=50

# Check for:
# - Missing environment variables
# - Secret access errors
# - Application startup errors

# If SSL certificate issues
gcloud compute ssl-certificates describe improv-cert --global

# If PROVISIONING, wait. If FAILED, check DNS.
```

### High Latency (P95 > 5s)

**Symptoms:**
- Users report slow responses
- Cloud Monitoring shows high latency

**Diagnosis:**
```bash
# Check current latency
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_latencies"' \
  --project=improvOlympics

# Check instance count
gcloud run services describe improv-olympics-app \
  --region=us-central1 \
  --format='value(status.traffic[0].revisionName)'

# Get detailed metrics
```

**Common causes:**
1. **Cold starts**: Too many instances scaling from zero
2. **VertexAI API slow**: Check Gemini API latency
3. **Firestore slow queries**: Review query patterns
4. **High concurrency**: Too many requests per instance

**Resolution:**
```bash
# Increase min instances (reduce cold starts)
gcloud run services update improv-olympics-app \
  --region=us-central1 \
  --min-instances=3

# Or update in Terraform
# min_instances = 3
# terraform apply

# Check VertexAI API status
curl https://status.cloud.google.com/

# Review Firestore indexes
gcloud firestore indexes list
```

### High Error Rate (> 5%)

**Symptoms:**
- Error rate alert fires
- Users report failures
- 500 errors in logs

**Diagnosis:**
```bash
# Read error logs
./scripts/logs.sh errors 100

# Check for patterns
gcloud logging read \
  "resource.type=cloud_run_revision \
  AND severity>=ERROR" \
  --limit=100 \
  --format=json | jq '.[] | .jsonPayload.message'

# Check VertexAI quota
gcloud logging read \
  "jsonPayload.error=~'quota'" \
  --limit=50
```

**Common causes:**
1. **VertexAI quota exceeded**: Request quota increase
2. **Application bugs**: Review recent code changes
3. **Firestore permissions**: Check service account IAM
4. **Secret access denied**: Verify Secret Manager permissions

**Resolution:**
```bash
# If quota exceeded
# Request increase: https://console.cloud.google.com/iam-admin/quotas

# If application bugs
./scripts/rollback.sh  # Rollback to stable version

# If IAM issues
gcloud projects get-iam-policy improvOlympics \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:improv-app-runtime@"
```

### SSL Certificate Issues

**Symptoms:**
- HTTPS fails with certificate error
- Browser shows "Not Secure"

**Diagnosis:**
```bash
# Check certificate status
gcloud compute ssl-certificates describe improv-cert --global

# Check DNS
dig ai4joy.org

# Test SSL
openssl s_client -connect ai4joy.org:443 -servername ai4joy.org
```

**Common causes:**
1. **Certificate still provisioning**: Wait 15-30 minutes
2. **DNS not propagated**: Wait up to 48 hours
3. **Domain validation failed**: Check DNS records

**Resolution:**
```bash
# If DNS issue, verify nameservers
terraform output dns_nameservers

# Compare with actual nameservers
dig NS ai4joy.org

# If they don't match, update at domain registrar

# Force DNS validation (if stuck)
# Delete and recreate certificate (use with caution)
```

### Out of Memory (OOM)

**Symptoms:**
- Container crashes with OOM
- Logs show "Killed" or exit code 137

**Diagnosis:**
```bash
# Check memory usage
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/container/memory/utilization"' \
  --project=improvOlympics

# Review container logs
./scripts/logs.sh read 100 | grep -i "memory\|oom"
```

**Resolution:**
```bash
# Increase memory allocation
gcloud run services update improv-olympics-app \
  --region=us-central1 \
  --memory=4Gi

# Or in Terraform
# cloud_run_memory = "4Gi"
# terraform apply

# Review application for memory leaks
# Check conversation_history array growth in sessions
```

---

## Monitoring & Alerts

### Key Metrics to Watch

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| Request Latency (P95) | < 2s | 2-5s | > 5s |
| Error Rate | < 1% | 1-5% | > 5% |
| Instance Count | 1-10 | 10-50 | > 50 |
| CPU Utilization | < 60% | 60-80% | > 80% |
| Memory Utilization | < 70% | 70-85% | > 85% |
| VertexAI QPM | < 500 | 500-900 | > 900 |
| Firestore Reads/s | < 100 | 100-500 | > 500 |

### Access Dashboards

```bash
# Cloud Monitoring
open "https://console.cloud.google.com/monitoring/dashboards?project=improvOlympics"

# Cloud Logging
open "https://console.cloud.google.com/logs?project=improvOlympics"

# Cloud Run Service
open "https://console.cloud.google.com/run/detail/us-central1/improv-olympics-app?project=improvOlympics"
```

### Alert Notifications

**Email alerts configured for:**
- High error rate (> 5% for 5 minutes)
- Service unavailable (uptime check fails)
- VertexAI quota exhausted (> 90%)
- Firestore write spike (> 10x baseline)
- Budget exceeded (50%, 90%, 100%)

**Check alert status:**
```bash
gcloud alpha monitoring policies list --project=improvOlympics
```

---

## Incident Response

### Severity Levels

**P0 - Critical (Service Down)**
- Service unavailable (uptime check failing)
- Error rate > 25%
- Response time: Immediate

**P1 - High (Major Degradation)**
- Error rate 10-25%
- Latency P95 > 10s
- Response time: < 1 hour

**P2 - Medium (Partial Impact)**
- Error rate 5-10%
- Latency P95 5-10s
- Response time: < 4 hours

**P3 - Low (Minor Issues)**
- Error rate 1-5%
- Individual user reports
- Response time: < 24 hours

### P0 Incident Response Runbook

**Step 1: Acknowledge (< 2 minutes)**
```bash
# Check service status
curl -I https://ai4joy.org/health

# Check Cloud Run
gcloud run services describe improv-olympics-app --region=us-central1

# Check error logs
./scripts/logs.sh errors 50
```

**Step 2: Mitigate (< 10 minutes)**
```bash
# If recent deployment caused issue, rollback immediately
./scripts/rollback.sh

# If not deployment-related, check external dependencies
# - VertexAI API: https://status.cloud.google.com/
# - Firestore: Check Cloud Console

# If widespread GCP issue, monitor status page
```

**Step 3: Communicate (< 15 minutes)**
- Post status update (if status page exists)
- Notify stakeholders via email/Slack
- Provide estimated time to resolution

**Step 4: Resolve (ASAP)**
- Fix root cause
- Deploy fix via Cloud Build
- Verify service is healthy

**Step 5: Post-Mortem (< 48 hours)**
- Document incident timeline
- Identify root cause
- List action items to prevent recurrence
- Update runbook with learnings

---

## Maintenance Procedures

### Scheduled Maintenance Window

**Recommended:** Sunday 2-4 AM UTC (low traffic)

**Preparation:**
1. Notify users 48 hours in advance
2. Create rollback plan
3. Test changes in staging
4. Have oncall engineer available

### Update Terraform Infrastructure

```bash
cd infrastructure/terraform

# Pull latest changes
git pull origin main

# Review changes
terraform plan

# Apply during maintenance window
terraform apply

# Verify no service disruption
curl https://ai4joy.org/health
```

### Rotate Secrets

```bash
# Generate new encryption key
NEW_KEY=$(openssl rand -base64 32)

# Create new secret version
echo -n "${NEW_KEY}" | gcloud secrets versions add session-encryption-key \
  --data-file=-

# Deploy new Cloud Run revision (picks up latest secret version)
gcloud run deploy improv-olympics-app \
  --region=us-central1 \
  --image=us-central1-docker.pkg.dev/improvOlympics/improv-app/improv-olympics:latest

# Wait for new revision to be healthy
# Then destroy old secret version
gcloud secrets versions destroy 1 --secret=session-encryption-key
```

### Database Maintenance

**Firestore exports** (automated daily at 2 AM UTC):
```bash
# Verify scheduled exports
gcloud scheduler jobs describe firestore-daily-backup --location=us-central1

# Manual export
gcloud firestore export gs://improvOlympics-backups/firestore/manual/$(date +%Y-%m-%d)
```

**Restore from backup:**
```bash
# List backups
gsutil ls gs://improvOlympics-backups/firestore/

# Restore
gcloud firestore import gs://improvOlympics-backups/firestore/2025-11-23/
```

### Update Dependencies

```bash
# Update Python packages
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt

# Test locally
pytest tests/

# Commit and push (triggers Cloud Build)
git add requirements.txt
git commit -m "Update dependencies"
git push origin main
```

---

## Emergency Contacts

**Primary Oncall:** [Contact Info]
**Secondary Oncall:** [Contact Info]
**GCP Support:** https://cloud.google.com/support (Premium Support recommended for production)

---

## Useful Commands Reference

```bash
# Service status
gcloud run services describe improv-olympics-app --region=us-central1

# Tail logs
./scripts/logs.sh tail

# Read error logs
./scripts/logs.sh errors 100

# List revisions
gcloud run revisions list --service=improv-olympics-app --region=us-central1

# Manual deployment
./scripts/deploy.sh

# Quick rollback
./scripts/rollback.sh

# Check SSL certificate
gcloud compute ssl-certificates describe improv-cert --global

# View monitoring dashboard
open "https://console.cloud.google.com/monitoring/dashboards?project=improvOlympics"

# Check budget
gcloud billing budgets list --billing-account=${BILLING_ACCOUNT_ID}
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-23
**Next Review:** 2026-02-23
