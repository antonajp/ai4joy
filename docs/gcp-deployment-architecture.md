# Improv Olympics - GCP Deployment Architecture

> **Note:** This project uses **Application-Level OAuth 2.0** for authentication. See [OAUTH_IMPLEMENTATION_CHANGE.md](OAUTH_IMPLEMENTATION_CHANGE.md) for details on why we chose application-level OAuth over IAP.

## Executive Summary

This document provides a production-ready GCP deployment strategy for the Improv Olympics multi-agent application built with Google Agent Development Kit (ADK). The architecture prioritizes serverless auto-scaling, cost efficiency, and operational simplicity while supporting future WebSocket integration for real-time voice interaction.

**Key Architecture Decisions:**
- **Compute**: Cloud Run (serverless containers) for HTTP traffic with future WebSocket support
- **State Management**: Firestore for session state with Memorystore Redis for caching
- **Domain**: Global HTTPS Load Balancer with Cloud CDN for ai4joy.org
- **Security**: Workload Identity Federation for VertexAI access, Secret Manager for credentials
- **Cost Estimate**: $150-300/month for moderate usage (1000-5000 sessions/month)

---

## 1. VertexAI Container Strategy

### Container Architecture

The ADK application will be containerized and deployed to Cloud Run, providing seamless integration with VertexAI APIs while maintaining serverless benefits.

**Container Design:**
```
improv-olympics-app/
├── Dockerfile (Python 3.11+ base)
├── requirements.txt (ADK, vertexai, fastapi, uvicorn)
├── app/
│   ├── main.py (FastAPI application)
│   ├── agents/
│   │   ├── stage_manager.py (Root orchestrator)
│   │   ├── mc_agent.py (Gemini Flash)
│   │   ├── audience_agent.py (The Room - Gemini Flash)
│   │   ├── partner_agent.py (Dynamic Scene Partner - Gemini Pro)
│   │   └── coach_agent.py (Post-game analysis)
│   ├── tools/
│   │   ├── game_database.py
│   │   ├── demographic_generator.py
│   │   ├── sentiment_gauge.py
│   │   └── improv_expert_database.py
│   ├── state/
│   │   └── session_manager.py (Firestore integration)
│   └── models/
│       └── schemas.py (Pydantic models)
└── cloudbuild.yaml
```

**Key Container Configuration:**
- **Base Image**: `python:3.11-slim` (minimize attack surface)
- **Multi-stage build**: Separate build and runtime stages to reduce image size
- **Health checks**: `/health` and `/ready` endpoints for Cloud Run probes
- **Graceful shutdown**: Handle SIGTERM for clean session persistence
- **Environment variables**: All configuration via env vars, secrets from Secret Manager

### Artifact Registry Setup

**Repository Configuration:**
```bash
# Repository: us-central1-docker.pkg.dev/improvOlympics/improv-app
Format: Docker
Location: us-central1 (same as Cloud Run for lowest latency)
Cleanup Policy: Keep last 10 images, delete untagged after 30 days
```

**Image Tagging Strategy:**
- `latest`: Always points to production
- `v{MAJOR}.{MINOR}.{PATCH}`: Semantic versioning
- `{GIT_SHA}`: Commit-based for traceability
- `dev`, `staging`, `prod`: Environment tags

### VertexAI Integration Patterns

**Model Access Configuration:**
```python
# ADK configuration for VertexAI
from google.adk import Agent
from google.cloud import aiplatform

aiplatform.init(
    project="improvOlympics",
    location="us-central1",
    credentials=None  # Uses Application Default Credentials via Workload Identity
)

# Agent definitions with specific models
mc_agent = Agent(
    name="MC",
    model="gemini-1.5-flash-002",
    temperature=0.8,
    system_instructions="High-energy improv host..."
)

partner_agent = Agent(
    name="DynamicPartner",
    model="gemini-1.5-pro-002",
    temperature=0.9,  # High creativity for Phase 1
    system_instructions="Expert improv scene partner..."
)
```

**API Quotas & Rate Limiting:**
- **Gemini Flash**: 1000 QPM (Queries Per Minute)
- **Gemini Pro**: 360 QPM
- **Strategy**: Implement client-side retry with exponential backoff (max 3 retries)
- **Circuit breaker**: Fail gracefully if VertexAI API is unavailable

---

## 2. Networking & DNS Architecture

### Cloud Load Balancer Configuration

**Architecture Pattern:**
```
Internet → Global HTTPS Load Balancer → Cloud CDN → Cloud Run (Backend Service)
         ↓
    Cloud Armor (DDoS protection)
         ↓
    SSL Certificate (ai4joy.org)
```

**Load Balancer Components:**
1. **Frontend Configuration**:
   - Protocol: HTTPS (port 443)
   - HTTP to HTTPS redirect (port 80 → 443)
   - IP Address: Global static IP (reserved)

2. **Backend Service**:
   - Type: Serverless Network Endpoint Group (NEG) pointing to Cloud Run
   - Session affinity: Cookie-based (for session continuity)
   - Health check: `/health` endpoint with 10s interval

