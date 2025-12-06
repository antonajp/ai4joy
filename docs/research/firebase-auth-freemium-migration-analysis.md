# Firebase Authentication & Freemium Tier Migration - Technical Analysis

**Document Version:** 1.0
**Date:** 2025-12-02
**Status:** Research Complete
**Prepared For:** Feature Implementation Planning

---

## Executive Summary

This document provides a comprehensive technical analysis for migrating from Google OAuth to Firebase Authentication with open user signup, mandatory MFA, and a freemium tier system. The analysis covers existing implementations, required changes, and detailed implementation recommendations.

**Key Findings:**
- Current system uses `authlib` with custom session management - NOT Firebase
- Firestore already in use for user management (good foundation)
- No Firebase SDK currently installed - requires new dependency
- No MFA implementation exists - greenfield implementation needed
- Freemium tier system partially documented in PRD but not implemented
- Existing premium tier tracking uses time-based limits (3600 seconds)
- Session tracking exists but NOT lifetime session counting

**Estimated Effort:** 40-60 hours (2-3 weeks for one developer)

---

## 1. Current OAuth Implementation Analysis

### 1.1 Authentication Architecture

**Files Involved:**
- `/app/routers/auth.py` - OAuth endpoints (login, callback, logout)
- `/app/middleware/oauth_auth.py` - Session middleware and validation
- `/app/middleware/iap_auth.py` - Google IAP integration (production)
- `/app/config.py` - Configuration management

**Current Flow:**

```python
# 1. User initiates login: GET /auth/login
# 2. Redirect to Google OAuth: authlib handles OAuth flow
# 3. Google redirects back: GET /auth/callback
# 4. Exchange code for token using authlib
# 5. Extract user info: email, sub (user_id), name
# 6. Check authorization (Firestore or ALLOWED_USERS env var)
# 7. Create signed session cookie using itsdangerous
# 8. Redirect to intended destination
```

**Key Components:**

```python
# OAuth client setup (auth.py:16-33)
oauth = OAuth(starlette_config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "prompt": "select_account",
    },
)

# Session cookie creation (oauth_auth.py:104-117)
def create_session_cookie(self, user_info: dict) -> str:
    session_data = {**user_info, "created_at": int(time.time())}
    return self.serializer.dumps(session_data)

# Session validation (oauth_auth.py:80-102)
def _get_session_data(self, request: Request) -> Optional[dict]:
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return None
    try:
        session_data = self.serializer.loads(session_cookie, max_age=self.max_age)
        return session_data
    except SignatureExpired:
        logger.info("Session expired")
        return None
```

**Authentication Modes:**
1. **Local Development**: OAuth with session cookies
2. **Production**: Google Identity-Aware Proxy (IAP) with header-based auth

### 1.2 User Management (Firestore)

**Files:**
- `/app/services/user_service.py` - User CRUD operations
- `/app/models/user.py` - User models and tier definitions

**Current User Schema:**

```python
@dataclass
class UserProfile:
    user_id: str                          # Google OAuth sub
    email: str                            # Primary key for lookups
    tier: UserTier                        # free, regular, premium
    display_name: Optional[str] = None
    tier_assigned_at: Optional[datetime]
    tier_expires_at: Optional[datetime]
    audio_usage_seconds: int = 0          # Time-based tracking
    audio_usage_reset_at: Optional[datetime]
    created_at: Optional[datetime]
    last_login_at: Optional[datetime]
    created_by: Optional[str] = None      # Admin who created user
```

**Current Tier System:**

```python
class UserTier(str, Enum):
    FREE = "free"        # No audio access
    REGULAR = "regular"  # No audio access
    PREMIUM = "premium"  # 3600 seconds (1 hour) audio per reset period

AUDIO_USAGE_LIMITS = {
    UserTier.FREE: 0,
    UserTier.REGULAR: 0,
    UserTier.PREMIUM: 3600,  # 1 hour
}
```

**Authorization Flow:**

```python
# Check if user is authorized (auth.py:339-363)
async def check_user_authorization(email: str) -> bool:
    if should_use_firestore_auth():
        user_profile = await validate_user_access(email)
        return user_profile is not None
    else:
        # Legacy: Check ALLOWED_USERS env var
        return validate_user_access_legacy(email)
```

**Key Operations:**
- `get_user_by_email(email)` - Lookup user
- `create_user(email, tier, ...)` - Create new user
- `update_user_tier(email, tier)` - Change tier
- `increment_audio_usage(email, seconds)` - Track audio time
- `update_last_login(email)` - Update login timestamp

### 1.3 Session Management

**Current Session Tracking:**

```python
# Rate limiter tracks DAILY sessions and CONCURRENT sessions
# But NOT lifetime session counting for freemium tier

class RateLimiter:
    """
    Limits:
    - Daily sessions: 10 sessions per user per day (resets at midnight UTC)
    - Concurrent sessions: 3 active sessions per user at any time
    """
```

