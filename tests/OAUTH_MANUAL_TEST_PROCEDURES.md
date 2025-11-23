# OAuth Authentication & Rate Limiting Manual Test Procedures

**Ticket:** IQS-45 - Deploy Improv Olympics ADK Application Infrastructure
**Date:** 2025-11-23
**Purpose:** Manual validation of OAuth authentication flow and rate limiting for production deployment

---

## Overview

This document provides step-by-step procedures for manually testing OAuth authentication via Identity-Aware Proxy (IAP) and per-user rate limiting. These tests complement the automated test suite and require human interaction with a web browser.

**Prerequisites:**
- Application deployed to https://ai4joy.org
- IAP enabled on backend service
- Test user accounts configured in `iap_allowed_users`
- Unauthorized test account available (for negative testing)

---

## Test Category 1: OAuth Authentication Flow

### TC-AUTH-MANUAL-01: Complete OAuth Flow (Authorized User)

**Objective:** Validate that an authorized user can successfully authenticate and access the application.

**Priority:** P0 (Critical)

**Test Duration:** 5 minutes

**Steps:**

1. **Prepare Browser**
   - Open incognito/private browsing window (to start with clean session)
   - Ensure you have credentials for an authorized test user

2. **Navigate to Application**
   - Visit https://ai4joy.org
   - **Expected:** Automatic redirect to Google Sign-In page

3. **Observe OAuth Consent Screen**
   - **Expected:** Google OAuth consent screen displays
   - **Expected:** Application name: "Improv Olympics"
   - **Expected:** Permissions requested (if first-time user)
   - Take screenshot of consent screen

4. **Sign In with Authorized User**
   - Enter test user credentials (must be in `iap_allowed_users` list)
   - Click "Sign In" or "Allow"
   - **Expected:** Successful authentication

5. **Verify Access Granted**
   - **Expected:** Redirect back to https://ai4joy.org
   - **Expected:** Application homepage loads
   - **Expected:** No error messages displayed
   - **Expected:** User can interact with application

6. **Verify User Identity Captured**
   - If application has a user profile or debug endpoint, verify:
     - User email displayed correctly
     - User ID matches OAuth subject ID
   - Take screenshot of authenticated state

**Expected Result:** PASS
- User successfully authenticates
- Access granted to application
- User identity correctly captured

**Actual Result:** _[To be filled during test execution]_

**Pass/Fail:** _[To be filled]_

**Notes/Issues:** _[Document any issues encountered]_

---

### TC-AUTH-MANUAL-02: OAuth Flow with Unauthorized User

**Objective:** Verify that users not in the IAP allowed list are denied access.

**Priority:** P0 (Critical)

**Test Duration:** 3 minutes

**Steps:**

1. **Prepare Browser**
   - Open incognito/private browsing window
   - Ensure you have credentials for a Google account NOT in `iap_allowed_users`

2. **Navigate to Application**
   - Visit https://ai4joy.org
   - **Expected:** Automatic redirect to Google Sign-In page

3. **Sign In with Unauthorized User**
   - Enter unauthorized user credentials
   - Complete authentication with Google
   - **Expected:** Google authentication succeeds (Google allows sign-in)

4. **Verify Access Denied by IAP**
   - **Expected:** HTTP 403 Forbidden error page
   - **Expected:** Error message indicates access denied
   - **Expected:** Message mentions contacting administrator or checking permissions
   - Take screenshot of 403 error page

5. **Verify No Access to Application**
   - Try accessing different URLs:
     - https://ai4joy.org/session/start
     - https://ai4joy.org/api/test
   - **Expected:** All protected endpoints return 403
   - **Expected:** Only /health and /ready accessible (200 OK)

**Expected Result:** PASS
- Unauthorized user authenticates with Google successfully
- IAP denies access with 403 error
- Clear error message displayed
- Protected endpoints inaccessible

**Actual Result:** _[To be filled during test execution]_

**Pass/Fail:** _[To be filled]_

**Notes/Issues:** _[Document error message clarity]_

---

### TC-AUTH-MANUAL-03: Sign-Out and Re-Authentication

**Objective:** Verify that signing out clears the session and requires re-authentication.

**Priority:** P1 (High)

**Test Duration:** 4 minutes

**Steps:**

1. **Authenticate and Access Application**
   - Sign in with authorized user (follow TC-AUTH-MANUAL-01)
   - Verify access to application

