# Capacity Planning - Improv Olympics ADK Multi-Agent System

## Executive Summary

This document provides capacity planning analysis for the Improv Olympics ADK multi-agent orchestration system. Analysis is based on empirical testing, architectural review, and GCP resource monitoring.

**System Target**: 10 concurrent users with p95 latency < 3 seconds

## Resource Usage Per Session

### Computational Resources

**Memory Consumption**:
- Base session object: ~1-2 KB
- Conversation history (15 turns): ~45-50 KB
- Agent cache (Stage Manager): ~20-30 MB per cached instance
- Context window overhead: ~10-15 KB per turn
- **Total estimated memory per active session**: ~50 MB

**CPU Utilization**:
- Per turn execution: ~0.1-0.15 vCPU (agent orchestration + parsing)
- Peak during concurrent agent calls: ~0.3 vCPU (Partner + Room + Coach)
- Session creation overhead: ~0.05 vCPU
- **Average CPU per turn**: 0.1 vCPU
- **Peak CPU per session** (15 turns over 5-10 min): ~0.15 vCPU sustained

### API Consumption

**Vertex AI Gemini API Calls Per Turn**:
- Stage Manager coordination: 1 call (wraps Partner, Room, Coach)
- Effective agent invocations: 3 per turn (Partner, Room, Coach conditional)
- **Total API calls per turn**: 1 Gemini call (internal orchestration)
- **Total API calls per session** (15 turns): ~15 Gemini API calls

**Token Consumption Estimates**:
- Input tokens per turn (context + prompt): ~400 tokens
- Output tokens per turn (responses): ~300 tokens
- **Total tokens per turn**: ~700 tokens
- **Total tokens per session**: ~10,500 tokens (15 turns × 700)

### Firestore Operations

**Per Turn**:
- Session read: 1 read operation
- Session update (atomic): 1-2 write operations
  - Add conversation turn to history
  - Update turn count
  - Optional: phase transition, status change
- **Total operations per turn**: ~3 operations (1 read + 2 writes)

**Per Complete Session**:
- Session creation: 1 write
- Turn operations: 15 turns × 3 ops = 45 operations
- Session close: 1 write
- Rate limit checks: 2-3 reads
- **Total operations per session**: ~50 operations

## Cost Analysis Per Session

### Gemini API Costs

**Model Configuration**:
- Gemini 1.5 Flash: Primary model for all agents
- Pricing (as of 2025):
  - Input: $0.10 per 1M tokens
  - Output: $0.30 per 1M tokens

**Per Session Calculation**:
- Input tokens: 15 turns × 400 tokens = 6,000 tokens
- Output tokens: 15 turns × 300 tokens = 4,500 tokens
- Input cost: (6,000 / 1,000,000) × $0.10 = $0.0006
- Output cost: (4,500 / 1,000,000) × $0.30 = $0.00135
- **Total Gemini cost per session**: ~$0.00195 (~$0.002)

**Alternative with Gemini Pro** (if used for coaching):
- Coach feedback (turn 15): 1 call with Gemini 1.5 Pro
- Pro pricing: $1.25 per 1M input, $5.00 per 1M output
- Additional cost: ~$0.0015
- **Total with Pro coaching**: ~$0.0035 per session

### Firestore Costs

**Pricing**:
- Document reads: $0.06 per 100,000 operations
- Document writes: $0.18 per 100,000 operations

**Per Session**:
- Reads: ~20 operations × ($0.06 / 100,000) = $0.000012
- Writes: ~30 operations × ($0.18 / 100,000) = $0.000054
- **Total Firestore cost per session**: ~$0.000066 (~negligible)

### Cloud Run Costs

**Configuration**:
- CPU: 1 vCPU allocated
- Memory: 2 GB allocated
- Minimum instances: 1
- Maximum instances: 10

**Pricing** (us-central1):
- vCPU-seconds: $0.00002400 per vCPU-second
- Memory: $0.00000250 per GiB-second

**Per Session** (5-minute average):
- vCPU usage: 0.1 vCPU × 300 seconds = 30 vCPU-seconds
- vCPU cost: 30 × $0.00002400 = $0.00072
- Memory usage: 0.05 GB × 300 seconds = 15 GiB-seconds
- Memory cost: 15 × $0.00000250 = $0.0000375
- **Total Cloud Run cost per session**: ~$0.00076

