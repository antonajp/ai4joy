# OAuth Integration - Complete Implementation Summary

> **Note:** This project uses **Application-Level OAuth 2.0** for authentication. See [OAUTH_IMPLEMENTATION_CHANGE.md](OAUTH_IMPLEMENTATION_CHANGE.md) for details on why we chose application-level OAuth over IAP.

**Date:** 2025-11-24
**Decision:** OAuth authentication is **mandatory for MVP** to prevent cost abuse from anonymous LLM usage

---

## Executive Summary

All project documentation, infrastructure code, Linear tickets, and test plans have been updated to reflect OAuth authentication as a core MVP requirement using **Application-Level Google OAuth 2.0**.

**Key Decision:** Application-Level OAuth 2.0 provides Google Sign-In at the application layer using secure session cookies. This approach was chosen over IAP because IAP requires a GCP Organization, which personal projects don't have.

---

## What Changed

### 1. Product Requirements (PRD)

**File:** `docs/improv-olympics-gcp-deployment-prd.md`

**Changes:**
- **FR-2 Updated:** "Anonymous Session Management" → "OAuth Authentication (MVP)"
  - Users must authenticate via Google Sign-In before accessing sessions
  - User identity (email, OAuth ID) captured and associated with all sessions
  - Failed authentication displays clear error with retry option

- **FR-11 Added:** "Per-User Rate Limiting (OAuth-Enabled)"
  - Maximum 10 sessions per user per day during pilot
  - Maximum 3 concurrent active sessions per user
  - Rate limit exceeded returns HTTP 429 with clear message
  - Admin interface to adjust rate limits per user

- **NFR-4 Updated:** "Security - Data Protection & OAuth"
  - OAuth 2.0 with Google Sign-In enforced via IAP
  - Only authenticated users can access application endpoints (except /health, /ready)
  - User email and OAuth subject ID stored with session data
  - Session IDs tied to OAuth user ID

- **NFR-6 Updated:** "Cost Management"
  - Per-user rate limits prevent individual abuse: max cost ~$2/user/day at 10 sessions
  - Budget: <$200/month for pilot (10-50 users with limits)
  - Emergency circuit breaker: Disable new sessions if daily cost exceeds $250
  - Cost allocation tags include user_id on Gemini API calls

---

### 2. Technical Architecture

**File:** `docs/gcp-deployment-architecture.md`

**New Section Added:** "OAuth Authentication via Identity-Aware Proxy (IAP) - MVP"

**Key Implementation Details:**
- **IAP Configuration:**
  - OAuth Brand: "Improv Olympics" with support email
  - OAuth Client: Web application type
  - Backend Service: Cloud Run with IAP enabled
  - IAM Policy: Grant `roles/iap.httpsResourceAccessor` to pilot users/groups

- **User Flow:**
  1. User visits https://ai4joy.org
  2. IAP intercepts request, checks for OAuth token
  3. If not authenticated → Redirect to Google Sign-In
  4. User signs in with Google account
  5. IAP validates token and creates signed JWT header
  6. Request forwarded to Cloud Run with IAP headers:
     - `X-Goog-IAP-JWT-Assertion`
     - `X-Goog-Authenticated-User-Email`
     - `X-Goog-Authenticated-User-ID`

- **Application Integration:**
  - Extract user identity from IAP headers
  - Associate all sessions with authenticated user_id
  - Check rate limits before session creation
  - Return 429 if limits exceeded

- **Cost Protection:**
  - Per-user daily limit: 10 sessions/user/day = ~$2/user/day max
  - Concurrent session limit: 3 active sessions/user
  - Firestore `user_limits` collection tracks usage

---

### 3. Infrastructure as Code (Terraform)

**Files Updated:**
- `infrastructure/terraform/main.tf`
- `infrastructure/terraform/variables.tf`
- `infrastructure/terraform/terraform.tfvars.example`

**Changes to main.tf:**

