# Deployment Runbook - Improv Olympics Production

**Version**: 1.0
**Last Updated**: 2025-11-24
**Branch**: IQS-46

This runbook provides step-by-step procedures for deploying the Improv Olympics application to Google Cloud Run.

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Steps](#deployment-steps)
3. [Post-Deployment Validation](#post-deployment-validation)
4. [Rollback Procedures](#rollback-procedures)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)
7. [Emergency Contacts](#emergency-contacts)

---

## Pre-Deployment Checklist

### Code Quality

- [ ] All unit tests passing (101+ tests)
- [ ] Integration tests reviewed (can run with `--run-integration` flag)
- [ ] Code review completed and approved
- [ ] Branch merged to main/master
- [ ] Git tag created for release (e.g., `v1.0.0`)

### Infrastructure Verification

- [ ] GCP Project ID verified: `coherent-answer-479115-e1`
- [ ] Firestore database accessible
- [ ] VertexAI API enabled
- [ ] Cloud Run API enabled
- [ ] Artifact Registry repository exists
- [ ] Service account permissions verified

### Configuration

- [ ] Environment variables reviewed in `.env.production`
- [ ] OAuth client credentials configured
- [ ] Allowed users list updated
- [ ] Rate limits configured appropriately
- [ ] Session timeout set correctly (default: 60 minutes)

### Security

- [ ] Service account follows principle of least privilege
- [ ] IAP authentication configured (if using)
- [ ] OAuth scopes reviewed
- [ ] Allowed users list validated
- [ ] Secrets stored in Secret Manager (not in code)

### Monitoring Setup

- [ ] Cloud Logging configured
- [ ] Cloud Monitoring dashboards created
- [ ] Alert policies defined
- [ ] Error reporting enabled
- [ ] Log retention policies set

---

## Deployment Steps

### Step 1: Prepare Build

```bash
# Navigate to project directory
cd /path/to/ai4joy

# Ensure on correct branch
git checkout main
git pull origin main

# Verify current commit
git log -1 --oneline

# Create release tag
git tag -a v1.0.0 -m "Production release v1.0.0"
git push origin v1.0.0
```

**Expected Output**: Tag created and pushed successfully

**Rollback**: Delete tag with `git tag -d v1.0.0; git push origin :refs/tags/v1.0.0`

---

### Step 2: Build Container Image

```bash
# Set variables
export PROJECT_ID="coherent-answer-479115-e1"
export REGION="us-central1"
export SERVICE_NAME="improv-olympics"
export IMAGE_TAG="v1.0.0"
export IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"

# Build container
gcloud builds submit \
  --tag ${IMAGE_NAME} \
  --project ${PROJECT_ID} \
  --timeout=20m

# Verify image exists
gcloud container images describe ${IMAGE_NAME} --project ${PROJECT_ID}
```

**Expected Output**:
```
BUILD SUCCESSFUL
Image: gcr.io/coherent-answer-479115-e1/improv-olympics:v1.0.0
```

**Rollback**: N/A (can rebuild if needed)

**Estimated Time**: 5-10 minutes

---

### Step 3: Deploy to Cloud Run

```bash
# Deploy service
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 80 \
  --max-instances 10 \
  --min-instances 1 \
  --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars "GCP_LOCATION=${REGION}" \
  --set-env-vars "FIRESTORE_DATABASE=(default)" \
  --set-env-vars "RATE_LIMIT_DAILY_SESSIONS=10" \
  --set-env-vars "RATE_LIMIT_CONCURRENT_SESSIONS=3" \
  --set-secrets "OAUTH_CLIENT_ID=oauth-client-id:latest" \
  --set-secrets "OAUTH_CLIENT_SECRET=oauth-client-secret:latest" \
  --set-secrets "SESSION_SECRET_KEY=session-secret-key:latest" \
  --set-secrets "ALLOWED_USERS=allowed-users:latest"

# Get service URL
gcloud run services describe ${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)'
```

**Expected Output**:
```
Deploying container to Cloud Run service [improv-olympics]
✓ Deploying... Done.
✓ Creating Revision...
✓ Routing traffic...
Service URL: https://improv-olympics-xxxxx-uc.a.run.app
```

**Rollback**: See [Rollback Procedures](#rollback-procedures)

**Estimated Time**: 3-5 minutes

---

### Step 4: Configure Traffic Routing (Blue-Green Deployment)

```bash
# Deploy new revision without traffic
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --no-traffic \
  --tag blue \
  --region ${REGION} \
  --project ${PROJECT_ID}

# Get revision name
export NEW_REVISION=$(gcloud run revisions list \
  --service ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(name)' \
  --limit 1)

echo "New revision: ${NEW_REVISION}"

# Test new revision (blue URL)
# Perform smoke tests on blue URL

# If tests pass, gradually shift traffic
gcloud run services update-traffic ${SERVICE_NAME} \
  --to-revisions ${NEW_REVISION}=10 \
  --region ${REGION} \
  --project ${PROJECT_ID}

# Monitor for 5-10 minutes

# If no issues, shift 100% traffic
gcloud run services update-traffic ${SERVICE_NAME} \
  --to-revisions ${NEW_REVISION}=100 \
  --region ${REGION} \
  --project ${PROJECT_ID}
```

**Expected Output**: Traffic gradually shifted to new revision

**Rollback**: Shift traffic back to previous revision

---

## Post-Deployment Validation

### 1. Health Check Verification

```bash
export SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)')

# Health endpoint
curl ${SERVICE_URL}/health

# Expected: {"status": "healthy", "timestamp": "..."}

# Ready endpoint
curl ${SERVICE_URL}/ready

# Expected: {"status": "ready", "timestamp": "..."}
```

**Success Criteria**: Both endpoints return 200 status

---

### 2. Smoke Test Execution

```bash
# Run automated smoke tests
python3 scripts/smoke_test.py --service-url ${SERVICE_URL}
```

**Expected Output**:
```
Running smoke tests...
✓ Health check passed
✓ Readiness check passed
✓ Session creation passed
✓ Turn execution passed
✓ Session closure passed

All smoke tests passed!
```

**Success Criteria**: All tests pass

---

### 3. Authentication Verification

```bash
# Test OAuth login flow
curl ${SERVICE_URL}/auth/login

# Should redirect to Google OAuth

# Test authenticated endpoint (requires valid session)
# Use browser to complete OAuth flow and verify session creation works
```

**Success Criteria**: OAuth flow completes successfully

---

### 4. Functional Testing

Manually execute:

1. **Create Session**: Navigate to app, click "Start Session"
2. **Execute Turn**: Submit user input, verify partner response
3. **Phase Transition**: Execute 5 turns, verify Phase 2 begins
4. **Coach Feedback**: Execute 15 turns, verify coach appears
5. **Rate Limits**: Check `/api/v1/user/limits` endpoint

**Success Criteria**: All user flows work as expected

---

### 5. Performance Validation

```bash
# Check response times in Cloud Monitoring
gcloud monitoring time-series list \
  --filter 'metric.type="run.googleapis.com/request_latencies"' \
  --project ${PROJECT_ID}

# Check error rates
gcloud monitoring time-series list \
  --filter 'metric.type="run.googleapis.com/request_count"' \
  --project ${PROJECT_ID}
```

**Success Criteria**:
- P95 latency < 5 seconds for turn execution
- Error rate < 1%
- No 5xx errors

---

### 6. Log Verification

```bash
# View recent logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=${SERVICE_NAME}" \
  --limit 50 \
  --project ${PROJECT_ID} \
  --format json

# Check for errors
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=${SERVICE_NAME} \
  AND severity>=ERROR" \
  --limit 20 \
  --project ${PROJECT_ID}
```

**Success Criteria**: No unexpected errors in logs

---

## Rollback Procedures

### Scenario 1: Immediate Rollback (Critical Issue)

```bash
# Get previous revision
export PREVIOUS_REVISION=$(gcloud run revisions list \
  --service ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(name)' \
  --limit 2 | tail -n 1)

echo "Rolling back to: ${PREVIOUS_REVISION}"

# Shift 100% traffic to previous revision
gcloud run services update-traffic ${SERVICE_NAME} \
  --to-revisions ${PREVIOUS_REVISION}=100 \
  --region ${REGION} \
  --project ${PROJECT_ID}

# Verify rollback
curl ${SERVICE_URL}/health
```

**Expected Time**: < 1 minute

---

### Scenario 2: Rollback to Specific Version

```bash
# List all revisions
gcloud run revisions list \
  --service ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID}

# Rollback to specific revision
export TARGET_REVISION="improv-olympics-00012-abc"

gcloud run services update-traffic ${SERVICE_NAME} \
  --to-revisions ${TARGET_REVISION}=100 \
  --region ${REGION} \
  --project ${PROJECT_ID}
```

---

### Scenario 3: Rollback Container Image

```bash
# Redeploy previous image tag
export ROLLBACK_IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:v0.9.0"

gcloud run deploy ${SERVICE_NAME} \
  --image ${ROLLBACK_IMAGE} \
  --region ${REGION} \
  --project ${PROJECT_ID}
```

---

## Monitoring

### Dashboards to Check

1. **Cloud Run Dashboard**
   - URL: https://console.cloud.google.com/run?project=coherent-answer-479115-e1
   - Metrics: Request count, latency, error rate, memory usage, CPU usage

2. **Cloud Logging Explorer**
   - URL: https://console.cloud.google.com/logs
   - Query: `resource.type="cloud_run_revision" resource.labels.service_name="improv-olympics"`

3. **Error Reporting**
   - URL: https://console.cloud.google.com/errors
   - Check for new error groups

4. **Firestore Console**
   - URL: https://console.cloud.google.com/firestore
   - Monitor document counts and operation metrics

### Key Metrics

| Metric | Threshold | Alert Condition |
|--------|-----------|-----------------|
| Request Latency (P95) | < 5s | > 8s |
| Error Rate | < 1% | > 5% |
| Memory Usage | < 80% | > 90% |
| CPU Usage | < 70% | > 85% |
| Active Sessions | N/A | Monitor trends |
| Daily Session Count | N/A | Monitor for spikes |

### Alert Policies

Ensure these alerts are configured:

- High error rate (> 5% for 5 minutes)
- High latency (P95 > 8s for 5 minutes)
- Memory usage (> 90% for 10 minutes)
- Service unavailable (no successful requests for 5 minutes)

---

## Troubleshooting

### Issue: Service Returns 503 Unavailable

**Symptoms**:
- All requests return 503
- Cloud Run dashboard shows no active instances

**Diagnosis**:
```bash
# Check service status
gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID}

# Check recent logs
gcloud logging read "resource.type=cloud_run_revision \
  AND severity>=ERROR" \
  --limit 20 \
  --project ${PROJECT_ID}
```

**Possible Causes**:
1. Container startup failure
2. Health check failures
3. Out of memory
4. Firestore connection issues

**Resolution**:
1. Check container logs for startup errors
2. Verify environment variables and secrets
3. Increase memory allocation if OOM errors
4. Verify Firestore permissions

---

### Issue: Authentication Failures

**Symptoms**:
- Users cannot log in
- OAuth callback errors

**Diagnosis**:
```bash
# Check OAuth configuration
gcloud secrets versions access latest --secret="oauth-client-id"
gcloud secrets versions access latest --secret="oauth-client-secret"

# Check logs for auth errors
gcloud logging read "resource.type=cloud_run_revision \
  AND jsonPayload.message=~'OAuth' \
  AND severity>=ERROR"
```

**Resolution**:
1. Verify OAuth redirect URIs match service URL
2. Check OAuth client credentials
3. Verify allowed users list
4. Test OAuth flow manually

---

### Issue: High Latency

**Symptoms**:
- Turn execution takes > 10 seconds
- Users report slow responses

**Diagnosis**:
```bash
# Check ADK execution times in logs
gcloud logging read "resource.type=cloud_run_revision \
  AND jsonPayload.message=~'Turn completed'" \
  --limit 50 \
  --project ${PROJECT_ID}

# Check Firestore operation times
# Review Cloud Trace
```

**Resolution**:
1. Check VertexAI quotas
2. Verify ADK agent configuration
3. Increase CPU allocation
4. Optimize Firestore queries
5. Consider caching strategy

---

### Issue: Firestore Connection Errors

**Symptoms**:
- Database operation failures
- Connection timeout errors

**Diagnosis**:
```bash
# Check service account permissions
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:*improv-olympics*"

# Check Firestore logs
gcloud logging read "resource.type=cloud_run_revision \
  AND jsonPayload.message=~'Firestore' \
  AND severity>=ERROR"
```

**Resolution**:
1. Verify service account has Firestore permissions
2. Check Firestore database exists
3. Verify network connectivity
4. Check Firestore quotas

---

## Emergency Contacts

### On-Call Rotation

**Primary**: [Your Name]
**Phone**: [Your Phone]
**Email**: [Your Email]

**Secondary**: [Backup Name]
**Phone**: [Backup Phone]
**Email**: [Backup Email]

### Escalation Path

1. **Level 1**: On-call engineer (response time: 15 minutes)
2. **Level 2**: Tech lead (response time: 30 minutes)
3. **Level 3**: Engineering manager (response time: 1 hour)

### External Contacts

**GCP Support**:
- Portal: https://cloud.google.com/support
- Phone: [Your support phone]
- Case Priority: P1 (production down)

---

## Appendix

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| GCP_PROJECT_ID | GCP project identifier | coherent-answer-479115-e1 |
| GCP_LOCATION | GCP region | us-central1 |
| FIRESTORE_DATABASE | Firestore database name | (default) |
| RATE_LIMIT_DAILY_SESSIONS | Max sessions per day | 10 |
| RATE_LIMIT_CONCURRENT_SESSIONS | Max concurrent sessions | 3 |
| OAUTH_CLIENT_ID | OAuth client ID | [from Secret Manager] |
| OAUTH_CLIENT_SECRET | OAuth client secret | [from Secret Manager] |
| SESSION_SECRET_KEY | Session encryption key | [from Secret Manager] |
| ALLOWED_USERS | Comma-separated email list | [from Secret Manager] |

### Service Account Permissions

Required IAM roles:
- `roles/datastore.user` (Firestore access)
- `roles/aiplatform.user` (VertexAI access)
- `roles/logging.logWriter` (Cloud Logging)
- `roles/monitoring.metricWriter` (Cloud Monitoring)

### Useful Commands

```bash
# View service configuration
gcloud run services describe ${SERVICE_NAME} --region ${REGION}

# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision"

# List all revisions
gcloud run revisions list --service ${SERVICE_NAME}

# Delete old revisions
gcloud run revisions delete ${REVISION_NAME} --region ${REGION}
```

---

**Document Version History**:
- v1.0.0 (2025-11-24): Initial production runbook for IQS-46
