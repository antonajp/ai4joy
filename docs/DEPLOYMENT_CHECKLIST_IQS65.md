# Deployment Checklist: IQS-65 Phase 4

**Ticket**: IQS-65 - Firebase Authentication, MFA, and Freemium Tier
**Deployment Date**: _________________
**Deployed By**: _________________

---

## Pre-Deployment Verification

### 1. Integration Tests ✅
- [ ] All integration tests pass (`pytest tests/test_integration_iqs65.py -v`)
- [ ] Phase 1 (Firebase Auth) tests pass
- [ ] Phase 2 (MFA) tests pass
- [ ] Phase 3 (Freemium) tests pass
- [ ] End-to-end user journey tests pass
- [ ] Security/race condition tests pass

### 2. Unit Tests ✅
- [ ] Firebase auth service tests pass
- [ ] MFA service tests pass
- [ ] Freemium session limiter tests pass
- [ ] Middleware tests pass

---

## Google Cloud Platform Configuration

### 3. Firebase Project Setup ⚠️ CRITICAL
- [ ] **Firebase project created** (or using existing project)
  - Project ID: `_______________________`
  - Project Number: `_______________________`

- [ ] **Firebase Admin SDK enabled**
  ```bash
  # Download service account key from Firebase Console:
  # Project Settings → Service Accounts → Generate New Private Key
  ```

- [ ] **Firebase APIs enabled in GCP**
  ```bash
  gcloud services enable identitytoolkit.googleapis.com --project=PROJECT_ID
  gcloud services enable firebase.googleapis.com --project=PROJECT_ID
  ```

- [ ] **Firebase Authentication providers enabled**
  - Google Sign-In enabled
  - Email/Password enabled
  - Email verification templates configured

### 4. Secret Manager Configuration ⚠️ CRITICAL
- [ ] **Firebase service account key uploaded**
  ```bash
  # Upload firebase-admin-sdk.json to Secret Manager
  gcloud secrets create firebase-admin-sdk \
    --data-file=firebase-admin-sdk.json \
    --project=PROJECT_ID
  ```

- [ ] **Firebase Web API key stored**
  ```bash
  # Get from Firebase Console → Project Settings → Web API Key
  gcloud secrets create firebase-web-api-key \
    --data-file=- <<< "YOUR_WEB_API_KEY" \
    --project=PROJECT_ID
  ```

- [ ] **Verify secrets exist**
  ```bash
  gcloud secrets list --project=PROJECT_ID | grep firebase
  ```

### 5. IAM Permissions ⚠️ CRITICAL
- [ ] **Cloud Run service account has Secret Manager access**
  ```bash
  # Grant secret accessor role
  gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor"
  ```

- [ ] **Service account can access Firestore**
  ```bash
  # Grant Firestore user role (should already be set)
  gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
    --role="roles/datastore.user"
  ```

### 6. Firestore Database Setup
- [ ] **Users collection exists** with indexes:
  - Index on `email` (ascending) - Single field
  - Index on `user_id` (ascending) - Single field
  - Index on `tier` (ascending) - Single field

- [ ] **MFA enrollments collection created**:
  - Collection name: `mfa_enrollments`
  - TTL policy: 15 minutes (for temporary enrollment data)

- [ ] **Firestore indexes created**
  ```bash
  # If using firestore.indexes.json:
  gcloud firestore indexes create --database=default --project=PROJECT_ID
  ```

---

## Cloud Run Deployment Configuration

### 7. Environment Variables ⚠️ CRITICAL

Update Cloud Run service with required environment variables:

```bash
# Deploy with environment variables
gcloud run services update improv-olympics \
  --update-env-vars="FIREBASE_AUTH_ENABLED=true" \
  --update-env-vars="FIREBASE_REQUIRE_EMAIL_VERIFICATION=true" \
  --update-env-vars="USE_FIRESTORE_AUTH=true" \
  --region=us-central1 \
  --project=PROJECT_ID
```

**Required Environment Variables**:
- [ ] `FIREBASE_AUTH_ENABLED=true`
- [ ] `FIREBASE_REQUIRE_EMAIL_VERIFICATION=true` (set to `false` for testing)
- [ ] `USE_FIRESTORE_AUTH=true`
- [ ] `FIRESTORE_USERS_COLLECTION=users`
- [ ] `GOOGLE_CLOUD_PROJECT=PROJECT_ID`