2. **Initiate Sign-Out**
   - Option A: If application has sign-out button, click it
   - Option B: Navigate to IAP sign-out URL: https://ai4joy.org/_gcp_iap/clear_login_cookie
   - **Expected:** Cookie clearing confirmation or redirect

3. **Verify Session Cleared**
   - Navigate to https://ai4joy.org again
   - **Expected:** Redirect to Google Sign-In (no cached authentication)
   - **Expected:** Must enter credentials again

4. **Test Re-Authentication**
   - Sign in again with the same user
   - **Expected:** Successful re-authentication
   - **Expected:** Access granted as before

**Expected Result:** PASS
- Sign-out clears IAP session cookie
- Subsequent access requires re-authentication
- Re-authentication succeeds

**Actual Result:** _[To be filled during test execution]_

**Pass/Fail:** _[To be filled]_

**Notes/Issues:** _[Document sign-out UX]_

---

### TC-AUTH-MANUAL-04: Multiple Browser Tabs (Session Persistence)

**Objective:** Verify that authenticated sessions persist across browser tabs.

**Priority:** P2 (Medium)

**Test Duration:** 3 minutes

**Steps:**

1. **Authenticate in First Tab**
   - Open browser and navigate to https://ai4joy.org
   - Complete OAuth authentication
   - Verify access granted

2. **Open Second Tab**
   - Open new tab (same browser window)
   - Navigate to https://ai4joy.org
   - **Expected:** No OAuth prompt (session cookie shared)
   - **Expected:** Immediate access to application

3. **Test Session Sharing**
   - Interact with application in Tab 1 (e.g., create session)
   - Switch to Tab 2
   - **Expected:** User remains authenticated
   - **Expected:** Can access application features

4. **Sign Out from One Tab**
   - Sign out from Tab 1
   - Refresh Tab 2
   - **Expected:** Tab 2 also requires re-authentication

**Expected Result:** PASS
- Authenticated session persists across tabs
- Single sign-on experience
- Sign-out affects all tabs

**Actual Result:** _[To be filled during test execution]_

**Pass/Fail:** _[To be filled]_

**Notes/Issues:** _[Document any inconsistencies]_

---

## Test Category 2: Rate Limiting Validation

### TC-RATE-MANUAL-01: Daily Session Limit (10 Sessions)

**Objective:** Verify that users are limited to 10 sessions per day.

**Priority:** P0 (Critical)

**Test Duration:** 15 minutes

**Prerequisites:**
- Authenticated as test user
- Test user has 0 sessions created today

**Steps:**

1. **Authenticate and Verify Starting State**
   - Sign in as test user
   - Verify no active sessions (fresh start)

2. **Create Sessions 1-10**
   - For each session (i = 1 to 10):
     - Create new session via application UI or API
     - Expected: HTTP 200 OK, session created successfully
     - Record session ID
     - Note time of creation

   **Tracking Table:**
   | Session # | Status | Session ID | Time | Notes |
   |-----------|--------|------------|------|-------|
   | 1         |        |            |      |       |
   | 2         |        |            |      |       |
   | 3         |        |            |      |       |
   | 4         |        |            |      |       |
   | 5         |        |            |      |       |
   | 6         |        |            |      |       |
   | 7         |        |            |      |       |
   | 8         |        |            |      |       |
   | 9         |        |            |      |       |
   | 10        |        |            |      |       |

3. **Attempt to Create 11th Session**
   - Try to create another session
   - **Expected:** HTTP 429 Too Many Requests
   - **Expected:** Error message: "Daily session limit reached (10/10)"
   - **Expected:** Message explains limit resets at midnight UTC
   - Take screenshot of error message

4. **Verify Retry-After Header**
   - Inspect HTTP response headers (use browser DevTools Network tab)
   - **Expected:** `Retry-After` header present
   - **Expected:** Value indicates seconds until midnight UTC

5. **Test Persistence After Page Reload**
   - Refresh browser page
   - Attempt to create session again
   - **Expected:** Still returns 429 (limit persists)

**Expected Result:** PASS
- First 10 sessions succeed
- 11th session denied with 429
- Error message clear and actionable
- Rate limit persists across requests

**Actual Result:** _[To be filled during test execution]_

**Pass/Fail:** _[To be filled]_

**Issues/Notes:**
- _[Document error message exact wording]_
- _[Note user experience - is error helpful?]_
- _[Record Retry-After value]_

---

### TC-RATE-MANUAL-02: Concurrent Session Limit (3 Active Sessions)