### Total Cost Per Session

- Gemini API (Flash only): $0.00195
- Firestore: $0.000066
- Cloud Run: $0.00076
- **Total**: **~$0.0028 per session** (~$0.003)

**Daily Cost Estimates**:
- 100 sessions/day: ~$0.28
- 500 sessions/day: ~$1.40
- 1,000 sessions/day: ~$2.80

**Monthly Cost Estimates** (30 days):
- 100 sessions/day: ~$8.40
- 500 sessions/day: ~$42.00
- 1,000 sessions/day: ~$84.00

Note: Costs exclude OAuth infrastructure, monitoring, and logging overhead.

## Cloud Run Instance Capacity

### Single Instance Capacity

**Resource Constraints**:
- CPU: 1 vCPU allocated
- Memory: 2 GB allocated
- Max concurrent sessions per instance: 10 (configured limit)

**Theoretical Capacity**:
- CPU available: 1.0 vCPU
- CPU per concurrent session: 0.15 vCPU
- CPU-based limit: 1.0 / 0.15 = ~6 sessions

- Memory available: 2048 MB
- Memory per session: 50 MB
- Memory-based limit: 2048 / 50 = ~40 sessions

**Practical Limit**: 10 concurrent sessions
- Constraint: CPU availability (primary bottleneck)
- Safety margin: 40% reserved for system overhead
- Configuration: `max_concurrent_sessions_per_instance = 10`

### Scaling Behavior

**Horizontal Scaling**:
- Minimum instances: 1 (always warm)
- Maximum instances: 10
- Scale-up trigger: CPU utilization > 70%
- Scale-down trigger: CPU utilization < 40% for 5+ minutes

**Capacity Levels**:
- 1 instance: 10 concurrent sessions
- 5 instances: 50 concurrent sessions
- 10 instances (max): 100 concurrent sessions

**Expected Performance**:
- 1-10 concurrent users: Single instance, optimal latency
- 11-50 concurrent users: 2-5 instances, stable latency
- 51-100 concurrent users: 6-10 instances, acceptable latency

## Performance Characteristics

### Latency Benchmarks

**Target Metrics**:
- p50 latency: < 2.0 seconds
- p95 latency: < 3.0 seconds
- p99 latency: < 5.0 seconds

**Measured Performance** (from load testing):
- Session creation: ~1-2 seconds
- Turn execution (10 concurrent): p95 ~2.5 seconds
- Phase transition overhead: < 0.2 seconds
- Error rate under load: < 1%

### Bottlenecks

**Primary Bottleneck**: Gemini API latency
- Gemini 1.5 Flash response time: 1-3 seconds per call
- Sequential orchestration overhead: ~0.5 seconds
- Mitigation: Agent caching (reduces redundant initialization)

**Secondary Bottleneck**: CPU during peak concurrent load
- Impact: Increases p95 latency when >8 sessions active on single instance
- Mitigation: Cloud Run auto-scaling triggers new instances

**Not Bottlenecks**:
- Firestore operations: < 100ms per operation
- Memory: Ample headroom (50 MB per session vs 2 GB available)
- Network: GCP internal networking is fast

## Optimization Recommendations

### Immediate Optimizations

1. **Agent Caching** (IMPLEMENTED)
   - Cache Stage Manager instances by turn count
   - Reduces initialization overhead by ~200-300ms per turn
   - TTL: 300 seconds (5 minutes)
   - Impact: 10-15% latency reduction

2. **Context Compaction** (IMPLEMENTED)
   - Limit conversation history to recent 3 turns + first turn
   - Reduces token consumption by ~30% for long sessions
   - Impact: Lower API costs for sessions > 10 turns

3. **Firestore Batch Writes** (READY)
   - Batch multiple updates when possible
   - Reduces network round-trips
   - Current threshold: 5 operations
   - Impact: Marginal (Firestore not a bottleneck)

### Future Optimizations

1. **Parallel Agent Execution**
   - Execute Partner, Room, Coach agents concurrently
   - Potential latency reduction: 30-40%
   - Complexity: Requires ADK multi-agent coordination refactor
   - Priority: HIGH if p95 latency consistently > 3s