**Existing Variables** (verify these remain set):
- [ ] `OAUTH_CLIENT_ID` (for backward compatibility)
- [ ] `OAUTH_CLIENT_SECRET` (for backward compatibility)
- [ ] `OAUTH_REDIRECT_URI` (for backward compatibility)

### 8. Cloud Run Secret Mounts ⚠️ CRITICAL

Mount secrets to Cloud Run service:

```bash
# Mount Firebase Admin SDK secret
gcloud run services update improv-olympics \
  --update-secrets="/secrets/firebase-admin-sdk.json=firebase-admin-sdk:latest" \
  --region=us-central1 \
  --project=PROJECT_ID

# Set environment variable pointing to mounted secret
gcloud run services update improv-olympics \
  --update-env-vars="GOOGLE_APPLICATION_CREDENTIALS=/secrets/firebase-admin-sdk.json" \
  --region=us-central1 \
  --project=PROJECT_ID
```

- [ ] Firebase Admin SDK secret mounted
- [ ] `GOOGLE_APPLICATION_CREDENTIALS` points to mounted secret

---

## Application Code Deployment

### 9. Docker Image Build & Push
- [ ] **Build Docker image with IQS-65 changes**
  ```bash
  # From project root
  docker build -t gcr.io/PROJECT_ID/improv-olympics:iqs65 .
  ```

- [ ] **Push to Google Container Registry**
  ```bash
  docker push gcr.io/PROJECT_ID/improv-olympics:iqs65
  ```

- [ ] **Deploy to Cloud Run**
  ```bash
  gcloud run deploy improv-olympics \
    --image=gcr.io/PROJECT_ID/improv-olympics:iqs65 \
    --region=us-central1 \
    --project=PROJECT_ID
  ```

### 10. Middleware Integration
- [ ] **Verify middleware order in `app/main.py`**:
  1. OAuthSessionMiddleware (handles session cookies)
  2. MFAEnforcementMiddleware (checks MFA requirements)
  3. OAuthAuthMiddleware (validates authentication)

- [ ] **Verify MFA-protected endpoints** configured:
  - `/api/v1/sessions` (creating improv sessions)
  - `/api/v1/user/me` (viewing user profile)
  - `/api/v1/turn` (executing turns)
  - WebSocket `/ws/audio` (audio streaming)

---

## Frontend Configuration

### 11. Firebase SDK Configuration
- [ ] **Add Firebase config to frontend** (`frontend/.env` or config file):
  ```javascript
  REACT_APP_FIREBASE_API_KEY=YOUR_WEB_API_KEY
  REACT_APP_FIREBASE_AUTH_DOMAIN=PROJECT_ID.firebaseapp.com
  REACT_APP_FIREBASE_PROJECT_ID=PROJECT_ID
  ```

- [ ] **Firebase Authentication UI integrated**:
  - Sign up with email/password
  - Sign up with Google
  - Email verification flow
  - MFA enrollment wizard
  - MFA verification prompt

- [ ] **Session counter displayed for freemium users**:
  - Format: "🎤 1/2 [Upgrade]"
  - Shown in header when authenticated
  - Updates after each audio session

- [ ] **Upgrade modal implemented**:
  - Shown when freemium limit reached
  - Clear upgrade CTA
  - Link to pricing/payment page

---

## Post-Deployment Verification

### 12. Smoke Tests ⚠️ CRITICAL

**Test 1: New User Signup (Freemium)**
- [ ] Navigate to signup page
- [ ] Sign up with new email + password
- [ ] Receive email verification link
- [ ] Click verification link
- [ ] Redirected to app with FREEMIUM tier
- [ ] Session counter shows "🎤 0/2"

**Test 2: MFA Enrollment**
- [ ] Login with verified account
- [ ] Navigate to MFA enrollment
- [ ] Scan QR code with Google Authenticator
- [ ] Save 8 recovery codes
- [ ] Enter TOTP code to confirm
- [ ] MFA enabled successfully

