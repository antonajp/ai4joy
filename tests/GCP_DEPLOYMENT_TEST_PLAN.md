# Improv Olympics GCP Production Deployment Test Plan

## Test Scope
This plan covers comprehensive testing for deploying the Improv Olympics multi-agent system to GCP production (ImprovOlympics project) with VertexAI container hosting and ai4joy.org domain access.

**System Architecture:**
- Hub-and-Spoke multi-agent orchestration via ADK
- 4 Agents: MC (Flash), The Room (Flash), Dynamic Scene Partner (Pro), Coach (Pro)
- Custom Tools: GameDatabase, DemographicGenerator, SentimentGauge, ImprovExpertDatabase
- Session-based state management with phase transitions
- VertexAI deployment with Load Balancer and SSL/TLS

## Critical Test Cases

### 1. PRE-DEPLOYMENT TESTING

#### TC-001: Container Build Verification - AUTOMATED
**Priority:** P0
**Objective:** Validate Docker container builds successfully with all dependencies
**Prerequisites:** Dockerfile present, requirements.txt complete
**Test Steps:**
1. Execute `docker build -t improv-olympics:test .`
2. Verify image creation with `docker images | grep improv-olympics`
3. Inspect layers for ADK, Gemini SDK, custom tools
4. Validate image size < 2GB (performance consideration)
**Expected Result:** Image builds without errors, all dependencies installed
**Automation:** `tests/test_container_build.py`

#### TC-002: ADK Agent Initialization - AUTOMATED
**Priority:** P0
**Objective:** Verify all 4 agents initialize correctly in local container
**Prerequisites:** Container built, service account credentials available
**Test Steps:**
1. Start container with `docker run -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json improv-olympics:test`
2. Verify MC agent loads with gemini-1.5-flash model
3. Verify The Room agent loads with gemini-1.5-flash model
4. Verify Dynamic Scene Partner loads with gemini-1.5-pro model
5. Verify Coach agent loads with gemini-1.5-pro model
6. Check agent registration in orchestrator
**Expected Result:** All agents report "ready" status, no initialization errors
**Automation:** `tests/test_agent_initialization.py`

#### TC-003: Gemini Model Access - AUTOMATED
**Priority:** P0
**Objective:** Validate connectivity to VertexAI Gemini models
**Prerequisites:** GCP credentials configured, VertexAI API enabled
**Test Steps:**
1. Invoke MC agent with test prompt
2. Invoke The Room with sentiment analysis request
3. Invoke Dynamic Scene Partner with scene generation prompt
4. Invoke Coach with session analysis request
5. Measure response latency for each model
**Expected Result:** All models respond successfully, latency < 3s per call
**Automation:** `tests/test_model_integration.py`

#### TC-004: GameDatabase Tool - AUTOMATED
**Priority:** P1
**Objective:** Verify GameDatabase retrieval returns valid game rules
**Test Steps:**
1. Query GameDatabase for short form games
2. Query GameDatabase for long form games
3. Verify returned schema includes: name, rules, constraints, difficulty
4. Test edge case: query non-existent game category
**Expected Result:** Valid game data returned, graceful handling of invalid queries
**Automation:** `tests/test_tools/test_game_database.py`

#### TC-005: DemographicGenerator Tool - AUTOMATED
**Priority:** P1
**Objective:** Validate audience archetype generation for "The Room"
**Test Steps:**
1. Request 5 archetypes for default demographics
2. Verify archetypes are diverse and non-repetitive
3. Test custom demographic parameters (e.g., "Tech Startup")
4. Validate archetype schema includes: persona, traits, reaction_style
**Expected Result:** 5 unique archetypes generated, appropriate to context
**Automation:** `tests/test_tools/test_demographic_generator.py`