```terraform
# Secret Manager secrets for OAuth
resource "google_secret_manager_secret" "oauth_client_id" {
  secret_id = "oauth-client-id"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret" "oauth_client_secret" {
  secret_id = "oauth-client-secret"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret" "session_secret_key" {
  secret_id = "session-secret-key"
  replication {
    automatic = true
  }
}

# Cloud Run service with OAuth secrets
resource "google_cloud_run_service" "improv_app" {
  # ... existing config ...

  template {
    spec {
      containers {
        env {
          name = "ALLOWED_USERS"
          value = var.allowed_users
        }
        env {
          name = "OAUTH_CLIENT_ID"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.oauth_client_id.secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "OAUTH_CLIENT_SECRET"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.oauth_client_secret.secret_id
              key  = "latest"
            }
          }
        }
        env {
          name = "SESSION_SECRET_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.session_secret_key.secret_id
              key  = "latest"
            }
          }
        }
      }
    }
  }
}
```

**New Variables Added:**

```terraform
variable "allowed_users" {
  description = "Comma-separated list of email addresses allowed to access the application"
  type        = string
}

variable "user_daily_session_limit" {
  description = "Maximum sessions per user per day (cost protection)"
  type        = number
  default     = 10
}

variable "user_concurrent_session_limit" {
  description = "Maximum concurrent active sessions per user"
  type        = number
  default     = 3
}
```

**Configuration Example (terraform.tfvars.example):**

```terraform
# OAuth Configuration - REQUIRED FOR MVP
allowed_users = "pilot1@example.com,pilot2@example.com,admin@ai4joy.org"

user_daily_session_limit      = 10
user_concurrent_session_limit = 3
```

---

### 4. Firestore Data Model

**Collections Updated:**

**sessions collection:**
```json
{
  "session_id": "uuid-v4",
  "user_id": "google-oauth2|1234567890",       // NEW: PRIMARY KEY for rate limiting
  "user_email": "user@example.com",            // NEW: For support/debugging
  "created_at": "Timestamp",
  "updated_at": "Timestamp",
  "status": "active|completed|abandoned",
  "current_phase": "PHASE_1_SUPPORT|PHASE_2_FALLIBLE",
  "turn_count": 7,
  "game_type": "worlds-worst-advice",
  // ... rest of session data
}
```

**user_limits collection (NEW):**
```json
{
  "user_id": "google-oauth2|1234567890",
  "email": "user@example.com",
  "sessions_today": 7,
  "last_reset": "Timestamp(2025-11-23T00:00:00Z)",
  "active_sessions": 2,
  "total_cost_estimate": 14.50  // dollars
}
```

---

### 5. Linear Tickets

#### IQS-45: Infrastructure Setup

**Updates:**
- Added "OAuth Authentication" as critical MVP requirement in business context
- Added 6 new acceptance criteria for Application-Level OAuth setup:
  - [ ] OAuth consent screen created
  - [ ] OAuth 2.0 Client ID created and stored in Secret Manager
  - [ ] Session secret key generated and stored in Secret Manager
  - [ ] ALLOWED_USERS environment variable configured
  - [ ] Firestore user_limits collection created
  - [ ] OAuth flow tested (unauthenticated → sign-in → access granted)

- New OAuth validation section:
  - [ ] Unauthenticated requests return 401 or redirect to /auth/login
  - [ ] Session cookies present after successful login
  - [ ] Only authorized users (in ALLOWED_USERS) can access
  - [ ] User rate limit test (11th session returns 429)

- Added OAuth user management via ALLOWED_USERS environment variable
- Updated implementation notes with OAuth setup in Week 1

#### IQS-46: Multi-Agent Implementation

**Updates:**
- Added "OAuth Integration Required" to business context
- New section: "OAuth Integration & Authentication (Must Have)"
  - [ ] OAuthSessionMiddleware extracting user from session cookies
  - [ ] Auth router with /auth/login, /auth/callback, /auth/logout endpoints
  - [ ] All API endpoints protected (except health checks)
  - [ ] Unauthenticated requests return 401
  - [ ] User identity logged with all operations

