# IQS-60 Phase 3 Infrastructure Gap Analysis - ai4joy

**Analysis Date:** 2025-11-30
**Target:** 50 Concurrent Audio Users
**Cost Target:** <$500/month at scale
**Performance Target:** No latency degradation from Phase 2

---

## Executive Summary

**Overall Assessment:** The current ai4joy infrastructure is **PARTIALLY READY** for 50 concurrent audio users. Critical autoscaling and cost monitoring capabilities exist in Terraform, but specific configurations for audio workload scaling and comprehensive cost dashboards are **MISSING**.

**Recommendation:** Infrastructure modifications are **REQUIRED** before Phase 3 launch to meet IQS-60 acceptance criteria.

---

## 1. Current Infrastructure Status

### ✅ Existing Capabilities

**Cloud Run Service (main.tf)**
```terraform
Service: improv-olympics-app
Region: us-central1
CPU: 2 vCPU (configurable via var.cloud_run_cpu)
Memory: 2Gi (configurable via var.cloud_run_memory)
Timeout: 300s
Concurrency: Variable (via cloudbuild.yaml: _CONCURRENCY: '20')

Autoscaling:
  min_instance_count = var.min_instances  # Default: 1
  max_instance_count = var.max_instances  # Default: 10
```

**Monitoring Infrastructure (main.tf lines 760-1394)**
- ✅ Log-based metrics (scene_turn_latency, token_usage, sentiment_score, agent_invocations)
- ✅ Cloud Monitoring Dashboard with 6 widgets
- ✅ Alert policies (high_error_rate, service_unavailable, high_latency_p95, session_spike, firestore_write_failures)
- ✅ Uptime checks on /health endpoint

**Load Balancing**
- ✅ Global HTTPS Load Balancer configured
- ✅ Cloud Armor security policy with rate limiting
- ✅ Session affinity (GENERATED_COOKIE)

**Cost Tracking Components**
- ✅ Log retention policies (variables.tf line 86-90)
- ⚠️ Budget alerts commented out (requires billing account permissions)

---

## 2. Infrastructure Gaps for 50 Concurrent Audio Users

### 🔴 CRITICAL GAPS

#### Gap 1: Audio-Specific Autoscaling Configuration

**Current State:**
```terraform
# variables.tf lines 27-36
variable "min_instances" {
  description = "Minimum number of Cloud Run instances (keep warm)"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}
```

**Issue:**
- Default max_instances = 10 is **INSUFFICIENT** for 50 concurrent audio users
- Audio workload requires concurrency of 10-15 per instance (not 20)
- Current timeout (300s) is **TOO SHORT** for 10-minute audio sessions

**Capacity Analysis:**
- **Current capacity:** 10 instances × 20 concurrency = 200 concurrent sessions (text chat)
- **Audio capacity needed:** 50 users ÷ 10 audio sessions/instance = 5 instances minimum
- **Recommended:** min_instances=2, max_instances=15 for audio workload

**Required Changes:**
1. **Increase timeout for WebSocket audio:**
   ```terraform
   timeout = "600s"  # 10 minutes for audio sessions
   ```

2. **Adjust concurrency for audio workload:**
   ```bash
   # cloudbuild.yaml line 307
   _CONCURRENCY: '10'  # Lower for audio processing
   ```

3. **Update scaling variables:**
   ```terraform
   variable "audio_min_instances" {
     description = "Min instances for audio workload"
     type        = number
     default     = 2  # Eliminate cold starts
   }

   variable "audio_max_instances" {
     description = "Max instances for audio workload"
     type        = number
     default     = 15  # Support 150 concurrent sessions
   }
   ```

**Impact if not fixed:** Audio sessions will experience cold starts (3-5s delay) and connection timeouts during peak usage.

---

#### Gap 2: Cost Monitoring Dashboards

**Current State:**
- ✅ Monitoring dashboard exists (main.tf lines 1005-1228)
- ❌ **NO cost-specific metrics or widgets**
- ❌ **NO Vertex AI token usage tracking**
- ❌ **NO audio-specific cost breakdown**

**Missing Capabilities:**
1. Real-time cost tracking dashboard
2. Vertex AI ADK API token consumption metrics
3. Cost per audio session calculation
4. Daily/monthly cost projections
5. Budget burn-rate alerts

**Required Changes:**