**Firestore Schema (user_limits collection):**

```json
{
  "user_id": "1234567890",
  "daily_sessions": {
    "count": 5,
    "reset_at": "2025-11-24T00:00:00Z"
  },
  "concurrent_sessions": {
    "count": 2,
    "active_session_ids": ["sess_1", "sess_2"]
  },
  "last_updated": "2025-11-23T15:30:00Z"
}
```

**⚠️ Gap Identified:**
- Current rate limiting uses **daily reset counters**
- Freemium tier needs **lifetime session counter** (never resets)
- No field exists to track `lifetime_premium_sessions_used`

---

## 2. Firebase Auth Migration Requirements

### 2.1 Why Firebase Auth vs. Current OAuth?

**Current System (authlib + itsdangerous):**
- ✅ Flexible, customizable OAuth flow
- ✅ Works with any OAuth provider
- ❌ No built-in MFA support
- ❌ Manual session management (cookies, expiration)
- ❌ No user management UI
- ❌ Must handle token refresh manually
- ❌ Security burden on application code

**Firebase Auth Benefits:**
- ✅ Built-in MFA (TOTP, SMS, email)
- ✅ Token management (refresh, expiration) handled automatically
- ✅ Multiple providers (Google, email/password, phone, etc.)
- ✅ User management console
- ✅ Security best practices enforced
- ✅ Client SDK reduces backend token passing
- ✅ Seamless integration with Firestore security rules
- ❌ More opinionated (less flexible)
- ❌ Vendor lock-in to Firebase

**Recommendation:** **Migrate to Firebase Auth** for MFA requirements and reduced security burden.

### 2.2 Firebase Auth Architecture

**New Flow:**

```
1. User initiates signup/login (Firebase Client SDK)
2. Firebase handles OAuth redirect (Google, Microsoft, etc.) OR email/password
3. User completes first factor authentication
4. Firebase triggers MFA enrollment (if not enrolled)
5. User completes second factor (TOTP, SMS)
6. Firebase returns ID token (JWT)
7. Client sends ID token to backend API
8. Backend verifies ID token with Firebase Admin SDK
9. Backend looks up/creates user in Firestore
10. Backend returns session data to client
```

**Key Components:**

```python
# Firebase Admin SDK (new dependency)
from firebase_admin import auth, credentials, initialize_app

# Initialize Firebase Admin
cred = credentials.ApplicationDefault()
firebase_app = initialize_app(cred)

# Verify ID token
async def verify_firebase_token(id_token: str) -> dict:
    try:
        decoded_token = auth.verify_id_token(id_token)
        return {
            "uid": decoded_token["uid"],
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False),
            "mfa_info": decoded_token.get("firebase", {}).get("sign_in_second_factor"),
        }
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
```

### 2.3 MFA Implementation

**Firebase MFA Options:**

1. **TOTP (Time-Based One-Time Password)** - Recommended
   - App-based: Google Authenticator, Authy, 1Password
   - No SMS costs
   - Offline capable
   - Most secure option

2. **SMS** - Optional
   - Requires phone number
   - Costs per SMS (Google charges)
   - Less secure (SIM swapping attacks)
   - Better for non-technical users

3. **Email** - Not recommended for MFA
   - Email compromised = account compromised
   - Not a true second factor

**Recommended Approach:**

```typescript
// Frontend: Enroll MFA after first authentication
import { getAuth, multiFactor, TotpMultiFactorGenerator } from "firebase/auth";

async function enrollTOTP(user) {
  const multiFactorSession = await multiFactor(user).getSession();
  const totpSecret = await TotpMultiFactorGenerator.generateSecret(multiFactorSession);

  // Display QR code to user
  const qrCodeUrl = totpSecret.generateQrCodeUrl(user.email, "Improv Olympics");

  // User scans QR code with authenticator app
  // User enters verification code
  const verificationCode = await promptUserForCode();

  // Complete enrollment
  const multiFactorAssertion = TotpMultiFactorGenerator.assertionForEnrollment(
    totpSecret,
    verificationCode
  );
  await multiFactor(user).enroll(multiFactorAssertion, "Authenticator App");
}
```

**Backend: Enforce MFA**

```python
# Check if user has MFA enabled
async def verify_mfa_enabled(uid: str) -> bool:
    user = auth.get_user(uid)
    enrolled_factors = user.multi_factor.enrolled_factors if user.multi_factor else []
    return len(enrolled_factors) > 0

# Require MFA enrollment on first login
async def check_mfa_status(user_info: dict) -> bool:
    uid = user_info["uid"]
    if not await verify_mfa_enabled(uid):
        # Return error to force enrollment
        raise HTTPException(
            status_code=403,
            detail="MFA enrollment required. Please complete setup."
        )
    return True
```