3. **URL Map**:
   - `/api/*` → Cloud Run backend (no cache)
   - `/static/*` → Cloud CDN cache (1 hour TTL)
   - `/ws` → WebSocket passthrough (for future voice support)

### SSL/TLS Certificate Management

**Cloud Certificate Manager Configuration:**
```bash
# Google-managed SSL certificate (auto-renewal)
Certificate Name: improv-olympics-cert
Domains:
  - ai4joy.org
  - www.ai4joy.org
Validation: DNS validation via Cloud DNS
Auto-renewal: Enabled (90-day lifecycle)
```

**Certificate Provisioning Process:**
1. Create DNS authorization records in Cloud DNS
2. Certificate Manager validates domain ownership
3. Certificate provisioned within 15-30 minutes
4. Automatic renewal 30 days before expiration

### DNS Configuration

**Cloud DNS Setup:**
```
Zone Name: ai4joy-org
DNS Name: ai4joy.org.
Type: Public zone

Records:
A     ai4joy.org.         300   <Global-Static-IP>
A     www.ai4joy.org.     300   <Global-Static-IP>
AAAA  ai4joy.org.         300   <Global-Static-IPv6> (optional)
CAA   ai4joy.org.         3600  0 issue "pki.goog"
TXT   ai4joy.org.         3600  "v=spf1 -all" (security)
```

**DNS Validation Records** (for SSL certificate):
```
CNAME _acme-challenge.ai4joy.org. → <validation-value>.gcp.google.com.
```

---

## 3. Compute & Scaling Strategy

### Cloud Run Configuration (Recommended)

**Why Cloud Run?**
- Serverless auto-scaling (0 to 1000+ instances)
- Pay-per-request pricing (no idle costs)
- Native HTTP/2 and WebSocket support (for future voice feature)
- Seamless VPC integration for Firestore and Memorystore access
- Built-in traffic splitting for canary deployments
- No container orchestration overhead

**Service Configuration:**
```yaml
Service: improv-olympics-app
Region: us-central1
Min Instances: 1 (keep warm, reduce cold starts)
Max Instances: 100 (cost protection)
CPU: 2 vCPU (for concurrent agent processing)
Memory: 2 GiB (ADK + multiple agent contexts)
Request Timeout: 300s (5 min for long-running scenes)
Concurrency: 20 requests per instance
Execution Environment: Gen 2 (faster cold starts)
```

**Auto-Scaling Configuration:**
```yaml
Scaling Metrics:
  - CPU Utilization: Scale at 70%
  - Request Count: Scale at 80% of concurrency (16 requests)
  - Response Latency: Scale if p95 > 2s

Cold Start Optimization:
  - Min instances: 1 (always warm)
  - Startup CPU boost: Enabled
  - Lazy loading: Defer heavy imports until first request
```

**Regional Deployment Strategy:**
- **Primary**: `us-central1` (Iowa) - Low latency to most US users
- **Future Multi-Region**: Add `europe-west1` for EU users if needed
- **Disaster Recovery**: Multi-region load balancing with health checks

### Resource Sizing & Performance

**Expected Performance:**
- Cold start: <3s (with 1 min instance)
- Warm request: 500ms-2s (depending on agent complexity)
- Scene turn latency: 1.5-3s (3 agent calls: MC, Partner, Audience)
- Concurrent users: 200-500 per instance (depending on session length)

**Load Testing Targets:**
- 100 concurrent sessions sustained
- 1000 requests per minute peak
- P95 latency < 3s
- P99 latency < 5s

---

## 4. IAM & Security Architecture

### Service Accounts & Roles

**Primary Service Account:**
```
Name: improv-app-runtime@improvOlympics.iam.gserviceaccount.com
Purpose: Cloud Run runtime identity

Roles:
- roles/aiplatform.user (VertexAI API access)
- roles/datastore.user (Firestore read/write)
- roles/redis.editor (Memorystore access - if used)
- roles/secretmanager.secretAccessor (Secret Manager read)
- roles/logging.logWriter (Cloud Logging write)
- roles/cloudtrace.agent (Cloud Trace write)
```

**Cloud Build Service Account:**
```
Name: cloud-build-deployer@improvOlympics.iam.gserviceaccount.com
Purpose: CI/CD pipeline execution

Roles:
- roles/run.admin (Deploy Cloud Run services)
- roles/iam.serviceAccountUser (Assign runtime service account)
- roles/artifactregistry.writer (Push container images)
- roles/storage.objectViewer (Read build artifacts)
```

### Workload Identity Federation

**Configuration for VertexAI Access:**
```bash
# Cloud Run automatically uses the service account's credentials
# No API keys or JSON key files needed

# Verify in application code:
from google.auth import default
credentials, project = default()  # Uses service account identity
```

**Security Benefits:**
- No long-lived API keys
- Automatic credential rotation
- Audit trail via Cloud Audit Logs
- Fine-grained IAM permissions

### Secret Manager Configuration

**Secrets to Store:**
```
Secret Name: session-encryption-key
Purpose: Encrypt sensitive session data in Firestore
Rotation: Manual (on-demand)

Secret Name: api-rate-limit-config
Purpose: Dynamic rate limiting configuration
Rotation: As needed

Secret Name: webhook-signing-secret (future)
Purpose: Verify incoming webhooks
Rotation: Manual
```