#### TC-006: SentimentGauge Tool - AUTOMATED
**Priority:** P1
**Objective:** Verify sentiment analysis accuracy
**Test Steps:**
1. Analyze positive exchange: "That's brilliant! Yes, and..."
2. Analyze negative exchange: "This isn't working. I'm confused."
3. Analyze neutral exchange: "Okay, let's try again."
4. Validate output schema: sentiment_score, room_temp, spotlight_trigger
**Expected Result:** Accurate sentiment classification, scores -1.0 to 1.0
**Automation:** `tests/test_tools/test_sentiment_gauge.py`

#### TC-007: ImprovExpertDatabase Tool - AUTOMATED
**Priority:** P2
**Objective:** Verify retrieval of improv coaching principles
**Test Steps:**
1. Query for "Yes-And" principle
2. Query for "Status Work" principle
3. Query for "Instructional Fading" principle
4. Verify returned data includes: principle, explanation, examples
**Expected Result:** Relevant principles returned with actionable guidance
**Automation:** `tests/test_tools/test_improv_expert_db.py`

---

### 2. INFRASTRUCTURE TESTING

#### TC-101: GCP Resource Provisioning - MANUAL
**Priority:** P0
**Objective:** Validate all GCP resources deployed correctly
**Prerequisites:** Terraform/gcloud scripts ready
**Test Steps:**
1. Verify Cloud Run service exists: `gcloud run services list --project=ImprovOlympics`
2. Verify Artifact Registry repository: `gcloud artifacts repositories list`
3. Verify IAM service account with correct permissions
4. Verify Cloud Load Balancer configured
5. Verify Cloud Armor policies (if applicable)
**Expected Result:** All resources present with correct configurations
**Validation Command:** `gcloud run services describe improv-olympics --region=us-central1`

#### TC-102: Network Connectivity - AUTOMATED
**Priority:** P0
**Objective:** Verify service is reachable via internal and external IPs
**Test Steps:**
1. Test internal VPC connectivity (if applicable)
2. Test external IP access via Load Balancer
3. Verify health check endpoint responds: `/health`
4. Test from multiple geographic regions (US, EU, APAC)
5. Verify firewall rules allow HTTPS (443) traffic
**Expected Result:** Service reachable, health check returns 200 OK
**Automation:** `tests/test_infrastructure/test_network.py`

#### TC-103: DNS Resolution - AUTOMATED
**Priority:** P0
**Objective:** Validate ai4joy.org resolves to Load Balancer IP
**Test Steps:**
1. Execute `nslookup ai4joy.org`
2. Verify A record points to Load Balancer IP
3. Test HTTPS access: `curl https://ai4joy.org/health`
4. Verify no DNS propagation delays
**Expected Result:** DNS resolves correctly, HTTPS accessible
**Automation:** `tests/test_infrastructure/test_dns.py`