**Grace Period Strategy:**
- Option 1: **Hard Enforcement** - Block access until MFA enrolled
- Option 2: **Grace Period** - Give 7 days to enroll, then block
- Option 3: **Reminder Nags** - Allow access but show persistent reminders

**Recommendation:** Hard enforcement for new signups, grace period for existing users during migration.

---

## 3. Freemium Tier Implementation

### 3.1 Tier Definition

**New Tier:**

```python
class UserTier(str, Enum):
    FREE = "free"        # Text-only, no audio
    FREEMIUM = "freemium"  # 2 audio sessions (lifetime)
    REGULAR = "regular"  # Text-only, no audio
    PREMIUM = "premium"  # Unlimited audio (time-based limits)

AUDIO_USAGE_LIMITS = {
    UserTier.FREE: 0,
    UserTier.FREEMIUM: 0,  # Time-based limit not applicable
    UserTier.REGULAR: 0,
    UserTier.PREMIUM: 3600,  # 1 hour per reset period
}
```

### 3.2 Updated User Schema

**Add Fields to UserProfile:**

```python
@dataclass
class UserProfile:
    # Existing fields...
    user_id: str
    email: str
    tier: UserTier
    audio_usage_seconds: int = 0

    # NEW FIELDS for freemium tier
    freemium_sessions_used: int = 0           # Lifetime counter
    freemium_sessions_limit: int = 2          # Default limit
    last_premium_session_at: Optional[datetime] = None  # Timestamp tracking
```

**Migration Script:**

```python
async def add_freemium_fields_to_existing_users():
    """Add freemium fields to all existing user records."""
    client = get_firestore_client()
    users_ref = client.collection("users")

    async for user_doc in users_ref.stream():
        updates = {
            "freemium_sessions_used": 0,
            "freemium_sessions_limit": 2,
            "last_premium_session_at": None,
        }
        await users_ref.document(user_doc.id).update(updates)
        logger.info(f"Added freemium fields to user: {user_doc.id}")
```

### 3.3 Auto-Provisioning Logic

**Create User on First Auth:**

```python
async def on_firebase_auth_success(firebase_user: dict) -> UserProfile:
    """
    Called after Firebase authentication completes.
    Auto-creates user with freemium tier if not exists.
    """
    email = firebase_user["email"]
    uid = firebase_user["uid"]

    # Check if user exists
    existing = await get_user_by_email(email)
    if existing:
        await update_last_login(email)
        return existing

    # Auto-create freemium user
    logger.info(f"Auto-provisioning new user: {email}")
    return await create_user(
        email=email,
        tier=UserTier.FREEMIUM,  # Default tier for new signups
        display_name=firebase_user.get("name"),
        user_id=uid,
        created_by="system:firebase-auto-provision",
    )
```

**Integration Point:**

```python
# Replace existing OAuth callback with Firebase token verification
@router.post("/auth/firebase/token")
async def verify_firebase_token(request: Request):
    """
    Verify Firebase ID token and create/update user.

    Request Body:
        {
            "id_token": "eyJhbGc...",
        }

    Returns:
        {
            "user": {
                "email": "user@example.com",
                "tier": "freemium",
                "freemium_sessions_used": 0,
                "freemium_sessions_limit": 2
            },
            "session_token": "signed-session-cookie-value"
        }
    """
    body = await request.json()
    id_token = body.get("id_token")

    # Verify Firebase token
    firebase_user = await verify_firebase_token(id_token)

    # Check MFA requirement
    await check_mfa_status(firebase_user)

    # Get or create user
    user_profile = await on_firebase_auth_success(firebase_user)

    # Create session cookie (keep existing session management)
    session_cookie = session_middleware.create_session_cookie({
        "email": user_profile.email,
        "sub": user_profile.user_id,
        "name": user_profile.display_name,
        "tier": user_profile.tier.value,
    })

    return {
        "user": UserProfileResponse.from_user_profile(user_profile),
        "session_token": session_cookie,
    }
```

### 3.4 Premium Middleware Updates

**Check Freemium Session Limit:**