**Access Pattern:**
```python
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
secret_name = "projects/improvOlympics/secrets/session-encryption-key/versions/latest"
response = client.access_secret_version(request={"name": secret_name})
encryption_key = response.payload.data.decode("UTF-8")
```

### OAuth Authentication via Application-Level OAuth 2.0 - MVP

**Critical Decision:** OAuth authentication is mandatory for MVP to prevent cost abuse from anonymous LLM usage.

**Implementation Strategy: Application-Level OAuth 2.0**

Application-level OAuth 2.0 provides Google Sign-In authentication at the application layer using secure session cookies. This approach was chosen over IAP because IAP requires a GCP Organization, which personal projects don't have.

**OAuth Configuration:**
```
OAuth Consent Screen:
  Application Name: Improv Olympics
  Support Email: support@ai4joy.org
  Authorized Domains: ai4joy.org
  Scopes: email, profile, openid

OAuth Client:
  Client Type: Web application
  Authorized Redirect URIs: https://ai4joy.org/auth/callback

Secret Manager Secrets:
  - oauth-client-id: OAuth 2.0 client ID
  - oauth-client-secret: OAuth 2.0 client secret
  - session-secret-key: Secret key for signing session cookies

Environment Variables:
  - ALLOWED_USERS: Comma-separated list of authorized emails
```

**User Flow:**
1. User visits https://ai4joy.org (protected endpoint)
2. OAuthSessionMiddleware checks for valid session cookie
3. If not authenticated → Redirect to /auth/login
4. User is redirected to Google Sign-In consent screen
5. User signs in with Google account
6. Google redirects to /auth/callback with authorization code
7. Application exchanges code for user info (email, id)
8. Application checks if user email is in ALLOWED_USERS whitelist
9. If authorized → Create signed session cookie and redirect to app
10. Session cookie sent with subsequent requests

**Application Integration:**
```python
# OAuth middleware extracts user from session cookie
from fastapi import FastAPI, Request
from authlib.integrations.starlette_client import OAuth
from itsdangerous import URLSafeSerializer

app = FastAPI()
oauth = OAuth()

oauth.register(
    name='google',
    client_id=os.getenv('OAUTH_CLIENT_ID'),
    client_secret=os.getenv('OAUTH_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Middleware to check session
@app.middleware("http")
async def oauth_session_middleware(request: Request, call_next):
    session_cookie = request.cookies.get('session')
    if session_cookie:
        try:
            serializer = URLSafeSerializer(os.getenv('SESSION_SECRET_KEY'))
            user_data = serializer.loads(session_cookie)
            request.state.user_email = user_data['email']
            request.state.user_id = user_data['id']
        except:
            pass
    return await call_next(request)

# Rate limiting per user
@app.post('/api/v1/session/start')
async def create_session(request: Request):
    if not hasattr(request.state, 'user_email'):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_email = request.state.user_email
    user_id = request.state.user_id

    # Check daily session limit (10 sessions/user/day)
    daily_count = firestore_client.collection('user_limits').document(user_id).get()
    if daily_count.exists and daily_count.to_dict().get('sessions_today', 0) >= 10:
        raise HTTPException(status_code=429, detail="Daily session limit reached (10/10). Try again tomorrow.")

    # Create session tied to user
    session = create_improv_session(user_id=user_id, user_email=user_email)
    return session
```

**Access Control Configuration:**
```bash
# Set allowed users via Terraform or environment variable
export ALLOWED_USERS="user1@example.com,user2@example.com,pilot@example.com"

# Or in terraform.tfvars:
allowed_users = "user1@example.com,user2@example.com,pilot@example.com"
```

**Cost Protection via Rate Limiting:**
- **Per-User Daily Limit:** 10 sessions/user/day = ~$2/user/day max
- **Concurrent Session Limit:** 3 active sessions/user
- **Cost Firestore Collection:**
  ```
  Collection: user_limits/{user_id}
  {
    "user_id": "oauth_subject_id",
    "email": "user@example.com",
    "sessions_today": 7,
    "last_reset": Timestamp("2025-11-23T00:00:00Z"),
    "active_sessions": 2,
    "total_cost_estimate": 14.50  // dollars
  }
  ```

**Monitoring & Alerting:**
- Track sessions per user per day (alert if >8)
- Alert if any user exceeds $20/day in Gemini costs
- Dashboard showing top 10 users by cost

### Network Security

**VPC Configuration:**
```
VPC Name: improv-vpc
Region: us-central1
Subnets:
  - app-subnet: 10.0.1.0/24 (Cloud Run VPC connector)
  - data-subnet: 10.0.2.0/24 (Firestore, Memorystore)
```

**Serverless VPC Access:**
```
VPC Connector: improv-vpc-connector
Region: us-central1
Subnet: app-subnet (10.0.1.0/28 - small subnet for connector)
Min Instances: 2
Max Instances: 10
Machine Type: e2-micro
```

