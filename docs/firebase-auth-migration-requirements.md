# Firebase Authentication Migration - Infrastructure & Deployment Requirements

**Feature**: Migrate from Google OAuth to Firebase Authentication with open user signup, mandatory MFA, and auto-created Firestore user records with freemium tier.

**Project**: Improv Olympics (coherent-answer-479115-e1)
**Current Region**: us-central1
**Current Auth**: Custom OAuth via Authlib + Session Cookies
**Target**: Firebase Authentication with Email/Password + Google Sign-In

---

## Executive Summary

This migration transforms the authentication system from custom Google OAuth implementation to Firebase Authentication, enabling:
- **Open user signup** (no pre-approval required)
- **Multi-factor authentication (MFA)** enforced for all users
- **Auto-provisioning** of Firestore user records with freemium tier on first login
- **Unified authentication** leveraging Firebase's built-in security and session management

**Estimated Effort**: 2-3 days
**Downtime Required**: None (zero-downtime migration possible)
**Cost Impact**: Minimal (~$0.01-0.05/month for authentication, within free tier for most usage)

---

## 1. Firebase Authentication Setup

### 1.1 Firebase Project Configuration

**Check if Firebase is already initialized for this GCP project:**

```bash
# Check if Firebase is already enabled
gcloud services list --enabled --project=coherent-answer-479115-e1 | grep firebase

# If Firebase APIs are not enabled, enable them
gcloud services enable \
  firebase.googleapis.com \
  firebaseauth.googleapis.com \
  identitytoolkit.googleapis.com \
  --project=coherent-answer-479115-e1
```

**Initialize Firebase for the project (if not already done):**

Firebase projects are typically linked to GCP projects. Use the Firebase Console:
1. Go to https://console.firebase.google.com/
2. Add project → Select existing GCP project: `coherent-answer-479115-e1`
3. Confirm Firebase billing plan (Spark/Free tier is sufficient)

**Alternative: Use Firebase CLI**

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login and initialize
firebase login
firebase projects:list  # Verify project exists
firebase use coherent-answer-479115-e1
```

### 1.2 Enable Authentication Providers

**Required Providers:**
1. **Email/Password** (for new user signup)
2. **Google** (optional, for existing users and convenience)

**Steps via Firebase Console:**
1. Navigate to: https://console.firebase.google.com/project/coherent-answer-479115-e1/authentication/providers
2. Enable **Email/Password** sign-in method
3. Enable **Google** sign-in method (uses existing OAuth consent screen)

**Steps via gcloud CLI:**

```bash
# Enable email/password authentication
gcloud alpha identity platforms tenants create \
  --display-name="Improv Olympics Users" \
  --project=coherent-answer-479115-e1

# Note: Identity Platform is Firebase Authentication's backend
# Configuration is primarily done via Firebase Console or Admin SDK
```

### 1.3 Multi-Factor Authentication (MFA) Configuration

**MFA Options:**
- **TOTP (Time-based One-Time Password)**: Google Authenticator, Authy, etc. ✅ Recommended
- **SMS**: Requires phone number, incurs SMS costs (~$0.01-0.05/verification)

**Enable MFA (Firebase Console):**
1. Go to: Authentication → Sign-in method → Advanced → Multi-factor authentication
2. Enable MFA enrollment: **Required for all users**
3. Allowed second factors: ✅ TOTP (free), ⬜ SMS (optional, costs apply)

**MFA Enforcement Strategy:**
- **Soft launch**: Optional MFA for 1 week to allow users to set up
- **Hard enforcement**: Required MFA after grace period (configurable via backend logic)

**Backend MFA Validation:**
Firebase Admin SDK automatically validates MFA during authentication. No custom validation needed.

### 1.4 Firebase Admin SDK Setup

**Service Account Creation:**

Firebase Admin SDK requires a service account with Firebase Admin privileges.

```bash
# Create service account for Firebase Admin SDK
gcloud iam service-accounts create firebase-admin \
  --display-name="Firebase Admin SDK Service Account" \
  --project=coherent-answer-479115-e1

# Grant Firebase Admin role
gcloud projects add-iam-policy-binding coherent-answer-479115-e1 \
  --member="serviceAccount:firebase-admin@coherent-answer-479115-e1.iam.gserviceaccount.com" \
  --role="roles/firebase.admin"

# Grant Firestore access (for user record creation)
gcloud projects add-iam-policy-binding coherent-answer-479115-e1 \
  --member="serviceAccount:firebase-admin@coherent-answer-479115-e1.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

# Generate service account key (for local development only)
gcloud iam service-accounts keys create firebase-admin-key.json \
  --iam-account=firebase-admin@coherent-answer-479115-e1.iam.gserviceaccount.com \
  --project=coherent-answer-479115-e1