```python
async def check_audio_access(
    user_profile: Optional[UserProfile],
) -> AudioAccessResponse:
    """
    Check if user has access to audio features.

    Updated logic:
    - Premium users: Check time-based limit (3600 seconds)
    - Freemium users: Check lifetime session limit (2 sessions)
    - Regular/Free users: 403 Forbidden
    """
    if user_profile is None:
        return AudioAccessResponse(
            allowed=False,
            error="Authentication required for audio features",
            status_code=401,
        )

    # Freemium tier: Check lifetime session limit
    if user_profile.tier == UserTier.FREEMIUM:
        if user_profile.freemium_sessions_used >= user_profile.freemium_sessions_limit:
            return AudioAccessResponse(
                allowed=False,
                error="You've used both of your free audio sessions! Upgrade to Premium for unlimited voice interactions.",
                status_code=429,
                remaining_seconds=0,
            )

        # Show warning before last session
        remaining = user_profile.freemium_sessions_limit - user_profile.freemium_sessions_used
        warning = None
        if remaining == 1:
            warning = "This is your last free audio session. Upgrade to Premium to continue!"

        return AudioAccessResponse(
            allowed=True,
            remaining_seconds=None,  # Not time-based
            warning=warning,
        )

    # Premium tier: Check time-based limit (existing logic)
    if user_profile.tier == UserTier.PREMIUM:
        usage_limit = AUDIO_USAGE_LIMITS.get(user_profile.tier, 0)
        current_usage = user_profile.audio_usage_seconds
        remaining = usage_limit - current_usage

        if remaining <= 0:
            return AudioAccessResponse(
                allowed=False,
                error="Audio usage limit exceeded for this period.",
                status_code=429,
                remaining_seconds=0,
            )

        return AudioAccessResponse(
            allowed=True,
            remaining_seconds=remaining,
        )

    # Regular/Free tier: No audio access
    return AudioAccessResponse(
        allowed=False,
        error="Premium subscription required for audio features.",
        status_code=403,
    )
```

**Increment Freemium Counter:**

```python
async def track_freemium_session_start(email: str) -> None:
    """
    Track that a freemium user has started an audio session.
    Increments lifetime counter (never resets).
    """
    user = await get_user_by_email(email)
    if not user or user.tier != UserTier.FREEMIUM:
        return

    client = get_firestore_client()
    users_ref = client.collection("users")
    query = users_ref.where("email", "==", email)

    async for doc in query.stream():
        await users_ref.document(doc.id).update({
            "freemium_sessions_used": firestore.Increment(1),
            "last_premium_session_at": datetime.now(timezone.utc),
        })
        logger.info(
            f"Incremented freemium session counter for {email}",
            sessions_used=user.freemium_sessions_used + 1,
            limit=user.freemium_sessions_limit,
        )
```

**WebSocket Integration:**

```python
# In websocket_handler.py or audio router
async def websocket_audio(websocket: WebSocket, session_id: str, token: str, game: str):
    # ... existing auth logic ...

    # Check audio access
    user_profile = await get_user_by_email(user_email)
    access = await check_audio_access(user_profile)

    if not access.allowed:
        await websocket.close(code=1008, reason=access.error)
        return

    # Track session start for freemium users
    if user_profile.tier == UserTier.FREEMIUM:
        await track_freemium_session_start(user_email)

    # ... continue with audio session ...
```

---

## 4. Technical Recommendations

### 4.1 Dependencies

**Add to `requirements.txt`:**

```txt
# Firebase Authentication
firebase-admin>=6.5.0
```

**Existing Dependencies (keep):**
```txt
# Already installed - continue using for Firestore
google-cloud-firestore>=2.14.0
```

**Remove (optional - after migration complete):**
```txt
# Can be removed after Firebase Auth migration
# authlib>=1.5.1,<2.0.0  # Keep if supporting other OAuth providers
# itsdangerous==2.1.2    # Keep if maintaining legacy sessions
```

### 4.2 Implementation Approach

**Phase 1: Firebase Auth Setup (Week 1)**

**Deliverables:**
1. Firebase project setup in GCP
2. Firebase Admin SDK integration in backend
3. New endpoint: `POST /auth/firebase/token` for token verification
4. MFA enrollment flow documentation
5. Update frontend to use Firebase Client SDK

**Steps:**

```bash
# 1. Enable Firebase in GCP project
gcloud services enable firebase.googleapis.com

# 2. Create Firebase project (if not exists)
firebase projects:addfirebase coherent-answer-479115-e1

# 3. Enable authentication providers
firebase auth:import users.json  # Migrate existing users

# 4. Update environment variables
export FIREBASE_PROJECT_ID="coherent-answer-479115-e1"

# 5. Install Python SDK
pip install firebase-admin
```

**Backend Implementation:**

```python
# app/services/firebase_auth_service.py
import firebase_admin
from firebase_admin import auth, credentials

def initialize_firebase_admin():
    """Initialize Firebase Admin SDK with application default credentials."""
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {
            'projectId': os.getenv('FIREBASE_PROJECT_ID'),
        })

async def verify_id_token(id_token: str) -> dict:
    """Verify Firebase ID token and return user info."""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return {
            "uid": decoded_token["uid"],
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False),
            "mfa_enrolled": bool(decoded_token.get("firebase", {}).get("sign_in_second_factor")),
        }
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Frontend Implementation:**

```javascript
// static/firebase-auth.js
import { initializeApp } from "firebase/app";
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  multiFactor,
  TotpMultiFactorGenerator
} from "firebase/auth";