**Firewall Rules:**
```
Rule: allow-health-checks
Direction: Ingress
Source: Google Load Balancer health check IPs (130.211.0.0/22, 35.191.0.0/16)
Target: Cloud Run via VPC connector
Ports: 8080
Action: Allow

Rule: allow-internal
Direction: Ingress
Source: 10.0.0.0/16 (VPC internal)
Target: All instances
Ports: All
Action: Allow

Rule: deny-all-ingress (default)
Direction: Ingress
Source: 0.0.0.0/0
Action: Deny
Priority: 65535
```

**Cloud Armor Security Policy:**
```
Policy: improv-olympics-security
Rules:
  1. Rate Limiting: 100 requests per minute per client IP
  2. Geographic Restrictions: Allow only US, CA, EU (if needed)
  3. OWASP Top 10 Protection: Enable preconfigured rules
  4. Custom Rule: Block requests without valid User-Agent
  5. DDoS Protection: Enabled (automatic)
```

---

## 5. State Management Architecture

### Session Persistence Strategy

**Firestore (Primary State Store)**

**Why Firestore?**
- Real-time synchronization (future WebSocket support)
- Flexible schema for evolving agent states
- Built-in indexing and querying
- Auto-scaling with no capacity planning
- Native GCP IAM integration
- Strong consistency for critical session data

**Database Design:**
```
Collection: sessions
Document ID: {session_id} (UUID)
Schema:
{
  "session_id": "uuid-v4",
  "user_id": "oauth_subject_id_from_iap",  // PRIMARY KEY for rate limiting
  "user_email": "user@example.com",  // For support/debugging
  "created_at": Timestamp,
  "updated_at": Timestamp,
  "status": "active|completed|abandoned",
  "current_phase": "PHASE_1_SUPPORT|PHASE_2_FALLIBLE",
  "turn_count": 7,
  "game_type": "worlds-worst-advice",
  "location": "Mars Colony Breakroom",
  "audience_archetypes": ["Grumpy New Yorker", "Giggling Teen", ...],
  "conversation_history": [
    {
      "turn": 1,
      "speaker": "user",
      "text": "I think we should...",
      "timestamp": Timestamp,
      "sentiment": 0.7
    },
    {
      "turn": 2,
      "speaker": "partner_agent",
      "text": "Yes! And we could...",
      "timestamp": Timestamp,
      "phase": "PHASE_1_SUPPORT"
    }
  ],
  "metrics": {
    "avg_response_time_ms": 1850,
    "sentiment_trajectory": [0.5, 0.6, 0.7, 0.8],
    "phase_transition_turn": 5
  },
  "coaching_notes": []
}
```

**Firestore Configuration:**
```
Database ID: (default)
Location: us-central1 (same as Cloud Run)
Mode: Native mode
Indexes:
  - Collection: sessions, Fields: user_id (asc), created_at (desc)
  - Collection: sessions, Fields: status (asc), updated_at (desc)
```

**Backup Strategy:**
```
Automated Exports:
  - Frequency: Daily at 2 AM UTC
  - Destination: gs://improvOlympics-backups/firestore/{date}/
  - Retention: 30 days
  - Encryption: Google-managed keys
```

### Caching Layer (Memorystore Redis - Optional)

**Use Case for Caching:**
- Game database rules (infrequently changing)
- Demographic archetype templates
- Rate limiting counters
- Session lock management (prevent concurrent updates)

**Memorystore Configuration (if needed):**
```
Instance ID: improv-cache
Tier: Basic (no HA needed for cache)
Capacity: 1 GB (start small)
Region: us-central1
Version: Redis 7.0
Eviction Policy: allkeys-lru (least recently used)
Persistence: Disabled (pure cache)
```

**Cost-Benefit Analysis:**
- **Without Memorystore**: ~$0/month (use in-memory cache per Cloud Run instance)
- **With Memorystore Basic 1GB**: ~$40/month
- **Recommendation**: Start without Memorystore, add if Firestore read costs exceed $20/month

### State Backup & Recovery

**Disaster Recovery Plan:**

1. **Firestore Point-in-Time Recovery (PITR):**
   - Enabled by default (7-day retention)
   - Restore to any point in last 7 days
   - Recovery Time Objective (RTO): 1 hour
   - Recovery Point Objective (RPO): 0 (real-time replication)

2. **Automated Exports:**
   - Daily full export to Cloud Storage
   - 30-day retention for compliance
   - Encrypted at rest with Google-managed keys

3. **Export Script** (Cloud Scheduler + Cloud Functions):
```python
# Triggered daily by Cloud Scheduler
from google.cloud import firestore
from google.cloud.firestore_admin_v1 import FirestoreAdminClient

def export_firestore(event, context):
    client = FirestoreAdminClient()
    database_name = "projects/improvOlympics/databases/(default)"
    bucket = "gs://improvOlympics-backups/firestore"

    client.export_documents(
        request={
            "name": database_name,
            "output_uri_prefix": f"{bucket}/{datetime.now().strftime('%Y-%m-%d')}"
        }
    )
```

---

## 6. Monitoring & Observability

### Cloud Logging Setup

**Log Aggregation Strategy:**
```
Log Router Sinks:
  1. Default sink → Cloud Logging (30-day retention)
  2. Long-term sink → Cloud Storage bucket (1-year retention, Coldline)
  3. Analytics sink → BigQuery dataset (for query analysis)
```