#### TC-104: SSL/TLS Certificate Validation - AUTOMATED
**Priority:** P0
**Objective:** Verify valid SSL certificate for ai4joy.org
**Test Steps:**
1. Check certificate validity: `openssl s_client -connect ai4joy.org:443 -servername ai4joy.org`
2. Verify certificate issuer (Google-managed or Let's Encrypt)
3. Verify certificate expiration > 30 days
4. Test HTTPS enforcement (HTTP redirects to HTTPS)
5. Validate certificate chain is complete
**Expected Result:** Valid certificate, HTTPS enforced, no security warnings
**Automation:** `tests/test_infrastructure/test_ssl.py`

#### TC-105: IAM Permissions Verification - MANUAL
**Priority:** P0
**Objective:** Validate service account has correct permissions
**Prerequisites:** Service account created
**Test Steps:**
1. Verify VertexAI API access: `aiplatform.googleapis.com`
2. Verify Cloud Storage access (if session persistence uses GCS)
3. Verify Secret Manager access (for API keys)
4. Test least privilege principle (no overly broad permissions)
5. Verify Cloud Logging write permissions
**Expected Result:** All required permissions granted, no excessive permissions
**Validation Command:** `gcloud projects get-iam-policy ImprovOlympics --flatten="bindings[].members" --filter="bindings.members:serviceAccount:*improv*"`

---

### 3. INTEGRATION TESTING

#### TC-201: End-to-End Session Flow - AUTOMATED
**Priority:** P0
**Objective:** Validate complete session from initialization to coach feedback
**Prerequisites:** Service deployed, all agents operational
**Test Steps:**
1. **Initialization:** POST `/session/start` with user config (location: "Mars Colony")
2. **MC Phase:** Verify MC welcomes user and requests relationship suggestion
3. **User Input:** Submit suggestion: "Two scientists arguing over oxygen rations"
4. **Game Selection:** Verify MC selects appropriate game from GameDatabase
5. **Scene Loop (10 turns):**
   - Turn 1-4: Verify Dynamic Scene Partner in PHASE_1 (supportive)
   - Turn 5+: Verify Partner transitions to PHASE_2 (fallible)
   - Each turn: Verify The Room provides vibe check
6. **Scene End:** Verify MC detects natural ending
7. **Coach Phase:** Verify Coach analyzes session and provides feedback
8. **Session Close:** Verify session state persisted correctly
**Expected Result:** Complete session executes without errors, phase transitions occur
**Automation:** `tests/test_integration/test_e2e_session.py`

#### TC-202: VertexAI Model API Integration - AUTOMATED
**Priority:** P0
**Objective:** Verify all agents communicate with VertexAI models correctly
**Test Steps:**
1. Monitor API calls during TC-201 session
2. Verify Flash model calls for MC and The Room
3. Verify Pro model calls for Dynamic Scene Partner and Coach
4. Validate request/response formats match VertexAI specs
5. Verify API authentication via service account
6. Check for API errors or retries
**Expected Result:** All API calls succeed, correct models invoked
**Automation:** `tests/test_integration/test_vertex_api.py`

#### TC-203: Session State Persistence - AUTOMATED
**Priority:** P1
**Objective:** Validate session state survives container restarts
**Prerequisites:** State persistence mechanism implemented (GCS/Firestore)
**Test Steps:**
1. Start session and complete 5 turns
2. Retrieve session state via API: GET `/session/{session_id}/state`
3. Simulate container restart (redeploy service)
4. Resume session with same session_id
5. Verify turn history, current phase, and context preserved
**Expected Result:** Session resumes seamlessly, no data loss
**Automation:** `tests/test_integration/test_session_persistence.py`

#### TC-204: Load Balancer Routing - MANUAL
**Priority:** P1
**Objective:** Verify Load Balancer routes traffic correctly
**Test Steps:**
1. Send 100 concurrent requests to `https://ai4joy.org/health`
2. Verify all requests routed to active Cloud Run instances
3. Verify sticky sessions (if implemented) maintain session affinity
4. Test failover: Scale down to 0 instances, verify cold start handling
5. Verify request distribution across multiple instances
**Expected Result:** All requests succeed, balanced distribution
**Validation:** Monitor Cloud Run metrics during test

---

### 4. PERFORMANCE TESTING

#### TC-301: Multi-Agent Response Latency - AUTOMATED
**Priority:** P0
**Objective:** Measure end-to-end latency for agent orchestration
**Prerequisites:** Service deployed in production environment
**Test Steps:**
1. Execute 50 user turns in a session
2. Measure latency for each component:
   - User input to Dynamic Scene Partner response
   - Partner response to The Room vibe check
   - Full turn latency (input to vibe check complete)
3. Calculate p50, p95, p99 latencies
4. Identify bottlenecks (model inference, tool calls, network)
**Expected Result:**
- p50 latency: < 2 seconds per turn
- p95 latency: < 4 seconds per turn
- p99 latency: < 6 seconds per turn
**Automation:** `tests/test_performance/test_latency.py`

#### TC-302: Concurrent Session Handling - AUTOMATED
**Priority:** P1
**Objective:** Validate system handles multiple simultaneous sessions
**Test Steps:**
1. Spawn 20 concurrent sessions
2. Each session executes 10-turn scene
3. Monitor resource utilization (CPU, memory, network)
4. Verify no session interference or data leakage
5. Measure degradation in response time under load
**Expected Result:** All sessions complete successfully, latency degrades < 20%
**Automation:** `tests/test_performance/test_concurrent_sessions.py`

#### TC-303: VertexAI Rate Limiting - AUTOMATED
**Priority:** P1
**Objective:** Verify handling of API rate limits and quotas
**Test Steps:**
1. Query current VertexAI quotas for gemini-1.5-pro and gemini-1.5-flash
2. Execute load test exceeding 80% of quota
3. Verify system implements backoff/retry logic
4. Verify user-facing error messages are graceful
5. Test quota reset behavior (next minute/hour)
**Expected Result:** Graceful degradation, no crashes, clear error messages
**Automation:** `tests/test_performance/test_rate_limiting.py`

#### TC-304: Resource Utilization Under Load - MANUAL
**Priority:** P2
**Objective:** Measure Cloud Run resource consumption
**Test Steps:**
1. Run TC-302 concurrent session test
2. Monitor Cloud Run metrics:
   - CPU utilization per instance
   - Memory usage per instance
   - Instance count (autoscaling behavior)
   - Request count and error rate
3. Verify autoscaling triggers appropriately
4. Identify memory leaks or resource exhaustion
**Expected Result:** CPU < 80%, Memory < 512MB per instance, autoscaling responsive
**Validation:** Cloud Run Monitoring dashboard

---

### 5. SECURITY TESTING

#### TC-401: Authentication/Authorization Flows - MANUAL
**Priority:** P0
**Objective:** Verify only authorized users can access the system
**Prerequisites:** Auth mechanism implemented (API keys, OAuth, etc.)
**Test Steps:**
1. Attempt access without credentials: `curl https://ai4joy.org/session/start`
2. Verify 401 Unauthorized response
3. Attempt access with invalid credentials
4. Verify 403 Forbidden response
5. Access with valid credentials, verify 200 OK
6. Test session hijacking: Use another user's session_id
7. Verify proper session isolation
**Expected Result:** Unauthorized access blocked, sessions properly isolated
**Validation:** Manual API testing

#### TC-402: API Key and Secret Protection - MANUAL
**Priority:** P0
**Objective:** Validate secrets are not exposed
**Test Steps:**
1. Verify environment variables do not contain hardcoded secrets
2. Verify secrets retrieved from Secret Manager, not config files
3. Test API error responses do not leak sensitive data
4. Verify logs do not contain API keys or credentials
5. Test container image for embedded secrets: `docker history improv-olympics:prod`
**Expected Result:** No secrets exposed in code, logs, or container image
**Validation:** Code review + secret scanning tools

#### TC-403: Network Security Validation - MANUAL
**Priority:** P1
**Objective:** Verify network security controls are active
**Test Steps:**
1. Verify Cloud Run ingress is set to "Allow external traffic" (if public)
2. Test Cloud Armor rules (if configured) block malicious traffic
3. Verify VPC Service Controls (if applicable) enforce perimeter
4. Test CORS policies allow only ai4joy.org origin
5. Verify no open ports beyond 443 on Load Balancer
**Expected Result:** Only necessary traffic allowed, protections active
**Validation:** GCP Security Console

#### TC-404: HTTPS Enforcement - AUTOMATED
**Priority:** P0
**Objective:** Verify HTTP traffic redirects to HTTPS
**Test Steps:**
1. Attempt HTTP access: `curl -I http://ai4joy.org`
2. Verify 301/302 redirect to https://ai4joy.org
3. Verify HSTS header present: `Strict-Transport-Security: max-age=31536000`
4. Test downgrade attack resistance
**Expected Result:** All HTTP traffic redirects to HTTPS, HSTS enforced
**Automation:** `tests/test_security/test_https_enforcement.py`

---

### 6. AGENT EVALUATION TESTING

#### TC-501: Outside-In Agent Evaluation - MANUAL
**Priority:** P1
**Objective:** Validate agent responses align with user intent
**Prerequisites:** ADK evaluation configuration prepared
**Test Steps:**
1. Define 10 test scenarios with expected behaviors:
   - User suggests "Two astronauts fixing a broken airlock"
   - Expected: MC selects appropriate game, Partner accepts premise
2. Execute scenarios via ADK Web UI for interactive evaluation
3. Measure response quality (1-5 scale):
   - Clarity: Is response understandable?
   - Relevance: Does response address user input?
   - Creativity: Is response engaging and imaginative?
4. Identify conversation flow issues (context loss, repetition)
5. Validate multi-turn coherence across 10+ turn sessions
**Expected Result:** 80%+ scenarios achieve quality score >= 4
**Evaluation Method:** Manual review with ADK Web UI + scoring rubric

#### TC-502: Inside-Out Agent Evaluation - AUTOMATED
**Priority:** P1
**Objective:** Validate correct tool invocation and agent reasoning
**Prerequisites:** Observability enabled (ADK logging)
**Test Steps:**
1. Execute test session with tool trajectory tracking
2. Verify GameDatabase called during MC initialization
3. Verify DemographicGenerator called before The Room initialization
4. Verify SentimentGauge called by The Room each turn
5. Verify ImprovExpertDatabase called by Coach during post-mortem
6. Validate tool parameters are correctly extracted
7. Check for redundant or unnecessary tool calls
**Expected Result:** 100% correct tool selection, no redundant calls
**Automation:** `tests/test_evaluation/test_tool_trajectories.py`

#### TC-503: Tool Trajectory Score Evaluation - AUTOMATED
**Priority:** P2
**Objective:** Measure efficiency of agent tool usage
**Test Steps:**
1. Define "golden trajectories" for standard sessions:
   - MC Phase: GameDatabase → DemographicGenerator → User prompt
   - Scene Loop (per turn): User input → Partner generation → SentimentGauge
   - Coach Phase: ImprovExpertDatabase → Analysis output
2. Compare actual trajectories from 20 test sessions against golden paths
3. Calculate trajectory accuracy score: (correct calls / total calls)
4. Calculate trajectory efficiency score: (necessary calls / actual calls)
5. Identify deviations and their root causes
**Expected Result:** Accuracy >= 95%, Efficiency >= 90%
**Automation:** `tests/test_evaluation/test_trajectory_scores.py`

#### TC-504: Response Quality Map Evaluation - MANUAL
**Priority:** P2
**Objective:** Evaluate mapping between user inputs and agent outputs
**Test Steps:**
1. Prepare test dataset: 50 diverse user inputs per agent
2. For each input, evaluate output across dimensions:
   - Accuracy: Does output correctly address input?
   - Completeness: Are all aspects of input addressed?
   - Relevance: Is information pertinent?
   - Consistency: Similar inputs → similar outputs?
3. Score each dimension 1-5
4. Calculate aggregate response quality score
5. Identify failure patterns (e.g., confusion with ambiguous inputs)
**Expected Result:** Average response quality score >= 4.0
**Evaluation Method:** Manual review with scoring spreadsheet

#### TC-505: Phase Transition Logic Evaluation - AUTOMATED
**Priority:** P1
**Objective:** Verify Dynamic Scene Partner transitions from PHASE_1 to PHASE_2 correctly
**Test Steps:**
1. Execute 10 test sessions
2. Verify PHASE_1 behavior (turns 1-4):
   - Partner accepts all user offers
   - High creativity (temperature 0.9+)
   - No fallibility introduced
3. Verify PHASE_2 transition (turn 5+):
   - Partner introduces "Strategic Fallibility"
   - Lowers status to force user leadership
   - Sentiment remains positive during transition
4. Validate transition logic: `IF Turn_Count > 4 AND Student_Sentiment is Stable`
5. Test edge case: User struggles early, phase transition delayed
**Expected Result:** 100% correct phase transitions, smooth user experience
**Automation:** `tests/test_evaluation/test_phase_transitions.py`

#### TC-506: Agent Observability Validation - MANUAL
**Priority:** P1
**Objective:** Verify complete visibility into agent decision-making
**Test Steps:**
1. Execute test session with verbose logging enabled
2. Verify observability captures:
   - Exact prompts sent to each agent
   - Tool availability for each agent invocation
   - Raw LLM responses (before parsing)
   - Execution flow and timing for each agent
   - Failure points and error details
   - Session state at each turn
3. Test debugging workflow: Reproduce unexpected behavior using logs
4. Verify logs are searchable and filterable (Cloud Logging)
**Expected Result:** Complete execution trace available, debugging effective
**Validation:** Review Cloud Logging console

---

### 7. REGRESSION TESTING

#### TC-601: Core Agent Interaction Regression - AUTOMATED
**Priority:** P0
**Objective:** Verify agent interactions remain consistent after deployments
**Prerequisites:** Baseline test results from previous version
**Test Steps:**
1. Execute standardized test suite of 20 scenarios
2. Compare current results against baseline:
   - Response quality scores
   - Tool trajectory patterns
   - Latency metrics
   - Error rates
3. Flag regressions: >10% degradation in any metric
4. Verify critical paths unchanged:
   - MC → User → Partner → The Room loop
   - Phase transition logic
   - Coach analysis quality
**Expected Result:** No regressions, or regressions documented and accepted
**Automation:** `tests/test_regression/test_agent_interactions.py`

#### TC-602: Game Mechanics and Tools Regression - AUTOMATED
**Priority:** P1
**Objective:** Ensure custom tools function consistently
**Test Steps:**
1. Execute tool test suite (TC-004 through TC-007)
2. Compare outputs against baseline snapshots
3. Verify schema consistency for all tool outputs
4. Test tool error handling remains robust
5. Validate tool performance (latency) unchanged
**Expected Result:** 100% tool tests pass, outputs match baseline
**Automation:** `tests/test_regression/test_tools_regression.py`

#### TC-603: Session Lifecycle Regression - AUTOMATED
**Priority:** P1
**Objective:** Validate session management remains stable
**Test Steps:**
1. Test session creation, progression, and closure
2. Verify session state persistence across turns
3. Test session expiration logic (if implemented)
4. Test concurrent session handling (revisit TC-302)
5. Verify session cleanup (no orphaned data)
**Expected Result:** All session lifecycle operations function correctly
**Automation:** `tests/test_regression/test_session_lifecycle.py`

---

### 8. MONITORING & OBSERVABILITY VALIDATION

#### TC-701: Logging Verification - MANUAL
**Priority:** P1
**Objective:** Validate logs capture necessary operational data
**Test Steps:**
1. Execute test session and review Cloud Logging
2. Verify log levels: INFO for operations, ERROR for failures
3. Verify structured logging (JSON format) for parsing
4. Validate log retention policy configured (e.g., 30 days)
5. Test log search queries for common debugging scenarios:
   - Find all errors for session_id
   - Find all tool calls for specific agent
   - Find sessions with high latency
**Expected Result:** Logs comprehensive, searchable, retention configured
**Validation:** Cloud Logging console review

#### TC-702: Metrics Collection - MANUAL
**Priority:** P1
**Objective:** Validate custom metrics are captured correctly
**Test Steps:**
1. Verify Cloud Monitoring collects:
   - Request count per endpoint
   - Response latency (p50, p95, p99)
   - Error rate and types
   - Active session count
   - Tool invocation counts
   - Agent-specific metrics (phase transitions, sentiment scores)
2. Create custom dashboard visualizing key metrics
3. Verify metrics update in real-time (< 1 minute delay)
**Expected Result:** All metrics collected, dashboard functional
**Validation:** Cloud Monitoring console

#### TC-703: Alerting Functionality - MANUAL
**Priority:** P1
**Objective:** Verify alerts trigger for critical conditions
**Prerequisites:** Alerting policies configured
**Test Steps:**
1. Simulate high error rate (>5% for 5 minutes)
2. Verify alert fires and notification sent (email/Slack/PagerDuty)
3. Simulate high latency (p95 > 6s for 5 minutes)
4. Verify alert fires
5. Test alert recovery: Verify alert clears when condition resolves
6. Test alert fatigue mitigation: Verify de-duplication and throttling
**Expected Result:** Alerts fire correctly, notifications delivered, recovery works
**Validation:** Cloud Monitoring Alerting console + notification channels

---

### 9. ROLLBACK TESTING

#### TC-801: Deployment Rollback Procedure - MANUAL
**Priority:** P0
**Objective:** Validate ability to rollback to previous version
**Prerequisites:** Previous version deployed and tagged
**Test Steps:**
1. Note current Cloud Run revision: `gcloud run revisions list --service=improv-olympics`
2. Deploy new version with intentional regression
3. Detect regression via monitoring or manual testing
4. Execute rollback: `gcloud run services update-traffic improv-olympics --to-revisions=REVISION_ID=100`
5. Verify service routes 100% traffic to previous revision
6. Test session functionality on rolled-back version
7. Verify rollback latency < 2 minutes
**Expected Result:** Rollback completes successfully, service operational
**Validation:** Manual execution + Cloud Run console

#### TC-802: State Recovery Validation - MANUAL
**Priority:** P1
**Objective:** Verify active sessions survive rollback
**Prerequisites:** Session persistence implemented
**Test Steps:**
1. Start 5 active sessions
2. Complete 3 turns in each session
3. Initiate rollback (TC-801)
4. Attempt to resume all 5 sessions
5. Verify turn history and context preserved
6. Complete sessions successfully
**Expected Result:** All sessions resume correctly, no data loss
**Validation:** Manual session testing

---

## Test Execution Strategy

### Phase 1: Pre-Deployment (Local/Staging)
Execute TC-001 through TC-007, TC-004 through TC-007, TC-501, TC-502, TC-505
**Gate:** 100% pass rate required before infrastructure deployment

### Phase 2: Infrastructure Setup
Execute TC-101 through TC-105
**Gate:** All resources provisioned correctly before integration testing

### Phase 3: Integration & Performance
Execute TC-201 through TC-204, TC-301 through TC-304
**Gate:** E2E session success + latency within SLA before production traffic

### Phase 4: Security Validation
Execute TC-401 through TC-404
**Gate:** No security issues before domain configuration

### Phase 5: Production Validation
Execute TC-503, TC-504, TC-506, TC-601 through TC-603, TC-701 through TC-703
**Gate:** All tests pass, monitoring operational

### Phase 6: Rollback Readiness
Execute TC-801, TC-802
**Gate:** Successful rollback test before declaring deployment complete

---

## Recommended Testing Tools & Frameworks

### Automation Frameworks
- **Python Testing:** `pytest` for all automated tests
- **API Testing:** `requests` library + `pytest-asyncio` for async tests
- **Load Testing:** `locust` for TC-302, TC-303, TC-304
- **Container Testing:** `testcontainers-python` for local container tests
- **ADK Testing:** Google ADK evaluation framework

### Infrastructure Testing
- **Network Testing:** `curl`, `httpx`, `socket` module
- **DNS Testing:** `dnspython` library
- **SSL Testing:** `ssl` module, `pyOpenSSL`
- **GCP SDK:** `google-cloud-run`, `google-cloud-logging`, `google-cloud-monitoring`

### Observability Tools
- **Logging:** Cloud Logging (Stackdriver), structured logging with `python-json-logger`
- **Tracing:** Cloud Trace for distributed tracing
- **Metrics:** Cloud Monitoring (Prometheus-compatible)
- **APM:** Consider Cloud Profiler for performance analysis

### Security Tools
- **Secret Scanning:** `gitleaks`, `trufflehog`
- **Container Scanning:** Artifact Registry vulnerability scanning
- **Dependency Scanning:** `safety`, `pip-audit`

### Agent Evaluation Tools
- **ADK Web UI:** Interactive agent testing and debugging
- **ADK Evaluation API:** Automated evaluation with custom metrics
- **Custom Scripts:** Python scripts for trajectory analysis and response scoring

---

## Success Criteria Summary

**Pre-Deployment:** 100% automated tests pass, all agents initialize correctly
**Infrastructure:** All GCP resources operational, DNS resolves, SSL valid
**Integration:** E2E session completes, all agents orchestrate correctly
**Performance:** p95 latency < 4s, 20 concurrent sessions supported
**Security:** No unauthorized access, secrets protected, HTTPS enforced
**Agent Quality:** Response quality >= 4.0/5, tool trajectory accuracy >= 95%
**Observability:** Logs comprehensive, metrics collected, alerts functional
**Rollback:** Rollback completes < 2 minutes, sessions preserved

---

## Risk Areas Requiring Focused Testing

1. **Phase Transition Logic (TC-505):** Complex state management, high user impact if broken
2. **VertexAI Rate Limiting (TC-303):** External dependency, quota limits could cause service degradation
3. **Session State Persistence (TC-203, TC-802):** Data loss risk during failures or rollbacks
4. **Multi-Agent Latency (TC-301):** User experience degradation if latency exceeds 4-6 seconds
5. **Tool Trajectory Correctness (TC-502, TC-503):** Incorrect tool calls lead to broken agent reasoning
6. **Security (TC-401, TC-402):** Unauthorized access or leaked secrets are critical vulnerabilities

---

## Test Data Requirements

**Session Configurations:**
- Diverse locations: "Mars Colony", "Corporate Boardroom", "Medieval Castle", "Submarine"
- User relationships: "Coworkers", "Rivals", "Family members", "Strangers"
- Demographic profiles: "Tech Startup", "Retirement Home", "High School", "Hospital"

**User Input Patterns:**
- Cooperative: "Yes! And we should also..."
- Challenging: "I don't think that makes sense..."
- Ambiguous: "Hmm, maybe?"
- Creative: "What if we turned the entire room upside down?"

**Agent Response Expected Patterns:**
- MC: Energetic, game selection, clear instructions
- The Room: Collective sentiment, occasional spotlight reactions
- Dynamic Scene Partner: Phase 1 (supportive), Phase 2 (fallible)
- Coach: Empathetic analysis, principle-based feedback

---

## Automation Coverage Target

- **Unit Tests (Tools):** 100% coverage for all 4 custom tools
- **Integration Tests:** 80% coverage for agent orchestration paths
- **E2E Tests:** 5 complete session scenarios automated
- **Performance Tests:** 100% coverage for latency and load scenarios
- **Regression Tests:** 100% coverage for critical paths
- **Security Tests:** 50% automated (authentication, HTTPS), 50% manual (code review, penetration testing)

---

## Estimated Test Execution Time

**Pre-Deployment (Automated):** ~30 minutes
**Infrastructure (Manual + Automated):** ~2 hours
**Integration (Automated):** ~1 hour
**Performance (Automated):** ~2 hours
**Security (Manual):** ~3 hours
**Agent Evaluation (Manual + Automated):** ~4 hours
**Regression (Automated):** ~30 minutes
**Monitoring (Manual):** ~1 hour
**Rollback (Manual):** ~30 minutes

**Total:** ~14.5 hours for comprehensive test execution

---

## Continuous Testing Recommendations

1. **CI/CD Integration:** Run TC-001 through TC-007 on every commit
2. **Nightly Regression:** Run TC-601 through TC-603 nightly
3. **Weekly Performance:** Run TC-301 through TC-304 weekly
4. **Monthly Security:** Run TC-401 through TC-404 monthly
5. **Quarterly Agent Evaluation:** Run TC-501 through TC-506 quarterly
6. **Production Smoke Tests:** Run subset of E2E tests every 6 hours in production

---

**Document Version:** 1.0
**Last Updated:** 2025-11-23
**Owner:** QA Engineering Team
**Review Cadence:** After each deployment, update based on lessons learned