const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "ai4joy.org",
  projectId: "coherent-answer-479115-e1",
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

async function signInWithGoogle() {
  const provider = new GoogleAuthProvider();
  try {
    const result = await signInWithPopup(auth, provider);
    const idToken = await result.user.getIdToken();

    // Send to backend
    const response = await fetch('/auth/firebase/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken }),
    });

    if (response.status === 403) {
      // MFA enrollment required
      await enrollMFA(result.user);
    }

    return await response.json();
  } catch (error) {
    console.error('Sign-in failed:', error);
  }
}
```

**Phase 2: MFA Implementation (Week 1-2)**

**Deliverables:**
1. TOTP enrollment flow in frontend
2. MFA verification in backend
3. Grace period logic for existing users
4. Admin UI to manage MFA requirements

**Enforcement Strategy:**

```python
# app/middleware/mfa_enforcement.py
from datetime import datetime, timezone, timedelta

MFA_GRACE_PERIOD_DAYS = 7

async def check_mfa_enforcement(user_profile: UserProfile, firebase_user: dict) -> None:
    """
    Enforce MFA requirement with grace period for existing users.

    Rules:
    - New users (created after deployment): Hard enforcement
    - Existing users: 7-day grace period
    """
    if firebase_user.get("mfa_enrolled"):
        return  # MFA already enrolled

    # Check if user is within grace period
    if user_profile.created_at:
        days_since_creation = (datetime.now(timezone.utc) - user_profile.created_at).days

        # Existing user within grace period
        if days_since_creation <= MFA_GRACE_PERIOD_DAYS:
            days_remaining = MFA_GRACE_PERIOD_DAYS - days_since_creation
            logger.warning(
                f"MFA not enrolled - {days_remaining} days remaining",
                email=user_profile.email
            )
            # Allow access but show warning
            return

    # Grace period expired or new user - enforce MFA
    raise HTTPException(
        status_code=403,
        detail={
            "error": "MFA enrollment required",
            "message": "Please complete two-factor authentication setup to continue.",
            "enrollment_required": True,
        }
    )
```

**Phase 3: Freemium Tier (Week 2)**

**Deliverables:**
1. Add freemium fields to UserProfile model
2. Migration script for existing users
3. Update `check_audio_access()` logic
4. Implement `track_freemium_session_start()`
5. Update frontend to display session counts

**Implementation:**

```python
# scripts/add_freemium_fields.py
async def migrate_users_to_freemium_schema():
    """Add freemium fields to all existing users."""
    client = get_firestore_client()
    users_ref = client.collection("users")

    batch = client.batch()
    count = 0

    async for user_doc in users_ref.stream():
        doc_ref = users_ref.document(user_doc.id)
        batch.update(doc_ref, {
            "freemium_sessions_used": 0,
            "freemium_sessions_limit": 2,
            "last_premium_session_at": None,
        })
        count += 1

        # Commit batch every 500 writes
        if count % 500 == 0:
            await batch.commit()
            batch = client.batch()

    # Commit remaining
    if count % 500 != 0:
        await batch.commit()

    logger.info(f"Migration complete: {count} users updated")
```

**Phase 4: Auto-Provisioning (Week 2-3)**

**Deliverables:**
1. Update `/auth/firebase/token` to auto-create users
2. Set default tier to FREEMIUM
3. Admin script to manually adjust tiers
4. Monitoring for auto-provision failures

**Phase 5: Testing & Deployment (Week 3)**

**Deliverables:**
1. Integration tests for Firebase Auth flow
2. E2E tests for MFA enrollment
3. Load testing for auto-provisioning (100 concurrent signups)
4. Rollback plan documented
5. Monitoring dashboard for new metrics

### 4.3 Firestore Indexes Required

**Create Indexes:**

```bash
# Index for freemium tier queries
gcloud firestore indexes composite create \
  --collection-group=users \
  --field-config field-path=tier,order=ascending \
  --field-config field-path=freemium_sessions_used,order=ascending

# Index for session tracking
gcloud firestore indexes composite create \
  --collection-group=users \
  --field-config field-path=tier,order=ascending \
  --field-config field-path=last_premium_session_at,order=descending
