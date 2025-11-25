# IQS-47 Test Plan: Production Observability & Public Launch

## Test Scope

Testing for **Week 9 (Monitoring & Alerting)** and **Week 11 (UX Implementation)** implementation.

### In Scope
- Cloud Monitoring dashboard validation (6 widgets)
- Alert policy verification
- OpenTelemetry instrumentation testing
- Landing page functionality
- Chat interface integration
- Accessibility compliance (WCAG 2.1 AA)
- Static file serving
- OAuth flow integration with frontend

### Out of Scope
- Week 10 (Load Testing) - Skipped per ticket
- Week 12 (Performance Optimization) - Skipped per ticket
- Infrastructure deployment automation (covered by Terraform)
- Domain DNS configuration

---

## Critical Test Cases

### Week 9: Monitoring & Alerting

**TC-W9-001: Cloud Monitoring Dashboard Creation** - Automated
Verify dashboard exists with 6 required widgets:
- Widget 1: Turn latency (p50, p95, p99)
- Widget 2: Agent execution latency by agent type
- Widget 3: Error rate over time
- Widget 4: Cache hit/miss ratio
- Widget 5: Concurrent session count
- Widget 6: Request rate and status codes

**TC-W9-002: Alert Policy Functionality** - Automated
Verify alert policies trigger correctly:
- High latency alert (p95 > 8s)
- Error rate alert (>5%)
- Low cache hit rate alert (<50%)

**TC-W9-003: OpenTelemetry Metrics Export** - Automated
Verify custom metrics are exported to Cloud Monitoring:
- `turn_latency_seconds` histogram
- `agent_latency_seconds` histogram by agent
- `cache_hits_total` and `cache_misses_total` counters
- `errors_total` counter
- `request_duration_seconds` histogram

**TC-W9-004: Trace Context Propagation** - Automated
Verify trace IDs propagate through:
- HTTP middleware → service layer → ADK agents
- Logs contain matching trace IDs
- Spans are correlated in Cloud Trace

**TC-W9-005: Log-Based Metrics** - Manual
Verify additional log-based metrics in Cloud Monitoring:
- Session creation rate
- Turn completion rate
- Agent-specific error counts

### Week 11: UX Implementation

**TC-W11-001: Landing Page Rendering** - Automated + Manual
Verify landing page (`/`) serves correctly:
- HTML loads successfully (200 status)
- OAuth login button present and functional
- Responsive design on mobile/tablet/desktop
- All static assets load (CSS, JS, images)

**TC-W11-002: Chat Interface Integration** - Automated
Verify chat interface connects to backend:
- POST `/session/start` creates session
- POST `/session/{id}/turn` sends messages
- Responses display in chat UI
- Error states handled gracefully

**TC-W11-003: Loading States** - Manual
Verify loading indicators during:
- Session creation (spinner/skeleton)
- Turn execution (typing indicator)
- Agent response generation (loading state)

**TC-W11-004: Error State Handling** - Automated
Verify error display for:
- Network failures (retry mechanism)
- Rate limit exceeded (clear message)
- Invalid session (redirect to home)
- Server errors (user-friendly message)

**TC-W11-005: WCAG 2.1 AA Compliance** - Automated + Manual
Verify accessibility requirements:
- Keyboard navigation (tab order, focus indicators)
- Screen reader compatibility (ARIA labels, semantic HTML)
- Color contrast ratios (4.5:1 for normal text, 3:1 for large text)
- Text resize up to 200% without loss of content
- No keyboard traps

**TC-W11-006: Static File Serving** - Automated
Verify static files served from Cloud Run:
- `/static/css/*` returns CSS with correct MIME type
- `/static/js/*` returns JavaScript with correct MIME type
- `/static/images/*` returns images with correct MIME type
- Cache headers set appropriately
- Gzip compression enabled

**TC-W11-007: OAuth Flow with Frontend** - Automated
Verify end-to-end OAuth flow:
- User clicks login button
- Redirects to Google OAuth consent screen
- Callback handles authorization code
- Session cookie established
- User redirected to chat interface
- Authenticated API requests succeed

---

## Risk Areas Requiring Focused Testing

1. **Observability Data Loss** (High Risk)
   - OpenTelemetry export failures to Cloud Monitoring
   - Trace context lost during agent execution
   - Alert policies not triggering despite threshold violations