**Add Cost Monitoring Widgets to Dashboard (Terraform):**
```terraform
# NEW: Add to google_monitoring_dashboard.improv_dashboard
{
  xPos   = 0
  yPos   = 12
  width  = 4
  height = 4
  widget = {
    title = "Estimated Daily Cost"
    scorecard = {
      timeSeriesQuery = {
        timeSeriesFilter = {
          filter = "metric.type=\"logging.googleapis.com/user/token_usage\""
          aggregation = {
            alignmentPeriod = "86400s"  # 1 day
            perSeriesAligner = "ALIGN_SUM"
          }
        }
      }
      sparkChartView = {
        sparkChartType = "SPARK_BAR"
      }
    }
  }
}
```

**Add Budget Alert Policy:**
```terraform
resource "google_monitoring_alert_policy" "daily_cost_threshold" {
  display_name = "Daily Cost Threshold Exceeded"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Daily cost > $20 (projected $600/month)"

    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"logging.googleapis.com/user/token_usage\"",
        "resource.type=\"cloud_run_revision\""
      ])
      duration        = "3600s"
      comparison      = "COMPARISON_GT"
      threshold_value = 200000  # ~$20 in tokens

      aggregations {
        alignment_period = "86400s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "Daily token usage exceeds $20, projecting to $600/month. Check for unexpected usage spikes or adjust quotas."
    mime_type = "text/markdown"
  }
}
```

**Impact if not fixed:** Cannot track progress toward $500/month cost target (AC7). Risk of budget overruns without early warning.

---

#### Gap 3: Load Testing Infrastructure

**Current State:**
- ✅ Load test exists: `/tests/load_testing/test_load_performance.py`
- ❌ **NOT configured for 50 concurrent audio sessions**
- ❌ **NO audio-specific WebSocket load tests**
- ❌ **NO automated load testing in CI/CD**

**Current Load Test Coverage:**
```python
# tests/load_testing/test_load_performance.py
- test_concurrent_session_creation: 10 users (text)
- test_concurrent_turn_execution: 10 users (text)
- test_full_session_flow_under_load: 5 users × 15 turns (text)
```

**Missing Audio Load Tests:**
1. **50 concurrent WebSocket audio connections**
2. **Sustained 10-minute audio sessions**
3. **Audio latency measurement (VAD + ADK response time)**
4. **Bandwidth consumption tracking**
5. **Connection stability over time**

**Required Changes:**

**Create Audio Load Test Suite:**
```python
# tests/load_testing/test_audio_load.py

@pytest.mark.load
@pytest.mark.asyncio
async def test_50_concurrent_audio_sessions():
    """
    AC5: 50 users can use audio concurrently

    Validates:
    - 50 WebSocket connections established
    - All connections stable for 10 minutes
    - p95 latency < 1 second (audio response time)
    - Error rate < 1%
    """
    # Test implementation needed

@pytest.mark.load
@pytest.mark.asyncio
async def test_audio_latency_no_degradation():
    """
    AC6: No latency degradation from Phase 2

    Baseline: Phase 2 p95 latency = X seconds
    Target: Phase 3 p95 latency ≤ X seconds at 50 concurrent
    """
    # Test implementation needed
```

**Impact if not fixed:** Cannot validate AC5 (50 concurrent users) before production deployment. Risk of performance issues discovered in production.

---

### ⚠️ MEDIUM PRIORITY GAPS

#### Gap 4: Audio-Specific SLO/SLA Definitions

**Current State:**
- ✅ General SLOs exist (availability, latency, error rate)
- ❌ **NO audio quality SLOs** (packet loss, jitter, audio latency)
- ❌ **NO WebSocket connection stability metrics**

**Missing Metrics:**
1. Audio packet loss percentage
2. Audio jitter/latency distribution
3. WebSocket connection duration
4. Reconnection rate
5. Voice Activity Detection (VAD) accuracy

**Required Changes:**
```terraform
# Add audio quality log-based metric
resource "google_logging_metric" "audio_quality" {
  name    = "audio_quality_score"
  project = var.project_id
  filter  = "jsonPayload.event=\"audio_session\" AND jsonPayload.quality_score != null"

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    unit         = "1"
    display_name = "Audio Quality Score"

    labels {
      key         = "session_id"
      value_type  = "STRING"
      description = "Audio session identifier"
    }
  }

  value_extractor = "EXTRACT(jsonPayload.quality_score)"

  label_extractors = {
    session_id = "EXTRACT(jsonPayload.session_id)"
  }

  bucket_options {
    linear_buckets {
      num_finite_buckets = 10
      width              = 0.1
      offset             = 0
    }
  }
}
```