```

### 4.4 Security Considerations

**1. Firebase Token Validation:**
- Always verify tokens on backend (never trust client)
- Check token expiration
- Verify email is verified (`email_verified` field)
- Use Firebase Admin SDK (not Client SDK) for server-side verification

**2. MFA Bypass Prevention:**
- Store MFA enrollment status in Firestore (redundant check)
- Log all MFA-related events
- Alert on suspicious patterns (multiple failed MFA attempts)

**3. Freemium Abuse Prevention:**
- Track `last_premium_session_at` to detect rapid account cycling
- Implement email verification requirement
- Rate limit account creation by IP address
- Monitor for disposable email domains

**4. Session Security:**
- Continue using `httponly`, `secure`, `samesite=lax` cookies
- Session expiration: 24 hours (current)
- Token refresh handled by Firebase Client SDK automatically

### 4.5 Monitoring & Observability

**New Metrics to Track:**

```python
# Cloud Logging custom metrics
metrics = [
    "firebase_auth_success_count",
    "firebase_auth_failure_count",
    "mfa_enrollment_count",
    "mfa_verification_failure_count",
    "freemium_user_creation_count",
    "freemium_session_limit_reached_count",
    "freemium_to_premium_conversion_count",
    "auto_provision_failure_count",
]
```

**Alerting Thresholds:**

| Metric | Threshold | Action |
|--------|-----------|--------|
| Auth failure rate | > 5% | Page on-call engineer |
| MFA enrollment failure | > 10% | Review enrollment UX |
| Auto-provision failure | > 1% | Check Firestore write permissions |
| Freemium conversion rate | < 10% | Review pricing/UX |

**Dashboard Queries:**

```sql
-- Freemium conversion funnel
SELECT
  freemium_sessions_used,
  COUNT(*) AS user_count,
  COUNTIF(tier = 'premium') AS converted_count,
  COUNTIF(tier = 'premium') / COUNT(*) AS conversion_rate
FROM `project.dataset.users`
WHERE tier IN ('freemium', 'premium')
GROUP BY freemium_sessions_used
ORDER BY freemium_sessions_used

-- MFA enrollment rate
SELECT
  DATE(created_at) AS signup_date,
  COUNT(*) AS signups,
  COUNTIF(mfa_enrolled = true) AS mfa_enrolled_count,
  COUNTIF(mfa_enrolled = true) / COUNT(*) AS enrollment_rate
FROM `project.dataset.users`
GROUP BY signup_date
ORDER BY signup_date DESC
```

---

## 5. Migration Strategy

### 5.1 Backward Compatibility

**Dual Authentication Support:**

During migration, support BOTH OAuth and Firebase Auth:

```python
# app/middleware/auth.py
async def get_authenticated_user(request: Request) -> dict:
    """
    Support both legacy OAuth session cookies and new Firebase tokens.
    """
    # Check for Firebase token in Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            firebase_user = await verify_firebase_token(token)
            return {
                "user_email": firebase_user["email"],
                "user_id": firebase_user["uid"],
                "auth_method": "firebase",
            }
        except Exception:
            pass  # Fall through to legacy check

    # Check for legacy OAuth session cookie
    session_data = session_middleware._get_session_data(request)
    if session_data:
        return {
            "user_email": session_data.get("email"),
            "user_id": session_data.get("sub"),
            "auth_method": "oauth_legacy",
        }

    # No valid authentication
    raise HTTPException(status_code=401, detail="Authentication required")
```

### 5.2 User Migration

**Migrate Existing Google OAuth Users to Firebase:**

```python
# scripts/migrate_oauth_to_firebase.py
import firebase_admin
from firebase_admin import auth

async def migrate_oauth_users_to_firebase():
    """
    Create Firebase accounts for existing OAuth users.
    """
    users = await list_users()  # Get all users from Firestore

    for user in users:
        try:
            # Check if Firebase user already exists
            try:
                firebase_user = auth.get_user_by_email(user.email)
                logger.info(f"User already exists in Firebase: {user.email}")
                continue
            except auth.UserNotFoundError:
                pass

            # Create Firebase user
            firebase_user = auth.create_user(
                uid=user.user_id,
                email=user.email,
                display_name=user.display_name,
                email_verified=True,  # Existing OAuth users are verified
            )

            logger.info(f"Migrated user to Firebase: {user.email}")

        except Exception as e:
            logger.error(f"Failed to migrate user {user.email}: {e}")
```

**Migration Timeline:**

```
Week 0 (Pre-deployment):
  - Deploy Firebase Auth alongside existing OAuth
  - No user-facing changes yet

Week 1:
  - Run migration script to create Firebase accounts
  - Test Firebase Auth with beta users
  - Monitor error rates

Week 2:
  - Enable Firebase Auth for all new signups
  - Existing users can continue with OAuth (dual support)
  - MFA grace period begins for existing users

Week 3:
  - Prompt existing OAuth users to migrate to Firebase
  - Show in-app banner: "Complete your account setup with 2FA"

Week 4:
  - Disable OAuth login endpoint
  - All users must use Firebase Auth
  - Legacy session cookies still work (24h grace period)

Week 5:
  - Remove authlib dependency
  - Remove legacy OAuth code
