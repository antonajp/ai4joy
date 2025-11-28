# GCP Architecture Decision Matrix: Real-Time Audio Deployment

## Quick Reference: Deployment Options Comparison

| Factor | Option 1: Same Cloud Run Service | Option 2: Separate Cloud Run Service ✅ | Option 3: Separate GCP Project |
|--------|----------------------------------|----------------------------------------|--------------------------------|
| **Complexity** | Low (single service) | Medium (two services, one LB) | High (separate project, separate Terraform) |
| **Isolation** | ❌ Shared resources | ✅ Isolated failure domain | ✅✅ Complete isolation |
| **Scaling** | ⚠️ Compromised (same concurrency) | ✅ Optimized per workload | ✅ Optimized per workload |
| **Cost** | Lowest (~$9,500/month) | Medium (~$10,500/month) | Highest (~$11,200/month) |
| **Operational Overhead** | Low (single deployment) | Medium (two deployments, shared infra) | High (separate monitoring, separate billing) |
| **Time to Deploy** | 1 week | 2-3 weeks | 3-4 weeks |
| **Blast Radius** | ❌ High (audio issues affect REST) | ✅ Low (audio issues isolated) | ✅✅ Minimal (completely separate) |
| **Authentication** | ✅ Shared IAP/OAuth | ✅ Shared IAP/OAuth | ⚠️ Separate (more complex) |
| **Firestore Access** | ✅ Single database | ✅ Single database | ⚠️ Cross-project access needed |
| **Monitoring** | Simple (one dashboard) | Medium (two services, one project) | Complex (separate dashboards) |
| **Billing** | Single bill | Single bill | Separate bill (useful for cost allocation) |
| **Best For** | Small scale (<100 concurrent) | **Production (100-5000 concurrent)** ✅ | Enterprise (>5000 concurrent, compliance) |

**Recommendation: Option 2 - Separate Cloud Run Service (Same Project)**

---

## Detailed Decision Criteria

### 1. Performance & Scalability

#### Option 1: Same Cloud Run Service
**Configuration:**
```yaml
Service: ai4joy-unified-service
Concurrency: 40 (compromise between REST and WebSocket)
  - REST optimal: 80-100
  - WebSocket optimal: 10-20
  - Compromise: 40 (suboptimal for both)

Impact:
  - REST API: 50% less efficient scaling
  - WebSocket: 2x higher resource usage per connection
  - Result: Higher costs, worse performance
```

**Scaling Behavior:**
- WebSocket connections trigger scaling intended for REST API
- REST traffic shares capacity with long-lived WebSocket connections
- Autoscaling thrashes between workload types

**Verdict:** ❌ Not recommended for production

---

#### Option 2: Separate Cloud Run Service ✅
**Configuration:**
```yaml
Service 1: ai4joy-api-service
  Concurrency: 80 (optimized for REST)
  Timeout: 30s
  CPU: 1 vCPU
  Memory: 512Mi

Service 2: ai4joy-audio-service
  Concurrency: 15 (optimized for WebSocket)
  Timeout: 3600s
  CPU: 2 vCPU
  Memory: 1Gi
```

**Scaling Behavior:**
- Independent autoscaling based on workload characteristics
- REST API scales aggressively for short bursts
- Audio service scales conservatively for stable connections
- No resource contention

**Verdict:** ✅ Recommended for production

---

#### Option 3: Separate GCP Project
**Configuration:**
Same as Option 2, but in separate project:
```yaml
Project 1: ai4joy-production (existing REST API)
Project 2: ai4joy-audio-production (new audio service)
```

**Scaling Behavior:**
- Same as Option 2
- Additional complexity: cross-project Firestore access requires VPC peering or public endpoints

**Verdict:** ✅ Good for enterprise scale (>5000 concurrent sessions)

---

### 2. Cost Analysis

#### Total Cost of Ownership (Monthly)

| Component | Option 1 | Option 2 ✅ | Option 3 |
|-----------|----------|-----------|----------|
| **Cloud Run - REST API** | Included in unified | $500 | $500 |
| **Cloud Run - Audio** | $2,100 (inefficient) | $1,770 (optimized) | $1,770 |
| **Load Balancer** | $35 (single backend) | $58 (dual backend) | $70 (two LBs) |
| **Vertex AI** | $8,275 | $8,275 | $8,275 |
| **Firestore** | $48 | $48 | $60 (cross-project) |
| **Logging** | $250 | $250 | $300 (separate project) |
| **Monitoring** | $129 | $129 | $200 (separate dashboards) |
| **Networking** | $0 | $0 | $25 (VPC peering/egress) |
| **TOTAL** | **$10,837** | **$10,530** ✅ | **$11,200** |

