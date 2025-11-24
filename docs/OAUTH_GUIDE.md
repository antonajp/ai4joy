# Application-Level OAuth 2.0 User Management Guide

> **Note:** This project uses **Application-Level OAuth 2.0** for authentication. See [OAUTH_IMPLEMENTATION_CHANGE.md](OAUTH_IMPLEMENTATION_CHANGE.md) for details on why we chose application-level OAuth over IAP.

Complete guide for managing user access to the Improv Olympics application via Application-Level Google OAuth 2.0.

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

### What is Application-Level OAuth 2.0?

Application-Level OAuth 2.0 provides authentication at the **application layer** using secure session cookies. Unlike IAP (which requires a GCP Organization), this approach works for personal projects and provides:

- Google Sign-In managed by application code (using authlib)
- User identity stored in signed, httponly session cookies
- Per-user cost tracking and rate limiting enabled
- Email whitelist access control

### Authentication Flow

```
User → /auth/login → Google Sign-In → /auth/callback
                                      ↓
                               Check ALLOWED_USERS
                                      ↓
                              Create session cookie
                                      ↓
                              Redirect to app
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

- GCP project with OAuth 2.0 credentials
- Project Owner or Editor role
- Domain name configured in Cloud DNS
- SSL certificate provisioned

### Step 1: Create OAuth Consent Screen

```bash
# Open OAuth consent screen configuration
open "https://console.cloud.google.com/apis/credentials/consent?project=YOUR_PROJECT_ID"
```

**Configuration:**

1. **User Type:**
   - **Internal** (Recommended if using Google Workspace): Only users in your organization
   - **External**: Anyone with a Google account (requires verification for production)

2. **App Information:**
   - App name: `Improv Olympics`
   - Support email: `your-email@example.com`
   - App logo: (optional)

3. **Authorized Domains:**
   - Add: `ai4joy.org`

4. **Scopes:**
   - Add: `email`, `profile`, `openid` (default scopes)

5. **Test Users (External only):**
   - Add pilot test users during development

### Step 2: Create OAuth 2.0 Client ID

```bash
# Open credentials page
open "https://console.cloud.google.com/apis/credentials?project=YOUR_PROJECT_ID"
```

1. Click "Create Credentials" → "OAuth client ID"
2. Application type: **Web application**
3. Name: `Improv Olympics OAuth Client`
4. Authorized redirect URIs:
   - `https://ai4joy.org/auth/callback`
   - `http://localhost:8080/auth/callback` (for local testing)
5. Click "Create"
6. **Download JSON** credentials file

### Step 3: Store Credentials in Secret Manager

```bash
# Extract values from downloaded JSON
CLIENT_ID=$(cat client_secret.json | jq -r '.web.client_id')
CLIENT_SECRET=$(cat client_secret.json | jq -r '.web.client_secret')

# Create secrets
echo -n "$CLIENT_ID" | gcloud secrets create oauth-client-id --data-file=-
echo -n "$CLIENT_SECRET" | gcloud secrets create oauth-client-secret --data-file=-

# Generate session secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))" | \
  gcloud secrets create session-secret-key --data-file=-

# Verify secrets created
gcloud secrets list
```

### Step 4: Configure Terraform Variables

Edit `infrastructure/terraform/terraform.tfvars`:

```terraform
# OAuth Configuration - REQUIRED FOR MVP
allowed_users = "your-email@example.com,pilot1@example.com,pilot2@example.com"

# Per-user rate limits (cost protection)
user_daily_session_limit       = 10  # Max sessions per user per day
user_concurrent_session_limit  = 3   # Max concurrent sessions per user
```

### Step 5: Deploy Infrastructure

```bash
cd infrastructure/terraform

# Preview changes
terraform plan

# Deploy (creates Cloud Run service with secrets)
terraform apply
```

---

## Managing User Access

### Add Users to Whitelist

**Option A: Via Terraform (Recommended)**