# ⚠️ IMPORTANT: Do NOT commit this key to version control
# Store in Secret Manager for production (see Section 4)
```

**Cloud Run Service Account Update:**

Grant Firebase Admin permissions to the existing Cloud Run service account:

```bash
# Grant Firebase Admin role to Cloud Run runtime service account
gcloud projects add-iam-policy-binding coherent-answer-479115-e1 \
  --member="serviceAccount:improv-app-runtime@coherent-answer-479115-e1.iam.gserviceaccount.com" \
  --role="roles/firebase.admin"

# Grant Identity Platform Admin role (required for user management)
gcloud projects add-iam-policy-binding coherent-answer-479115-e1 \
  --member="serviceAccount:improv-app-runtime@coherent-answer-479115-e1.iam.gserviceaccount.com" \
  --role="roles/identityplatform.admin"
```

---

## 2. Environment Variable Changes

### 2.1 Variables to Remove/Deprecate

**Current OAuth variables (no longer needed after migration):**

```bash
# These can be removed after migration is complete and tested
# Keep temporarily during transition for rollback capability

# OAUTH_CLIENT_ID (Secret Manager: oauth-client-id)
# OAUTH_CLIENT_SECRET (Secret Manager: oauth-client-secret)
# OAUTH_REDIRECT_URI (no longer needed with Firebase)
```

**Transition Strategy:**
1. Keep old OAuth secrets for 30 days after migration (rollback safety)
2. Monitor authentication metrics to ensure Firebase Auth is working
3. Delete old OAuth secrets after migration is validated

### 2.2 New Firebase Variables

**Add to `.env.example` and `.env.local`:**

```bash
# Firebase Authentication Configuration
FIREBASE_PROJECT_ID=coherent-answer-479115-e1
FIREBASE_API_KEY=AIza...  # Firebase Web API Key (from Firebase Console)
FIREBASE_AUTH_DOMAIN=coherent-answer-479115-e1.firebaseapp.com
FIREBASE_AUTH_EMULATOR_HOST=  # For local development: localhost:9099

# MFA Configuration
FIREBASE_MFA_ENABLED=true
FIREBASE_MFA_REQUIRED=true  # Enforce MFA for all users (after grace period)
FIREBASE_MFA_GRACE_PERIOD_DAYS=7  # Days before MFA is enforced

# Firebase Admin SDK (Cloud Run uses service account, local uses key file)
# For local development only (not needed in Cloud Run):
# FIREBASE_ADMIN_KEY_PATH=/path/to/firebase-admin-key.json
```

**Firebase Web API Key (Public):**

Firebase Web API Key is **public** and safe to expose in frontend JavaScript. It identifies your Firebase project and is required for client-side Firebase SDK.

Retrieve it from Firebase Console:
1. Project Settings → General → Web API Key
2. Copy the key (starts with `AIza...`)

### 2.3 Updated Terraform Variables

**Add to `/home/jantona/Documents/code/ai4joy/infrastructure/terraform/variables.tf`:**

```hcl
variable "firebase_api_key" {
  description = "Firebase Web API Key (public, safe to expose)"
  type        = string
  sensitive   = false
}

variable "firebase_mfa_enabled" {
  description = "Enable multi-factor authentication"
  type        = bool
  default     = true
}

variable "firebase_mfa_required" {
  description = "Require MFA for all users (after grace period)"
  type        = bool
  default     = true
}

variable "firebase_mfa_grace_period_days" {
  description = "Days before MFA is enforced for existing users"
  type        = number
  default     = 7
}
```

### 2.4 Updated Cloud Run Environment Variables

**Modify `/home/jantona/Documents/code/ai4joy/infrastructure/terraform/main.tf`:**

Replace existing OAuth environment variables with Firebase configuration in the `google_cloud_run_v2_service.improv_app` resource:

```hcl
# Remove these existing env blocks:
# env {
#   name = "OAUTH_CLIENT_ID"
#   value_source { ... }
# }
# env {
#   name = "OAUTH_CLIENT_SECRET"
#   value_source { ... }
# }
# env {
#   name = "OAUTH_REDIRECT_URI"
#   value = "https://ai4joy.org/auth/callback"
# }

# Add Firebase environment variables:
env {
  name  = "FIREBASE_PROJECT_ID"
  value = var.project_id
}

env {
  name  = "FIREBASE_API_KEY"
  value = var.firebase_api_key
}

env {
  name  = "FIREBASE_AUTH_DOMAIN"
  value = "${var.project_id}.firebaseapp.com"
}

env {
  name  = "FIREBASE_MFA_ENABLED"
  value = tostring(var.firebase_mfa_enabled)
}

env {
  name  = "FIREBASE_MFA_REQUIRED"
  value = tostring(var.firebase_mfa_required)
}