**Winner:** Option 2 (saves $307/month vs Option 1, $670/month vs Option 3)

**Cost Drivers:**
- Option 1: Higher Cloud Run costs due to inefficient concurrency
- Option 2: Optimal balance
- Option 3: Additional networking and project overhead

---

### 3. Operational Complexity

#### Deployment Pipeline Complexity

**Option 1: Same Service**
```bash
# Single deployment
gcloud run deploy ai4joy-unified-service --image=IMAGE

# Pros: Simple
# Cons: Risky (single point of failure), no independent rollback
```

**Option 2: Separate Services ✅**
```bash
# Two deployments, same project
gcloud run deploy ai4joy-api-service --image=API_IMAGE
gcloud run deploy ai4joy-audio-service --image=AUDIO_IMAGE

# Pros: Independent deployments, shared project resources
# Cons: Two CI/CD pipelines (manageable)
```

**Option 3: Separate Projects**
```bash
# Two deployments, two projects
gcloud run deploy ai4joy-api-service --image=API_IMAGE --project=ai4joy-production
gcloud run deploy ai4joy-audio-service --image=AUDIO_IMAGE --project=ai4joy-audio-production

# Pros: Complete isolation
# Cons: Separate Terraform state, separate monitoring, cross-project IAM
```

**Winner:** Option 2 (balance of simplicity and isolation)

---

#### Monitoring & Alerting

**Option 1: Same Service**
- ✅ Single dashboard
- ❌ Cannot differentiate REST vs WebSocket metrics
- ❌ Alerts trigger for mixed workload (false positives)

**Option 2: Separate Services ✅**
- ✅ Dedicated dashboard per service
- ✅ Workload-specific alerts (e.g., WebSocket disconnect rate)
- ✅ Same project (unified view in Cloud Console)
- ⚠️ Two dashboards to manage

**Option 3: Separate Projects**
- ❌ Completely separate dashboards
- ❌ No unified view across projects
- ❌ Cross-project monitoring queries complex
- ✅ Clear cost attribution per project

**Winner:** Option 2 (best monitoring granularity without complexity)

---

### 4. Failure Isolation & Reliability

#### Blast Radius Analysis

**Scenario: Audio Service Memory Leak**

| Option | Impact | Recovery Time |
|--------|--------|---------------|
| **Option 1** | ❌ Entire service OOMKilled → REST API down | 5-10 minutes (full restart) |
| **Option 2** | ✅ Audio service OOMKilled → REST API unaffected | 1-2 minutes (audio only) |
| **Option 3** | ✅ Audio service OOMKilled → REST API unaffected | 1-2 minutes (audio only) |

**Scenario: Vertex AI Quota Exhausted**

| Option | Impact | Recovery Time |
|--------|--------|---------------|
| **Option 1** | ⚠️ Audio requests fail, may impact REST performance | 15 minutes (quota increase) |
| **Option 2** | ✅ Audio requests fail, REST unaffected | 15 minutes (quota increase) |
| **Option 3** | ✅ Audio requests fail, REST unaffected | 15 minutes (quota increase) |

**Scenario: DDoS Attack on Audio Endpoint**

| Option | Impact | Recovery Time |
|--------|--------|---------------|
| **Option 1** | ❌ Entire service overwhelmed | 10-20 minutes (scale limits, Cloud Armor) |
| **Option 2** | ✅ Audio service scaled to max, REST unaffected | 5 minutes (Cloud Armor blocks) |
| **Option 3** | ✅ Audio project scaled to max, REST completely isolated | 5 minutes (Cloud Armor blocks) |

**Winner:** Options 2 & 3 (tie for reliability, Option 2 wins on simplicity)

---

### 5. Security & Compliance

#### IAM & Access Control

**Option 1: Same Service**
```yaml
Service Account: unified-service@project.iam.gserviceaccount.com
Permissions:
  - roles/aiplatform.user (for audio)
  - roles/datastore.user (for both)
  - roles/secretmanager.secretAccessor (all secrets)

Risk: Overprivileged (single SA has access to all resources)
```