**Impact if not fixed:** Cannot measure audio quality degradation. Risk of poor user experience without detection.

---

#### Gap 5: Separate Audio Service Isolation

**Current State:**
- ✅ Single Cloud Run service handles text + audio
- ❌ **NO separation between text and audio workloads**

**Trade-Off Analysis:**

**Option A: Keep Single Service (Current)**
- ✅ Simpler deployment pipeline
- ✅ Shared authentication and session state
- ❌ Audio workload can impact text chat performance
- ❌ Cannot optimize autoscaling separately

**Option B: Separate Audio Service**
- ✅ Isolated failure domain
- ✅ Independent scaling (audio: 10 concurrency, text: 80 concurrency)
- ✅ Optimized timeout (audio: 600s, text: 30s)
- ❌ More complex infrastructure
- ❌ Requires path-based routing in load balancer

**Recommendation:** **Defer to Phase 4** unless audio workload impacts text performance. Single service is acceptable for 50 concurrent users if properly configured.

**Required Changes (if implementing):**
- New Cloud Run service: `improv-olympics-audio`
- Load balancer path routing: `/ws/audio/*` → audio service
- Shared Firestore and Secret Manager access

---

### ✅ LOW PRIORITY / NICE-TO-HAVE

#### Gap 6: Regional Failover

**Current State:**
- Single region deployment (us-central1)
- No multi-region failover

**Recommendation:** **Defer to future phases**. Not required for 50 concurrent users.

---

## 3. Cost Analysis for 50 Concurrent Users

### Baseline Cost Estimate (Current Docs)

**From CAPACITY_PLANNING.md:**
```
Cost per session (15 turns, 5-10 minutes):
- Gemini API: $0.00195
- Firestore: $0.000066
- Cloud Run: $0.00076
Total: ~$0.003 per session
```

**Audio Session Cost Estimate:**
```
Audio session (10 minutes):
- Vertex AI ADK Live API: ~$0.08-0.15 (streaming audio tokens)
- Firestore: $0.000066 (minimal)
- Cloud Run: $0.0015 (2x longer session)
Total: ~$0.10 per audio session
```

**50 Concurrent Users Scenario:**
```
Assumptions:
- 50 concurrent users
- Average session: 10 minutes
- 6 sessions per user per hour (600 minutes = 6 × 10min sessions)
- Peak usage: 4 hours per day

Daily calculations:
- Total sessions: 50 users × 6 sessions = 300 sessions/day
- Total cost: 300 × $0.10 = $30/day
- Monthly cost: $30 × 30 = $900/month

Cloud Run baseline (min instances):
- 2 min instances × 730 hours × ($0.00002400 CPU + $0.00000250 × 2GB memory)
- ~$40/month for always-on instances

Total estimated: $900 + $40 = $940/month
```

**❌ EXCEEDS $500/month TARGET**

### Cost Optimization Required

**To meet <$500/month target:**

1. **Reduce Vertex AI costs (70% of spend):**
   - Request enterprise pricing discount (15-25% off)
   - Implement response caching for common patterns
   - Optimize token usage (reduce context window)
   - Target: $630/month → $500/month

2. **Right-size Cloud Run:**
   - Reduce min_instances from 2 to 1 during off-peak
   - Use Committed Use Discounts (20% discount)
   - Target: Save $10-15/month

3. **Usage controls:**
   - Enforce session limits (10 sessions/user/day)
   - Implement time-based quotas (4 hours peak usage)
   - Auto-terminate idle sessions

**Revised Estimate with Optimizations:**
```
Vertex AI ADK (with 20% discount): $720/month
Cloud Run (with CUD): $35/month
Firestore: $5/month
Monitoring/Logging: $20/month
Total: ~$780/month (still over target)
```

**Conclusion:** **$500/month target is AGGRESSIVE** for 50 concurrent audio users. Recommend:
- **Phase 3 target:** $800/month (achievable with optimizations)
- **Future goal:** $500/month (requires usage reduction or enterprise discounts)

---

## 4. Required File Modifications

### Critical Priority

#### 1. `/infrastructure/terraform/variables.tf`

**ADD:**
```terraform
# Audio-specific scaling variables
variable "audio_enabled" {
  description = "Enable audio workload optimizations"
  type        = bool
  default     = false
}

variable "audio_timeout" {
  description = "Timeout for audio sessions (seconds)"
  type        = number
  default     = 600  # 10 minutes
}

variable "audio_concurrency" {
  description = "Max concurrent audio sessions per instance"
  type        = number
  default     = 10
}

variable "audio_min_instances" {
  description = "Minimum Cloud Run instances for audio workload"
  type        = number
  default     = 2
}

variable "audio_max_instances" {
  description = "Maximum Cloud Run instances for audio workload"
  type        = number
  default     = 15
}
```