**Structured Logging Format:**
```python
import logging
import json
from google.cloud import logging as cloud_logging

# Configure structured logging
cloud_logging.Client().setup_logging()

logger = logging.getLogger("improv-olympics")

# Log session events with structured fields
logger.info(json.dumps({
    "event": "scene_turn",
    "session_id": session_id,
    "turn": turn_count,
    "agent": "partner_agent",
    "phase": current_phase,
    "latency_ms": latency,
    "sentiment": sentiment_score,
    "trace_id": trace_id  # For correlation
}))
```

**Log-Based Metrics:**
```
Metric: scene_turn_latency
Filter: jsonPayload.event="scene_turn"
Extraction: jsonPayload.latency_ms
Aggregation: Distribution (p50, p95, p99)

Metric: agent_errors
Filter: severity="ERROR" AND jsonPayload.agent EXISTS
Extraction: jsonPayload.agent
Aggregation: Count by agent type

Metric: phase_transitions
Filter: jsonPayload.event="phase_transition"
Extraction: jsonPayload.session_id
Aggregation: Count
```

### Cloud Monitoring Dashboards

**Primary Dashboard: "Improv Olympics - Operations"**

**Panels:**
1. **Request Metrics**
   - Cloud Run request count (line chart)
   - Request latency (heatmap: p50, p95, p99)
   - Error rate (percentage)
   - Active sessions (gauge)

2. **Agent Performance**
   - Scene turn latency by agent (stacked area chart)
   - Agent API errors (bar chart)
   - Phase transition rate (line chart)
   - Average turns per session (gauge)

3. **Resource Utilization**
   - Cloud Run CPU utilization (line chart)
   - Memory utilization (line chart)
   - Instance count (area chart)
   - Cold start rate (line chart)

4. **VertexAI Metrics**
   - Gemini API QPM (line chart)
   - API error rate by model (bar chart)
   - Token consumption (line chart)
   - API latency p95 (line chart)

5. **Data Layer**
   - Firestore read/write operations (line chart)
   - Firestore document count (gauge)
   - Memorystore hit rate (if used)
   - Backup status (uptime check)

**Dashboard JSON** (example panel):
```json
{
  "displayName": "Scene Turn Latency",
  "xyChart": {
    "dataSets": [{
      "timeSeriesQuery": {
        "timeSeriesFilter": {
          "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/scene_turn_latency\"",
          "aggregation": {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_DELTA",
            "crossSeriesReducer": "REDUCE_PERCENTILE_95"
          }
        }
      },
      "plotType": "LINE"
    }]
  }
}
```

### Alerting Policies

**Critical Alerts (PagerDuty/Email):**

1. **High Error Rate**
   - Condition: Error rate > 5% for 5 minutes
   - Notification: Immediate email + PagerDuty
   - Runbook: Check Cloud Logging for error patterns

2. **Service Unavailable**
   - Condition: Uptime check fails for 2 consecutive minutes
   - Notification: Immediate email + PagerDuty
   - Runbook: Verify Cloud Run service health, check VertexAI API status

3. **VertexAI Quota Exhausted**
   - Condition: Quota usage > 90% or API rate limit errors
   - Notification: Email + Slack
   - Runbook: Request quota increase or implement aggressive rate limiting

4. **Firestore Write Spike**
   - Condition: Write operations > 10x baseline for 10 minutes
   - Notification: Email
   - Runbook: Check for runaway sessions or data corruption

**Warning Alerts (Email only):**

1. **High Latency**
   - Condition: P95 latency > 5s for 10 minutes
   - Notification: Email
   - Action: Review agent performance, consider scaling

2. **Cold Start Rate**
   - Condition: Cold starts > 20% of requests for 15 minutes
   - Notification: Email
   - Action: Increase min instances

3. **Cost Anomaly**
   - Condition: Daily spend > 2x baseline
   - Notification: Email
   - Action: Review usage patterns, check for abuse

### Distributed Tracing (Cloud Trace)

**Trace Configuration:**
```python
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure Cloud Trace exporter
tracer_provider = TracerProvider()
cloud_trace_exporter = CloudTraceSpanExporter()
tracer_provider.add_span_processor(BatchSpanProcessor(cloud_trace_exporter))
trace.set_tracer_provider(tracer_provider)

tracer = trace.get_tracer(__name__)

# Instrument agent calls
with tracer.start_as_current_span("scene_turn") as span:
    span.set_attribute("session_id", session_id)
    span.set_attribute("turn", turn_count)

    with tracer.start_as_current_span("partner_agent_call"):
        partner_response = await partner_agent.generate()

    with tracer.start_as_current_span("audience_agent_call"):
        audience_response = await audience_agent.generate()
```

**Trace Analysis:**
- Identify slow agent calls
- Visualize request flow across agents
- Detect retry loops and cascading failures
- Correlate logs with traces using trace_id

---

## 7. CI/CD Pipeline Architecture

### Cloud Build Configuration

**Trigger Setup:**
```
Trigger Name: deploy-to-production
Repository: github.com/{org}/improv-olympics (Cloud Build GitHub App)
Branch Pattern: ^main$
Build Config: cloudbuild.yaml
Service Account: cloud-build-deployer@improvOlympics.iam.gserviceaccount.com
```

