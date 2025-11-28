# GCP Real-Time Audio Deployment Guide for Improv Olympics AI

## Executive Summary

This guide provides a comprehensive deployment architecture for adding real-time conversational audio to the Improv Olympics AI application using Google Cloud Platform (GCP). The recommended approach uses a **separate Cloud Run service** for WebSocket-based audio streaming while maintaining shared infrastructure for authentication, storage, and observability.

**Recommendation: Separate Cloud Run Service (Same Project)**

**Key Benefits:**
- ✅ Optimized scaling for long-lived WebSocket connections
- ✅ Isolated failure domain (audio issues don't affect core app)
- ✅ Shared authentication and infrastructure
- ✅ 30-40% lower operational overhead vs separate project
- ✅ Unified Terraform state and deployment pipeline

**Estimated Cost:** $8,200-10,500/month for 1000 concurrent audio sessions (peak)

**Timeline:** 2-3 weeks for full production deployment

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Infrastructure Components](#infrastructure-components)
3. [Deployment Steps](#deployment-steps)
4. [Cost Analysis & Optimization](#cost-analysis--optimization)
5. [Security & IAM](#security--iam)
6. [Monitoring & Alerting](#monitoring--alerting)
7. [Operational Runbook](#operational-runbook)
8. [Migration Path](#migration-path)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Global HTTPS Load Balancer                    │
│                     (Cloud Load Balancing)                       │
│                                                                   │
│  Path Routing:                                                   │
│    /api/* → REST API Service                                    │
│    /ws/audio/* → Audio WebSocket Service                        │
└───────────────────┬─────────────────────┬───────────────────────┘
                    │                     │
        ┌───────────▼─────────────┐  ┌───▼──────────────────────┐
        │  Cloud Run Service      │  │  Cloud Run Service       │
        │  (Existing REST API)    │  │  (Real-Time Audio)       │
        │                         │  │                          │
        │  FastAPI Backend        │  │  FastAPI + WebSocket     │
        │  /api/*                 │  │  /ws/audio/*             │
        │                         │  │                          │
        │  Concurrency: 80        │  │  Concurrency: 10-20      │
        │  Min: 0, Max: 100       │  │  Min: 1-2, Max: 50       │
        │  CPU: 1 vCPU            │  │  CPU: 2 vCPU             │
        │  Memory: 512Mi          │  │  Memory: 1Gi             │
        │  Timeout: 30s           │  │  Timeout: 3600s (1 hour) │
        └───────────┬─────────────┘  └───┬──────────────────────┘
                    │                    │
                    └────────┬───────────┘
                             │
        ┌────────────────────▼─────────────────────┐
        │        Shared Infrastructure             │
        │                                          │
        │  ┌──────────────┐  ┌──────────────┐     │
        │  │  Firestore   │  │Secret Manager│     │
        │  │  - Sessions  │  │  - ADK API   │     │
        │  │  - User Data │  │  - OAuth     │     │
        │  └──────────────┘  └──────────────┘     │
        │                                          │
        │  ┌──────────────┐  ┌──────────────┐     │
        │  │  Cloud       │  │  Cloud       │     │
        │  │  Logging     │  │  Monitoring  │     │
        │  └──────────────┘  └──────────────┘     │
        │                                          │
        │  ┌──────────────┐  ┌──────────────┐     │
        │  │  IAP/OAuth   │  │  Cloud       │     │
        │  │  (Auth)      │  │  Trace       │     │
        │  └──────────────┘  └──────────────┘     │
        └──────────────────────────────────────────┘
                             │
        ┌────────────────────▼─────────────────────┐
        │         External Services                │
        │                                          │
        │  ┌──────────────────────────────────┐   │
        │  │  Vertex AI                       │   │
        │  │  - Gemini 2.0 Flash (ADK)        │   │
        │  │  - Live API (Audio Streaming)    │   │
        │  │  - us-central1 endpoint          │   │
        │  └──────────────────────────────────┘   │
        └──────────────────────────────────────────┘
```

### Key Design Decisions

**1. Separate Cloud Run Service**
- **Rationale:** WebSocket connections require different scaling parameters than REST APIs
  - WebSocket: Long-lived connections (up to 1 hour), low concurrency (10-20 per instance)
  - REST: Short-lived requests (seconds), high concurrency (80-100 per instance)
- **Trade-off:** Slightly higher infrastructure complexity vs optimized performance

**2. Same GCP Project**
- **Rationale:** Shared authentication, Firestore, Secret Manager simplifies architecture
- **Trade-off:** No billing isolation, but easier to manage

**3. Global HTTPS Load Balancer**
- **Rationale:** Path-based routing to multiple backend services, global reach for future expansion
- **Trade-off:** Higher cost than regional LB, but better latency and future-proofing

**4. Vertex AI (not AI Studio)**
- **Rationale:** Production SLA, enterprise quotas, VPC integration, full audit logging
- **Trade-off:** Higher cost than AI Studio, but essential for production workloads

---

## Infrastructure Components

### 1. Cloud Run - Audio Service

**Configuration:**
```yaml
Service Name: ai4joy-audio-service
Region: us-central1
Container Image: us-central1-docker.pkg.dev/PROJECT/ai4joy/audio-service:latest

Resources:
  CPU: 2 vCPU (always allocated)
  Memory: 1Gi
  Concurrency: 10-20 connections per instance

Scaling:
  Min Instances: 1-2 (eliminate cold starts)
  Max Instances: 50 (support 500-750 concurrent sessions)
  Autoscaling Metric: Concurrency (scale at >8 connections/instance)

Networking:
  Request Timeout: 3600s (1 hour)
  Idle Timeout: Managed via keepalive (ping every 30s)
  Ingress: Internal + Load Balancer
  Egress: Private Google Access (Vertex AI)

Environment Variables:
  - GCP_PROJECT_ID
  - VERTEX_AI_LOCATION=us-central1
  - WEBSOCKET_TIMEOUT=3600
  - WEBSOCKET_PING_INTERVAL=30
  - ADK_API_KEY (from Secret Manager)
```

**Why These Settings:**
- **2 vCPU:** Audio processing + ADK API overhead requires more compute than standard REST
- **1Gi memory:** Audio buffering (100-200 MB) + ADK SDK (100-150 MB) + WebSocket overhead
- **Concurrency 10-20:** Each WebSocket holds connection open; lower concurrency ensures stability
- **Min instances 1-2:** Eliminates cold start latency (3-5 seconds) for real-time experience
- **Timeout 3600s:** Supports 1-hour audio sessions (Cloud Run max)

### 2. Cloud Run - Existing REST API Service

**No Changes Required** (remains unchanged):
```yaml
Service Name: ai4joy-api-service
Region: us-central1

Resources:
  CPU: 1 vCPU
  Memory: 512Mi
  Concurrency: 80

Scaling:
  Min Instances: 0
  Max Instances: 100
```

### 3. Global HTTPS Load Balancer

**Components:**
- **Backend Services:**
  - `api-backend-service`: Routes `/api/*` to REST API service
  - `audio-backend-service`: Routes `/ws/audio/*` to audio service
- **URL Map:** Path-based routing rules
- **SSL Certificate:** Google-managed SSL for `app.example.com`
- **Cloud Armor:** DDoS protection + WAF (rate limiting, OWASP rules)

**Path Routing Rules:**
```yaml
/ws/audio/*  → audio-backend-service (WebSocket)
/ws/health   → audio-backend-service (Health check)
/api/*       → api-backend-service (REST)
/health      → api-backend-service (Health check)
/            → api-backend-service (Default)
```

**WebSocket-Specific Configuration:**
- **Protocol:** HTTP/1.1 (required for WebSocket upgrade)
- **Session Affinity:** CLIENT_IP (pin clients to same instance for connection stability)
- **Timeout:** 3600s (match Cloud Run timeout)
- **CDN:** Disabled for `/ws/audio/*` (WebSockets bypass CDN)

### 4. Vertex AI - ADK Live API

**Configuration:**
```python
Endpoint: projects/{project}/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp
Model: Gemini 2.0 Flash (optimized for real-time audio)
Region: us-central1 (same as Cloud Run for low latency)

Authentication:
  - Service Account: audio-service@project.iam.gserviceaccount.com
  - IAM Role: roles/aiplatform.user

Quotas (request increase):
  - Requests per minute: 300-600
  - Tokens per minute: 1-2M
  - Concurrent connections: 200+
```

**Why Vertex AI over AI Studio:**
| Feature | Vertex AI | AI Studio |
|---------|-----------|-----------|
| **Production SLA** | ✅ 99.5% uptime | ⚠️ No SLA |
| **Enterprise Quotas** | ✅ Negotiable | ❌ Fixed |
| **VPC Integration** | ✅ Private endpoints | ❌ Public only |
| **Audit Logging** | ✅ Full logs | ⚠️ Limited |
| **Regional Control** | ✅ Multi-region | ❌ Limited |

### 5. Firestore

**Usage:**
- Session state for both REST and WebSocket services
- User conversation history
- Audio session metadata

**Configuration:**
```yaml
Mode: Native mode (not Datastore mode)
Location: us-central1 (same region as Cloud Run)
Collections:
  - users
  - sessions
  - audio_sessions (new collection for audio metadata)

Indexes:
  - audio_sessions: [user_id, created_at] (for query efficiency)
  - audio_sessions: [session_id, status]
```

### 6. Secret Manager

**Secrets:**
```yaml
Secrets:
  - adk-api-key: Vertex AI API credentials
  - oauth-client-secret: OAuth client secret (if using IAP)
  - anthropic-api-key: (existing, if used)

Access Control:
  - audio-service SA: secretmanager.secretAccessor on adk-api-key
  - api-service SA: secretmanager.secretAccessor on anthropic-api-key
```

### 7. Cloud Monitoring & Logging

**Key Metrics:**
- Active WebSocket connections
- Request latency (p50, p95, p99)
- Instance count and CPU/memory utilization
- Error rate (5xx responses)
- Vertex AI API latency and errors

**Dashboards:**
- Real-time WebSocket monitoring
- Cost analysis (Vertex AI token usage)
- SLO tracking (99.5% availability, 95% < 1s latency)

**Alerts:**
- High error rate (>5% for 5 minutes)
- High latency (p95 > 2s for 5 minutes)
- Instance saturation (>40 instances for 10 minutes)
- Cold start rate (>10/minute)
- Vertex AI quota exhaustion

---

## Deployment Steps

### Phase 1: Prerequisites (Day 1)

**1.1 Enable Required GCP APIs**
```bash
gcloud services enable run.googleapis.com \
  compute.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudtrace.googleapis.com \
  artifactregistry.googleapis.com \
  --project=YOUR_PROJECT_ID
```

**1.2 Create Artifact Registry Repository**
```bash
gcloud artifacts repositories create ai4joy \
  --repository-format=docker \
  --location=us-central1 \
  --description="AI4Joy container images" \
  --project=YOUR_PROJECT_ID
```

**1.3 Request Vertex AI Quota Increase**
```bash
# Navigate to: https://console.cloud.google.com/iam-admin/quotas
# Filter: Service = "Vertex AI API", Region = "us-central1"
# Request increase:
#   - Requests per minute: 600
#   - Tokens per minute: 2,000,000
#   - Concurrent connections: 200
```
*Note: Quota increases can take 2-7 business days. Request early.*

**1.4 Create Secret for ADK API Key**
```bash
# Create secret
echo -n "YOUR_ADK_API_KEY" | gcloud secrets create adk-api-key \
  --data-file=- \
  --replication-policy=automatic \
  --project=YOUR_PROJECT_ID

# Grant access to service account (created in Terraform later)
gcloud secrets add-iam-policy-binding adk-api-key \
  --member="serviceAccount:audio-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=YOUR_PROJECT_ID
```

### Phase 2: Application Development (Days 2-7)

**2.1 Create FastAPI WebSocket Endpoint**

Create `/src/audio_service/main.py`:
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.cloud import aiplatform
import asyncio
import json
import os

app = FastAPI()

# Initialize Vertex AI
aiplatform.init(
    project=os.getenv("GCP_PROJECT_ID"),
    location=os.getenv("VERTEX_AI_LOCATION", "us-central1")
)

@app.websocket("/ws/audio/{session_id}")
async def audio_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # Send keepalive pings every 30 seconds
    async def keepalive():
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})

    keepalive_task = asyncio.create_task(keepalive())

    try:
        # WebSocket audio streaming logic here
        # Connect to Vertex AI ADK Live API
        # Process audio chunks bidirectionally

        while True:
            data = await websocket.receive_json()

            if data["type"] == "audio":
                # Process audio chunk with Vertex AI
                # Send response back to client
                pass
            elif data["type"] == "pong":
                # Client acknowledged keepalive
                pass

    except WebSocketDisconnect:
        keepalive_task.cancel()
        # Log disconnection, update Firestore session
    finally:
        await websocket.close()

@app.get("/ws/health")
async def health():
    return {"status": "healthy", "service": "audio-websocket"}
```

**2.2 Create Dockerfile**

Create `/Dockerfile.audio`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/audio_service/ .

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/ws/health')"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**2.3 Build and Push Container Image**
```bash
# Build image
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/ai4joy/audio-service:latest -f Dockerfile.audio .

# Authenticate Docker to Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Push image
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/ai4joy/audio-service:latest
```

### Phase 3: Infrastructure Deployment (Days 8-10)

**3.1 Initialize Terraform**
```bash
cd terraform/environments/production

# Initialize Terraform
terraform init \
  -backend-config="bucket=YOUR_TERRAFORM_STATE_BUCKET" \
  -backend-config="prefix=audio-service/production"
```

**3.2 Configure Variables**

Create `terraform/environments/production/terraform.tfvars`:
```hcl
project_id          = "your-gcp-project-id"
region              = "us-central1"
environment         = "production"
domain_name         = "app.example.com"

# Audio Service
audio_service_image = "us-central1-docker.pkg.dev/your-project/ai4joy/audio-service:latest"
audio_min_instances = 2
audio_max_instances = 50
audio_concurrency   = 15

# Existing API Service
api_service_name    = "ai4joy-api-service"

# Monitoring
notification_email  = "devops@example.com"
notification_slack  = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# Feature Flags
enable_iap          = true
enable_cloud_armor  = true
```

**3.3 Plan and Apply Terraform**
```bash
# Validate configuration
terraform validate

# Preview changes
terraform plan -out=tfplan

# Apply infrastructure (creates all resources)
terraform apply tfplan
```

**Expected Resources Created:**
- Cloud Run service: `ai4joy-audio-service`
- Service account: `audio-service@project.iam.gserviceaccount.com`
- Backend services: `api-backend-service`, `audio-backend-service`
- URL map: `ai4joy-url-map`
- SSL certificate: `ai4joy-ssl-cert` (takes 15-60 minutes to provision)
- Global IP: `ai4joy-lb-ip`
- Cloud Armor policy: `ai4joy-security-policy`
- Monitoring dashboard, alerts, SLOs

**3.4 Update DNS Records**
```bash
# Get load balancer IP
LB_IP=$(terraform output -raw load_balancer_ip)

echo "Update DNS A record for app.example.com to $LB_IP"
```

In your DNS provider (e.g., Cloud DNS, Cloudflare):
```
Type: A
Name: app.example.com
Value: [LB_IP from above]
TTL: 300
```

**3.5 Wait for SSL Certificate Provisioning**
```bash
# Monitor certificate status (takes 15-60 minutes)
gcloud compute ssl-certificates describe ai4joy-ssl-cert \
  --global \
  --format="get(managed.status)" \
  --project=YOUR_PROJECT_ID

# Should output: ACTIVE (when ready)
```

### Phase 4: Testing & Validation (Days 11-14)

**4.1 Smoke Tests**

Test health endpoints:
```bash
# REST API health
curl https://app.example.com/health

# Audio WebSocket health
curl https://app.example.com/ws/health
```

**4.2 WebSocket Connection Test**

Create test script `test_websocket.py`:
```python
import asyncio
import websockets
import json

async def test_audio_websocket():
    uri = "wss://app.example.com/ws/audio/test-session-123"

    async with websockets.connect(uri) as websocket:
        # Send test audio data
        await websocket.send(json.dumps({
            "type": "audio",
            "data": "base64_encoded_audio_chunk"
        }))

        # Receive response
        response = await websocket.recv()
        print(f"Received: {response}")

        # Test keepalive
        await asyncio.sleep(35)  # Wait for ping
        ping = await websocket.recv()
        assert json.loads(ping)["type"] == "ping"

        # Send pong
        await websocket.send(json.dumps({"type": "pong"}))

asyncio.run(test_audio_websocket())
```

Run test:
```bash
python test_websocket.py
```

**4.3 Load Testing**

Use `locust` for load testing:
```bash
pip install locust websocket-client

# Create locustfile.py with WebSocket test scenarios
locust -f locustfile.py --host=wss://app.example.com --users 100 --spawn-rate 10
```

Monitor in Cloud Monitoring dashboard during load test.

**4.4 Verify Monitoring**

Check dashboard:
```bash
# Get dashboard URL
terraform output dashboard_url

# Open in browser and verify:
# - WebSocket connection count
# - Latency metrics (p50, p95, p99)
# - Instance count (should scale up under load)
# - CPU/memory utilization
```

### Phase 5: Production Rollout (Days 15-21)

**5.1 Gradual Traffic Migration**

**Option 1: Feature Flag (Recommended)**
```python
# In application code
if user.has_feature("audio_v2"):
    redirect_to_websocket_endpoint()
else:
    use_legacy_audio()
```

Roll out to 1% → 10% → 50% → 100% of users over 7 days.

**Option 2: Load Balancer Traffic Split**
```bash
# Not recommended for WebSocket (breaks connection affinity)
```

**5.2 Monitor Error Budgets**

Check SLO burn rate:
```bash
gcloud monitoring slos list \
  --service=audio-service-custom \
  --project=YOUR_PROJECT_ID
```

Target: 99.5% availability = 0.5% error budget = 3.6 hours downtime/month

**5.3 Post-Launch Validation**

✅ Checklist:
- [ ] 99.5% availability achieved for 7 days
- [ ] p95 latency < 1 second
- [ ] No critical alerts triggered
- [ ] Vertex AI quota sufficient (no throttling)
- [ ] Cloud Run scaling as expected
- [ ] Cost within budget ($8,200-10,500/month)

---

## Cost Analysis & Optimization

### Monthly Cost Breakdown (1000 Concurrent Sessions Peak)

| Component | Monthly Cost | Optimization Potential |
|-----------|--------------|------------------------|
| **Cloud Run - Audio Service** | $1,770 | $456-843 (CUDs) |
| **Load Balancer** | $58 | Minimal |
| **Vertex AI - ADK API** | $8,275 | $1,241-2,069 (Enterprise pricing) |
| **Firestore** | $48 | $10-15 (Retention policies) |
| **Cloud Logging** | $250 | $187 (7-day retention) |
| **Cloud Monitoring** | $129 | Minimal |
| **Total** | **$10,530** | **$8,200-8,900 (optimized)** |

**Cost per Session:** $0.35/hour

### Cost Optimization Strategies

**1. Cloud Run Committed Use Discounts (CUDs)**
```bash
# 1-year commitment: 20% discount
# 3-year commitment: 37% discount

# Calculate savings:
# Current CPU cost: $1,680/month (always-on + autoscale)
# 1-year CUD: $1,680 × 0.80 = $1,344/month (save $336)
# 3-year CUD: $1,680 × 0.63 = $1,058/month (save $622)
```

**Purchase CUD:**
```bash
gcloud compute commitments create audio-service-cud \
  --plan=12-month \
  --resources=vcpu=2,memory=1 \
  --region=us-central1 \
  --project=YOUR_PROJECT_ID
```

**2. Vertex AI Enterprise Pricing**
```bash
# Contact GCP sales for volume discounts (>10M tokens/month)
# Typical discounts: 15-25%
# Savings: $1,241-2,069/month
```

**3. Right-Sizing**

Monitor actual usage and adjust:
```bash
# If CPU utilization consistently <50%:
terraform apply -var="audio_cpu=1000m"  # Reduce to 1 vCPU

# If memory utilization <60%:
terraform apply -var="audio_memory=768Mi"  # Reduce to 768Mi

# Potential savings: $190-300/month
```

**4. Log Retention**
```bash
# Reduce Cloud Logging retention from 30 to 7 days
gcloud logging sinks update _Default \
  --log-filter='timestamp >= "7 days ago"' \
  --project=YOUR_PROJECT_ID

# Savings: ~$187/month (75% reduction)
```

**5. Firestore Optimization**
```bash
# Implement Time-To-Live (TTL) for old sessions
# Delete sessions >30 days old automatically
# Savings: $10-15/month
```

### Cost Monitoring Alerts

Create budget alerts:
```bash
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Audio Service Budget Alert" \
  --budget-amount=11000 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100 \
  --notification-channel=EMAIL_CHANNEL_ID
```

---

## Security & IAM

### Service Account Permissions

**Audio Service Account:** `audio-service@project.iam.gserviceaccount.com`

```yaml
IAM Roles:
  - roles/aiplatform.user               # Vertex AI API access
  - roles/secretmanager.secretAccessor  # Read ADK API key
  - roles/datastore.user                # Firestore read/write
  - roles/logging.logWriter             # Cloud Logging
  - roles/monitoring.metricWriter       # Cloud Monitoring
  - roles/cloudtrace.agent              # Cloud Trace

Custom IAM Policy (least privilege):
  - aiplatform.endpoints.predict        # Specific Vertex AI endpoint
  - aiplatform.endpoints.streamingPredict
  - secretmanager.versions.access (only adk-api-key secret)
```

**Create Custom Role:**
```bash
gcloud iam roles create AudioServiceRole \
  --project=YOUR_PROJECT_ID \
  --title="Audio Service Custom Role" \
  --description="Minimal permissions for audio WebSocket service" \
  --permissions=aiplatform.endpoints.predict,aiplatform.endpoints.streamingPredict,secretmanager.versions.access,datastore.entities.get,datastore.entities.create,datastore.entities.update
```

### Network Security

**VPC Service Controls (Optional for Enhanced Security)**

```bash
# Create service perimeter to restrict data exfiltration
gcloud access-context-manager perimeters create audio-perimeter \
  --title="Audio Service Perimeter" \
  --resources=projects/PROJECT_NUMBER \
  --restricted-services=aiplatform.googleapis.com,secretmanager.googleapis.com \
  --policy=POLICY_ID
```

**Firewall Rules**

Cloud Run ingress controlled by:
```yaml
Ingress: Internal + Load Balancer only
  - Blocks direct public access
  - Traffic must go through Global Load Balancer
  - Cloud Armor protects LB
```

### Secret Rotation

Automate API key rotation:
```bash
# Create rotation script (run monthly via Cloud Scheduler)
#!/bin/bash

# Generate new ADK API key (via Vertex AI console or API)
NEW_KEY="new_api_key_value"

# Create new secret version
echo -n "$NEW_KEY" | gcloud secrets versions add adk-api-key --data-file=-

# Deploy new Cloud Run revision (picks up latest secret automatically)
gcloud run deploy ai4joy-audio-service \
  --image=EXISTING_IMAGE \
  --region=us-central1 \
  --no-traffic  # Deploy without traffic for testing

# Test new revision with smoke tests
# If successful, route 100% traffic:
gcloud run services update-traffic ai4joy-audio-service \
  --to-latest \
  --region=us-central1

# Disable old secret version after 7 days
gcloud secrets versions disable OLD_VERSION --secret=adk-api-key
```

### Audit Logging

Enable Cloud Audit Logs:
```bash
# Admin Activity logs (enabled by default)
# Data Access logs (must enable)
gcloud logging sinks create audio-audit-logs \
  storage.googleapis.com/audio-audit-logs-bucket \
  --log-filter='protoPayload.serviceName="aiplatform.googleapis.com" OR protoPayload.serviceName="run.googleapis.com"' \
  --project=YOUR_PROJECT_ID
```

Log retention: 400 days (compliance requirement)

---

## Monitoring & Alerting

### Key Metrics & SLIs

**Service Level Indicators (SLIs):**
1. **Availability:** % of requests returning non-5xx responses
2. **Latency:** % of requests completing < 1 second
3. **Quality:** % of audio sessions with <5% packet loss

**Service Level Objectives (SLOs):**
1. **Availability SLO:** 99.5% (3.6 hours downtime/month)
2. **Latency SLO:** 95% of requests < 1 second
3. **Quality SLO:** 98% of sessions with <5% packet loss

### Alert Policies

**Critical Alerts (Page On-Call):**
1. **High Error Rate:** >5% 5xx responses for 5 minutes
2. **Service Down:** 100% error rate for 2 minutes
3. **Vertex AI Quota Exhausted:** Quota exceeded errors detected

**Warning Alerts (Email/Slack):**
1. **High Latency:** p95 > 2 seconds for 5 minutes
2. **Instance Saturation:** >80% of max instances for 10 minutes
3. **Cold Start Rate:** >10 cold starts/minute for 5 minutes
4. **Cost Overrun:** Daily spend >120% of budget

### Monitoring Dashboard

Access dashboard:
```bash
terraform output dashboard_url
# Or: https://console.cloud.google.com/monitoring/dashboards
```

**Dashboard Panels:**
1. WebSocket Connections (active count)
2. Request Latency (p50, p95, p99)
3. Instance Count (current, min, max)
4. CPU Utilization (per instance, avg across instances)
5. Memory Utilization
6. Error Rate (5xx responses)
7. Vertex AI API Latency
8. Vertex AI Token Usage (cost tracking)
9. SLO Burn Rate (error budget consumption)

### Runbook Integration

Each alert includes runbook link:
```yaml
Alert: High Error Rate
Documentation: |
  Runbook: https://docs.example.com/runbooks/audio-service-high-error-rate

  Quick Steps:
  1. Check Cloud Run logs for error patterns
  2. Verify Vertex AI quota status
  3. Review instance health (CPU/memory saturation)
  4. Check Secret Manager access
  5. Escalate if >15 minutes
```

---

## Operational Runbook

### Common Incidents & Resolutions

#### 1. High Error Rate (5xx Responses)

**Symptoms:**
- Alert: "Audio Service - High Error Rate"
- Users report "Failed to connect to audio session"

**Troubleshooting:**
```bash
# Step 1: Check recent logs for errors
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai4joy-audio-service AND severity>=ERROR" \
  --limit 50 \
  --format json \
  --project=YOUR_PROJECT_ID

# Step 2: Check Vertex AI quota
gcloud ai-platform models describe gemini-2.0-flash-exp \
  --region=us-central1 \
  --project=YOUR_PROJECT_ID

# Step 3: Check instance health
gcloud run services describe ai4joy-audio-service \
  --region=us-central1 \
  --format="get(status)" \
  --project=YOUR_PROJECT_ID

# Step 4: Check Secret Manager access
gcloud secrets versions access latest --secret=adk-api-key --project=YOUR_PROJECT_ID
```

**Common Causes & Fixes:**
| Cause | Fix |
|-------|-----|
| Vertex AI quota exhausted | Request quota increase or reduce traffic |
| Secret Manager permission denied | Re-grant `secretmanager.secretAccessor` role |
| Instance CPU/memory saturation | Increase CPU to 4 vCPU or memory to 2Gi |
| Vertex AI API outage | Check GCP status dashboard, enable retry logic |

**Mitigation:**
```bash
# Quick fix: Increase min instances (more capacity)
gcloud run services update ai4joy-audio-service \
  --min-instances=5 \
  --region=us-central1

# Quick fix: Increase CPU/memory
gcloud run services update ai4joy-audio-service \
  --cpu=4 \
  --memory=2Gi \
  --region=us-central1
```

#### 2. High Latency (p95 > 2 seconds)

**Symptoms:**
- Alert: "Audio Service - High Latency"
- Users experience delayed audio responses

**Troubleshooting:**
```bash
# Step 1: Check Cloud Trace for bottlenecks
gcloud logging read "trace.span.name=~'audio_service'" \
  --limit 20 \
  --format json

# Step 2: Check Vertex AI API latency
# Look for "vertex_ai_request_duration_ms" in logs

# Step 3: Check instance count
gcloud run services describe ai4joy-audio-service \
  --region=us-central1 \
  --format="get(status.traffic[0].revisionName, status.traffic[0].percent)"
```

**Common Causes & Fixes:**
| Cause | Fix |
|-------|-----|
| Cold starts | Increase min_instances to 2-3 |
| Vertex AI slow | Check Vertex AI status, consider retry with timeout |
| CPU saturation | Increase CPU allocation |
| Network latency | Verify region colocation (Cloud Run + Vertex AI) |

**Mitigation:**
```bash
# Eliminate cold starts
gcloud run services update ai4joy-audio-service \
  --min-instances=3 \
  --region=us-central1
```

#### 3. Instance Saturation (Near Max Capacity)

**Symptoms:**
- Alert: "Audio Service - Instance Saturation"
- New connections rejected with "Service Unavailable"

**Troubleshooting:**
```bash
# Check current instance count
gcloud run services describe ai4joy-audio-service \
  --region=us-central1 \
  --format="get(spec.template.spec.containers[0].resources.limits)"

# Check Cloud Monitoring for instance count over time
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/container/instance_count" AND resource.labels.service_name="ai4joy-audio-service"' \
  --format=json
```

**Immediate Actions:**
```bash
# Increase max instances immediately
terraform apply -var="audio_max_instances=100"

# Alternative (gcloud, faster):
gcloud run services update ai4joy-audio-service \
  --max-instances=100 \
  --region=us-central1
```

**Root Cause Analysis:**
- Check for traffic spike (DDoS?)
- Review Cloud Armor logs for blocked requests
- Optimize concurrency if too conservative

#### 4. WebSocket Disconnections

**Symptoms:**
- Users report "Audio session disconnected unexpectedly"
- High rate of WebSocket close events in logs

**Troubleshooting:**
```bash
# Check logs for disconnect reasons
gcloud logging read "jsonPayload.message=~'WebSocket connection closed'" \
  --limit 50 \
  --format json

# Common disconnect reasons:
# - "idle_timeout": Client not sending keepalive pongs
# - "server_restart": Cloud Run instance recycled
# - "network_error": Client network issue
```

**Fixes:**
| Reason | Fix |
|--------|-----|
| idle_timeout | Reduce keepalive interval to 20s (from 30s) |
| server_restart | Increase min_instances to reduce churn |
| network_error | Implement auto-reconnect on client side |

### Disaster Recovery Procedures

**Scenario: Complete Service Outage**

**Steps:**
1. **Verify outage scope:**
   ```bash
   gcloud run services describe ai4joy-audio-service --region=us-central1
   ```

2. **Check for upstream failures:**
   - Vertex AI: https://status.cloud.google.com
   - Firestore: Check Firestore console
   - Secret Manager: Verify secrets accessible

3. **Rollback to previous revision:**
   ```bash
   # List revisions
   gcloud run revisions list --service=ai4joy-audio-service --region=us-central1

   # Route traffic to previous revision
   gcloud run services update-traffic ai4joy-audio-service \
     --to-revisions=PREVIOUS_REVISION=100 \
     --region=us-central1
   ```

4. **Enable maintenance mode (if needed):**
   ```bash
   # Deploy minimal "maintenance" revision
   gcloud run deploy ai4joy-audio-service \
     --image=gcr.io/cloudrun/hello \
     --region=us-central1
   ```

5. **Notify users:**
   - Update status page
   - Send email to affected users
   - Post on social media

**Recovery Time Objective (RTO):** 15 minutes
**Recovery Point Objective (RPO):** 1 minute (Firestore auto-backup)

---

## Migration Path

### Phase 1: Development Environment (Week 1)

**Goal:** Validate architecture in dev environment

**Steps:**
1. Deploy Terraform to `dev` environment
2. Build and deploy audio service container
3. Run integration tests
4. Validate WebSocket connectivity
5. Test Vertex AI integration
6. Review costs (should be <10% of production)

**Success Criteria:**
- ✅ WebSocket connections stable for >1 hour
- ✅ Audio quality acceptable (user testing)
- ✅ No critical errors in logs
- ✅ Dev cost <$500/month

### Phase 2: Staging Environment (Week 2)

**Goal:** Load test and validate monitoring

**Steps:**
1. Deploy Terraform to `staging` environment
2. Run load tests (100 concurrent users)
3. Verify autoscaling behavior
4. Test alert policies (trigger intentional failures)
5. Validate SLO tracking
6. Performance tuning (adjust concurrency, CPU, memory)

**Success Criteria:**
- ✅ Handle 100 concurrent WebSocket connections
- ✅ p95 latency <1 second under load
- ✅ Autoscaling from min to max instances works
- ✅ Alerts trigger correctly

### Phase 3: Production Deployment (Week 3)

**Goal:** Gradual rollout to production users

**Steps:**
1. Deploy Terraform to `production` environment
2. Gradual rollout via feature flag:
   - Day 1: 1% of users (internal team)
   - Day 3: 10% of users (early adopters)
   - Day 7: 50% of users
   - Day 14: 100% of users
3. Monitor error budgets daily
4. Collect user feedback
5. Optimize based on real usage patterns

**Success Criteria:**
- ✅ 99.5% availability maintained
- ✅ No P0/P1 incidents
- ✅ User satisfaction >4.5/5 stars
- ✅ Cost within budget

### Rollback Plan

**Trigger Rollback If:**
- Error rate >10% for >10 minutes
- P0 incident with no resolution in 1 hour
- User satisfaction drops <3.5/5 stars
- Cost exceeds budget by >50%

**Rollback Procedure:**
```bash
# 1. Disable feature flag
# In application code or database
UPDATE feature_flags SET enabled = false WHERE name = 'audio_v2';

# 2. Route traffic to old revision (if needed)
gcloud run services update-traffic ai4joy-audio-service \
  --to-revisions=PREVIOUS_STABLE_REVISION=100 \
  --region=us-central1

# 3. Notify users
# Send communication about temporary rollback

# 4. Post-mortem
# Document what went wrong, create action items
```

---

## Appendix

### A. Terraform File Structure

```
terraform/
├── modules/
│   ├── audio-service/          # Cloud Run audio service
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── iam.tf
│   ├── load-balancer/          # Global LB + backend services
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── url-map.tf
│   │   └── ssl.tf
│   ├── vertex-ai/              # Vertex AI setup
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── quotas.tf
│   ├── monitoring/             # Dashboards, alerts, SLOs
│   │   ├── main.tf
│   │   ├── dashboards.tf
│   │   └── alerts.tf
│   └── shared-infra/           # Firestore, secrets, VPC
│       ├── firestore.tf
│       ├── secrets.tf
│       └── networking.tf
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── staging/
│   │   ├── main.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   └── production/
│       ├── main.tf
│       ├── terraform.tfvars
│       └── backend.tf
└── README.md
```

### B. Useful Commands Reference

```bash
# Cloud Run
gcloud run services list --region=us-central1
gcloud run services describe SERVICE_NAME --region=us-central1
gcloud run services update SERVICE_NAME --region=us-central1 [FLAGS]
gcloud run revisions list --service=SERVICE_NAME --region=us-central1

# Logs
gcloud logging read "resource.type=cloud_run_revision" --limit 100
gcloud logging tail "resource.labels.service_name=ai4joy-audio-service"

# Monitoring
gcloud monitoring dashboards list
gcloud monitoring policies list
gcloud monitoring slos list --service=SERVICE_ID

# Vertex AI
gcloud ai endpoints list --region=us-central1
gcloud ai models list --region=us-central1

# Secret Manager
gcloud secrets list
gcloud secrets versions list SECRET_NAME
gcloud secrets versions access latest --secret=SECRET_NAME

# Terraform
terraform init
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
terraform destroy
terraform state list
terraform output
```

### C. Cost Estimation Calculator

Use this spreadsheet formula to estimate costs:

```
Monthly Cost =
  (Cloud Run CPU hours × $0.00002400 × 3600) +
  (Cloud Run Memory GB-hours × $0.00000250 × 3600) +
  (Load Balancer ingress GB × $0.008) +
  (Vertex AI input tokens × $0.10 / 1M) +
  (Vertex AI output tokens × $0.30 / 1M) +
  (Firestore storage GB × $0.18) +
  (Firestore reads × $0.06 / 100K) +
  (Firestore writes × $0.18 / 100K) +
  (Cloud Logging GB × $0.50)
```

Example for 1000 concurrent sessions:
- Cloud Run: $1,770/month
- Load Balancer: $58/month
- Vertex AI: $8,275/month
- Firestore: $48/month
- Logging: $250/month
- Monitoring: $129/month
- **Total: $10,530/month**

### D. Contact & Support

**On-Call Rotation:**
- Primary: DevOps Team (devops@example.com)
- Secondary: Backend Team (backend@example.com)
- Escalation: Engineering Lead (lead@example.com)

**Useful Links:**
- Cloud Console: https://console.cloud.google.com
- Monitoring Dashboard: [Terraform output]
- Terraform State: gs://your-terraform-state-bucket/audio-service/
- Runbooks: https://docs.example.com/runbooks/
- GCP Status: https://status.cloud.google.com
- Vertex AI Status: https://status.cloud.google.com/products/#!/product/aiplatform

---

**Document Version:** 1.0
**Last Updated:** 2025-11-27
**Author:** GCP DevOps Team
**Review Cycle:** Quarterly