#### 2. `/infrastructure/terraform/main.tf`

**MODIFY Cloud Run service (lines 311-444):**
```terraform
resource "google_cloud_run_v2_service" "improv_app" {
  # ... existing config ...

  template {
    # ... existing config ...

    scaling {
      min_instance_count = var.audio_enabled ? var.audio_min_instances : var.min_instances
      max_instance_count = var.audio_enabled ? var.audio_max_instances : var.max_instances
    }

    # ... rest of template ...

    timeout = var.audio_enabled ? "${var.audio_timeout}s" : "300s"
  }
}
```

**ADD cost monitoring alert (after line 1351):**
```terraform
# Alert: Daily cost exceeds budget
resource "google_monitoring_alert_policy" "daily_cost_alert" {
  display_name = "Daily Cost Alert - Audio Workload"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Token usage indicates >$20/day spend"

    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"logging.googleapis.com/user/token_usage\"",
        "resource.type=\"cloud_run_revision\""
      ])
      duration        = "3600s"
      comparison      = "COMPARISON_GT"
      threshold_value = 200000  # Approximate $20 in tokens

      aggregations {
        alignment_period = "86400s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = var.notification_channels

  alert_strategy {
    auto_close = "86400s"
  }

  documentation {
    content   = "Daily Vertex AI token usage exceeds $20 threshold (projects to $600/month). Review audio session usage and optimize token consumption."
    mime_type = "text/markdown"
  }

  depends_on = [module.project_services]
}
```

**ADD audio quality metric (after line 1002):**
```terraform
# Log-based metric for audio session quality
resource "google_logging_metric" "audio_session_quality" {
  name    = "audio_session_quality"
  project = var.project_id
  filter  = "jsonPayload.event=\"audio_session_complete\" AND jsonPayload.quality_score != null"

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "DISTRIBUTION"
    unit         = "1"
    display_name = "Audio Session Quality Score"

    labels {
      key         = "session_type"
      value_type  = "STRING"
      description = "Session type (practice, coaching, etc.)"
    }
  }

  value_extractor = "EXTRACT(jsonPayload.quality_score)"

  label_extractors = {
    session_type = "EXTRACT(jsonPayload.session_type)"
  }

  bucket_options {
    linear_buckets {
      num_finite_buckets = 10
      width              = 0.1
      offset             = 0
    }
  }

  depends_on = [module.project_services]
}
```

#### 3. `/cloudbuild.yaml`

**MODIFY concurrency (line 307):**
```yaml
substitutions:
  # ... existing substitutions ...
  _CONCURRENCY: '10'  # Changed from 20 for audio workload
```

#### 4. Create `/tests/load_testing/test_audio_load.py`

**NEW FILE:**
```python
"""
IQS-60 Phase 3 Audio Load Testing

Tests 50 concurrent audio sessions to validate:
- AC5: 50 users can use audio concurrently
- AC6: No latency degradation from Phase 2
- AC7: Total cost < $500/month at scale
"""

import pytest
import asyncio
import websockets
import time
import statistics
from typing import List, Dict

# Test implementation for 50 concurrent WebSocket audio sessions
# See full implementation requirements in Gap Analysis
```

---

## 5. Deployment Checklist

### Pre-Deployment (Before IQS-60 Phase 3 Launch)

- [ ] **Update Terraform variables** (`variables.tf`) with audio-specific settings
- [ ] **Modify Cloud Run configuration** (`main.tf`) to use conditional audio scaling
- [ ] **Add cost monitoring alerts** (`main.tf`) for budget tracking
- [ ] **Add audio quality metrics** (`main.tf`) for SLO tracking
- [ ] **Update cloudbuild.yaml** concurrency to 10 for audio workload
- [ ] **Create audio load tests** (`tests/load_testing/test_audio_load.py`)
- [ ] **Run load tests** with 50 concurrent WebSocket connections
- [ ] **Validate cost projections** using Cloud Billing reports
- [ ] **Set up notification channels** for cost and latency alerts
- [ ] **Update documentation** with audio-specific runbooks

### Post-Deployment Validation