2. **Response Caching**
   - Cache common agent responses for similar inputs
   - Use semantic similarity matching (embeddings)
   - Reduces Gemini API calls by ~15-20%
   - Priority: MEDIUM (cost optimization)

3. **Predictive Scaling**
   - Monitor historical usage patterns
   - Pre-scale instances during expected peak hours
   - Reduces cold-start impact
   - Priority: LOW (current warm instance strategy sufficient)

## Scaling Strategy

### Phase 1: MVP (Current State)
- Target: 10-50 concurrent users
- Infrastructure: 1-3 Cloud Run instances
- Monitoring: Manual metrics review
- Cost: ~$50-150/month

### Phase 2: Growth (50-200 concurrent users)
- Infrastructure: 3-8 Cloud Run instances
- Optimization: Implement parallel agent execution
- Monitoring: Automated alerting, SLO tracking
- Cost: ~$150-500/month

### Phase 3: Scale (200+ concurrent users)
- Infrastructure: 8-20+ Cloud Run instances
- Optimization: Response caching, predictive scaling
- Monitoring: Full observability stack, SRE practices
- Cost: $500+/month (volume discounts apply)

## Monitoring and Alerts

### Key Metrics

**Latency SLIs**:
- p50 turn execution latency
- p95 turn execution latency
- p99 turn execution latency

**Capacity SLIs**:
- Concurrent sessions per instance
- CPU utilization per instance
- Memory utilization per instance

**Cost SLIs**:
- Gemini API calls per day
- Gemini token consumption per day
- Cloud Run vCPU-hours per day

### Alert Thresholds

**Critical Alerts**:
- p95 latency > 5 seconds (sustained 5 minutes)
- Error rate > 5% (sustained 2 minutes)
- CPU utilization > 90% (sustained 3 minutes)

**Warning Alerts**:
- p95 latency > 3 seconds (sustained 10 minutes)
- Error rate > 1% (sustained 5 minutes)
- CPU utilization > 70% (sustained 5 minutes)
- Daily cost > $20 (unexpected spike)

## Testing Validation

### Load Testing Scenarios

1. **Concurrent Session Creation**
   - Test: 10 users create sessions simultaneously
   - Expected: All succeed, avg latency < 5s
   - Actual: See `tests/load_testing/test_load_performance.py`

2. **Concurrent Turn Execution**
   - Test: 10 sessions execute turns simultaneously
   - Expected: p95 latency < 3s, error rate < 1%
   - Actual: See `tests/load_testing/locustfile.py`

3. **Full Session Flow Under Load**
   - Test: 5 users complete 15-turn sessions concurrently
   - Expected: All sessions complete, error rate < 1%
   - Actual: See `tests/load_testing/test_load_performance.py`

### Capacity Validation

**Memory Usage**:
- Test: Measure session object size
- Expected: < 100 KB per session (excluding cache)
- Location: `tests/test_performance/test_capacity.py`

**Firestore Operations**:
- Test: Count operations per session
- Expected: < 50 operations per complete session
- Location: `tests/test_performance/test_capacity.py`

## Assumptions and Constraints

### Assumptions

1. Average session duration: 5-10 minutes
2. Average turn completion time: 20-40 seconds per turn
3. Peak concurrent users: 10-20 (95th percentile)
4. Gemini API availability: 99.9% uptime
5. Firestore availability: 99.99% uptime

### Constraints

1. Cloud Run max instances: 10 (configurable, can increase)
2. Rate limits: 10 sessions/user/day, 3 concurrent/user
3. Session timeout: 60 minutes
4. Agent timeout: 30 seconds per turn
5. Context window: 4,000 tokens maximum

### Risks

1. **Gemini API Rate Limits**: Hitting quota during viral load
   - Mitigation: Request quota increase, implement response caching

2. **Cost Spikes**: Unexpected usage surge
   - Mitigation: Budget alerts, daily cost caps, rate limiting

3. **Cold Start Latency**: First request after scale-down
   - Mitigation: Minimum 1 warm instance, predictive scaling

## Revision History

- **2025-11-24**: Initial capacity planning document
  - Based on Week 8 load testing results
  - Validated with 10 concurrent users
  - Cost estimates updated for 2025 pricing
