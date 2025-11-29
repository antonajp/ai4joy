# GCP Deployment Analysis: Real-Time Audio Features (IQS-58)

## Executive Summary

This analysis reviews the Google Cloud Platform deployment requirements for real-time audio features in the Improv Olympics application. The current infrastructure is already well-suited for WebSocket-based audio streaming with some configuration adjustments needed for optimal performance.

**Key Findings:**
- Current Cloud Run configuration supports WebSocket connections
- Recommended adjustments: Increase timeout to 600s, adjust concurrency to 10-15
- Estimated cost: $0.15-0.25 per audio session (5-10 minutes)
- Target: 50 concurrent sessions achievable with current architecture
- No separate Cloud Run service required - use existing service with optimized settings

---

## 1. Cloud Run Configuration for WebSocket

### Current Configuration (from `cloudbuild.yaml` & Terraform)
```yaml
CPU: 2 vCPU
Memory: 2Gi
Timeout: 300s (5 minutes)
Concurrency: 20 requests per instance
Min Instances: 1
Max Instances: 100
```

### WebSocket-Specific Analysis

**✅ What Works:**
- Cloud Run natively supports WebSocket connections (HTTP/1.1 with Upgrade header)
- Current 2 vCPU / 2Gi configuration sufficient for audio processing
- VPC connector already configured for private network access
- Global HTTPS Load Balancer compatible with WebSocket

**⚠️ Recommended Changes:**

#### 1. Request Timeout Extension
```terraform
# Current: 300s (5 minutes)
# Recommended: 600s (10 minutes) for audio sessions

timeout = "600s"  # Allows 10-minute voice conversations
```

**Rationale:**
- Audio sessions typically last 5-10 minutes
- ADK Live API streaming requires persistent connections
- Prevents premature disconnections during conversations
- Cloud Run supports up to 3600s (1 hour) timeout

#### 2. Concurrency Adjustment
```yaml
# Current (cloudbuild.yaml): _CONCURRENCY: '20'
# Recommended: _CONCURRENCY: '10-15'
```

**Rationale:**
- Audio processing with Vertex AI is more resource-intensive than text chat
- Each WebSocket connection maintains:
  - ADK LiveRequestQueue
  - Bidirectional audio streams
  - Memory for audio buffering (~2-4MB per session)
- Lower concurrency = better audio quality and lower latency
- 10-15 concurrent sessions per instance is optimal for 2 vCPU / 2Gi

#### 3. Memory Configuration
```terraform
# Current: 2Gi - KEEP AS IS
# No changes needed
```

**Rationale:**
- 2Gi provides ~130-200MB per concurrent session (at 10-15 concurrency)
- Audio buffering requires ~2-4MB per session
- ADK session overhead ~5-10MB per session
- Sufficient headroom for 10-15 concurrent audio sessions

#### 4. CPU Configuration
```terraform
# Current: 2 vCPU - KEEP AS IS
# Optional: Consider 4 vCPU for lower latency
```

**Rationale:**
- Audio encoding/decoding is CPU-light (PCM16 is uncompressed)
- Vertex AI handles heavy ML processing
- 2 vCPU sufficient for target workload
- Upgrade to 4 vCPU only if p99 latency > 3 seconds

### Recommended Terraform Changes

**File:** `/infrastructure/terraform/main.tf`

```terraform
resource "google_cloud_run_v2_service" "improv_app" {
  # ... existing configuration ...

  template {
    # ... existing template config ...

    containers {
      # ... existing container config ...

      # Add request timeout for WebSocket
      timeout = "600s"  # Extended for audio sessions

      # Keep existing resource limits
      resources {
        limits = {
          cpu    = var.cloud_run_cpu      # 2 vCPU (keep as is)
          memory = var.cloud_run_memory   # 2Gi (keep as is)
        }
      }

      # Add environment variable for audio configuration
      env {
        name  = "AUDIO_SESSION_TIMEOUT"
        value = "600"  # Seconds
      }

      env {
        name  = "MAX_CONCURRENT_AUDIO_SESSIONS"
        value = "10"  # Per instance
      }
    }

    # IMPORTANT: Adjust concurrency via cloudbuild.yaml
    # Cannot set max_instance_request_concurrency in Terraform
    # when using --concurrency flag in gcloud deploy
  }
}
```

**File:** `/cloudbuild.yaml`

```yaml
# Step 6: Deploy to Cloud Run
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  args:
    - 'run'
    - 'deploy'
    - '${_SERVICE_NAME}'
    # ... existing args ...
    - '--timeout=600s'          # 10 minutes for audio sessions
    - '--concurrency=12'         # Reduced from 20 for audio workload
    # ... rest of args ...
```

---

## 2. Networking & Security

### Current Infrastructure Assessment

**✅ Already Configured:**
- VPC Connector: `improv-vpc-connector` (2-10 e2-micro instances)
- VPC Egress: Private ranges only
- HTTPS Load Balancer: Global, supports WebSocket
- SSL/TLS: Managed certificate for ai4joy.org
- Cloud Armor: Rate limiting, DDoS protection