**cloudbuild.yaml:**
```yaml
steps:
  # Step 1: Run unit tests
  - name: 'python:3.11'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        pip install -r requirements.txt
        pip install pytest pytest-cov
        pytest tests/ --cov=app --cov-report=term-missing
    id: 'run-tests'

  # Step 2: Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'us-central1-docker.pkg.dev/improvOlympics/improv-app/improv-olympics:$COMMIT_SHA'
      - '-t'
      - 'us-central1-docker.pkg.dev/improvOlympics/improv-app/improv-olympics:latest'
      - '--cache-from'
      - 'us-central1-docker.pkg.dev/improvOlympics/improv-app/improv-olympics:latest'
      - '.'
    id: 'build-image'
    waitFor: ['run-tests']

  # Step 3: Push image to Artifact Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - 'us-central1-docker.pkg.dev/improvOlympics/improv-app/improv-olympics'
    id: 'push-image'
    waitFor: ['build-image']

  # Step 4: Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'improv-olympics-app'
      - '--image=us-central1-docker.pkg.dev/improvOlympics/improv-app/improv-olympics:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--service-account=improv-app-runtime@improvOlympics.iam.gserviceaccount.com'
      - '--no-allow-unauthenticated'
      - '--min-instances=1'
      - '--max-instances=100'
      - '--cpu=2'
      - '--memory=2Gi'
      - '--timeout=300s'
      - '--concurrency=20'
      - '--set-env-vars=PROJECT_ID=improvOlympics,REGION=us-central1'
      - '--set-secrets=SESSION_ENCRYPTION_KEY=session-encryption-key:latest'
    id: 'deploy-cloud-run'
    waitFor: ['push-image']

  # Step 5: Run smoke tests
  - name: 'gcr.io/cloud-builders/curl'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        # Get Cloud Run service URL
        SERVICE_URL=$(gcloud run services describe improv-olympics-app --region=us-central1 --format='value(status.url)')

        # Test health endpoint
        curl -f $SERVICE_URL/health || exit 1

        # Test ready endpoint
        curl -f $SERVICE_URL/ready || exit 1
    id: 'smoke-tests'
    waitFor: ['deploy-cloud-run']

options:
  machineType: 'E2_HIGHCPU_8'
  logging: CLOUD_LOGGING_ONLY

timeout: 1800s  # 30 minutes

substitutions:
  _DEPLOY_REGION: 'us-central1'
```

### Deployment Environments

**Environment Strategy:**
```
Development: Feature branches → manual Cloud Build trigger
Staging: develop branch → auto-deploy to staging Cloud Run service
Production: main branch → auto-deploy with manual approval gate
```

**Staging Service Configuration:**
```bash
Service Name: improv-olympics-app-staging
URL: https://staging.ai4joy.org
Min Instances: 0 (cost savings)
Max Instances: 10
CPU: 1 vCPU
Memory: 1 GiB
Traffic: 100% to latest revision
```

**Production Service Configuration:**
```bash
Service Name: improv-olympics-app
URL: https://ai4joy.org
Min Instances: 1 (always warm)
Max Instances: 100
CPU: 2 vCPU
Memory: 2 GiB
Traffic: 90% latest, 10% previous (canary)
```

### Rollback Procedures

**Automated Rollback (if smoke tests fail):**
```yaml
# Add to cloudbuild.yaml after smoke tests
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      if [ $? -ne 0 ]; then
        echo "Smoke tests failed. Rolling back..."
        gcloud run services update-traffic improv-olympics-app \
          --region=us-central1 \
          --to-revisions=LATEST=0,improv-olympics-app-previous=100
        exit 1
      fi
  waitFor: ['smoke-tests']
```

**Manual Rollback:**
```bash
# List revisions
gcloud run revisions list --service=improv-olympics-app --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic improv-olympics-app \
  --region=us-central1 \
  --to-revisions=improv-olympics-app-00042-xyz=100
```

---

## 8. Cost Analysis & Optimization

### Estimated Monthly Costs (Moderate Usage)

**Assumptions:**
- 2000 sessions per month
- Average 12 turns per session (24,000 turns/month)
- 3 agent calls per turn (72,000 agent calls/month)
- Average session duration: 8 minutes
- 50% Gemini Pro, 50% Gemini Flash

