# IQS-47 Test Strategy Summary

**Ticket**: IQS-47 - Production Observability, Load Testing & Public Launch at ai4joy.org
**Scope**: Week 9 (Monitoring & Alerting) + Week 11 (UX Implementation)
**QA Tester**: Claude (AI QA Agent)
**Date**: 2025-11-24

---

## Executive Summary

Comprehensive test strategy prepared for IQS-47 covering production observability infrastructure (Week 9) and public-facing UX implementation (Week 11). The testing approach balances automated test coverage (~70%) with critical manual validation (~30%), focusing on high-risk areas like monitoring data accuracy, accessibility compliance, and OAuth integration.

**Key Metrics**:
- **Total Test Cases**: 24 critical scenarios
- **Automation Coverage**: 17 automated test files
- **Manual Testing Time**: ~3 hours (first run), ~1.5 hours (regression)
- **Risk Areas Identified**: 4 high-risk, 2 medium-risk

---

## 1. Existing Test Infrastructure Analysis

### Test Directory Structure
```
tests/
├── test_monitoring/          ✅ Exists - observability tests
├── test_week11_frontend/     ✅ Created - new frontend tests
├── load_testing/             ✅ Exists - Locust performance tests
├── test_integration/         ✅ Exists - E2E integration tests
├── test_agents/              ✅ Exists - ADK agent tests
├── test_security/            ✅ Exists - security compliance tests
└── conftest_integration.py   ✅ Shared fixtures
```

### Testing Frameworks Available
- **Backend**: PyTest + httpx + pytest-asyncio
- **Frontend**: Playwright (newly added)
- **Accessibility**: axe-playwright (newly added)
- **Load Testing**: Locust
- **Cloud Validation**: Google Cloud Monitoring SDK

### Existing Test Patterns
- Integration tests use `--run-integration` flag to skip when credentials unavailable
- Fixtures for session management, auth headers, test data
- Consistent use of AAA (Arrange-Act-Assert) pattern
- Real infrastructure testing via `@pytest.mark.integration`

---

## 2. Week 9 Test Strategy (Monitoring & Alerting)

### Critical Test Cases

#### TC-W9-001: Cloud Monitoring Dashboard Creation ✅ Automated
**Location**: `/Users/jpantona/Documents/code/ai4joy/tests/test_monitoring/test_week9_dashboard.py`

**What**: Verify dashboard exists with 6 required widgets
- Widget 1: Turn latency (p50, p95, p99)
- Widget 2: Agent execution latency by agent type
- Widget 3: Error rate over time
- Widget 4: Cache hit/miss ratio
- Widget 5: Concurrent session count
- Widget 6: Request rate and status codes

**How to Test**:
```bash
# Unit tests (mock-based)
pytest tests/test_monitoring/test_week9_dashboard.py::TestCloudMonitoringDashboard -v

# Integration test (requires GCP credentials)
pytest tests/test_monitoring/test_week9_dashboard.py::TestCloudMonitoringDashboard::test_dashboard_exists_in_production -v --run-integration

# Manual validation script
python tests/test_monitoring/validate_dashboard.py --project improvOlympics --dashboard-name "Improv Olympics Production"
```

**Risk**: HIGH - Dashboard misconfiguration could blind operators to production issues

#### TC-W9-002: Alert Policy Functionality ✅ Automated
**Location**: `/Users/jpantona/Documents/code/ai4joy/tests/test_monitoring/test_week9_dashboard.py`

**What**: Verify alert policies trigger correctly
- High latency alert (p95 > 8s)
- Error rate alert (>5%)
- Low cache hit rate alert (<50%)

**How to Test**:
```bash
pytest tests/test_monitoring/test_week9_dashboard.py::TestAlertPolicies -v --run-integration
```

**Manual Validation**: Trigger test alert by simulating threshold violation
```bash
# Use load test to push latency above threshold
locust -f tests/load_testing/locustfile.py --host=https://ai4joy.org --users 50 --spawn-rate 10 --run-time 5m
# Check Cloud Monitoring console for alert firing
```