### WebSocket-Specific Considerations

#### A. WebSocket Protocol Support
```
Client → Load Balancer → Cloud Run
  ws://  → Upgrade: websocket → WebSocket handler
  wss:// → (TLS termination)   → Plain WebSocket
```

**Status:** ✅ Fully supported
- Cloud Run supports HTTP/1.1 Upgrade header
- Load balancer passes WebSocket traffic transparently
- SSL/TLS termination at load balancer (wss:// → ws://)

#### B. CORS Configuration
**Current:** Not explicitly configured (defaults to allow all origins)

**Recommended:** Add explicit CORS middleware for WebSocket

**File:** `app/main.py`
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai4joy.org",
        "https://www.ai4joy.org",
        "http://localhost:3000",  # Development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

**Rationale:**
- WebSocket handshake starts as HTTP request
- CORS preflight may be required for cross-origin requests
- Explicit origins prevent unauthorized WebSocket connections

#### C. IAM Permissions

**Current IAM Roles (app_runtime service account):**
```terraform
✅ roles/aiplatform.user          # Vertex AI access
✅ roles/datastore.user           # Firestore
✅ roles/secretmanager.secretAccessor
✅ roles/logging.logWriter
✅ roles/cloudtrace.agent
```

**Status:** ✅ No additional IAM roles needed for audio
- Vertex AI Live API uses same `aiplatform.user` role
- Firestore user session tracking already permitted

#### D. Load Balancer Configuration

**Current Setup:**
```terraform
Backend Service: improv_backend
  - Protocol: HTTP
  - Session Affinity: GENERATED_COOKIE
  - Load Balancing Scheme: EXTERNAL_MANAGED
```

**WebSocket Compatibility:** ✅ Fully compatible
- Session affinity ensures WebSocket reconnects to same instance
- HTTP protocol supports WebSocket upgrade
- No backend service timeout (Cloud Run timeout applies)

**Potential Issue:** ⚠️ Cloud Armor rate limiting

**Current Rate Limit:**
```terraform
rate_limit_threshold {
  count        = 100
  interval_sec = 60
}
ban_duration_sec = 600
```

**Recommendation:** Add exception for WebSocket endpoints

```terraform
# Add new rule BEFORE general rate limiting (priority < 1000)
rule {
  action   = "allow"
  priority = "900"
  match {
    expr {
      expression = "request.path.matches('/ws/audio/.*')"
    }
  }
  description = "Allow WebSocket audio connections (rate limited at application layer)"
}
```

**Rationale:**
- WebSocket maintains single connection for extended duration
- Application-level rate limiting prevents abuse (premium tier gating)
- Cloud Armor would see connection as single request

#### E. SSL/TLS Considerations

**Current:** ✅ Managed SSL certificate
- Domain: ai4joy.org, www.ai4joy.org
- TLS termination at load balancer
- HTTP/2 and HTTP/1.1 supported

**WebSocket Protocol:**
- Client connects with `wss://ai4joy.org/ws/audio/{session_id}`
- Load balancer terminates TLS
- Cloud Run receives plain WebSocket (ws://)

**Status:** ✅ No changes needed

---

## 3. Cost Analysis

### A. Vertex AI Live API Costs

**Gemini 2.0 Flash Live API Pricing (as of Jan 2025):**
```
Audio Input: $0.0015 per 1,000 characters (transcription)
Audio Output: $0.006 per 1,000 characters (synthesis)
Model Processing: Included in standard Gemini pricing
```

**Assumptions:**
- Average audio session: 5-10 minutes
- Speech rate: 150 words/minute = 750-1500 words per session
- Characters: 5 chars/word = 3,750-7,500 chars
- Bidirectional: Input + Output

**Cost Calculation (per session):**
```
Input (transcription):
  7,500 chars × $0.0015/1000 = $0.01125

Output (synthesis):
  7,500 chars × $0.006/1000 = $0.045

Total per 5-min session: ~$0.056
Total per 10-min session: ~$0.11
```

### B. Cloud Run Instance Costs

**Pricing (us-central1):**
```
CPU: $0.00002400 per vCPU-second
Memory: $0.00000250 per GiB-second
Requests: $0.40 per million requests
```

**Configuration:**
```
2 vCPU × 600s = 1,200 vCPU-seconds
2 GiB × 600s = 1,200 GiB-seconds
1 WebSocket request (connection initiation)
```

**Cost Calculation (per session):**
```
CPU: 1,200 × $0.000024 = $0.0288
Memory: 1,200 × $0.0000025 = $0.003
Request: 1 × $0.0000004 = negligible

Total: ~$0.032 per session
```

**With Minimum Instances:**
```
1 instance always running:
  2 vCPU × 86,400 sec/day × $0.000024 = $4.15/day
  2 GiB × 86,400 sec/day × $0.0000025 = $0.43/day

Total idle cost: ~$4.58/day = $137/month
```

**Recommendation:** Keep min_instances=1 for warm starts
- WebSocket connections cannot tolerate cold starts (5-10s delay)
- Idle cost minimal compared to user experience improvement

### C. Total Cost Per Audio Session

```
Vertex AI Live API:     $0.056 - $0.11
Cloud Run (compute):    $0.032
Firestore (user data):  $0.001 (negligible)
Egress (audio data):    $0.005 (avg 5MB @ $0.12/GB)
---------------------------------------------
Total per session:      $0.094 - $0.148
```

**Rounded estimate:** $0.10 - $0.15 per 5-10 minute session

### D. Monthly Cost Projections

**Scenario 1: Light Usage (10 sessions/day)**
```
Sessions: 10/day × 30 days = 300/month
Session cost: 300 × $0.12 = $36
Idle cost: $137 (min instances)
---------------------------------------------
Total: ~$173/month
```

**Scenario 2: Moderate Usage (50 sessions/day)**
```
Sessions: 50/day × 30 days = 1,500/month
Session cost: 1,500 × $0.12 = $180
Idle cost: $137
Additional instances: ~$50 (peak hours)
---------------------------------------------
Total: ~$367/month
```

**Scenario 3: Target Scale (50 concurrent sessions)**
```
Peak: 50 concurrent × 8 hours/day
Sessions: ~400/day × 30 days = 12,000/month
Session cost: 12,000 × $0.12 = $1,440
Compute (scaled): $500-700
Firestore: $50
---------------------------------------------
Total: ~$2,000-2,200/month
```

### E. Budget Monitoring Alerts

**Recommended Budget Configuration:**
```
Budget: $500/month (moderate usage threshold)
Alerts:
  - 50% ($250): Warning - review usage patterns
  - 75% ($375): Action - verify no runaway costs
  - 90% ($450): Critical - investigate immediately
```

**Implementation:**
```bash
# Manual setup required (no Terraform permissions)
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Improv Olympics Audio Budget" \
  --budget-amount=500USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=75 \
  --threshold-rule=percent=90
```

---

## 4. Monitoring & Observability

### A. WebSocket Connection Metrics

**Recommended Custom Metrics:**

**1. Active WebSocket Connections**
```python
# File: app/audio/websocket_handler.py

from opentelemetry import metrics

meter = metrics.get_meter(__name__)
active_connections_gauge = meter.create_up_down_counter(
    "audio.websocket.active_connections",
    description="Number of active WebSocket connections",
    unit="connections",
)

# In AudioWebSocketHandler.connect():
active_connections_gauge.add(1)

# In AudioWebSocketHandler.disconnect():
active_connections_gauge.add(-1)
```

**Cloud Monitoring Query:**
```
fetch generic_task
| metric 'custom.googleapis.com/audio/websocket/active_connections'
| group_by 1m, [value_active_connections_mean: mean(value.active_connections)]
| every 1m
```

**2. Audio Session Duration**
```python
session_duration_histogram = meter.create_histogram(
    "audio.session.duration",
    description="Audio session duration in seconds",
    unit="seconds",
)

# In disconnect():
duration = time.time() - session_start_time
session_duration_histogram.record(duration)
```

**3. Audio Processing Latency**
```python
audio_latency_histogram = meter.create_histogram(
    "audio.processing.latency",
    description="Time from audio input to response",
    unit="milliseconds",
)

# In process_audio_message():
start = time.time()
result = await self.orchestrator.send_audio_chunk(session_id, audio_bytes)
latency_ms = (time.time() - start) * 1000
audio_latency_histogram.record(latency_ms)
```

### B. Health Check Configuration

**Current Health Endpoints:**
```
GET /health         - Basic liveness probe
GET /ready          - Readiness probe
GET /api/audio/health - Audio service health
```

**Recommended Addition: WebSocket Health Check**

```python
# File: app/routers/audio.py

@audio_health_router.get("/websocket-health")
async def websocket_health() -> Dict[str, Any]:
    """WebSocket-specific health check.

    Returns:
        Active connections, session capacity, error rate
    """
    handler = audio_handler

    return {
        "active_connections": len(handler.active_connections),
        "max_capacity": 10,  # Per instance concurrency limit
        "capacity_percentage": len(handler.active_connections) / 10 * 100,
        "sessions_today": await get_audio_sessions_today(),
        "avg_session_duration": await get_avg_session_duration(),
        "error_rate_1h": await get_audio_error_rate(hours=1),
    }
```

**Cloud Monitoring Uptime Check:**
```terraform
resource "google_monitoring_uptime_check_config" "audio_health" {
  display_name = "Audio Service Health Check"
  project      = var.project_id
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/api/audio/websocket-health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "ai4joy.org"
    }
  }
}
```

### C. Audio Latency Tracking

**Key Metrics to Monitor:**
1. **End-to-End Latency** (user speaks → hears response)
2. **Transcription Latency** (audio → text)
3. **Agent Processing Time** (text → response text)
4. **Synthesis Latency** (response text → audio)
5. **Network Round-Trip Time**

**Implementation:**
```python
# File: app/audio/audio_orchestrator.py

async def send_audio_chunk(self, session_id: str, audio_bytes: bytes):
    start_time = time.time()

    # Send to ADK
    await session.queue.send_realtime(audio_blob)

    # Log detailed timing
    logger.info(
        "audio_chunk_sent",
        session_id=session_id,
        chunk_size=len(audio_bytes),
        latency_ms=(time.time() - start_time) * 1000,
    )
```

**Cloud Logging Filter:**
```
jsonPayload.event="audio_chunk_sent"
```

**Log-Based Metric:**
```terraform
resource "google_logging_metric" "audio_processing_latency" {
  name    = "audio_processing_latency"
  project = var.project_id
  filter  = "jsonPayload.event=\"audio_chunk_sent\""

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    unit         = "ms"
    display_name = "Audio Processing Latency"
  }

  value_extractor = "EXTRACT(jsonPayload.latency_ms)"

  bucket_options {
    exponential_buckets {
      num_finite_buckets = 64
      growth_factor      = 2
      scale              = 1
    }
  }
}
```

### D. Error Rate Dashboards

**Recommended Alert Policy:**

```terraform
resource "google_monitoring_alert_policy" "audio_high_error_rate" {
  display_name = "Audio Service - High Error Rate"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Audio error rate > 5% for 5 minutes"

    condition_threshold {
      filter = join(" AND ", [
        "resource.type=\"cloud_run_revision\"",
        "metric.type=\"run.googleapis.com/request_count\"",
        "resource.labels.service_name=\"improv-olympics-app\"",
        "metric.label.response_code_class=\"5xx\"",
        # Filter for audio endpoints only
        "metadata.user_labels.endpoint=~\"/ws/audio/.*\""
      ])
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content = <<-EOT
    Audio WebSocket service error rate exceeded 5% for 5 minutes.

    **Troubleshooting Steps:**
    1. Check Cloud Logging for error details:
       `jsonPayload.event="audio_error"`
    2. Verify Vertex AI quota not exceeded
    3. Check WebSocket connection stability
    4. Review audio session metrics in dashboard

    **Common Causes:**
    - Vertex AI Live API throttling
    - Invalid audio format from client
    - Authentication failures
    - Network timeouts
    EOT
    mime_type = "text/markdown"
  }
}
```

### E. Real-Time Monitoring Dashboard

**Cloud Monitoring Dashboard JSON:**

```json
{
  "displayName": "Audio Service - Real-Time Monitoring",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Active WebSocket Connections",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/audio/websocket/active_connections\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_MEAN"
                  }
                }
              },
              "plotType": "LINE"
            }],
            "yAxis": {
              "label": "Connections",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "xPos": 6,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Audio Processing Latency (p50, p95, p99)",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "metric.type=\"logging.googleapis.com/user/audio_processing_latency\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "crossSeriesReducer": "REDUCE_PERCENTILE_50"
                    }
                  }
                },
                "plotType": "LINE",
                "legendTemplate": "p50"
              },
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "metric.type=\"logging.googleapis.com/user/audio_processing_latency\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "crossSeriesReducer": "REDUCE_PERCENTILE_95"
                    }
                  }
                },
                "plotType": "LINE",
                "legendTemplate": "p95"
              },
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "metric.type=\"logging.googleapis.com/user/audio_processing_latency\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "crossSeriesReducer": "REDUCE_PERCENTILE_99"
                    }
                  }
                },
                "plotType": "LINE",
                "legendTemplate": "p99"
              }
            ],
            "yAxis": {
              "label": "Latency (ms)",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "yPos": 4,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Audio Session Duration Distribution",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"custom.googleapis.com/audio/session/duration\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_DELTA",
                    "crossSeriesReducer": "REDUCE_MEAN"
                  }
                }
              },
              "plotType": "LINE"
            }],
            "yAxis": {
              "label": "Duration (seconds)",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "xPos": 6,
        "yPos": 4,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "WebSocket Error Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.label.response_code_class=\"5xx\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              },
              "plotType": "LINE"
            }],
            "yAxis": {
              "label": "Errors/second",
              "scale": "LINEAR"
            }
          }
        }
      }
    ]
  }
}
```

**Terraform Implementation:**
```terraform
resource "google_monitoring_dashboard" "audio_dashboard" {
  dashboard_json = file("${path.module}/dashboards/audio-monitoring.json")
  project        = var.project_id

  depends_on = [
    module.project_services,
    google_logging_metric.audio_processing_latency
  ]
}
```

---

## 5. Scaling Considerations

### A. Target: 50 Concurrent Audio Sessions

**Instance Calculation:**
```
Concurrency per instance: 10-12
Target concurrent sessions: 50

Required instances: 50 / 10 = 5 instances
Peak instances (buffer): 7 instances
```

**Current Configuration:**
```terraform
min_instances = 1   # Always warm
max_instances = 100 # Far exceeds needs
```

**Recommendation:** Add audio-specific scaling

```terraform
# Option 1: Keep current service, rely on autoscaling
# Cloud Run will automatically scale 1 → 7 instances as load increases

# Option 2: Create dedicated audio service (NOT RECOMMENDED)
# Adds complexity without significant benefit for current scale
```

### B. Autoscaling Configuration

**Current:** Cloud Run autoscales based on:
- Request queue depth
- CPU utilization
- Custom metrics (if configured)

**Recommended:** Configure custom metrics for audio workload

```terraform
resource "google_cloud_run_v2_service" "improv_app" {
  # ... existing config ...

  template {
    scaling {
      min_instance_count = 1
      max_instance_count = 20  # Reduced from 100 for cost control

      # Custom scaling based on active WebSocket connections
      # Note: Requires Cloud Run v2 API
      scaling_mode = "automatic"
    }
  }
}
```

**Autoscaling Behavior:**
```
Concurrent Sessions → Instances
0-10  → 1 instance  (min_instances)
11-20 → 2 instances
21-30 → 3 instances
31-40 → 4 instances
41-50 → 5 instances
51-60 → 6 instances
60+   → 7+ instances
```

**Scale-Down Policy:**
- Idle instances scaled down after 15 minutes (Cloud Run default)
- Min instances (1) always maintained for warm starts

### C. Regional Deployment Considerations

**Current Region:** `us-central1` (Iowa)

**Global Latency Analysis:**
```
us-central1 → North America: 20-80ms (excellent)
us-central1 → Europe: 100-150ms (acceptable)
us-central1 → Asia: 150-250ms (marginal for real-time audio)
us-central1 → South America: 80-120ms (acceptable)
```

**Recommendation for Phase 1:** Keep single-region (us-central1)
- 80% of expected users in North America
- Latency acceptable for MVP
- Lower operational complexity

**Future Multi-Region Strategy (50+ concurrent globally):**
```
Primary: us-central1 (North America)
Secondary: europe-west1 (Belgium) - for EU users
Tertiary: asia-northeast1 (Tokyo) - for Asia-Pacific
```

**Multi-Region Implementation:**
```terraform
# Duplicate Cloud Run service in each region
module "audio_service_us" {
  source = "./modules/cloud-run-audio"
  region = "us-central1"
}

module "audio_service_eu" {
  source = "./modules/cloud-run-audio"
  region = "europe-west1"
}

# Global Load Balancer routes to nearest region
resource "google_compute_url_map" "audio_lb" {
  # ... geo-routing configuration ...
}
```

**Cost Impact:**
- Multi-region: 3x infrastructure cost
- Benefit: 50-150ms latency reduction for global users
- Recommended trigger: >100 daily active users outside North America

### D. Vertex AI Quota Considerations

**Current Quotas (check via Console):**
```bash
gcloud alpha services quotas list \
  --service=aiplatform.googleapis.com \
  --project=coherent-answer-479115-e1 \
  --filter="metric.displayName:gemini"
```

**Key Quotas to Monitor:**
```
1. Gemini Live API Requests per Minute: Default 60
2. Gemini Live API Active Connections: Default 10
3. Gemini API Requests per Day: Default 1,500
```

**For 50 Concurrent Sessions:**
```
Required quota:
  - Active Connections: 50
  - Requests per Minute: 100+ (for session creation)
```

**Quota Increase Request:**
```bash
# Navigate to: https://console.cloud.google.com/apis/api/aiplatform.googleapis.com/quotas
# Search for: "Gemini Live API"
# Request increase:
  - Active Connections: 50 → 100 (buffer)
  - Requests per Minute: 60 → 200
```

**Handling Quota Exceeded:**
```python
# File: app/audio/audio_orchestrator.py

from google.api_core import exceptions

async def start_session(self, session_id: str, user_email: str):
    try:
        queue = self.create_session_queue(session_id)
        # ... existing code ...
    except exceptions.ResourceExhausted as e:
        logger.error(
            "Vertex AI quota exceeded",
            session_id=session_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=503,
            detail="Audio service temporarily unavailable. Please try again in a few minutes.",
        )
```

---

## 6. Terraform/Infrastructure Changes

### A. Required Terraform Modifications

**File Structure:**
```
infrastructure/terraform/
├── main.tf                      # Main infrastructure
├── variables.tf                 # Variables
├── outputs.tf                   # Outputs
├── modules/
│   └── audio-service/          # NEW: Audio-specific module
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── dashboards/
    └── audio-monitoring.json    # NEW: Audio dashboard
```

**NEW MODULE: `modules/audio-service/main.tf`**

```terraform
# Audio-specific Cloud Run configuration adjustments
# Applied as a Cloud Run service revision

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "service_account_email" {
  type = string
}

variable "vpc_connector_id" {
  type = string
}

# Audio-specific environment variables
locals {
  audio_env_vars = {
    AUDIO_SESSION_TIMEOUT         = "600"
    MAX_CONCURRENT_AUDIO_SESSIONS = "10"
    AUDIO_BUFFER_SIZE_BYTES       = "4096"
    ENABLE_AUDIO_METRICS          = "true"
  }
}

# Cloud Run service modifications
# Note: This is applied via gcloud in cloudbuild.yaml
# Terraform cannot modify existing service without recreation

# Audio-specific monitoring
resource "google_logging_metric" "audio_session_count" {
  name    = "audio_session_count"
  project = var.project_id
  filter  = "jsonPayload.event=\"audio_session_started\""

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "sessions"
    display_name = "Audio Session Count"
  }
}

resource "google_logging_metric" "audio_error_count" {
  name    = "audio_error_count"
  project = var.project_id
  filter  = "jsonPayload.event=\"audio_error\""

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "errors"
    display_name = "Audio Error Count"
  }
}

# Alert policy for audio quota exceeded
resource "google_monitoring_alert_policy" "audio_quota_exceeded" {
  display_name = "Audio Service - Vertex AI Quota Exceeded"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Quota exhausted errors detected"

    condition_threshold {
      filter = join(" AND ", [
        "resource.type=\"cloud_run_revision\"",
        "metric.type=\"logging.googleapis.com/user/audio_error_count\"",
        "jsonPayload.error=~\".*quota.*\""
      ])
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5  # More than 5 quota errors per minute

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content = <<-EOT
    Vertex AI quota limits reached for audio service.

    **Immediate Actions:**
    1. Check quota usage: Console → APIs & Services → Quotas
    2. Request quota increase if legitimate traffic
    3. Review for potential abuse or misconfiguration

    **Quota Limits:**
    - Gemini Live API Active Connections: Check current limit
    - Requests per Minute: Check current limit
    EOT
    mime_type = "text/markdown"
  }
}
```

### B. Environment Variables to Add

**Cloud Run Environment Variables:**
```yaml
# In cloudbuild.yaml, Step 6 (Deploy):
--set-env-vars=\
  PROJECT_ID=${PROJECT_ID},\
  REGION=${_REGION},\
  ENVIRONMENT=production,\
  BUILD_ID=${BUILD_ID},\
  AUDIO_SESSION_TIMEOUT=600,\
  MAX_CONCURRENT_AUDIO_SESSIONS=10,\
  ENABLE_AUDIO_METRICS=true
```

**Application Configuration (`app/config.py`):**
```python
# Add audio-specific settings
class Settings(BaseSettings):
    # ... existing settings ...

    # Audio Configuration
    audio_session_timeout: int = int(os.getenv("AUDIO_SESSION_TIMEOUT", "600"))
    max_concurrent_audio_sessions: int = int(
        os.getenv("MAX_CONCURRENT_AUDIO_SESSIONS", "10")
    )
    audio_buffer_size_bytes: int = int(os.getenv("AUDIO_BUFFER_SIZE_BYTES", "4096"))
    enable_audio_metrics: bool = (
        os.getenv("ENABLE_AUDIO_METRICS", "true").lower() == "true"
    )

    # Audio rate limiting
    audio_daily_limit_minutes: int = int(
        os.getenv("AUDIO_DAILY_LIMIT_MINUTES", "60")  # 1 hour per day for free tier
    )
```

### C. Secrets Management

**Current Secrets (Secret Manager):**
```
✅ oauth-client-id
✅ oauth-client-secret
✅ session-secret-key
```

**No Additional Secrets Needed:**
- Vertex AI uses service account authentication (no API key)
- WebSocket auth uses existing OAuth session tokens
- No third-party audio services requiring credentials

### D. Infrastructure as Code Summary

**Files to Modify:**
1. `infrastructure/terraform/main.tf`
   - Add audio monitoring metrics
   - Add audio alert policies
   - Add Cloud Armor WebSocket exception

2. `infrastructure/terraform/variables.tf`
   - Add audio concurrency variable
   - Add audio timeout variable

3. `cloudbuild.yaml`
   - Update timeout: 600s
   - Update concurrency: 12
   - Add audio environment variables

**Files to Create:**
1. `infrastructure/terraform/modules/audio-service/` (optional module)
2. `infrastructure/terraform/dashboards/audio-monitoring.json`

**No Terraform Apply Required for:**
- Cloud Run configuration (managed by cloudbuild.yaml)
- Environment variables (deployed via gcloud)

**Terraform Apply Required for:**
- Monitoring metrics
- Alert policies
- Dashboard creation

---

## 7. Deployment Checklist

### Pre-Deployment

- [ ] **Vertex AI Quota Request**
  - Request increase: Active Connections (10 → 50)
  - Request increase: Requests per Minute (60 → 200)
  - Allow 2-3 business days for approval

- [ ] **Infrastructure Review**
  - Review Terraform changes in `main.tf`
  - Add audio monitoring metrics
  - Add alert policies
  - Update Cloud Armor rules

- [ ] **Code Review**
  - WebSocket handler implementation complete
  - Audio orchestrator tested
  - Error handling comprehensive
  - Logging structured and complete

- [ ] **Configuration**
  - Update `cloudbuild.yaml` timeout to 600s
  - Update concurrency to 12
  - Add audio environment variables
  - Update `app/config.py` with audio settings

### Deployment Steps

1. **Apply Terraform Changes**
   ```bash
   cd infrastructure/terraform
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

2. **Deploy Application**
   ```bash
   git add .
   git commit -m "IQS-58: Configure Cloud Run for audio WebSocket support"
   git push origin IQS-58-mc-audio-voice

   # Cloud Build trigger will deploy automatically
   ```

3. **Verify Deployment**
   ```bash
   # Check service URL
   gcloud run services describe improv-olympics-app \
     --region=us-central1 \
     --format='value(status.url)'

   # Check revision timeout
   gcloud run revisions describe [REVISION_NAME] \
     --region=us-central1 \
     --format='value(spec.timeout)'
   ```

### Post-Deployment Validation

- [ ] **Health Checks**
  - [ ] `/health` endpoint returns 200
  - [ ] `/ready` endpoint returns 200
  - [ ] `/api/audio/health` returns service status
  - [ ] WebSocket upgrade succeeds

- [ ] **WebSocket Testing**
  - [ ] Connect to `wss://ai4joy.org/ws/audio/{session_id}`
  - [ ] Send audio message (base64 PCM16)
  - [ ] Receive audio response
  - [ ] Verify bidirectional streaming
  - [ ] Test graceful disconnect

- [ ] **Monitoring**
  - [ ] Audio dashboard visible in Cloud Console
  - [ ] Metrics populating:
    - Active connections
    - Audio latency
    - Session duration
  - [ ] Alerts configured:
    - High error rate
    - Quota exceeded
    - High latency

- [ ] **Performance Testing**
  - [ ] Single session latency < 500ms (p95)
  - [ ] 10 concurrent sessions stable
  - [ ] No memory leaks (24-hour test)
  - [ ] CPU utilization < 70% at peak

### Rollback Plan

If issues occur post-deployment:

```bash
# Option 1: Traffic rollback (gradual)
gcloud run services update-traffic improv-olympics-app \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# Option 2: Instant rollback (emergency)
gcloud run services rollback improv-olympics-app \
  --region=us-central1

# Option 3: Terraform rollback
cd infrastructure/terraform
git checkout HEAD~1 main.tf
terraform apply
```

---

## 8. Cost Optimization Recommendations

### A. Short-Term Optimizations (Immediate)

1. **Implement Usage-Based Billing**
   - Track audio minutes per user
   - Enforce tier limits (free: 60min/month, premium: unlimited)
   - Alert users at 80% of quota

2. **Smart Idle Timeout**
   ```python
   # File: app/audio/websocket_handler.py

   IDLE_TIMEOUT_SECONDS = 30  # Disconnect after 30s silence

   async def monitor_activity(self, session_id: str):
       last_activity = time.time()
       while self.is_session_active(session_id):
           if time.time() - last_activity > IDLE_TIMEOUT_SECONDS:
               await self.disconnect(session_id)
               break
           await asyncio.sleep(5)
   ```

3. **Batch Audio Processing**
   - Send audio in 100ms chunks (not 10ms)
   - Reduces API calls by 10x
   - Minimal latency impact

### B. Medium-Term Optimizations (1-3 months)

1. **Audio Compression**
   - Use Opus codec instead of PCM16
   - 10-20x size reduction
   - Lower egress costs

2. **CDN for Static Audio Assets**
   - Cache welcome messages
   - Pre-synthesized common responses
   - Reduces Live API costs

3. **Regional Scaling**
   - Scale down min_instances to 0 during low-traffic hours (2am-6am UTC)
   - Save ~$2/day ($60/month)
   - Accept cold start penalty for off-hours

### C. Long-Term Optimizations (3-6 months)

1. **Separate Audio Service**
   - Dedicated Cloud Run service for audio
   - Independent scaling from main app
   - Optimized concurrency (5-8 for audio)

2. **Firestore → Cloud SQL Migration**
   - For high-volume session data
   - Better query performance
   - Cost-effective at scale (>10K sessions/month)

3. **Audio Quality Tiers**
   - Free: 16kHz, basic voice
   - Premium: 24kHz, enhanced voice
   - 30-40% cost savings on free tier

---

## Appendix A: Linear Ticket Deployment Section

**Copy this into the IQS-58 Linear ticket:**

```markdown
## Deployment Configuration

### Infrastructure Changes Required

**Terraform (`infrastructure/terraform/main.tf`):**
- ✅ Add audio monitoring metrics (log-based)
- ✅ Add audio alert policies (quota, error rate)
- ✅ Update Cloud Armor rules (WebSocket exception)

**Cloud Build (`cloudbuild.yaml`):**
- ⚠️ Update `--timeout=600s` (from 300s)
- ⚠️ Update `--concurrency=12` (from 20)
- ⚠️ Add audio environment variables

**Application Config (`app/config.py`):**
- ✅ Add `audio_session_timeout` setting
- ✅ Add `max_concurrent_audio_sessions` setting

### Cloud Run Configuration

**Current:**
```yaml
CPU: 2 vCPU
Memory: 2Gi
Timeout: 300s
Concurrency: 20
```

**Updated:**
```yaml
CPU: 2 vCPU (no change)
Memory: 2Gi (no change)
Timeout: 600s (CHANGED)
Concurrency: 12 (CHANGED)
```

**Rationale:**
- 600s timeout allows 10-minute conversations
- Lower concurrency (12) ensures quality for resource-intensive audio processing
- 2 vCPU / 2Gi sufficient for 10-12 concurrent sessions per instance

### Monitoring Setup

**Metrics to Track:**
1. Active WebSocket connections (gauge)
2. Audio session duration (histogram)
3. Audio processing latency (histogram)
4. Audio error rate (counter)

**Alerts:**
1. High audio error rate (>5% for 5min)
2. Vertex AI quota exceeded
3. High audio latency (p95 > 3s)

**Dashboard:** Audio Real-Time Monitoring (auto-created via Terraform)

### Cost Estimates

**Per Audio Session (5-10 minutes):**
- Vertex AI Live API: $0.06 - $0.11
- Cloud Run compute: $0.03
- Network egress: $0.01
- **Total: $0.10 - $0.15 per session**

**Monthly (50 sessions/day):**
- Sessions: 1,500 × $0.12 = $180
- Idle instances: $137
- **Total: ~$317/month**

### Pre-Deployment Checklist

- [ ] Request Vertex AI quota increase (Active Connections: 50, RPM: 200)
- [ ] Review Terraform changes (`terraform plan`)
- [ ] Update cloudbuild.yaml configuration
- [ ] Add audio settings to app/config.py
- [ ] Create audio monitoring dashboard JSON
- [ ] Configure budget alerts ($500/month threshold)

### Deployment Steps

1. Apply Terraform changes (metrics, alerts, dashboard)
2. Push code to trigger Cloud Build
3. Verify deployment (check timeout, concurrency)
4. Test WebSocket connection
5. Monitor initial sessions for errors

### Rollback Plan

If issues detected:
```bash
# Rollback to previous revision
gcloud run services rollback improv-olympics-app \
  --region=us-central1
```

### Post-Deployment Validation

- [ ] WebSocket connects successfully
- [ ] Audio streaming bidirectional
- [ ] Latency < 500ms (p95)
- [ ] No quota errors in logs
- [ ] Dashboard showing metrics
- [ ] Alerts configured and tested
```

---

## Appendix B: Cost Breakdown (Detailed)

### Vertex AI Live API Pricing

**Gemini 2.0 Flash Live API (as of January 2025):**
```
Audio Input (Transcription):
  - $0.0015 per 1,000 characters
  - Example: 5,000 chars = $0.0075

Audio Output (Synthesis):
  - $0.006 per 1,000 characters
  - Example: 5,000 chars = $0.03

Total per 5-min session (10K chars):
  Input: $0.015
  Output: $0.06
  Total: $0.075
```

### Cloud Run Compute Pricing (us-central1)

**CPU Time:**
```
Rate: $0.00002400 per vCPU-second
2 vCPU × 600s = 1,200 vCPU-seconds
Cost: 1,200 × $0.000024 = $0.0288
```

**Memory:**
```
Rate: $0.00000250 per GiB-second
2 GiB × 600s = 1,200 GiB-seconds
Cost: 1,200 × $0.0000025 = $0.003
```

**Requests:**
```
Rate: $0.40 per million requests
1 WebSocket connection = 1 request
Cost: 1 × $0.0000004 = negligible
```

**Total Cloud Run per session:** $0.032

### Network Egress

**Audio Data Transfer:**
```
Avg session: 5 minutes
Audio: 24kHz PCM16 = 48KB/s
Total: 48KB/s × 300s = 14.4 MB

Egress rate: $0.12 per GB (0-10 TB/month)
Cost: 0.0144 GB × $0.12 = $0.0017 per session
```

**Firestore Operations:**
```
User session writes: ~10 writes per session
Cost: 10 × $0.00000036 = $0.0000036 (negligible)
```

### Total Cost Per Session

```
Vertex AI:      $0.075
Cloud Run:      $0.032
Egress:         $0.002
Firestore:      ~$0.000
----------------------------
Total:          $0.109 ≈ $0.11 per 5-minute session
```

### Monthly Costs at Scale

**Scenario: 50 sessions/day (moderate usage)**
```
Sessions per month: 50 × 30 = 1,500
Session costs: 1,500 × $0.11 = $165

Cloud Run (always-on):
  Min instance: 2 vCPU × 86,400s/day × 30 days
  CPU: 5,184,000 × $0.000024 = $124
  Memory: 5,184,000 × $0.0000025 = $13
  Subtotal: $137

Additional instances (peak hours):
  Avg 2 extra instances × 8 hours/day
  Daily: 2 × 2 vCPU × 28,800s × ($0.000024 + memory) ≈ $2.20
  Monthly: $2.20 × 30 = $66

Firestore: $10 (session storage, user profiles)
Monitoring: $5 (log ingestion)
Network: Included above

----------------------------
Total Monthly: $165 + $137 + $66 + $15 = $383
```

---

**Document Prepared By:** GCP DevOps Engineer (AI Assistant)
**Date:** November 29, 2025
**Version:** 1.0
**For:** IQS-58 - MC Agent Voice Implementation
