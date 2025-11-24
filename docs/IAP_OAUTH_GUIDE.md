# IAP OAuth User Management Guide

Complete guide for managing user access to the Improv Olympics application via Google Cloud Identity-Aware Proxy (IAP).

## Table of Contents

1. [Overview](#overview)
2. [Initial OAuth Setup](#initial-oauth-setup)
3. [Managing User Access](#managing-user-access)
4. [Testing OAuth Flow](#testing-oauth-flow)
5. [Per-User Rate Limiting](#per-user-rate-limiting)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## Overview

### What is IAP?

Identity-Aware Proxy (IAP) provides OAuth 2.0 authentication at the load balancer level, **before** requests reach your Cloud Run application. This means:

- No application code changes required for authentication
- Google Sign-In managed entirely by Google
- User identity passed to application via secure HTTP headers
- Per-user cost tracking and rate limiting enabled

### Authentication Flow

```
User → Load Balancer → IAP Check → Authenticated?
                                      ├─ No  → Google Sign-In
                                      └─ Yes → Forward to Cloud Run
                                                (with IAP headers)
```

### Cost Protection Strategy

**Without OAuth:**
- Anonymous access = unlimited sessions
- Potential cost: $1000+/month with abuse

**With OAuth + Rate Limiting:**
- 10 users × 10 sessions/day × 30 days = 3,000 sessions/month
- Estimated cost: $100/month
- Per-user maximum: $2/day (10 sessions × $0.20/session)

---

## Initial OAuth Setup

### Prerequisites

- GCP project with IAP API enabled
- Project Owner or Editor role
- Domain name configured in Cloud DNS
- SSL certificate provisioned

### Step 1: Create OAuth Consent Screen (One-Time)

**IMPORTANT:** This step **must** be done manually via GCP Console. Terraform cannot create the first OAuth brand.

```bash
# Open OAuth consent screen
open "https://console.cloud.google.com/apis/credentials/consent?project=YOUR_PROJECT_ID"
```

**Configuration:**

1. **User Type:**
   - **Internal** (Recommended if using Google Workspace): Only users in your organization can sign in
   - **External**: Anyone with a Google account can request access

2. **App Information:**
   - App name: `Improv Olympics`
   - Support email: `your-email@example.com` (or your email)
   - App logo: (optional)

3. **Developer Contact:**
   - Email addresses: `your-email@example.com`

4. **Scopes:**
   - Skip this section (click "Save and Continue")

5. **Test Users (External only):**
   - Skip if using Internal type
   - Add test users if External

6. **Summary:**
   - Review and click "Back to Dashboard"

### Step 2: Configure Terraform Variables

Edit `/Users/jpantona/Documents/code/ai4joy/infrastructure/terraform/terraform.tfvars`:

```terraform
# OAuth / IAP Configuration - REQUIRED FOR MVP
iap_support_email = "your-email@example.com"  # Must match OAuth consent screen

iap_allowed_users = [
  "user:your-email@example.com",
  "user:pilot1@example.com",
  # Add more pilot testers:
  # "user:tester1@example.com",
  # "user:tester2@example.com",
  # "group:improv-testers@ai4joy.org",  # Recommended: use Google Group
]

# Per-user rate limits (cost protection)
user_daily_session_limit       = 10  # Max sessions per user per day
user_concurrent_session_limit  = 3   # Max concurrent sessions per user
```

### Step 3: Deploy IAP Configuration

```bash
cd infrastructure/terraform

# Preview IAP resources
terraform plan | grep -A 10 "google_iap"

# Deploy (creates IAP client and configures backend)
terraform apply
```

**Resources Created:**
- IAP OAuth Client (uses existing OAuth brand)
- IAP configuration on backend service
- IAM binding granting IAP access to specified users

### Step 4: Verify IAP Configuration

```bash
# Check IAP status
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=improv-backend

# Test authentication
curl -I https://ai4joy.org
# Expected: 302 redirect to Google Sign-In (if not authenticated)

# Test health endpoint (should work without auth)
curl https://ai4joy.org/health
# Expected: {"status": "healthy"}
```

---

## Managing User Access

### Add Individual User

Grant access to a specific user:

```bash
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=improv-backend \
  --member='user:newuser@example.com' \
  --role='roles/iap.httpsResourceAccessor'
```

### Add Google Group (Recommended)

**Why use groups?**
- Easier management (add/remove users in one place)
- No infrastructure changes needed
- Supports Google Workspace groups

**Step 1:** Create Google Group
```bash
# Via Google Admin Console (if using Workspace)
# Or via Google Groups: https://groups.google.com
# Group email: improv-testers@ai4joy.org
```

**Step 2:** Grant IAP access to group
```bash
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=improv-backend \
  --member='group:improv-testers@ai4joy.org' \
  --role='roles/iap.httpsResourceAccessor'
```

**Step 3:** Add users to group
- Via Google Admin Console (Workspace)
- Via Google Groups interface
- No GCP changes needed

### Add Entire Domain (Google Workspace Only)

Grant access to all users in your Google Workspace domain:

```bash
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=improv-backend \
  --member='domain:ai4joy.org' \
  --role='roles/iap.httpsResourceAccessor'
```

**Warning:** Use with caution in production. Consider using groups for better control.

### Remove User Access

Revoke access for a specific user:

```bash
gcloud iap web remove-iam-policy-binding \
  --resource-type=backend-services \
  --service=improv-backend \
  --member='user:remove@example.com' \
  --role='roles/iap.httpsResourceAccessor'
```

### List Current Users

View all users with IAP access:

```bash
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=improv-backend
```

### Update Via Terraform (Alternative)

Add users to `/Users/jpantona/Documents/code/ai4joy/infrastructure/terraform/terraform.tfvars`:

```terraform
iap_allowed_users = [
  "user:your-email@example.com",
  "user:pilot1@example.com",
  "user:newuser@example.com",           # Add new user
  "group:improv-testers@ai4joy.org",    # Add group
]
```

Then apply:

```bash
cd infrastructure/terraform
terraform apply
```

**Note:** This replaces the entire IAP policy. Use gcloud for incremental changes.

---

## Testing OAuth Flow

### Test 1: Unauthenticated Access

```bash
# Test in incognito/private browser window
open "https://ai4joy.org"

# Expected behavior:
# 1. Redirect to Google Sign-In page
# 2. Sign in with authorized Google account
# 3. Redirect back to application
# 4. Access granted
```

### Test 2: Unauthorized User

```bash
# Sign in with account NOT in iap_allowed_users list

# Expected behavior:
# 1. Google Sign-In succeeds
# 2. IAP returns 403 Forbidden error
# 3. Message: "You don't have access to this app. Contact your administrator."
```

### Test 3: Health Check Bypass

```bash
# Health checks should work without authentication
curl https://ai4joy.org/health
# Expected: {"status": "healthy"}

curl https://ai4joy.org/ready
# Expected: {"status": "ready"}
```

### Test 4: IAP Headers Present

After authenticating, check that application receives IAP headers:

```bash
# View application logs
gcloud run services logs read improv-olympics-app \
  --region=us-central1 \
  --limit=10

# Look for IAP headers in logs:
# X-Goog-Authenticated-User-Email: accounts.google.com:user@example.com
# X-Goog-Authenticated-User-ID: accounts.google.com:1234567890
# X-Goog-IAP-JWT-Assertion: eyJhbGc...
```

---

## Per-User Rate Limiting

### Overview

Rate limiting is enforced **in the application code** (not by IAP) using user identity from IAP headers.

### Configuration

Set limits in `terraform.tfvars`:

```terraform
user_daily_session_limit       = 10  # Max sessions per user per day
user_concurrent_session_limit  = 3   # Max concurrent active sessions
```

### Firestore Schema

**Collection: `user_limits`**

Document ID: `{user_id}` (from IAP header)

```json
{
  "user_id": "accounts.google.com:1234567890",
  "email": "user@example.com",
  "sessions_today": 7,
  "last_reset": "2025-11-23T00:00:00Z",
  "active_sessions": 2,
  "total_cost_estimate": 14.50
}
```

### Testing Rate Limits

**Test Daily Limit:**

```bash
# Create 10 sessions as authorized user
for i in {1..10}; do
  curl -X POST https://ai4joy.org/api/v1/session \
    -H "Cookie: YOUR_SESSION_COOKIE" \
    -d '{"user_id":"test","location":"Test"}' &
done

# Attempt 11th session
curl -X POST https://ai4joy.org/api/v1/session \
  -H "Cookie: YOUR_SESSION_COOKIE" \
  -d '{"user_id":"test","location":"Test"}'

# Expected: HTTP 429 Too Many Requests
# Response: {"error": "Daily session limit reached (10/10). Try again tomorrow."}
```

**Test Concurrent Limit:**

```bash
# Create 3 concurrent sessions
# Attempt 4th concurrent session

# Expected: HTTP 429 Too Many Requests
# Response: {"error": "Concurrent session limit reached (3/3). Please complete an existing session first."}
```

### Admin Override (Development Only)

To bypass rate limits for testing:

```bash
# Delete user limit document in Firestore
gcloud firestore documents delete \
  "user_limits/accounts.google.com:1234567890"
```

---

## Troubleshooting

### Problem: "OAuth brand not found" error in Terraform

**Cause:** OAuth consent screen not created manually

**Solution:**
1. Visit https://console.cloud.google.com/apis/credentials/consent
2. Create OAuth consent screen (see Step 1 above)
3. Run `terraform apply` again

---

### Problem: 403 Forbidden after signing in

**Possible Causes:**

1. **User not in allowed list**
   ```bash
   # Check current IAP policy
   gcloud iap web get-iam-policy \
     --resource-type=backend-services \
     --service=improv-backend

   # Add user
   gcloud iap web add-iam-policy-binding \
     --resource-type=backend-services \
     --service=improv-backend \
     --member='user:youruser@example.com' \
     --role='roles/iap.httpsResourceAccessor'
   ```

2. **IAP not enabled on backend service**
   ```bash
   # Check backend service configuration
   gcloud compute backend-services describe improv-backend --global

   # Look for "iap" section
   # If missing, run: terraform apply
   ```

3. **IAM policy propagation delay**
   - Wait 1-2 minutes after adding user
   - Clear browser cookies and try again

---

### Problem: Redirect loop during sign-in

**Possible Causes:**

1. **SSL certificate not active**
   ```bash
   gcloud compute ssl-certificates describe improv-cert --global
   # Status should be: ACTIVE
   ```

2. **DNS not configured**
   ```bash
   dig ai4joy.org
   # Should point to load balancer IP
   ```

3. **OAuth redirect URI mismatch**
   - Visit IAP console: https://console.cloud.google.com/security/iap
   - Check "Authorized redirect URIs" includes: `https://ai4joy.org/_gcp_gatekeeper/authenticate`

---

### Problem: Health checks failing

**Cause:** IAP blocking health check probes

**Solution:**
Health checks are configured to bypass IAP in Cloud Armor. Verify:

```bash
gcloud compute security-policies describe improv-security-policy
# Look for rule allowing /health and /ready paths
```

If missing, update Terraform and reapply (already fixed in latest code).

---

### Problem: IAP headers not present in application

**Possible Causes:**

1. **Request not going through load balancer**
   ```bash
   # Always use: https://ai4joy.org
   # NOT: https://improv-olympics-app-xxx.run.app (direct Cloud Run URL)
   ```

2. **Cloud Run IAM misconfigured**
   ```bash
   # Check Cloud Run IAM
   gcloud run services get-iam-policy improv-olympics-app --region=us-central1

   # Should include IAP service account, NOT allUsers
   ```

---

## Best Practices

### 1. Use Google Groups for Access Management

**Benefits:**
- Centralized user management
- No infrastructure changes needed
- Supports nested groups
- Easier onboarding/offboarding

**Setup:**
```bash
# Create group: improv-testers@ai4joy.org
# Add users to group via Google Admin Console or Groups UI
# Grant IAP access to group once:
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=improv-backend \
  --member='group:improv-testers@ai4joy.org' \
  --role='roles/iap.httpsResourceAccessor'
```

### 2. Use Internal User Type (Google Workspace)

If your organization uses Google Workspace:
- Set OAuth consent screen to "Internal"
- Only users in your domain can sign in
- No "unverified app" warning
- Simpler compliance

### 3. Monitor User Activity

Track user sessions in Firestore:

```bash
# Query user sessions
gcloud firestore documents list user_limits \
  --format="table(name,sessions_today,total_cost_estimate)"

# View user session details
gcloud firestore documents describe \
  "user_limits/accounts.google.com:1234567890"
```

### 4. Set Up Cost Alerts

Configure budget alerts in Terraform:

```terraform
# Already configured in main.tf
# Alert at 50%, 90%, 100% of budget
```

Monitor costs by user:

```bash
# View Cloud Logging for cost tracking
gcloud logging read "jsonPayload.user_id:*" \
  --limit=50 \
  --format=json
```

### 5. Regular Access Reviews

Review IAP access quarterly:

```bash
# Export current IAP policy
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=improv-backend \
  --format=json > iap_policy_$(date +%Y%m%d).json

# Review and remove inactive users
```

### 6. Test in Incognito/Private Browsing

Always test OAuth flow in incognito mode to avoid cached credentials:

```bash
# Chrome: Cmd+Shift+N (Mac) or Ctrl+Shift+N (Windows/Linux)
# Firefox: Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows/Linux)
# Safari: Cmd+Shift+N (Mac)
```

### 7. Document Emergency Access Procedures

Keep a runbook for emergency access:

```bash
# Grant emergency access to on-call engineer
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=improv-backend \
  --member='user:oncall@ai4joy.org' \
  --role='roles/iap.httpsResourceAccessor'

# Remove after incident
gcloud iap web remove-iam-policy-binding \
  --resource-type=backend-services \
  --service=improv-backend \
  --member='user:oncall@ai4joy.org' \
  --role='roles/iap.httpsResourceAccessor'
```

---

## Support

### GCP IAP Documentation
- IAP Overview: https://cloud.google.com/iap/docs/concepts-overview
- IAP Setup: https://cloud.google.com/iap/docs/enabling-cloud-run
- IAP Troubleshooting: https://cloud.google.com/iap/docs/troubleshooting

### Console Links
- IAP Dashboard: https://console.cloud.google.com/security/iap
- OAuth Consent Screen: https://console.cloud.google.com/apis/credentials/consent
- Cloud Logging: https://console.cloud.google.com/logs

### Getting Help
1. Check troubleshooting section above
2. Review Cloud Logging for error messages
3. Contact: support@ai4joy.org

---

**Document Version:** 1.0
**Last Updated:** 2025-11-23
**Maintained by:** ai4joy.org team