- New section: "Per-User Rate Limiting (Must Have)"
  - [ ] `RateLimiter` class checking Firestore user_limits
  - [ ] Daily session limit (10/user/day) enforced
  - [ ] Concurrent session limit (3/user) enforced
  - [ ] HTTP 429 returned when limits exceeded
  - [ ] Admin override capability for testing

- New integration tests:
  - [ ] OAuth test: Request without session cookie returns 401
  - [ ] Rate limit test: 11th session returns 429
  - [ ] Concurrent session test: 4th session returns 429
  - [ ] User isolation test: User A cannot access User B's session

- Added authentication middleware and rate limiting code examples
- Updated cost estimate with rate limiting: ~$100/month (within budget)

#### IQS-47: Production Launch

**Existing Coverage:**
- UX section already mentions "User accounts & authentication" as out of scope
- Testing already includes "Security tests: IAM permissions, secret protection"
- Launch checklist includes "Security scan: No critical vulnerabilities"

**OAuth-Specific Additions Needed (already covered in IQS-45/46):**
- OAuth consent screen UX is handled by Google IAP (no custom UI needed)
- Authentication testing covered in IQS-45 acceptance criteria
- Per-user cost monitoring covered in IQS-46 monitoring requirements

---

### 6. Test Plans

**File:** `tests/GCP_DEPLOYMENT_TEST_PLAN.md`

**OAuth Test Cases to Add:**

#### OAuth Authentication Tests (6 new test cases)

**TC-AUTH-01: Unauthenticated Access Blocked**
- Navigate to https://ai4joy.org without authentication
- Expected: Redirect to Google Sign-In consent screen
- Success: User cannot access application without OAuth

**TC-AUTH-02: OAuth Flow Success**
- Complete Google Sign-In flow with authorized user
- Expected: Redirect back to application with access granted
- Success: User can create sessions and interact with agents

**TC-AUTH-03: Unauthorized User Denied**
- Sign in with Google account NOT in `iap_allowed_users` list
- Expected: 403 Forbidden error with clear message
- Success: Only authorized users can access

**TC-AUTH-04: IAP Headers Present**
- Make authenticated request to Cloud Run
- Expected: Request headers include `X-Goog-Authenticated-User-Email` and `X-Goog-Authenticated-User-ID`
- Success: Application can extract user identity

**TC-AUTH-05: Daily Rate Limit Enforcement**
- Create 10 sessions as User A
- Attempt 11th session
- Expected: HTTP 429 with message "Daily session limit reached (10/10)"
- Success: Rate limiting prevents abuse

**TC-AUTH-06: Concurrent Session Limit**
- Create 3 active sessions for User A
- Attempt 4th concurrent session
- Expected: HTTP 429 with message "Concurrent session limit reached (3/3)"
- Success: Concurrent limits enforced

---

## Implementation Checklist

### Phase 1: Infrastructure (IQS-45)

- [ ] Create OAuth consent screen via GCP Console
- [ ] Create OAuth 2.0 Client ID via GCP Console
- [ ] Store OAuth credentials in Secret Manager (oauth-client-id, oauth-client-secret)
- [ ] Generate and store session secret key in Secret Manager
- [ ] Configure Terraform variables (`allowed_users`)
- [ ] Deploy Terraform (creates Cloud Run service with secrets)
- [ ] Test OAuth flow: Visit ai4joy.org/auth/login → Sign in → Access granted
- [ ] Add pilot users to ALLOWED_USERS environment variable
- [ ] Create Firestore `user_limits` collection

### Phase 2: Application (IQS-46)

- [ ] Implement OAuthSessionMiddleware (checks session cookies)
- [ ] Implement auth router (/auth/login, /auth/callback, /auth/logout)
- [ ] Protect all API endpoints (check request.state.user_email)
- [ ] Implement `RateLimiter` class
- [ ] Check rate limits before session creation
- [ ] Return 429 when limits exceeded
- [ ] Associate sessions with user_id in Firestore
- [ ] Log user_id with all Gemini API calls