2. **Frontend-Backend Integration** (High Risk)
   - CORS misconfigurations blocking frontend requests
   - OAuth state mismatch between frontend and backend
   - WebSocket/long-polling fallback for chat interface

3. **Accessibility Barriers** (Medium Risk)
   - Screen reader users unable to navigate chat interface
   - Keyboard users trapped in modal dialogs
   - Color-only indicators without text labels

4. **Static File Performance** (Medium Risk)
   - Large assets causing slow page load
   - Missing cache headers causing repeated downloads
   - Compression not applied to text assets

---

## Automation Strategy

### Test Framework: PyTest + Playwright
- **Backend tests**: PyTest with `httpx.AsyncClient` for API testing
- **Frontend tests**: Playwright for browser automation and accessibility
- **Load tests**: Existing Locust framework for monitoring under load

### What to Automate (Priority Order)

1. **Cloud Monitoring Dashboard Validation** (Python SDK)
   - Use Google Cloud Monitoring API to verify dashboard structure
   - Assert widget configurations match specifications
   - Check alert policy existence and thresholds

2. **OpenTelemetry Metrics Collection** (PyTest)
   - Instrument test harness to verify metrics exported
   - Assert metric values within expected ranges
   - Verify metric labels and attributes

3. **Frontend Component Tests** (Playwright)
   - Landing page rendering and navigation
   - Chat interface message flow
   - Error state rendering
   - OAuth redirect flow

4. **Accessibility Tests** (Playwright + axe-core)
   - Automated WCAG 2.1 AA checks using axe-playwright
   - Keyboard navigation verification
   - Screen reader landmark detection

5. **Static File Serving** (PyTest)
   - HTTP requests for static assets
   - Header validation (Content-Type, Cache-Control, Content-Encoding)
   - Response code verification

### What Requires Manual Testing

1. **Visual Validation**
   - UI design consistency with mockups
   - Responsive layout behavior across devices
   - Loading animation smoothness

2. **Screen Reader Testing**
   - NVDA/JAWS on Windows
   - VoiceOver on macOS/iOS
   - TalkBack on Android

3. **Cloud Monitoring Dashboard UX**
   - Dashboard layout and readability
   - Widget chart legibility
   - Time range selection functionality

4. **Real User Flow Testing**
   - Complete user journey from landing to session completion
   - Browser compatibility (Chrome, Firefox, Safari, Edge)
   - Mobile device testing (iOS Safari, Android Chrome)

---

## Test Execution Commands

### Run All IQS-47 Tests
```bash
pytest tests/test_monitoring/ tests/test_week11_frontend/ -v --run-integration
```

### Run Only Monitoring Tests
```bash
pytest tests/test_monitoring/ -v
```

### Run Frontend Integration Tests
```bash
pytest tests/test_week11_frontend/ --headed --browser chromium
```

### Run Accessibility Tests
```bash
pytest tests/test_week11_frontend/test_accessibility.py --headed
```

### Run Load Test with Monitoring Validation
```bash
locust -f tests/load_testing/locustfile.py --host=https://ai4joy.org --users 10 --spawn-rate 2
```

### Validate Cloud Monitoring Dashboard (Manual)
```bash
python tests/test_monitoring/validate_dashboard.py --project improvOlympics --dashboard-name "Improv Olympics Production"
```

---

## Tools and Dependencies Needed

### Python Dependencies (add to `tests/requirements-test.txt`)
```
# Frontend Testing
playwright>=1.40.0
axe-playwright>=0.1.0

# Cloud Monitoring SDK
google-cloud-monitoring>=2.15.0

# Accessibility Validation
axe-core>=4.8.0
```

### Additional Tools
- **Lighthouse CI**: For automated performance and accessibility audits
- **Google Cloud Console**: Manual dashboard and alert verification
- **Browser DevTools**: Network tab analysis, console error checking
- **NVDA/JAWS**: Screen reader testing on Windows
- **VoiceOver**: Screen reader testing on macOS

### Environment Variables Required
```bash
# Testing against production
export GCP_PROJECT_ID=improvOlympics
export TEST_BASE_URL=https://ai4joy.org
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# OAuth testing
export OAUTH_CLIENT_ID=<client-id>
export OAUTH_CLIENT_SECRET=<client-secret>
export TEST_USER_EMAIL=<test-user-email>
export TEST_USER_PASSWORD=<test-user-password>
```

---

## Manual Testing Checklist