**Risk**: HIGH - Silent failures if alerts don't fire when thresholds exceeded

#### TC-W9-003: OpenTelemetry Metrics Export ✅ Automated
**Location**: `/Users/jpantona/Documents/code/ai4joy/tests/test_monitoring/test_week9_otel_metrics.py`

**What**: Verify custom metrics are exported to Cloud Monitoring
- `turn_latency_seconds` histogram
- `agent_latency_seconds` histogram by agent
- `cache_hits_total` and `cache_misses_total` counters
- `errors_total` counter
- `request_duration_seconds` histogram

**How to Test**:
```bash
pytest tests/test_monitoring/test_week9_otel_metrics.py::TestOpenTelemetryMetricsExport -v
```

**Risk**: MEDIUM - Missing metrics prevent accurate monitoring

#### TC-W9-004: Trace Context Propagation ✅ Automated
**Location**: `/Users/jpantona/Documents/code/ai4joy/tests/test_monitoring/test_week9_otel_metrics.py`

**What**: Verify trace IDs propagate through HTTP → services → agents → logs

**How to Test**:
```bash
pytest tests/test_monitoring/test_week9_otel_metrics.py::TestTraceContextPropagation -v
```

**Manual Validation**: Execute turn and verify trace ID in Cloud Trace and Cloud Logging
```bash
# 1. Execute turn via API
# 2. Get trace ID from response header X-Trace-ID
# 3. Search Cloud Trace for trace ID
# 4. Search Cloud Logging for same trace ID
# 5. Verify spans correlated
```

**Risk**: MEDIUM - Trace loss makes debugging distributed issues difficult

---

## 3. Week 11 Test Strategy (UX Implementation)

### Critical Test Cases

#### TC-W11-001: Landing Page Rendering ✅ Automated + Manual
**Location**: `/Users/jpantona/Documents/code/ai4joy/tests/test_week11_frontend/test_landing_page.py`

**What**: Verify landing page serves correctly across devices

**How to Test**:
```bash
# Automated tests
pytest tests/test_week11_frontend/test_landing_page.py::TestLandingPageRendering -v --headed

# Mobile viewport
pytest tests/test_week11_frontend/test_landing_page.py::TestLandingPageRendering::test_landing_page_responsive_mobile -v

# Tablet viewport
pytest tests/test_week11_frontend/test_landing_page.py::TestLandingPageRendering::test_landing_page_responsive_tablet -v
```

**Manual Testing**:
- [ ] Test on real iPhone (Safari)
- [ ] Test on real Android device (Chrome)
- [ ] Test on iPad (Safari)
- [ ] Verify responsive design breakpoints

**Risk**: MEDIUM - Poor mobile experience impacts majority of users

#### TC-W11-005: WCAG 2.1 AA Compliance ✅ Automated + Manual
**Location**: `/Users/jpantona/Documents/code/ai4joy/tests/test_week11_frontend/test_accessibility.py`

**What**: Verify accessibility compliance

**How to Test**:
```bash
# Install Playwright browsers first
playwright install chromium

# Automated accessibility scan
pytest tests/test_week11_frontend/test_accessibility.py::TestAutomatedAccessibility -v --headed

# Keyboard navigation tests
pytest tests/test_week11_frontend/test_accessibility.py::TestKeyboardNavigation -v

# Screen reader support tests
pytest tests/test_week11_frontend/test_accessibility.py::TestScreenReaderSupport -v
```

**Manual Testing** (CRITICAL):
- [ ] Navigate entire site with keyboard only (no mouse)
- [ ] Test with NVDA screen reader (Windows)
- [ ] Test with VoiceOver (macOS/iOS)
- [ ] Verify color contrast with browser extension
- [ ] Zoom to 200% - verify no content loss
- [ ] Check focus indicators visible on all interactive elements