### Phase 3: Testing & Launch (IQS-47)

- [ ] Run OAuth authentication test suite (6 test cases)
- [ ] Load test with multiple authenticated users
- [ ] Verify per-user cost tracking in monitoring
- [ ] Test rate limiting under concurrent load
- [ ] Security audit (IAP config, IAM policies)
- [ ] Launch with pilot user group

---

## Cost Protection Summary

**Without OAuth (Anonymous Access):**
- Risk: Unlimited sessions = runaway costs
- Potential: $1000+/month with abuse

**With OAuth + Rate Limiting:**
- 10 users × 10 sessions/day × 30 days = 3,000 sessions/month
- Cost: ~$85/month Gemini API + $15/month infrastructure = **$100/month**
- Maximum per-user cost: $2/day
- Circuit breaker: Disable new sessions at $250/day

**Savings:** 90% cost reduction through rate limiting

---

## OAuth User Management

### Add Users to Whitelist

**Via Terraform (Recommended):**
```bash
# Edit terraform.tfvars
vim infrastructure/terraform/terraform.tfvars

# Update allowed_users:
allowed_users = "user1@example.com,user2@example.com,newuser@example.com"

# Apply changes
terraform apply
```

**Via Direct Cloud Run Update:**
```bash
gcloud run services update improv-olympics-app \
  --region=us-central1 \
  --set-env-vars ALLOWED_USERS="user1@example.com,user2@example.com,newuser@example.com"
```

### Remove Users from Whitelist
Simply remove the email from the ALLOWED_USERS list and redeploy:
```bash
# Via Terraform
vim infrastructure/terraform/terraform.tfvars
# Remove email from allowed_users
terraform apply

# Or via direct update
gcloud run services update improv-olympics-app \
  --region=us-central1 \
  --set-env-vars ALLOWED_USERS="user1@example.com,user2@example.com"
```

---

## Next Steps

1. **Review all updated Linear tickets:**
   - [IQS-45: Infrastructure with OAuth](https://linear.app/iqsubagents/issue/IQS-45)
   - [IQS-46: Multi-Agent with Auth Integration](https://linear.app/iqsubagents/issue/IQS-46)
   - [IQS-47: Production Launch](https://linear.app/iqsubagents/issue/IQS-47)

2. **Configure OAuth settings:**
   - Create OAuth consent screen and client ID in GCP Console
   - Store credentials in Secret Manager
   - Update `infrastructure/terraform/terraform.tfvars` with pilot user emails in `allowed_users`

3. **Begin implementation:**
   - Start with IQS-45 (Infrastructure + OAuth setup)
   - Proceed to IQS-46 once Application-Level OAuth is operational
   - Launch with IQS-47 after full testing

---

## Files Modified

### Documentation
- `docs/improv-olympics-gcp-deployment-prd.md` (Updated: FR-2, FR-11, NFR-4, NFR-6)
- `docs/gcp-deployment-architecture.md` (Added: OAuth/IAP section, updated Firestore schema)
- `docs/OAUTH_INTEGRATION_SUMMARY.md` (New: This file)

### Infrastructure
- `infrastructure/terraform/main.tf` (Added: IAP resources, updated backend service)
- `infrastructure/terraform/variables.tf` (Added: 4 OAuth variables)
- `infrastructure/terraform/terraform.tfvars.example` (Added: OAuth configuration section)

### Linear Tickets
- IQS-45: Updated with OAuth acceptance criteria
- IQS-46: Updated with authentication middleware and rate limiting requirements
- IQS-47: OAuth UX covered by IAP (no custom UI changes needed)

### Test Plans
- OAuth test cases documented in this summary (to be added to test plan)

---

## Questions?

Contact: support@ai4joy.org
Linear Project: [Studycard](https://linear.app/iqsubagents/project/studycard-f71f654a7c5f)