**Option 2: Separate Services ✅**
```yaml
API Service Account: api-service@project.iam.gserviceaccount.com
  - roles/datastore.user
  - roles/secretmanager.secretAccessor (API keys only)

Audio Service Account: audio-service@project.iam.gserviceaccount.com
  - roles/aiplatform.user
  - roles/datastore.user
  - roles/secretmanager.secretAccessor (ADK key only)

Risk: Least privilege (each SA has minimal permissions)
```

**Option 3: Separate Projects**
```yaml
API Project:
  - api-service@api-project.iam.gserviceaccount.com
  - Permissions: Limited to API project resources

Audio Project:
  - audio-service@audio-project.iam.gserviceaccount.com
  - Permissions: Limited to audio project resources
  - Cross-project access: Requires explicit IAM binding (firestore)

Risk: Maximum isolation, but cross-project complexity
```

**Winner:** Option 2 (best security without cross-project overhead)

---

#### Compliance & Audit

**HIPAA/SOC 2/PCI-DSS Considerations:**

| Requirement | Option 1 | Option 2 ✅ | Option 3 |
|-------------|----------|-----------|----------|
| **Data Isolation** | ❌ Shared service | ⚠️ Shared project (acceptable) | ✅ Separate projects |
| **Audit Logs** | ⚠️ Mixed workload logs | ✅ Separate logs per service | ✅ Separate logs per project |
| **Access Control** | ❌ Overprivileged SA | ✅ Least privilege SAs | ✅ Project-level isolation |
| **Cost Attribution** | ❌ Cannot separate | ⚠️ Can tag by service | ✅ Separate billing |
| **VPC Service Controls** | ⚠️ Same perimeter | ✅ Same perimeter (acceptable) | ✅ Separate perimeters |

**Compliance Verdict:**
- **HIPAA:** Option 2 or 3 (Option 1 fails due to overprivileged access)
- **SOC 2:** Option 2 or 3 (Option 1 acceptable with additional controls)
- **PCI-DSS:** Option 3 (strict isolation required for cardholder data)

---

### 6. Development & Testing

#### Local Development Experience

**Option 1: Same Service**
- ✅ Simple: Run one service locally
- ❌ Complex: Must handle both REST and WebSocket in same process
- ⚠️ Environment parity: Difficult to test scaling behavior

**Option 2: Separate Services ✅**
- ⚠️ Two services to run locally (use Docker Compose)
- ✅ Independent development (REST team ≠ Audio team)
- ✅ Environment parity: Mimics production architecture

**Option 3: Separate Projects**
- ⚠️ Two services + two projects (complex local setup)
- ⚠️ Cross-project access difficult to test locally
- ✅ Environment parity: Exact production match

**Developer Experience Winner:** Option 1 (simplest), but Option 2 is acceptable

---

### 7. Migration & Rollback

#### Rollback Complexity

**Option 1: Same Service**
```bash
# Rollback: Revert entire service
gcloud run services update-traffic ai4joy-unified-service \
  --to-revisions=PREVIOUS_REVISION=100

# Impact: REST API also rolled back (unnecessary)
```

**Option 2: Separate Services ✅**
```bash
# Rollback: Revert only audio service
gcloud run services update-traffic ai4joy-audio-service \
  --to-revisions=PREVIOUS_REVISION=100

# Impact: REST API unaffected (independent rollback)
```

**Option 3: Separate Projects**
```bash
# Rollback: Same as Option 2, but in separate project
gcloud run services update-traffic ai4joy-audio-service \
  --to-revisions=PREVIOUS_REVISION=100 \
  --project=ai4joy-audio-production

# Impact: REST API completely isolated
```

**Rollback Winner:** Options 2 & 3 (independent rollback)

---

## Final Recommendation

### Production Recommendation: **Option 2 - Separate Cloud Run Service (Same Project)** ✅

**Rationale:**
1. **Optimal Performance:** Independent scaling for REST and WebSocket workloads
2. **Cost-Effective:** Saves $307/month vs Option 1, $670/month vs Option 3
3. **Failure Isolation:** Audio issues don't impact REST API
4. **Operational Simplicity:** Shared infrastructure, unified monitoring project
5. **Security:** Least privilege with separate service accounts
6. **Rollback Safety:** Independent deployments and rollbacks
7. **Time to Market:** 2-3 weeks (vs 3-4 weeks for Option 3)