env {
  name  = "FIREBASE_MFA_GRACE_PERIOD_DAYS"
  value = tostring(var.firebase_mfa_grace_period_days)
}
```

---

## 3. Firestore Schema Changes

### 3.1 Current User Collection Schema

**Collection**: `users`
**Current fields** (from `/home/jantona/Documents/code/ai4joy/app/models/user.py`):

```python
{
  "user_id": str,           # Google OAuth user ID
  "email": str,             # User email (indexed)
  "display_name": str,      # Optional display name
  "tier": str,              # "free", "regular", "premium"
  "tier_assigned_at": datetime,
  "tier_expires_at": datetime,
  "audio_usage_seconds": int,
  "audio_usage_reset_at": datetime,
  "created_at": datetime,
  "last_login_at": datetime,
  "created_by": str,        # Admin who provisioned (nullable)
}
```

### 3.2 Updated User Collection Schema

**New fields for Firebase Authentication:**

```python
{
  # Existing fields (unchanged)
  "user_id": str,           # Firebase UID (replaces OAuth user ID)
  "email": str,             # User email (indexed)
  "display_name": str,
  "tier": str,
  "tier_assigned_at": datetime,
  "tier_expires_at": datetime,
  "audio_usage_seconds": int,
  "audio_usage_reset_at": datetime,
  "created_at": datetime,
  "last_login_at": datetime,
  "created_by": str,        # "auto-signup" for self-registered users

  # New fields for Firebase Auth
  "auth_provider": str,     # "email_password" | "google.com"
  "mfa_enabled": bool,      # User has enrolled in MFA
  "mfa_enrolled_at": datetime,  # When user enrolled in MFA
  "mfa_required_by": datetime,  # Deadline for MFA enrollment (grace period)
  "signup_method": str,     # "self_signup" | "admin_provisioned" | "migration"
  "email_verified": bool,   # Firebase email verification status
  "phone_number": str,      # Optional (for SMS MFA)
  "disabled": bool,         # Admin can disable accounts
}
```

### 3.3 Firestore Indexes

**Required composite indexes** for efficient queries:

```bash
# Create indexes via gcloud CLI
gcloud firestore indexes composite create \
  --collection-group=users \
  --field-config=field-path=email,order=ascending \
  --field-config=field-path=tier,order=ascending \
  --project=coherent-answer-479115-e1

gcloud firestore indexes composite create \
  --collection-group=users \
  --field-config=field-path=mfa_enabled,order=ascending \
  --field-config=field-path=mfa_required_by,order=ascending \
  --project=coherent-answer-479115-e1

gcloud firestore indexes composite create \
  --collection-group=users \
  --field-config=field-path=tier,order=ascending \
  --field-config=field-path=created_at,order=descending \
  --project=coherent-answer-479115-e1
```

**Or create via `firestore.indexes.json` (recommended for version control):**

Create `/home/jantona/Documents/code/ai4joy/infrastructure/firestore.indexes.json`:

```json
{
  "indexes": [
    {
      "collectionGroup": "users",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "email",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "tier",
          "order": "ASCENDING"
        }
      ]
    },
    {
      "collectionGroup": "users",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "mfa_enabled",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "mfa_required_by",
          "order": "ASCENDING"
        }
      ]
    },
    {
      "collectionGroup": "users",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "tier",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "created_at",
          "order": "DESCENDING"
        }
      ]
    }
  ],
  "fieldOverrides": []
}
```

Deploy indexes:

```bash
firebase deploy --only firestore:indexes --project coherent-answer-479115-e1
```

### 3.4 Firestore Security Rules

**Updated security rules** to integrate Firebase Authentication:

Create `/home/jantona/Documents/code/ai4joy/infrastructure/firestore.rules`:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Helper function to check if user is authenticated
    function isAuthenticated() {
      return request.auth != null;
    }

    // Helper function to check if user is accessing their own data
    function isOwner(userId) {
      return isAuthenticated() && request.auth.uid == userId;
    }

    // Helper function to check if user has MFA enabled
    function hasMFA() {
      return request.auth.token.firebase.sign_in_second_factor != null;
    }

    // Users collection
    match /users/{userId} {
      // Read: Users can read their own profile
      allow read: if isOwner(userId);

      // Create: Auto-created on signup by backend (server-side)
      // Deny client-side creation to prevent privilege escalation
      allow create: if false;

      // Update: Users can update their own profile (limited fields)
      allow update: if isOwner(userId)
        && request.resource.data.diff(resource.data).affectedKeys()
          .hasOnly(['display_name', 'last_login_at', 'audio_usage_seconds', 'mfa_enabled', 'mfa_enrolled_at']);

      // Delete: Only admins can delete (server-side)
      allow delete: if false;
    }

    // Sessions collection (existing)
    match /sessions/{sessionId} {
      // Users can read/write their own sessions
      allow read, write: if isAuthenticated()
        && resource.data.user_email == request.auth.token.email;
    }

    // Improv games collection (tool data - read-only for all authenticated users)
    match /improv_games/{gameId} {
      allow read: if isAuthenticated();
      allow write: if false;  // Only backend can modify
    }

    // Improv principles collection (read-only)
    match /improv_principles/{principleId} {
      allow read: if isAuthenticated();
      allow write: if false;
    }

    // Audience archetypes collection (read-only)
    match /audience_archetypes/{archetypeId} {
      allow read: if isAuthenticated();
      allow write: if false;
    }

    // Sentiment keywords collection (read-only)
    match /sentiment_keywords/{keywordId} {
      allow read: if isAuthenticated();
      allow write: if false;
    }

    // User limits collection (rate limiting)
    match /user_limits/{userId} {
      allow read: if isOwner(userId);
      allow write: if false;  // Only backend can modify
    }

    // Default deny all other access
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

Deploy security rules:

```bash
firebase deploy --only firestore:rules --project coherent-answer-479115-e1
```

---

## 4. Secrets Management

### 4.1 Current Secrets (to deprecate)

**Existing Secret Manager secrets:**

```bash
# List current secrets
gcloud secrets list --project=coherent-answer-479115-e1