```bash
# Edit terraform.tfvars
vim infrastructure/terraform/terraform.tfvars

# Update allowed_users (comma-separated):
allowed_users = "user1@example.com,user2@example.com,newuser@example.com"

# Apply changes
terraform apply
```

**Option B: Direct Cloud Run Update (Quick)**

```bash
# Update environment variable
gcloud run services update improv-olympics-app \
  --region=us-central1 \
  --set-env-vars ALLOWED_USERS="user1@example.com,user2@example.com,newuser@example.com"
```

### Remove Users from Whitelist

Simply remove the email from the `ALLOWED_USERS` list and redeploy:

```bash
# Option A: Terraform
vim infrastructure/terraform/terraform.tfvars
# Remove email from allowed_users
terraform apply

# Option B: Direct update
gcloud run services update improv-olympics-app \
  --region=us-central1 \
  --set-env-vars ALLOWED_USERS="user1@example.com,user2@example.com"
```

### List Current Users

```bash
# View current allowed users
gcloud run services describe improv-olympics-app \
  --region=us-central1 \
  --format='value(spec.template.spec.containers[0].env[?name=="ALLOWED_USERS"].value)'
```

---

## Testing OAuth Flow

### Test 1: Unauthenticated Access

```bash
# Test in incognito/private browser window
open "https://ai4joy.org/api/v1/session/start"

# Expected behavior:
# 1. 401 Unauthorized (no session cookie)
# 2. User must visit /auth/login first
```

### Test 2: OAuth Login Flow

```bash
# Start OAuth flow
open "https://ai4joy.org/auth/login"

# Expected behavior:
# 1. Redirect to Google Sign-In page
# 2. Sign in with authorized Google account
# 3. Redirect to /auth/callback
# 4. Application checks ALLOWED_USERS whitelist
# 5. If authorized: Create session cookie and redirect to app
# 6. If not authorized: Show "Access denied" message
```

### Test 3: Unauthorized User

```bash
# Sign in with account NOT in ALLOWED_USERS list

# Expected behavior:
# 1. Google Sign-In succeeds
# 2. Application checks whitelist
# 3. Returns error: "Access denied. Your email is not authorized."
# 4. No session cookie created
```

### Test 4: Session Cookie Present

After authenticating, check session cookie in browser DevTools:

```javascript
// In browser console
document.cookie
// Should show: session=<signed-token>; HttpOnly; Secure; SameSite=Lax
```

### Test 5: Authenticated API Access

```bash
# After logging in, test protected endpoint
curl -X POST https://ai4joy.org/api/v1/session/start \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{"location":"Test Location"}'

# Expected: {"session_id": "...", ...}
```

---

## Per-User Rate Limiting

### Overview

Rate limiting is enforced **in the application code** using user identity from session cookies.

### Configuration

Set limits in `terraform.tfvars`:

```terraform
user_daily_session_limit       = 10  # Max sessions per user per day
user_concurrent_session_limit  = 3   # Max concurrent active sessions
```

### Firestore Schema

**Collection: `user_limits`**

Document ID: `{user_id}` (from OAuth)

```json
{
  "user_id": "google-oauth2|1234567890",
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
  curl -X POST https://ai4joy.org/api/v1/session/start \
    -H "Cookie: session=YOUR_SESSION_COOKIE" \
    -d '{"location":"Test"}' &
done

# Attempt 11th session
curl -X POST https://ai4joy.org/api/v1/session/start \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{"location":"Test"}'

# Expected: HTTP 429 Too Many Requests
# Response: {"detail": "Daily session limit reached (10/10). Try again tomorrow."}
```

### Admin Override (Development Only)

To bypass rate limits for testing:

```bash
# Delete user limit document in Firestore
gcloud firestore documents delete "user_limits/google-oauth2|1234567890"
```

---

## Troubleshooting

### Problem: "OAuth client not configured" error

**Cause:** OAuth credentials not in Secret Manager