- [ ] **Monitor dashboard** shows audio-specific metrics
- [ ] **Cost tracking** functional (daily cost visible in dashboard)
- [ ] **Alerts trigger correctly** (test by exceeding thresholds)
- [ ] **Autoscaling works** (verify instances scale 2 → 5 → 15 under load)
- [ ] **p95 latency < 1 second** for audio sessions at 50 concurrent users
- [ ] **Error rate < 1%** during sustained 50-user load test
- [ ] **Cost < $800/month** (revised target with optimizations)

---

## 6. Deferred Infrastructure (Phase 4+)

The following infrastructure improvements are **NOT REQUIRED** for IQS-60 Phase 3 but should be considered for future phases:

1. **Separate Cloud Run service for audio workload**
   - Priority: MEDIUM
   - Benefit: Isolated failure domain, optimized scaling
   - Complexity: Moderate (requires load balancer path routing)

2. **Regional failover and multi-region deployment**
   - Priority: LOW
   - Benefit: Higher availability, lower latency for global users
   - Complexity: High (requires multi-region Firestore, traffic routing)

3. **Response caching with semantic similarity**
   - Priority: MEDIUM
   - Benefit: 15-20% cost reduction on Vertex AI
   - Complexity: Moderate (requires embedding model + cache layer)

4. **Predictive autoscaling**
   - Priority: LOW
   - Benefit: Reduced cold starts during known peak hours
   - Complexity: Moderate (requires historical usage analysis)

5. **Advanced cost allocation and chargebacks**
   - Priority: LOW
   - Benefit: Granular cost tracking per user/session
   - Complexity: Low (requires additional labels and dashboards)

---

## 7. Recommendations Summary

### MUST DO (Before Phase 3 Launch)

1. ✅ **Modify Terraform configuration** for audio-specific autoscaling
2. ✅ **Add cost monitoring dashboard** with token usage and daily cost tracking
3. ✅ **Create audio load tests** for 50 concurrent WebSocket sessions
4. ✅ **Update cloudbuild.yaml** concurrency to 10 for audio workload
5. ✅ **Set up budget alerts** at $20/day threshold

### SHOULD DO (Phase 3 Sprint)

1. ⚠️ **Run baseline load test** to establish Phase 2 p95 latency
2. ⚠️ **Implement audio quality logging** for session quality scores
3. ⚠️ **Optimize Vertex AI token usage** to reduce costs
4. ⚠️ **Request Vertex AI enterprise pricing** (15-25% discount)

### CAN DEFER (Phase 4)

1. ⏸️ **Separate Cloud Run service** for audio isolation
2. ⏸️ **Multi-region deployment** for global failover
3. ⏸️ **Response caching** for cost optimization
4. ⏸️ **Predictive autoscaling** for cold start reduction

---

## 8. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Cost exceeds $500/month target** | HIGH | HIGH | Revised target to $800/month with optimizations. Request enterprise pricing. |
| **Autoscaling insufficient for 50 users** | MEDIUM | HIGH | Update max_instances to 15. Run load tests before launch. |
| **Audio latency degrades under load** | MEDIUM | MEDIUM | Reduce concurrency to 10. Monitor p95 latency continuously. |
| **No cost visibility during rollout** | HIGH | MEDIUM | Add cost monitoring alerts before Phase 3 launch. |
| **Load tests not audio-specific** | HIGH | MEDIUM | Create new audio load test suite with WebSocket connections. |

---

## Conclusion

The current ai4joy infrastructure provides a **SOLID FOUNDATION** for 50 concurrent audio users, but **CRITICAL MODIFICATIONS ARE REQUIRED** to meet IQS-60 acceptance criteria:

1. **Autoscaling configuration** must be updated for audio workload (timeout, concurrency, instance limits)
2. **Cost monitoring dashboards** must be created to track progress toward <$500/month target
3. **Audio-specific load tests** must be written and executed to validate 50 concurrent users
4. **Cost target** should be revised to ~$800/month (realistic with optimizations)

**Estimated Effort:**
- Terraform modifications: 4-6 hours
- Audio load test creation: 8-12 hours
- Load testing execution & tuning: 8-12 hours
- Documentation updates: 4 hours
- **Total: 24-34 hours (3-4 sprint days)**

**Timeline:**
- Week 1: Terraform modifications + cost monitoring
- Week 2: Audio load test creation + baseline testing
- Week 3: Load testing at scale + performance tuning
- Week 4: Production deployment + validation

This analysis should be shared with the team to plan IQS-60 Phase 3 infrastructure work.