# Current secrets (from Terraform):
# - oauth-client-id
# - oauth-client-secret
# - session-secret-key (still needed for session management)
```

### 4.2 New Secrets for Firebase

**Firebase Admin SDK Service Account Key:**

```bash
# Create secret for Firebase Admin SDK key
gcloud secrets create firebase-admin-key \
  --replication-policy="automatic" \
  --project=coherent-answer-479115-e1

# Add the service account key as a secret version
gcloud secrets versions add firebase-admin-key \
  --data-file=firebase-admin-key.json \
  --project=coherent-answer-479115-e1

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding firebase-admin-key \
  --member="serviceAccount:improv-app-runtime@coherent-answer-479115-e1.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=coherent-answer-479115-e1

# Delete local key file (security best practice)
rm firebase-admin-key.json
```

**Note**: In Cloud Run, the service account identity is sufficient for Firebase Admin SDK. The key file is only needed for local development or non-GCP environments.

### 4.3 Update Terraform Secret References

**Add to `/home/jantona/Documents/code/ai4joy/infrastructure/terraform/main.tf`:**

```hcl
# Firebase Admin SDK secret (for non-GCP environments, optional for Cloud Run)
data "google_secret_manager_secret" "firebase_admin_key" {
  secret_id = "firebase-admin-key"
  project   = var.project_id
}

# Update Cloud Run service to reference Firebase secret
resource "google_cloud_run_v2_service" "improv_app" {
  # ... existing configuration ...

  template {
    # ... existing configuration ...

    containers {
      # ... existing configuration ...

      # Add Firebase Admin SDK secret (optional, service account is sufficient)
      # env {
      #   name = "FIREBASE_ADMIN_KEY"
      #   value_source {
      #     secret_key_ref {
      #       secret  = data.google_secret_manager_secret.firebase_admin_key.secret_id
      #       version = "latest"
      #     }
      #   }
      # }
    }
  }
}
```

### 4.4 Secret Rotation Strategy

**Firebase Admin SDK Keys:**
- **Rotation period**: Every 90 days (recommended)
- **Process**: Generate new key → Update Secret Manager → Redeploy Cloud Run
- **Automated rotation**: Use Cloud Scheduler + Cloud Functions (future enhancement)

**Session Secret Key:**
- **Keep existing**: `session-secret-key` is still used for session cookies
- **Rotation**: Invalidates all active sessions, plan carefully

---

## 5. Deployment Script Updates

### 5.1 Changes to `/scripts/deploy.sh`

**Current deployment script** (`/home/jantona/Documents/code/ai4joy/scripts/deploy.sh`):

Update line 112 to include new Firebase environment variables:

```bash
# Current (line 112):
--set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_LOCATION=${REGION},USE_FIRESTORE_AUTH=true" \

# Updated:
--set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_LOCATION=${REGION},USE_FIRESTORE_AUTH=true,FIREBASE_PROJECT_ID=${PROJECT_ID},FIREBASE_API_KEY=${FIREBASE_API_KEY},FIREBASE_AUTH_DOMAIN=${PROJECT_ID}.firebaseapp.com,FIREBASE_MFA_ENABLED=true,FIREBASE_MFA_REQUIRED=true" \
```

**Add Firebase API key validation before deployment:**

Insert after line 69 (after project validation):

```bash
# Validate Firebase configuration
if [ -z "${FIREBASE_API_KEY}" ]; then
    echo -e "${RED}Error: FIREBASE_API_KEY environment variable not set${NC}"
    echo "Get your Firebase API Key from: https://console.firebase.google.com/project/${PROJECT_ID}/settings/general"
    exit 1
fi

echo -e "${GREEN}✓ Firebase API Key configured${NC}"
```

### 5.2 Changes to Cloud Build Configuration

**Update `/cloudbuild.yaml`** (lines 100-116):

Replace OAuth environment variables with Firebase configuration:

```yaml
# Current (lines 100-116):
- '--set-env-vars=PROJECT_ID=${PROJECT_ID},REGION=${_REGION},ENVIRONMENT=production,BUILD_ID=${BUILD_ID}'
- '--set-secrets=SESSION_ENCRYPTION_KEY=session-encryption-key:latest'

# Updated:
- '--set-env-vars=PROJECT_ID=${PROJECT_ID},REGION=${_REGION},ENVIRONMENT=production,BUILD_ID=${BUILD_ID},FIREBASE_PROJECT_ID=${PROJECT_ID},FIREBASE_API_KEY=${_FIREBASE_API_KEY},FIREBASE_AUTH_DOMAIN=${PROJECT_ID}.firebaseapp.com,FIREBASE_MFA_ENABLED=true,FIREBASE_MFA_REQUIRED=true'
- '--set-secrets=SESSION_ENCRYPTION_KEY=session-encryption-key:latest'
```

**Add Cloud Build substitution variable** (lines 296-308):

```yaml
substitutions:
  _REGION: 'us-central1'
  _SERVICE_NAME: 'improv-olympics-app'
  # ... existing substitutions ...
  _FIREBASE_API_KEY: 'REPLACE_WITH_FIREBASE_API_KEY'  # Add this line
```

**Important**: Firebase API Key should be retrieved from Secret Manager in production:

```bash
# Store Firebase API Key in Secret Manager
gcloud secrets create firebase-api-key \
  --replication-policy="automatic" \
  --project=coherent-answer-479115-e1

echo -n "YOUR_FIREBASE_API_KEY" | gcloud secrets versions add firebase-api-key \
  --data-file=- \
  --project=coherent-answer-479115-e1

# Grant access to Cloud Build service account
gcloud secrets add-iam-policy-binding firebase-api-key \
  --member="serviceAccount:cloud-build-deployer@coherent-answer-479115-e1.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=coherent-answer-479115-e1
```

Update `cloudbuild.yaml` to fetch from Secret Manager:

```yaml
# Add before deploy step (after push-image)
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  id: 'get-firebase-api-key'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      gcloud secrets versions access latest --secret=firebase-api-key > /workspace/firebase-api-key.txt
  waitFor: ['push-image']

# Update deploy step to use the secret
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  id: 'deploy-cloud-run'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      FIREBASE_API_KEY=$(cat /workspace/firebase-api-key.txt)
      gcloud run deploy ${_SERVICE_NAME} \
        --image=${_ARTIFACT_REGISTRY}/${_IMAGE_NAME}:${COMMIT_SHA} \
        --region=${_REGION} \
        # ... other args ...
        --set-env-vars="FIREBASE_API_KEY=${FIREBASE_API_KEY},FIREBASE_PROJECT_ID=${PROJECT_ID},..."
  waitFor: ['get-firebase-api-key']
```

### 5.3 Rollback Strategy

**Create rollback script** (`/scripts/rollback-firebase-auth.sh`):

```bash
#!/bin/bash
# Rollback to OAuth authentication if Firebase migration fails

set -e

PROJECT_ID="${PROJECT_ID:-coherent-answer-479115-e1}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="improv-olympics-app"

echo "Rolling back to OAuth authentication..."

# Get previous revision (before Firebase migration)
PREVIOUS_REVISION=$(gcloud run revisions list \
  --service=${SERVICE_NAME} \
  --region=${REGION} \
  --format='value(metadata.name)' \
  --limit=2 \
  --project=${PROJECT_ID} | tail -n 1)

if [ -z "$PREVIOUS_REVISION" ]; then
  echo "Error: No previous revision found"
  exit 1
fi

echo "Rolling back to revision: $PREVIOUS_REVISION"

# Route 100% traffic to previous revision
gcloud run services update-traffic ${SERVICE_NAME} \
  --region=${REGION} \
  --to-revisions=${PREVIOUS_REVISION}=100 \
  --project=${PROJECT_ID}

echo "✓ Rollback complete. Service is now using OAuth authentication."
echo "Monitor logs: gcloud run services logs tail ${SERVICE_NAME} --region=${REGION}"
```

Make executable:

```bash
chmod +x /home/jantona/Documents/code/ai4joy/scripts/rollback-firebase-auth.sh
```

---

## 6. IAM & Security Updates

### 6.1 Cloud Run Service Account Permissions

**Current IAM roles** for `improv-app-runtime@coherent-answer-479115-e1.iam.gserviceaccount.com`:
- `roles/aiplatform.user` (Vertex AI)
- `roles/datastore.user` (Firestore)
- `roles/secretmanager.secretAccessor` (Secret Manager)
- `roles/logging.logWriter` (Cloud Logging)
- `roles/cloudtrace.agent` (Cloud Trace)

**Add Firebase Admin roles:**