**Cost Breakdown:**

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| **Cloud Run** | 320 vCPU-hours, 320 GiB-hours | $0.00002400/vCPU-sec, $0.00000250/GiB-sec | $75 |
| **VertexAI Gemini Pro** | 36,000 requests, ~20M input tokens, ~5M output tokens | $0.00025/1K input, $0.001/1K output | $10 |
| **VertexAI Gemini Flash** | 36,000 requests, ~10M input tokens, ~2M output tokens | $0.000075/1K input, $0.0003/1K output | $1.50 |
| **Firestore** | 150K writes, 500K reads, 2GB storage | $0.18/100K writes, $0.06/100K reads, $0.18/GB | $0.65 |
| **Cloud Load Balancing** | 100GB ingress, 200GB egress | $0.025/GB | $7.50 |
| **Cloud Logging** | 50GB logs | First 50GB free | $0 |
| **Cloud Monitoring** | Standard metrics | Free tier | $0 |
| **Artifact Registry** | 10GB storage | $0.10/GB | $1 |
| **Cloud Storage (backups)** | 20GB Coldline | $0.004/GB | $0.08 |
| **Cloud DNS** | 1 zone, 10M queries | $0.20/zone, $0.40/M queries | $4.20 |
| **Cloud Armor** | 1 policy, 1M requests | $5 + $0.75/M requests | $5.75 |
| **Secret Manager** | 5 secrets, 10K access ops | $0.06/secret, $0.03/10K ops | $0.33 |
| **SSL Certificate** | Google-managed | Free | $0 |
| | | **Total** | **~$105/month** |

**With Higher Usage (10,000 sessions/month):**
- Cloud Run: $320
- VertexAI: $50
- Firestore: $3
- Load Balancing: $30
- Other: $20
- **Total: ~$423/month**

### Cost Optimization Strategies

**Immediate Optimizations:**
1. **Use Gemini Flash for simple tasks**: MC and Audience agents use Flash (3x cheaper)
2. **Efficient prompting**: Minimize token usage with concise system instructions
3. **Session timeout**: Auto-expire inactive sessions after 15 minutes
4. **Image optimization**: Multi-stage Docker builds to reduce storage costs
5. **Log retention**: Move old logs to Coldline storage after 30 days

**Advanced Optimizations:**
1. **Prompt caching** (when available): Cache system instructions to reduce input tokens
2. **Request batching**: Batch multiple agent calls when possible (with careful orchestration)
3. **Committed use discounts**: If usage stabilizes, commit to 1-year Cloud Run usage for 17% discount
4. **Regional optimization**: Serve users from closest region to reduce latency and egress
5. **Firestore indexes**: Minimize indexes to reduce write costs

**Budget Alerts:**
```bash
# Set up budget alert at $150/month (50% buffer)
gcloud billing budgets create \
  --billing-account=<BILLING_ACCOUNT_ID> \
  --display-name="Improv Olympics Monthly Budget" \
  --budget-amount=150 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

---

## 9. WebSocket Architecture (Future Voice Support)

### Architecture Changes for Real-Time Voice

**Current (HTTP):**
```
User → Load Balancer → Cloud Run → ADK Agents → VertexAI
                         ↓
                    Firestore (state)
```

**Future (WebSocket):**
```
User → WebSocket → Cloud Run (WebSocket handler) → ADK Agents → VertexAI
         ↓                ↓                             ↓
    Audio Stream    Session State                 Audio Stream
                    (Firestore)                   (Speech-to-Text)
```

**Cloud Run WebSocket Support:**
```python
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = create_session()

    try:
        while True:
            # Receive audio chunk
            audio_data = await websocket.receive_bytes()

            # Process with Voice Activity Detection (VAD)
            if is_speech_complete(audio_data):
                # Transcribe with Speech-to-Text
                text = await transcribe_audio(audio_data)

                # Process through agents
                response = await process_turn(session_id, text)

                # Synthesize response
                audio_response = await text_to_speech(response)

                # Send back to client
                await websocket.send_bytes(audio_response)

    except WebSocketDisconnect:
        cleanup_session(session_id)
```

**Additional Services Needed:**
- **Cloud Speech-to-Text**: Streaming recognition API
- **Cloud Text-to-Speech**: Neural2 voices for natural responses
- **Voice Activity Detection**: Client-side library (Web Audio API)

**Cost Impact:**
- Speech-to-Text: ~$0.024/minute ($2.40 for 100 minutes)
- Text-to-Speech: ~$16/1M characters ($0.16 for 10K characters)
- WebSocket connections: No additional Cloud Run cost (same pricing)

---

## 10. Deployment Runbook

### Prerequisites

**1. GCP Project Setup:**
```bash
# Set project
gcloud config set project improvOlympics

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  dns.googleapis.com \
  compute.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com
```

**2. Domain Verification:**
```bash
# Verify ai4joy.org ownership in Google Search Console
# Add TXT record: google-site-verification=<verification-string>
```

### Initial Deployment (Step-by-Step)

**Phase 1: Infrastructure Setup**

See separate Terraform configuration files for automated provisioning.

**Phase 2: Application Deployment**

```bash
# 1. Clone repository
git clone https://github.com/{org}/improv-olympics.git
cd improv-olympics

# 2. Build and push initial image
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/improvOlympics/improv-app/improv-olympics:v1.0.0

# 3. Deploy to Cloud Run
gcloud run deploy improv-olympics-app \
  --image us-central1-docker.pkg.dev/improvOlympics/improv-app/improv-olympics:v1.0.0 \
  --region us-central1 \
  --platform managed \
  --service-account improv-app-runtime@improvOlympics.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --min-instances 1 \
  --max-instances 100 \
  --cpu 2 \
  --memory 2Gi \
  --timeout 300s \
  --set-env-vars PROJECT_ID=improvOlympics,REGION=us-central1