```

### 5.3 Rollback Plan

**Rollback Triggers:**
1. Firebase Auth availability < 98%
2. Auth failure rate > 10%
3. Auto-provision failure > 5%
4. User complaints > 10/hour

**Rollback Procedure:**

```bash
# 1. Revert Cloud Run deployment
gcloud run services update-traffic improv-olympics-app \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# 2. Disable Firebase Auth endpoints
gcloud compute security-policies rules create 1000 \
  --security-policy=block-firebase-auth \
  --expression="request.path.matches('/auth/firebase/.*')" \
  --action=deny-403

# 3. Re-enable OAuth login page
# (automatic with revision rollback)

# 4. Verify existing users can authenticate
curl -I https://ai4joy.org/auth/login

# 5. Post-mortem analysis
```

---

## 6. Risk Assessment & Mitigation

### 6.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Firebase outage | Low | High | Dual auth during migration, fallback to OAuth |
| MFA enrollment friction | High | Medium | Clear UX, help documentation, grace period |
| Auto-provision race conditions | Medium | Low | Firestore transactions, idempotent creates |
| Session cookie incompatibility | Low | High | Keep existing cookie logic, gradual migration |
| Firestore write quota exceeded | Low | High | Rate limit signups, batch writes, monitoring |

### 6.2 User Experience Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MFA setup too complex | High | High | Step-by-step wizard, video tutorial, support chat |
| Freemium limit confusion | Medium | Medium | Clear messaging, in-app counter, proactive warnings |
| Lost access (MFA device lost) | Medium | High | Backup codes, email recovery, admin override |
| Upgrade prompt too aggressive | Medium | Medium | A/B test messaging, allow text mode fallback |

### 6.3 Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Conversion rate < 10% | Medium | High | Optimize upgrade CTA, improve trial experience |
| Freemium abuse (disposable emails) | High | Low | Email verification, IP rate limiting |
| Support volume spike | High | Medium | Documentation, FAQ, automated responses |

---

## 7. Effort Estimation

### 7.1 Development Tasks

| Task | Effort (hours) | Notes |
|------|---------------|-------|
| Firebase Admin SDK integration | 4-6 | Setup, token verification |
| Firebase Client SDK frontend | 6-8 | Login UI, OAuth flow |
| MFA enrollment flow (TOTP) | 8-12 | Frontend + backend |
| MFA enforcement middleware | 4-6 | Grace period logic |
| UserProfile schema updates | 2-3 | Add freemium fields |
| Freemium access control logic | 6-8 | Update premium_middleware.py |
| Session tracking (lifetime counter) | 4-6 | Increment on audio start |
| Auto-provisioning logic | 4-6 | Create user on first auth |
| Migration scripts | 4-6 | OAuth to Firebase, add fields |
| Integration tests | 8-10 | E2E auth flow, MFA, freemium |
| Documentation updates | 4-6 | API docs, user guides |
| Monitoring & alerting | 4-6 | Custom metrics, dashboard |

**Total Estimated Effort:** 58-87 hours (7-11 days for one developer)

### 7.2 Testing & QA

| Task | Effort (hours) |
|------|---------------|
| Unit tests (new modules) | 8-10 |
| Integration tests | 10-12 |
| E2E tests (Playwright/Selenium) | 8-10 |
| Security testing (token validation) | 4-6 |
| Load testing (auto-provisioning) | 4-6 |
| UAT (user acceptance testing) | 8-10 |

**Total Testing Effort:** 42-54 hours (5-7 days)

### 7.3 Total Timeline

**Best Case:** 2 weeks (one developer, no blockers)
**Realistic:** 3 weeks (includes testing, reviews, unexpected issues)
**Conservative:** 4-5 weeks (includes migration, grace period monitoring)

---

## 8. Success Metrics

### 8.1 Technical Success Criteria

- [ ] Firebase Auth success rate > 97%
- [ ] MFA enrollment rate > 85% (within 7 days)
- [ ] Auto-provision success rate > 99.5%
- [ ] P95 auth latency < 1 second
- [ ] Zero downtime during migration
- [ ] Rollback plan tested and documented

### 8.2 Business Success Criteria

- [ ] 500+ freemium signups in first month
- [ ] 15% freemium-to-premium conversion rate (after 30 days)
- [ ] Support ticket volume < 10/day (auth-related)
- [ ] User satisfaction score > 4.2/5 for auth experience

### 8.3 User Experience Criteria

- [ ] MFA enrollment completable in < 2 minutes
- [ ] Upgrade CTA click-through rate > 20%
- [ ] < 5% of users abandon during MFA setup
- [ ] Clear session counter visible on profile page
- [ ] Text mode fallback works seamlessly

---

## 9. Open Questions

### 9.1 Product Decisions Required

1. **MFA Enrollment Timing:**
   - Q: Require MFA immediately after first signup, or allow first session without MFA?
   - A: Recommend immediate requirement to avoid building "MFA-free" user habit

2. **Freemium Session Definition:**
   - Q: Does opening audio WebSocket count as session, or first message sent?
   - A: Recommend first audio message sent (clear, measurable)

3. **Upgrade Prompt Location:**
   - Q: Show modal immediately when limit hit, or inline banner?
   - A: Recommend modal with "Upgrade" and "Continue with Text" options

4. **MFA Recovery Process:**
   - Q: If user loses MFA device, how do they regain access?
   - A: Recommend backup codes (generated on enrollment) + admin override

### 9.2 Technical Investigations Needed

1. **Firebase Quota Limits:**
   - Q: Does Firebase Auth have rate limits on token verification?
   - A: Need to confirm with Firebase documentation (likely 10K/min for ID token verification)

2. **Session Cookie Domain:**
   - Q: Should cookies be scoped to `ai4joy.org` or `*.ai4joy.org`?
   - A: Current implementation uses `ai4joy.org` - verify if subdomains planned

3. **Firestore Write Throughput:**
   - Q: Can Firestore handle 100 concurrent user record creates?
   - A: Need load testing - Firestore supports 10K writes/second per database

4. **MFA Device Limit:**
   - Q: How many TOTP devices can a user enroll?
   - A: Firebase supports up to 5 multi-factor enrollments per user

---

## 10. Appendix

### 10.1 File Change Summary

**Files to Create:**
- `/app/services/firebase_auth_service.py` - Firebase Admin SDK integration
- `/app/middleware/mfa_enforcement.py` - MFA requirement enforcement
- `/app/routers/firebase_auth.py` - Firebase auth endpoints
- `/static/firebase-auth.js` - Firebase Client SDK frontend
- `/scripts/migrate_oauth_to_firebase.py` - User migration script
- `/scripts/add_freemium_fields.py` - Schema migration script

**Files to Modify:**
- `/app/models/user.py` - Add freemium fields to UserProfile
- `/app/services/user_service.py` - Update create_user() for auto-provision
- `/app/audio/premium_middleware.py` - Add freemium tier logic
- `/app/routers/auth.py` - Add Firebase token verification endpoint
- `/app/middleware/oauth_auth.py` - Support dual authentication
- `/app/main.py` - Initialize Firebase Admin SDK
- `/app/config.py` - Add Firebase configuration
- `/requirements.txt` - Add firebase-admin dependency

**Files to (Eventually) Remove:**
- `/app/middleware/oauth_auth.py` - After migration complete (keep session logic)
- OAuth-related tests in `/tests/` - Replace with Firebase tests

### 10.2 Firebase Configuration

**Environment Variables:**

```bash
# .env.local
FIREBASE_PROJECT_ID=coherent-answer-479115-e1
FIREBASE_API_KEY=your-api-key-from-console