### Week 9: Monitoring Validation
- [ ] Cloud Monitoring dashboard displays all 6 widgets correctly
- [ ] Widget charts show live data from production
- [ ] Alert policies exist in Cloud Monitoring console
- [ ] Trigger test alert by exceeding latency threshold
- [ ] Verify alert notification sent (email/Slack/PagerDuty)
- [ ] Check Cloud Trace for distributed traces across agents
- [ ] Verify trace IDs in Cloud Logging match trace viewer

### Week 11: Frontend UX
- [ ] Landing page loads on desktop Chrome
- [ ] Landing page loads on mobile Safari (iOS)
- [ ] Landing page loads on Android Chrome
- [ ] OAuth login flow completes successfully
- [ ] Chat interface displays after login
- [ ] Send message in chat and receive response
- [ ] Loading spinner displays during turn execution
- [ ] Error message displays when network disconnected
- [ ] Rate limit message displays after 10 sessions
- [ ] Logout button functions correctly
- [ ] Navigate with keyboard only (no mouse)
- [ ] Test with screen reader (VoiceOver/NVDA)
- [ ] Zoom to 200% - verify no content loss
- [ ] Check color contrast with browser extension
- [ ] Verify focus indicators visible on all interactive elements

### Cross-Cutting Validation
- [ ] Check browser console for JavaScript errors
- [ ] Verify no mixed content warnings (HTTP on HTTPS page)
- [ ] Test with browser extensions disabled (uBlock, etc.)
- [ ] Verify CORS headers allow frontend origin
- [ ] Check network tab for failed static asset loads
- [ ] Validate SSL certificate on ai4joy.org
- [ ] Test OAuth flow with multiple Google accounts
- [ ] Verify session persistence across page refreshes

---

## Acceptance Criteria from Testing Perspective

### Week 9: Monitoring
- ✅ Cloud Monitoring dashboard exists with 6 configured widgets
- ✅ All custom OpenTelemetry metrics appear in dashboard
- ✅ Alert policies trigger within 2 minutes of threshold violation
- ✅ Trace context propagates from HTTP request through all agents
- ✅ Log-based metrics updated in real-time

### Week 11: UX
- ✅ Landing page loads in < 2 seconds on 3G connection
- ✅ Chat interface sends/receives messages successfully
- ✅ All WCAG 2.1 AA automated checks pass (0 violations)
- ✅ Keyboard navigation covers all interactive elements
- ✅ Screen reader announces all UI changes
- ✅ Static files cached appropriately (CSS/JS 1 year, HTML no-cache)
- ✅ OAuth flow completes for Google accounts
- ✅ Error states display user-friendly messages

---

## Estimated Test Execution Time

### Automated Tests
- Monitoring tests: 10 minutes
- Frontend integration tests: 15 minutes
- Accessibility tests: 20 minutes
- Static file tests: 5 minutes
- **Total automated: ~50 minutes**

### Manual Tests
- Monitoring dashboard validation: 30 minutes
- Frontend cross-browser testing: 60 minutes
- Screen reader testing: 45 minutes
- Mobile device testing: 30 minutes
- OAuth flow validation: 15 minutes
- **Total manual: ~3 hours**

### **Grand Total: ~4 hours** (first run, ~1.5 hours for regression)

---

## Test Data Requirements

### Monitoring Test Data
- 50+ turn executions to populate latency histograms
- Mix of successful and failed requests for error rate metrics
- Cache hit/miss operations for cache metrics
- Concurrent session load for session count widget

### Frontend Test Data
- Valid Google OAuth test account credentials
- Test location scenarios for session creation
- Sample user inputs for chat testing
- Invalid session IDs for error state testing

---

## Definition of Done (Testing)

- [ ] All automated test cases implemented and passing
- [ ] Cloud Monitoring dashboard validated in production
- [ ] Alert policies tested with triggered thresholds
- [ ] Frontend accessibility audit passes with 0 critical issues
- [ ] Manual testing checklist completed (100%)
- [ ] Cross-browser compatibility verified (Chrome, Firefox, Safari, Edge)
- [ ] Mobile responsiveness confirmed (iOS, Android)
- [ ] OAuth flow validated end-to-end
- [ ] Performance benchmarks met (page load < 2s, API < 3s p95)
- [ ] Test documentation updated with findings
- [ ] Critical bugs (P0/P1) resolved
- [ ] Regression test suite updated for Week 9 + Week 11 features