**Risk**: HIGH - Accessibility violations could exclude users and create legal compliance issues

#### TC-W11-006: Static File Serving ✅ Automated
**Location**: `/Users/jpantona/Documents/code/ai4joy/tests/test_week11_frontend/test_landing_page.py`

**What**: Verify static files served correctly from Cloud Run

**How to Test**:
```bash
pytest tests/test_week11_frontend/test_landing_page.py::TestStaticFileServing -v
```

**Manual Validation**:
```bash
# Check CSS MIME type
curl -I https://ai4joy.org/static/css/main.css | grep content-type

# Check JavaScript MIME type
curl -I https://ai4joy.org/static/js/app.js | grep content-type

# Check gzip compression
curl -I -H "Accept-Encoding: gzip" https://ai4joy.org/static/js/app.js | grep content-encoding

# Check cache headers
curl -I https://ai4joy.org/static/css/main.css | grep cache-control
```

**Risk**: MEDIUM - Slow page loads impact user experience and SEO

#### TC-W11-007: OAuth Flow with Frontend ✅ Automated (partial)
**Location**: `/Users/jpantona/Documents/code/ai4joy/tests/test_week11_frontend/test_chat_interface.py`

**What**: Verify end-to-end OAuth flow from frontend

**How to Test**:
```bash
# Automated (limited - requires manual OAuth)
pytest tests/test_week11_frontend/test_chat_interface.py::TestOAuthFlowIntegration::test_login_button_redirects_to_oauth -v
```

**Manual Testing** (REQUIRED):
- [ ] Click "Sign in with Google" button
- [ ] Complete Google OAuth consent screen
- [ ] Verify redirect to callback URL
- [ ] Confirm session cookie established
- [ ] Access protected chat interface
- [ ] Verify API requests include session
- [ ] Test logout clears session

**Risk**: HIGH - OAuth failures prevent all user access

---

## 4. Test Gaps and Manual Testing Requirements

### What MUST Be Manually Tested

1. **Visual Validation** (Week 11)
   - UI design matches mockups/wireframes
   - Responsive layout transitions smoothly
   - Loading animations are smooth (not janky)
   - Color scheme and branding consistent

2. **Screen Reader Compatibility** (Week 11)
   - NVDA on Windows
   - VoiceOver on macOS/iOS
   - TalkBack on Android
   - All content announced correctly
   - Navigation landmarks recognized

3. **Cloud Monitoring Dashboard UX** (Week 9)
   - Dashboard layout readable
   - Charts render correctly
   - Time range selector works
   - Drill-down functionality
   - Mobile Cloud Console view

4. **Real OAuth Flow** (Week 11)
   - Google consent screen appearance
   - Callback handling
   - Session persistence across refresh
   - Multi-account switching
   - Logout behavior

5. **Cross-Browser Testing** (Week 11)
   - Chrome (desktop + mobile)
   - Firefox (desktop)
   - Safari (desktop + mobile)
   - Edge (desktop)

6. **Mobile Device Testing** (Week 11)
   - Real iOS device (Safari)
   - Real Android device (Chrome)
   - Tablet (iPad)

### What Can Be Automated

1. **Monitoring Infrastructure**
   - Dashboard widget existence
   - Alert policy configuration
   - Metric export verification
   - Trace context propagation

2. **Frontend Integration**
   - API endpoint connectivity
   - Static file serving
   - Error state rendering
   - Loading state display

3. **Accessibility**
   - Automated WCAG 2.1 AA scan (axe-core)
   - Keyboard navigation flow
   - ARIA label presence
   - Color contrast calculation

---

## 5. Automation Implementation Status

### Created Test Files