**Objective:** Verify that users can have at most 3 active sessions simultaneously.

**Priority:** P0 (Critical)

**Test Duration:** 10 minutes

**Prerequisites:**
- Authenticated as test user
- Test user has no active sessions

**Steps:**

1. **Create First Active Session**
   - Create session via application UI
   - Start interacting with session (do not complete it)
   - **Expected:** Success, session remains active

2. **Create Second Active Session**
   - Without completing first session, create another
   - **Expected:** Success, 2 sessions active

3. **Create Third Active Session**
   - Without completing previous sessions, create third
   - **Expected:** Success, 3 sessions active

4. **Attempt to Create Fourth Concurrent Session**
   - Try to create 4th session while others still active
   - **Expected:** HTTP 429 Too Many Requests
   - **Expected:** Error message: "Concurrent session limit reached (3/3)"
   - Take screenshot of error

5. **Complete One Session**
   - Go back to one of the active sessions
   - Complete/close the session
   - **Expected:** Session marked as complete

6. **Create New Session After Completion**
   - Try to create a new session
   - **Expected:** Success (slot freed by completion)
   - **Expected:** Now have 3 active sessions again

**Expected Result:** PASS
- First 3 concurrent sessions succeed
- 4th concurrent session denied
- Completing session frees up slot
- Can create new session after completion

**Actual Result:** _[To be filled during test execution]_

**Pass/Fail:** _[To be filled]_

**Issues/Notes:**
- _[Document which user actions count as "completing" a session]_
- _[Test abandoned session cleanup if applicable]_

---

### TC-RATE-MANUAL-03: Rate Limit Error UX Validation

**Objective:** Evaluate the user experience when hitting rate limits.

**Priority:** P1 (High)

**Test Duration:** 5 minutes

**Steps:**

1. **Trigger Daily Limit**
   - Create 10 sessions (follow TC-RATE-MANUAL-01)
   - Attempt 11th session

2. **Evaluate Error Message Quality**
   - Read error message displayed to user
   - **Evaluate:**
     - Is it clear what limit was hit?
     - Does it explain why (cost protection)?
     - Does it tell user when they can try again?
     - Is tone appropriate (not angry/blaming)?
   - Rate error message: 1 (Poor) to 5 (Excellent): _____

3. **Check for Helpful Guidance**
   - **Expected:** Error includes:
     - Current usage: "10 of 10 sessions used today"
     - Reset time: "Limit resets at midnight UTC (X hours)"
     - Alternative actions: "Complete existing sessions to free up capacity"

4. **Test Multiple Limit Scenarios**
   - Also trigger concurrent limit
   - Compare error messages for consistency
   - **Expected:** Both errors follow similar format

**Expected Result:** PASS
- Error messages clear and actionable
- User understands what happened and what to do next
- Consistent error format across different limits

**Actual Result:** _[To be filled during test execution]_

**Pass/Fail:** _[To be filled]_

**UX Improvements Suggested:** _[List any recommendations]_

---

## Test Category 3: IAP Header Validation

### TC-HEADER-MANUAL-01: Verify IAP Headers in Requests

**Objective:** Confirm that IAP injects user identity headers into requests reaching Cloud Run.

**Priority:** P1 (High)

**Test Duration:** 5 minutes

**Prerequisites:**
- Application has debug endpoint that echoes back request headers, OR
- Access to Cloud Logging to view incoming requests

**Steps:**

**Option A: Debug Endpoint (if available)**

1. **Authenticate and Access Debug Endpoint**
   - Sign in as test user
   - Navigate to https://ai4joy.org/debug/headers (if implemented)
   - **Expected:** Page displays all request headers

2. **Verify IAP Headers Present**
   - Look for these headers:
     - `X-Goog-Authenticated-User-Email: accounts.google.com:USER_EMAIL`
     - `X-Goog-Authenticated-User-ID: accounts.google.com:USER_SUBJECT_ID`
     - `X-Goog-IAP-JWT-Assertion: <JWT_TOKEN>`
   - **Expected:** All three headers present
   - **Expected:** Email matches authenticated user
   - **Expected:** ID is numeric OAuth subject ID

3. **Verify Header Format**
   - Confirm format: `accounts.google.com:value`
   - Validate JWT token is present (long base64 string)

**Option B: Cloud Logging**

1. **Trigger Request from Browser**
   - Perform any authenticated action (e.g., create session)