# Cloud Run environment
gcloud run services update improv-olympics-app \
  --update-env-vars FIREBASE_PROJECT_ID=coherent-answer-479115-e1
```

**Frontend Firebase Config:**

```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "ai4joy.org",
  projectId: "coherent-answer-479115-e1",
  storageBucket: "coherent-answer-479115-e1.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

### 10.3 References

**Firebase Documentation:**
- [Firebase Auth Admin SDK (Python)](https://firebase.google.com/docs/auth/admin)
- [Firebase Multi-Factor Authentication](https://firebase.google.com/docs/auth/web/multi-factor)
- [ID Token Verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens)

**Current Implementation:**
- [PRD: Multi-Provider OAuth & Freemium Tier](/docs/prds/multi-provider-oauth-freemium-tier-prd.md)
- [Firestore Schema Documentation](/docs/FIRESTORE_SCHEMA.md)

**External Resources:**
- [TOTP Algorithm (RFC 6238)](https://datatracker.ietf.org/doc/html/rfc6238)
- [OAuth 2.0 Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)

---

## 11. Next Steps

### 11.1 Pre-Implementation Checklist

- [ ] Product approval on freemium tier limits (2 sessions)
- [ ] Legal review of MFA requirements and data handling
- [ ] Design mockups for MFA enrollment flow
- [ ] Firebase project setup in GCP console
- [ ] Create Firebase API keys for frontend
- [ ] Set up Secret Manager for Firebase credentials
- [ ] Load testing plan for auto-provisioning
- [ ] Monitoring dashboard mockups
- [ ] Customer support playbook for MFA issues

### 11.2 Post-Implementation Review

- [ ] Monitor Firebase Auth success rates (daily for 2 weeks)
- [ ] A/B test MFA enrollment UX variations
- [ ] Analyze freemium-to-premium conversion funnel
- [ ] Gather user feedback on MFA experience
- [ ] Optimize upgrade CTA based on conversion data
- [ ] Review and adjust freemium limits based on usage patterns
- [ ] Document lessons learned for future migrations

---

**End of Technical Analysis**

**Document Prepared By:** Claude (AI Assistant)
**Review Status:** Ready for Engineering Review
**Contact:** Project Lead for implementation planning