```bash
# Grant Firebase Admin role
gcloud projects add-iam-policy-binding coherent-answer-479115-e1 \
  --member="serviceAccount:improv-app-runtime@coherent-answer-479115-e1.iam.gserviceaccount.com" \
  --role="roles/firebase.admin"

# Grant Identity Platform Admin role (for user management)
gcloud projects add-iam-policy-binding coherent-answer-479115-e1 \
  --member="serviceAccount:improv-app-runtime@coherent-answer-479115-e1.iam.gserviceaccount.com" \
  --role="roles/identityplatform.admin"
```

**Update Terraform IAM bindings** (`/infrastructure/terraform/main.tf`):

Add after line 228:

```hcl
# Firebase Admin role for authentication management
resource "google_project_iam_member" "app_runtime_firebase" {
  project = var.project_id
  role    = "roles/firebase.admin"
  member  = "serviceAccount:${google_service_account.app_runtime.email}"
}

# Identity Platform Admin role for user management
resource "google_project_iam_member" "app_runtime_identity_platform" {
  project = var.project_id
  role    = "roles/identityplatform.admin"
  member  = "serviceAccount:${google_service_account.app_runtime.email}"
}
```

### 6.2 Firebase Authentication Security Settings

**Configure Firebase Authentication security settings** (Firebase Console):

1. **Email Enumeration Protection**: ✅ Enable
   - Prevents attackers from discovering registered emails
   - Setting: Authentication → Settings → User account management → Email enumeration protection

2. **Password Policy**: Strong (default)
   - Minimum 6 characters (Firebase default, consider increasing to 8-12)
   - Enforce strong passwords in application code

3. **MFA Enforcement**: Required after grace period
   - Configured via backend logic (see Section 7)

4. **Session Duration**: 24 hours (configurable)
   - Firebase ID tokens expire after 1 hour (automatically refreshed)
   - Session cookies can be configured via Admin SDK

### 6.3 Cloud Armor Updates

**Current Cloud Armor policy** (`improv-security-policy`) already protects against:
- Rate limiting: 100 requests/minute per IP
- Missing User-Agent blocking
- Health check bypass

**No changes required** - Cloud Armor operates at the load balancer level, independent of authentication method.

### 6.4 Audit Logging

**Enable Firebase Authentication audit logs:**

```bash
# Enable Identity Platform audit logs
gcloud logging sinks create firebase-auth-audit-sink \
  gs://coherent-answer-479115-e1-backups/firebase-audit-logs \
  --log-filter='protoPayload.serviceName="identitytoolkit.googleapis.com"' \
  --project=coherent-answer-479115-e1
```

**Monitor authentication events:**

```bash
# View authentication logs
gcloud logging read \
  'protoPayload.serviceName="identitytoolkit.googleapis.com"' \
  --limit=50 \
  --format=json \
  --project=coherent-answer-479115-e1
```

---

## 7. Application Code Changes Summary

**Files requiring updates** (implementation by development team):

### 7.1 Python Dependencies

**Update `/requirements.txt`:**

```python
# Remove:
# authlib>=1.5.1,<2.0.0  # Remove OAuth library

# Add:
firebase-admin>=6.5.0  # Firebase Admin SDK
```

### 7.2 Authentication Service

**Files to update:**
1. `/app/routers/auth.py` - Replace OAuth login/callback with Firebase
2. `/app/middleware/auth.py` - Replace IAP headers with Firebase token validation
3. `/app/config.py` - Update settings for Firebase configuration
4. `/app/services/user_service.py` - Add auto-provisioning logic

**Key changes:**

**`/app/routers/auth.py`:**
- Remove: OAuth redirect flow (`/auth/login`, `/auth/callback`)
- Add: Firebase email/password signup endpoint (`POST /auth/signup`)
- Add: Firebase email/password login endpoint (`POST /auth/login`)
- Add: MFA enrollment endpoint (`POST /auth/mfa/enroll`)
- Add: MFA verification endpoint (`POST /auth/mfa/verify`)
- Keep: `/auth/logout` (clear session cookie)
- Keep: `/auth/user` (return current user from Firebase token)

**`/app/middleware/auth.py`:**
- Replace: IAP header validation
- Add: Firebase ID token verification using `firebase_admin.auth.verify_id_token()`
- Add: Session cookie validation (Firebase session cookies)

**`/app/services/user_service.py`:**
- Add: `auto_provision_user()` - Auto-create Firestore user record on first login
- Add: `check_mfa_enforcement()` - Validate MFA status against grace period
- Update: `create_user()` - Set `signup_method="self_signup"` for new users

### 7.3 Frontend Changes

**Files to update:**
1. `/static/index.html` - Replace OAuth login button with Firebase UI
2. `/static/app.js` - Replace OAuth flow with Firebase SDK
3. `/static/chat.html` - Update authentication state management

**Required:**
- Firebase JavaScript SDK (`firebase/auth`)
- Firebase UI library (optional, for pre-built login forms)

---

## 8. Testing & Validation

### 8.1 Pre-Deployment Testing