**When to Choose Option 1:**
- ❌ **Never for production** (too risky, inefficient scaling)
- ⚠️ **Only for prototypes/POCs** with <10 concurrent users

**When to Choose Option 3:**
- ✅ **Enterprise scale** (>5000 concurrent sessions)
- ✅ **Strict compliance** (PCI-DSS, separate billing required)
- ✅ **Multi-tenant SaaS** (separate projects per customer tier)
- ✅ **Cost attribution** (separate P&L for premium tier)

---

## Implementation Checklist

### Phase 1: Prerequisites ✅
- [ ] Enable GCP APIs (run, compute, aiplatform, secretmanager, etc.)
- [ ] Create Artifact Registry repository
- [ ] Request Vertex AI quota increase (600 requests/min, 2M tokens/min)
- [ ] Create Secret Manager secret for ADK API key
- [ ] Set up Terraform remote state (Cloud Storage bucket)

### Phase 2: Development ✅
- [ ] Create FastAPI WebSocket endpoint (`/ws/audio/{session_id}`)
- [ ] Implement Vertex AI ADK Live API integration
- [ ] Add WebSocket keepalive mechanism (ping/pong every 30s)
- [ ] Create Dockerfile for audio service
- [ ] Build and push container image to Artifact Registry
- [ ] Write unit tests and integration tests

### Phase 3: Infrastructure (Terraform) ✅
- [ ] Create Terraform modules:
  - [ ] `audio-service` (Cloud Run + IAM)
  - [ ] `load-balancer` (Global LB + backend services + SSL)
  - [ ] `monitoring` (Dashboards + Alerts + SLOs)
- [ ] Configure environments (dev, staging, production)
- [ ] Apply Terraform to dev environment
- [ ] Validate dev deployment

### Phase 4: Testing & Validation ✅
- [ ] Run smoke tests (health endpoints)
- [ ] Test WebSocket connections (connect, send audio, receive response)
- [ ] Load test (100 concurrent users)
- [ ] Verify autoscaling behavior
- [ ] Trigger test alerts (validate alert policies)
- [ ] Performance tuning (adjust concurrency, CPU, memory)

### Phase 5: Production Rollout ✅
- [ ] Deploy Terraform to production
- [ ] DNS cutover (A record to load balancer IP)
- [ ] Wait for SSL certificate provisioning (15-60 minutes)
- [ ] Gradual rollout via feature flag:
  - [ ] 1% of users (Day 1)
  - [ ] 10% of users (Day 3)
  - [ ] 50% of users (Day 7)
  - [ ] 100% of users (Day 14)
- [ ] Monitor SLOs daily
- [ ] Collect user feedback
- [ ] Optimize based on real usage

### Phase 6: Operations ✅
- [ ] Set up on-call rotation
- [ ] Create runbooks for common incidents
- [ ] Configure cost alerts (budget $11,000/month, alert at 80%)
- [ ] Schedule monthly cost optimization review
- [ ] Document architecture for team

---

## Decision Log

| Date | Decision | Rationale | Owner |
|------|----------|-----------|-------|
| 2025-11-27 | Option 2 - Separate Cloud Run Service | Best balance of performance, cost, and simplicity | DevOps Team |
| 2025-11-27 | Vertex AI (not AI Studio) | Production SLA required | Engineering Lead |
| 2025-11-27 | Global HTTPS Load Balancer | Future multi-region expansion | Architect |
| 2025-11-27 | Min instances = 2 for audio service | Eliminate cold starts for real-time UX | Product Manager |

---

## Key Metrics & Success Criteria

**Post-Launch (30 Days):**
- ✅ 99.5% availability SLO achieved
- ✅ p95 latency < 1 second
- ✅ Cost within budget ($8,200-10,500/month)
- ✅ Zero P0/P1 incidents related to audio service
- ✅ User satisfaction > 4.5/5 stars
- ✅ Scalability proven (handled peak load without issues)

**Long-Term (6 Months):**
- ✅ 15-25% cost reduction via CUDs and Vertex AI enterprise pricing
- ✅ Multi-region deployment (us-central1 + us-east1 for HA)
- ✅ Advanced features: Voice cloning, emotion detection, language translation
- ✅ Global scale: 5,000+ concurrent sessions

---

**Document Version:** 1.0
**Last Updated:** 2025-11-27
**Next Review:** 2025-12-27 (post-launch review)