**Solution:**
```bash
# Verify secrets exist
gcloud secrets list | grep oauth

# If missing, create them (see Step 3 above)
```

---

### Problem: "Access denied" after signing in

**Possible Causes:**

1. **User email not in ALLOWED_USERS**
   ```bash
   # Check current allowed users
   gcloud run services describe improv-olympics-app \
     --region=us-central1 \
     --format='value(spec.template.spec.containers[0].env[?name=="ALLOWED_USERS"].value)'

   # Add user to whitelist
   gcloud run services update improv-olympics-app \
     --region=us-central1 \
     --update-env-vars ALLOWED_USERS="user1@example.com,newuser@example.com"
   ```

2. **Email case mismatch**
   - Ensure emails in ALLOWED_USERS match exactly (including case)

---

### Problem: Redirect loop during sign-in

**Possible Causes:**

1. **SSL certificate not active**
   ```bash
   gcloud compute ssl-certificates describe improv-cert --global
   # Status should be: ACTIVE
   ```

2. **Redirect URI mismatch**
   - Visit: https://console.cloud.google.com/apis/credentials
   - Check "Authorized redirect URIs" includes: `https://ai4joy.org/auth/callback`

3. **Session secret not configured**
   ```bash
   # Verify session secret exists
   gcloud secrets versions access latest --secret=session-secret-key
   ```

---

### Problem: Session expires too quickly

**Cause:** Session cookie expiration set too short

**Solution:**
Check session expiration in application code:
```python
# In app/routers/auth.py
expires = datetime.utcnow() + timedelta(hours=24)  # 24-hour expiration
```

---

## Best Practices

### 1. Use Descriptive Email Addresses

Keep ALLOWED_USERS organized:
```terraform
allowed_users = "admin@ai4joy.org,pilot1@example.com,pilot2@example.com"
```

### 2. Monitor User Activity

Track user sessions in Firestore:

```bash
# Query user sessions
gcloud firestore documents list user_limits \
  --format="table(name,sessions_today,total_cost_estimate)"
```

### 3. Set Up Cost Alerts

Configure budget alerts in Terraform:

```terraform
# Already configured in main.tf
# Alert at 50%, 90%, 100% of budget
```

### 4. Regular Access Reviews

Review allowed users quarterly:

```bash
# Export current allowed users
gcloud run services describe improv-olympics-app \
  --region=us-central1 \
  --format='value(spec.template.spec.containers[0].env[?name=="ALLOWED_USERS"].value)' \
  > allowed_users_$(date +%Y%m%d).txt
```

### 5. Test in Incognito/Private Browsing

Always test OAuth flow in incognito mode to avoid cached credentials.

### 6. Rotate Secrets Regularly

Rotate OAuth credentials and session secrets quarterly:

```bash
# Generate new session secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))" | \
  gcloud secrets versions add session-secret-key --data-file=-

# Redeploy application to use new secret
terraform apply
```

---

## Support

### Documentation
- OAuth Implementation Change: [OAUTH_IMPLEMENTATION_CHANGE.md](OAUTH_IMPLEMENTATION_CHANGE.md)
- GCP Deployment Architecture: [gcp-deployment-architecture.md](gcp-deployment-architecture.md)
- Deployment Guide: [../DEPLOYMENT.md](../DEPLOYMENT.md)

### Console Links
- OAuth Credentials: https://console.cloud.google.com/apis/credentials
- OAuth Consent Screen: https://console.cloud.google.com/apis/credentials/consent
- Secret Manager: https://console.cloud.google.com/security/secret-manager
- Cloud Logging: https://console.cloud.google.com/logs

### Getting Help
1. Check troubleshooting section above
2. Review Cloud Logging for error messages
3. Contact: support@ai4joy.org

---

**Document Version:** 2.0 (Application-Level OAuth)
**Last Updated:** 2025-11-24
**Maintained by:** ai4joy.org team