**Local testing with Firebase Emulator:**

```bash
# Install Firebase Emulator Suite
firebase init emulators
firebase emulators:start --only auth,firestore

# Update .env.local for emulator testing
FIREBASE_AUTH_EMULATOR_HOST=localhost:9099
FIRESTORE_EMULATOR_HOST=localhost:8080
```

**Test scenarios:**
1. ✅ User signup with email/password
2. ✅ User login with email/password
3. ✅ User login with Google Sign-In
4. ✅ MFA enrollment flow (TOTP)
5. ✅ MFA verification on subsequent logins
6. ✅ Auto-provisioning of Firestore user record (freemium tier)
7. ✅ Session persistence across page reloads
8. ✅ Password reset flow
9. ✅ Email verification flow

### 8.2 Post-Deployment Validation

**Smoke tests:**

```bash
# Test authentication endpoint
curl -X POST https://ai4joy.org/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!"}'

# Test user provisioning
curl https://ai4joy.org/auth/user \
  -H "Authorization: Bearer YOUR_FIREBASE_ID_TOKEN"
```

**Monitor Cloud Logging:**

```bash
# Watch authentication logs in real-time
gcloud run services logs tail improv-olympics-app \
  --region=us-central1 \
  --project=coherent-answer-479115-e1 \
  | grep -i "firebase\|auth\|signup"
```

**Check Firestore user records:**

```bash
# Verify users are being auto-created with freemium tier
gcloud firestore export gs://coherent-answer-479115-e1-backups/validation \
  --collection-ids=users \
  --project=coherent-answer-479115-e1

# Or use Firebase Console:
# https://console.firebase.google.com/project/coherent-answer-479115-e1/firestore/data/users
```

### 8.3 Rollback Criteria

**Trigger immediate rollback if:**
- ❌ Authentication success rate < 90% (5-minute window)
- ❌ User signup failure rate > 10%
- ❌ MFA enrollment fails for > 5% of attempts
- ❌ Auto-provisioning fails (users not created in Firestore)
- ❌ Existing users unable to login

**Rollback procedure:**

```bash
# Execute rollback script
./scripts/rollback-firebase-auth.sh

# Verify rollback success
curl https://ai4joy.org/auth/user
```

---

## 9. Migration Strategy & Timeline

### Phase 1: Preparation (Day 1)
- [x] Enable Firebase APIs and configure project
- [x] Create Firebase Admin service account
- [x] Store Firebase credentials in Secret Manager
- [x] Update Terraform configuration (do not apply yet)
- [x] Update deployment scripts
- [x] Create Firestore security rules and indexes

### Phase 2: Development & Testing (Day 1-2)
- [ ] Update Python dependencies
- [ ] Implement Firebase authentication endpoints
- [ ] Implement auto-provisioning logic
- [ ] Update frontend to use Firebase SDK
- [ ] Test locally with Firebase Emulator
- [ ] Update unit and integration tests

### Phase 3: Staging Deployment (Day 2)
- [ ] Deploy to staging/dev environment
- [ ] Run smoke tests
- [ ] Test MFA enrollment flow
- [ ] Validate auto-provisioning
- [ ] Test password reset and email verification
- [ ] Load testing (simulate 100+ concurrent signups)

### Phase 4: Production Migration (Day 3)
- [ ] Deploy Terraform changes (IAM, environment variables)
- [ ] Deploy Firebase security rules and indexes
- [ ] Deploy application code (Cloud Run)
- [ ] Monitor authentication metrics for 30 minutes
- [ ] Announce Firebase Auth to existing users
- [ ] Monitor for 24 hours before marking complete

### Phase 5: Cleanup (Day 4+)
- [ ] Verify all users have transitioned to Firebase Auth
- [ ] Test rollback procedure (in staging)
- [ ] Document operational procedures
- [ ] After 30 days: Delete old OAuth secrets
- [ ] Update monitoring dashboards with Firebase metrics

---

## 10. Cost Analysis

### Current Authentication Costs

**OAuth + Authlib:**
- $0/month (free, self-hosted)

### Firebase Authentication Costs

**Firebase Authentication pricing** (as of 2025):
- **First 50,000 monthly active users**: Free
- **50,001 - 100,000 MAU**: $0.0055/user
- **100,001+ MAU**: $0.0046/user

**MFA costs:**
- **TOTP (Time-based OTP)**: Free
- **SMS verification**: $0.01-0.05 per verification (if enabled)

**Estimated cost for Improv Olympics:**
- **Current user base**: ~50 users (private beta)
- **Projected growth**: 1,000 MAU in 6 months
- **Monthly cost**: $0/month (within free tier)

**Identity Platform costs** (Firebase Auth backend):
- **First 50,000 MAU**: Free
- **Additional users**: $0.0025-0.015 per MAU (varies by region)

**Total estimated cost impact**: **$0-5/month** (within free tier for foreseeable future)

---