| File | Test Cases | Status |
|------|-----------|---------|
| `test_week9_dashboard.py` | 10 | ✅ Created |
| `test_week9_otel_metrics.py` | 15 | ✅ Created |
| `test_landing_page.py` | 14 | ✅ Created |
| `test_accessibility.py` | 18 | ✅ Created |
| `test_chat_interface.py` | 11 | ✅ Created |
| `validate_dashboard.py` | 3 validation functions | ✅ Created |
| `conftest.py` (frontend) | 8 fixtures | ✅ Created |

**Total**: 71 test cases across 7 files

### Test Execution Examples

```bash
# Full test suite for IQS-47
pytest tests/test_monitoring/test_week9_*.py tests/test_week11_frontend/ -v

# Week 9 only
pytest tests/test_monitoring/test_week9_*.py -v

# Week 11 only (requires Playwright browsers)
playwright install chromium
pytest tests/test_week11_frontend/ -v --headed

# Integration tests (requires GCP credentials)
export GCP_PROJECT_ID=improvOlympics
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
pytest tests/test_monitoring/ -v --run-integration

# Accessibility tests only
pytest tests/test_week11_frontend/test_accessibility.py -v --headed

# Manual dashboard validation
python tests/test_monitoring/validate_dashboard.py --project improvOlympics
```

---

## 6. Tools and Dependencies

### Added to `tests/requirements-test.txt`

```
# Week 11 Frontend Testing
playwright>=1.40.0
pytest-playwright>=0.4.0

# Week 11 Accessibility Testing
axe-playwright>=0.1.3

# Week 9 Dashboard Validation
google-cloud-monitoring-dashboards>=1.0.0
```

### Installation Steps

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt

# Install Playwright browsers
playwright install chromium firefox webkit