```

**Phase 3: Load Balancer & DNS Configuration**

```bash
# 1. Create serverless NEG
gcloud compute network-endpoint-groups create improv-neg \
  --region=us-central1 \
  --network-endpoint-type=serverless \
  --cloud-run-service=improv-olympics-app

# 2. Create backend service
gcloud compute backend-services create improv-backend \
  --global \
  --load-balancing-scheme=EXTERNAL_MANAGED

gcloud compute backend-services add-backend improv-backend \
  --global \
  --network-endpoint-group=improv-neg \
  --network-endpoint-group-region=us-central1

# 3. Create URL map
gcloud compute url-maps create improv-lb \
  --default-service=improv-backend

# 4. Reserve static IP
gcloud compute addresses create improv-ip \
  --ip-version=IPV4 \
  --global

# 5. Create SSL certificate
gcloud compute ssl-certificates create improv-cert \
  --domains=ai4joy.org,www.ai4joy.org \
  --global

# 6. Create HTTPS proxy
gcloud compute target-https-proxies create improv-https-proxy \
  --url-map=improv-lb \
  --ssl-certificates=improv-cert

# 7. Create forwarding rule
gcloud compute forwarding-rules create improv-https-rule \
  --global \
  --target-https-proxy=improv-https-proxy \
  --address=improv-ip \
  --ports=443

# 8. Create HTTP to HTTPS redirect
gcloud compute url-maps import improv-lb \
  --global \
  --source=/dev/stdin <<EOF
defaultService: global/backendServices/improv-backend
hostRules:
- hosts:
  - ai4joy.org
  - www.ai4joy.org
  pathMatcher: path-matcher-1
pathMatchers:
- defaultUrlRedirect:
    httpsRedirect: true
    redirectResponseCode: MOVED_PERMANENTLY_DEFAULT
  name: path-matcher-1
EOF

# 9. Update DNS
gcloud dns record-sets transaction start --zone=ai4joy-org
gcloud dns record-sets transaction add <STATIC_IP> \
  --name=ai4joy.org. \
  --ttl=300 \
  --type=A \
  --zone=ai4joy-org
gcloud dns record-sets transaction execute --zone=ai4joy-org
```

**Phase 4: Monitoring Setup**

```bash
# 1. Create notification channel
gcloud alpha monitoring channels create \
  --display-name="Email Alerts" \
  --type=email \
  --channel-labels=email_address=alerts@ai4joy.org

# 2. Create alerting policies (see monitoring section for details)
```

**Phase 5: CI/CD Setup**

```bash
# 1. Connect GitHub repository
gcloud builds repositories create improv-olympics-repo \
  --remote-uri=https://github.com/{org}/improv-olympics.git \
  --connection=github-connection

# 2. Create build trigger
gcloud builds triggers create github \
  --name=deploy-production \
  --repo-name=improv-olympics \
  --repo-owner={org} \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml
```

### Validation Checklist

After deployment, verify:
- [ ] Cloud Run service is healthy (`gcloud run services describe`)
- [ ] HTTPS load balancer returns 200 OK (`curl https://ai4joy.org/health`)
- [ ] SSL certificate is provisioned and valid
- [ ] DNS resolves to correct IP (`dig ai4joy.org`)
- [ ] Firestore can read/write session data
- [ ] VertexAI API calls succeed (check Cloud Logging)
- [ ] Monitoring dashboard shows metrics
- [ ] Alerting policies are active
- [ ] CI/CD trigger builds successfully

### Troubleshooting Common Issues

**1. SSL Certificate Provisioning Fails:**
- Check DNS propagation: `dig _acme-challenge.ai4joy.org`
- Verify domain ownership in Search Console
- Wait 15-30 minutes for validation
- Check certificate status: `gcloud compute ssl-certificates describe improv-cert`

**2. Cloud Run Service Unhealthy:**
- Check logs: `gcloud run services logs read improv-olympics-app --region=us-central1`
- Verify service account permissions
- Test locally: `docker run -p 8080:8080 <image>`
- Check health endpoint: `curl http://localhost:8080/health`

**3. VertexAI API Errors:**
- Verify APIs enabled: `gcloud services list --enabled`
- Check IAM permissions: Service account needs `roles/aiplatform.user`
- Verify quota: Check VertexAI quotas in console
- Test credentials: `gcloud auth application-default print-access-token`

**4. High Latency:**
- Check Cloud Run instance count (may need to increase min instances)
- Review agent prompt length (reduce token usage)
- Enable Cloud CDN for static assets
- Check Firestore query performance (add indexes if needed)

---

## Conclusion

This architecture provides a production-ready foundation for the Improv Olympics application with:
- **Serverless auto-scaling** via Cloud Run
- **Secure VertexAI integration** with Workload Identity
- **Robust state management** with Firestore
- **Professional domain setup** with ai4joy.org
- **Comprehensive monitoring** and alerting
- **Automated CI/CD** with Cloud Build
- **Future-proof design** for WebSocket voice support

**Estimated monthly cost**: $105-425 depending on usage
**Deployment time**: 2-4 hours for initial setup
**Maintenance effort**: <2 hours per month (mostly monitoring)

Next steps: Proceed to Terraform infrastructure provisioning (see separate files).