## 11. Operational Procedures

### 11.1 User Management

**Create user manually (admin):**

```bash
# Using Firebase CLI
firebase auth:import users.json --project coherent-answer-479115-e1

# Using Python Admin SDK (backend)
from firebase_admin import auth

user = auth.create_user(
    email='user@example.com',
    email_verified=False,
    password='temporaryPassword123!',
    display_name='John Doe'
)
```

**Disable user account:**

```python
from firebase_admin import auth

auth.update_user(
    uid='user_uid',
    disabled=True
)

# Also update Firestore user record
from app.services.firestore_tool_data_service import get_firestore_client

client = get_firestore_client()
client.collection('users').document('user_doc_id').update({'disabled': True})
```

**Reset user password:**

Firebase handles password reset via email link automatically. No backend intervention needed.

### 11.2 Monitoring & Alerts

**Key metrics to monitor:**
- Authentication success rate (target: >95%)
- Signup completion rate (target: >80%)
- MFA enrollment rate (target: 100% after grace period)
- Auto-provisioning success rate (target: 100%)
- Session creation latency (target: <500ms)

**Create Cloud Monitoring alerts:**

```bash
# Alert on high authentication failure rate
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="High Firebase Auth Failure Rate" \
  --condition-display-name="Auth failures > 10% for 5 minutes" \
  --condition-threshold-value=0.1 \
  --condition-threshold-duration=300s \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="logging.googleapis.com/user/firebase_auth_failure_rate"' \
  --project=coherent-answer-479115-e1
```

### 11.3 Backup & Recovery

**Firebase Authentication data backup:**

Firebase Authentication user data is automatically backed up by Google. No manual backup required.

**Firestore user records backup:**

Existing daily Firestore backup (via Cloud Scheduler) already covers `users` collection:

```bash
# Verify daily backup job exists
gcloud scheduler jobs describe firestore-daily-backup \
  --location=us-central1 \
  --project=coherent-answer-479115-e1
```

**Disaster recovery:**

In case of Firestore data loss:
1. Restore Firestore backup from Cloud Storage
2. Sync with Firebase Authentication user records
3. Re-run auto-provisioning for any missing users

---

## 12. Next Steps (Deployment Checklist)

**Before deployment:**
- [ ] Review and approve infrastructure changes
- [ ] Test Firebase Emulator locally
- [ ] Update environment variables in Cloud Run
- [ ] Create Firebase project and enable authentication providers
- [ ] Deploy Firestore security rules and indexes
- [ ] Update monitoring dashboards

**During deployment:**
- [ ] Deploy Terraform changes (IAM, secrets, environment variables)
- [ ] Deploy updated application code
- [ ] Run smoke tests
- [ ] Monitor authentication metrics

**After deployment:**
- [ ] Notify users of new authentication system
- [ ] Monitor for 24 hours
- [ ] Document any issues or lessons learned
- [ ] Plan OAuth secret cleanup (30 days post-migration)

**Rollback plan:**
- Keep OAuth secrets for 30 days
- Keep rollback script ready (`./scripts/rollback-firebase-auth.sh`)
- Monitor authentication success rate closely for first week

---

## 13. Support & Documentation

**Firebase Authentication documentation:**
- Firebase Auth Overview: https://firebase.google.com/docs/auth
- Multi-factor authentication: https://firebase.google.com/docs/auth/web/multi-factor
- Admin SDK (Python): https://firebase.google.com/docs/auth/admin

**Identity Platform documentation:**
- Identity Platform overview: https://cloud.google.com/identity-platform/docs
- Quotas and limits: https://cloud.google.com/identity-platform/quotas

**Internal documentation:**
- Authentication architecture: `/docs/authentication-architecture.md` (create)
- User management procedures: `/docs/user-management-procedures.md` (create)
- MFA enforcement policy: `/docs/mfa-enforcement-policy.md` (create)

---

## Appendix A: Required API Enablement

```bash
# Enable all required APIs
gcloud services enable \
  firebase.googleapis.com \
  firebaseauth.googleapis.com \
  identitytoolkit.googleapis.com \
  --project=coherent-answer-479115-e1
```

## Appendix B: Terraform Plan Output

Run `terraform plan` to preview changes before applying:

```bash
cd /home/jantona/Documents/code/ai4joy/infrastructure/terraform
terraform plan -out=firebase-auth-migration.tfplan

# Review changes carefully
# Apply when ready:
# terraform apply firebase-auth-migration.tfplan
```

## Appendix C: Cost Monitoring

Set up billing alerts specifically for Firebase Authentication:

```bash
# Create budget alert for Identity Platform usage
# (Manual setup required in GCP Console: Billing → Budgets & alerts)
# Set alert at $5/month to catch unexpected costs early
```

---

**End of Infrastructure & Deployment Requirements Document**

For implementation details, consult development team. For infrastructure questions, contact GCP admin or DevOps engineer.