# Verify installation
playwright --version
pytest --version
```

### Environment Variables Required

```bash
# Production testing
export GCP_PROJECT_ID=improvOlympics
export TEST_BASE_URL=https://ai4joy.org
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# OAuth testing (for manual testing)
export TEST_USER_EMAIL=test@example.com
export TEST_USER_PASSWORD=<password>
```

---

## 7. Risk Assessment

### High-Risk Areas (Require Intensive Testing)

1. **Observability Data Loss** (Week 9)
   - **Impact**: Blind to production issues
   - **Mitigation**: Integration tests + manual validation + canary metrics
   - **Testing**: Automated + manual dashboard check + alert trigger test

2. **OAuth Authentication Failures** (Week 11)
   - **Impact**: Complete access denial
   - **Mitigation**: Manual end-to-end OAuth flow testing
   - **Testing**: Manual + partial automation

3. **Accessibility Violations** (Week 11)
   - **Impact**: User exclusion + legal compliance
   - **Mitigation**: Automated axe-core scan + manual screen reader testing
   - **Testing**: Automated + mandatory manual validation

4. **Frontend-Backend Integration** (Week 11)
   - **Impact**: Broken user experience
   - **Mitigation**: CORS validation + API integration tests
   - **Testing**: Automated API tests + manual flow testing

### Medium-Risk Areas

1. **Static File Performance** (Week 11)
   - **Impact**: Slow page loads
   - **Mitigation**: Cache header validation + compression check
   - **Testing**: Automated

2. **Monitoring Alert Accuracy** (Week 9)
   - **Impact**: False positives/negatives
   - **Mitigation**: Threshold tuning + load test validation
   - **Testing**: Automated + load test

---

## 8. Acceptance Criteria Checklist

### Week 9: Monitoring & Alerting
- [ ] Cloud Monitoring dashboard exists with 6 configured widgets
- [ ] All custom OpenTelemetry metrics appear in dashboard
- [ ] Alert policies trigger within 2 minutes of threshold violation
- [ ] Trace context propagates from HTTP request through all agents
- [ ] Log-based metrics updated in real-time
- [ ] Dashboard validated via automation and manual review

### Week 11: UX Implementation
- [ ] Landing page loads in < 2 seconds on 3G connection
- [ ] Chat interface sends/receives messages successfully
- [ ] All WCAG 2.1 AA automated checks pass (0 violations)
- [ ] Keyboard navigation covers all interactive elements
- [ ] Screen reader announces all UI changes
- [ ] Static files cached appropriately (CSS/JS 1 year, HTML no-cache)
- [ ] OAuth flow completes for Google accounts
- [ ] Error states display user-friendly messages
- [ ] Cross-browser compatibility verified (Chrome, Firefox, Safari, Edge)
- [ ] Mobile responsiveness confirmed (iOS, Android)

---

## 9. Estimated Testing Timeline

### Automated Test Development: ✅ COMPLETE
- Test implementation: 71 test cases created
- Fixtures and utilities: conftest.py, validation scripts
- Documentation: Test plan and summary

### Test Execution Schedule

**Day 1: Automated Testing (4 hours)**
- Install dependencies and Playwright browsers (30 min)
- Run Week 9 monitoring tests (1 hour)
- Run Week 11 frontend tests (1.5 hours)
- Fix test failures and environment issues (1 hour)

**Day 2: Manual Testing (4 hours)**
- Cloud Monitoring dashboard validation (1 hour)
- Screen reader testing (1.5 hours)
- Cross-browser testing (1 hour)
- Mobile device testing (30 min)

**Day 3: Integration and Validation (3 hours)**
- OAuth flow end-to-end testing (1 hour)
- Load test with monitoring validation (1 hour)
- Alert trigger validation (30 min)
- Final regression suite (30 min)

**Total: ~11 hours** (spread over 3 days)

---

## 10. Next Steps

### Immediate Actions (Before Implementation)

1. **Install Test Dependencies**
   ```bash
   pip install -r tests/requirements-test.txt
   playwright install chromium
   ```

2. **Set Up Test Environment**
   ```bash
   export GCP_PROJECT_ID=improvOlympics
   export TEST_BASE_URL=https://ai4joy.org  # or staging URL
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
   ```

3. **Validate Test Infrastructure**
   ```bash
   pytest tests/test_monitoring/test_week9_dashboard.py -v
   playwright open https://ai4joy.org  # Verify Playwright works
   ```

### During Implementation

1. **Run Tests Incrementally**
   - Week 9 dashboard → run dashboard validation script
   - Week 9 metrics → run OpenTelemetry tests
   - Week 11 landing page → run Playwright tests
   - Week 11 accessibility → run axe-core scan

2. **Document Failures**
   - Screenshot any visual issues
   - Save browser console logs for errors
   - Record screen reader output for accessibility issues

3. **Regression Testing**
   - Re-run existing integration tests after each change
   - Verify OAuth flow still works
   - Check monitoring still reports metrics

### After Implementation

1. **Execute Full Manual Checklist**
   - Complete all [ ] items in test plan
   - Document results in test report

2. **Create Defect Reports**
   - Use structured defect format from test plan
   - Include steps to reproduce, screenshots, severity

3. **Update Test Suite**
   - Add regression tests for any bugs found
   - Update test data as needed
   - Maintain test documentation

---

## Appendix: File Locations

All test files created in this strategy:

```
/Users/jpantona/Documents/code/ai4joy/tests/
├── IQS47_TEST_PLAN.md                              # Detailed test plan
├── IQS47_TEST_SUMMARY.md                           # This summary
├── requirements-test.txt                           # Updated with new deps
├── test_monitoring/
│   ├── test_week9_dashboard.py                    # Dashboard & alerts
│   ├── test_week9_otel_metrics.py                 # Metrics & traces
│   └── validate_dashboard.py                      # Manual validation script
└── test_week11_frontend/
    ├── __init__.py
    ├── conftest.py                                 # Playwright fixtures
    ├── test_landing_page.py                       # Landing page & static files
    ├── test_accessibility.py                      # WCAG 2.1 AA compliance
    └── test_chat_interface.py                     # Chat & OAuth integration
```

---

**Prepared by**: Claude (QA Tester Agent)
**Date**: 2025-11-24
**Status**: Ready for Execution