**Test 3: MFA Verification on Login**
- [ ] Logout
- [ ] Login with email + password
- [ ] Prompted for TOTP code
- [ ] Enter code from authenticator app
- [ ] Successfully authenticated

**Test 4: Freemium Audio Sessions**
- [ ] Start 1st audio session (works)
- [ ] Complete 1st session → counter shows "🎤 1/2"
- [ ] Start 2nd audio session (works)
- [ ] Complete 2nd session → counter shows "🎤 2/2"
- [ ] Attempt 3rd audio session → **BLOCKED**
- [ ] Upgrade modal displayed

**Test 5: Premium User Unlimited Access**
- [ ] Manually upgrade user to PREMIUM tier in Firestore
- [ ] Login
- [ ] No session counter displayed
- [ ] Audio sessions work unlimited times

**Test 6: Recovery Code Flow**
- [ ] Login with MFA-enabled account
- [ ] Select "Use recovery code" option
- [ ] Enter one of 8 recovery codes
- [ ] Successfully authenticated
- [ ] Recovery code consumed (7 remaining)

**Test 7: OAuth Migration**
- [ ] Login with existing OAuth user (pre-Firebase)
- [ ] User migrated to Firebase automatically
- [ ] Tier and history preserved
- [ ] Can enroll in MFA

### 13. Performance & Security Checks
- [ ] **Load testing**: 100 concurrent users
- [ ] **Session increment race condition** tested (multiple tabs)
- [ ] **MFA timing attack** prevention verified (constant-time comparison)
- [ ] **Recovery code reuse** blocked
- [ ] **Unverified email** blocked from app access
- [ ] **Expired tokens** rejected properly

### 14. Monitoring & Alerts
- [ ] **Cloud Logging filters created**:
  - Firebase auth errors
  - MFA enrollment/verification events
  - Freemium session limit events
  - Recovery code usage

- [ ] **Error alerts configured**:
  - Firebase token verification failures > 10/min
  - MFA verification failures > 20/min
  - Session increment failures > 5/min

- [ ] **Business metrics dashboards**:
  - Daily signups (Firebase vs OAuth)
  - MFA enrollment rate
  - Freemium → Premium conversion rate
  - Average sessions before limit

---

## Rollback Plan

### 15. Emergency Rollback Procedure ⚠️
If critical issues occur, rollback steps:

1. **Disable Firebase authentication**:
   ```bash
   gcloud run services update improv-olympics \
     --update-env-vars="FIREBASE_AUTH_ENABLED=false" \
     --region=us-central1 \
     --project=PROJECT_ID
   ```

2. **Rollback to previous Cloud Run revision**:
   ```bash
   # List revisions
   gcloud run revisions list --service=improv-olympics --region=us-central1

   # Rollback to specific revision
   gcloud run services update-traffic improv-olympics \
     --to-revisions=PREVIOUS_REVISION=100 \
     --region=us-central1 \
     --project=PROJECT_ID
   ```

3. **Disable MFA enforcement** (if needed):
   - Comment out `MFAEnforcementMiddleware` in `app/main.py`
   - Redeploy

---

## Sign-Off

### Deployment Team Sign-Off
- [ ] **Engineering Lead**: _____________________ Date: _______
- [ ] **QA Lead**: _____________________ Date: _______
- [ ] **DevOps/SRE**: _____________________ Date: _______
- [ ] **Product Manager**: _____________________ Date: _______

### Post-Deployment Review (24 hours after deployment)
- [ ] **No critical errors** in last 24 hours
- [ ] **Smoke tests passed** in production
- [ ] **User metrics** tracked and within expected ranges:
  - Firebase signups: _______
  - MFA enrollment rate: _______
  - Freemium limit hits: _______
  - Support tickets: _______

---

## Additional Resources

- **Runbook**: `/docs/RUNBOOK_IQS65.md` (create if needed)
- **Firebase Console**: https://console.firebase.google.com/project/PROJECT_ID
- **GCP Console**: https://console.cloud.google.com/project/PROJECT_ID
- **Cloud Run Logs**: https://console.cloud.google.com/run/detail/REGION/SERVICE_NAME/logs
- **Firestore Console**: https://console.cloud.google.com/firestore/data

---

## Notes / Issues Encountered

```
(Record any issues or deviations from this checklist during deployment)




```