2. **View Cloud Logging**
   - Open GCP Console → Logging
   - Filter logs for Cloud Run service
   - Find log entry for your request

3. **Inspect Request Headers**
   - Expand log entry
   - Look for `httpRequest.headers` field
   - Verify IAP headers present

**Expected Result:** PASS
- All three IAP headers present in requests
- Header format correct
- User email and ID match authenticated user

**Actual Result:** _[To be filled during test execution]_

**Pass/Fail:** _[To be filled]_

**Headers Captured:**
```
X-Goog-Authenticated-User-Email: _________________
X-Goog-Authenticated-User-ID: _________________
X-Goog-IAP-JWT-Assertion: _________________ (first 50 chars)
```

---

## Test Execution Checklist

Before starting tests:
- [ ] Application deployed to https://ai4joy.org
- [ ] IAP enabled and configured
- [ ] At least 2 test user accounts prepared (1 authorized, 1 unauthorized)
- [ ] Browser with incognito/private mode available
- [ ] Screenshot tool ready
- [ ] Access to GCP Console (for logging inspection)

During test execution:
- [ ] Record actual results for each test case
- [ ] Take screenshots of key screens (consent, errors, etc.)
- [ ] Note exact error messages
- [ ] Document any deviations from expected behavior
- [ ] Record timestamps for rate limiting tests

After test execution:
- [ ] Summarize pass/fail status
- [ ] Document any bugs or issues found
- [ ] Create Linear tickets for any failures
- [ ] Update test cases if procedures need refinement

---

## Test Results Summary Template

**Test Execution Date:** _____________
**Tester:** _____________
**Application Version:** _____________

| Test Case ID           | Test Name                          | Pass/Fail | Notes        |
|------------------------|------------------------------------|-----------|--------------|
| TC-AUTH-MANUAL-01      | Complete OAuth Flow                |           |              |
| TC-AUTH-MANUAL-02      | Unauthorized User Denied           |           |              |
| TC-AUTH-MANUAL-03      | Sign-Out and Re-Auth               |           |              |
| TC-AUTH-MANUAL-04      | Multiple Browser Tabs              |           |              |
| TC-RATE-MANUAL-01      | Daily Session Limit (10)           |           |              |
| TC-RATE-MANUAL-02      | Concurrent Session Limit (3)       |           |              |
| TC-RATE-MANUAL-03      | Rate Limit Error UX                |           |              |
| TC-HEADER-MANUAL-01    | IAP Headers Validation             |           |              |

**Overall Result:** PASS / FAIL

**Critical Issues Found:** _[List any blocking issues]_

**Recommendations:** _[Suggestions for improvements]_

---

## Troubleshooting Guide

### Issue: OAuth redirect loop (keeps redirecting to Google Sign-In)

**Possible Causes:**
- IAP not properly configured on backend service
- OAuth client ID/secret mismatch
- Browser blocking third-party cookies

**Resolution:**
- Verify IAP configuration: `gcloud compute backend-services describe improv-backend --global`
- Check OAuth client credentials in Terraform output
- Try different browser or disable cookie blocking

---

### Issue: 403 error for authorized user

**Possible Causes:**
- User not in `iap_allowed_users` list
- IAM policy not applied correctly
- OAuth brand/client misconfigured

**Resolution:**
- Verify user in allowed list: Check Terraform `iap_allowed_users` variable
- Check IAM policy: `gcloud iap web get-iam-policy --resource-type=backend-services --service=improv-backend`
- Add user manually: `gcloud iap web add-iam-policy-binding --member=user:EMAIL --role=roles/iap.httpsResourceAccessor`

---

### Issue: Rate limits not working (can create unlimited sessions)

**Possible Causes:**
- Rate limiting logic not implemented
- Firestore user_limits collection not created
- User ID not extracted from IAP headers

**Resolution:**
- Check application logs for rate limit checks
- Verify user_limits collection exists in Firestore
- Inspect logs for IAP header extraction

---

## Additional Resources

- **IAP Documentation:** https://cloud.google.com/iap/docs
- **OAuth 2.0 Spec:** https://oauth.net/2/
- **GCP Test Plan:** `/tests/GCP_DEPLOYMENT_TEST_PLAN.md`
- **OAuth Integration Summary:** `/docs/OAUTH_INTEGRATION_SUMMARY.md`
- **Linear Ticket:** IQS-45

---

**Document Version:** 1.0
**Last Updated:** 2025-11-23
**Owner:** QA Engineering
