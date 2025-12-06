# Firebase Authentication Setup (IQS-65 Phase 1)

This document describes the Firebase Authentication implementation for the Improv Olympics application.

## Overview

Phase 1 implements Firebase Authentication alongside the existing Google OAuth 2.0 flow, providing:

- Email/password authentication (AC-AUTH-01)
- Google Sign-In via Firebase (AC-AUTH-02)
- Email verification enforcement (AC-AUTH-03)
- Firebase ID token verification (AC-AUTH-04)
- Automatic migration for existing OAuth users (AC-AUTH-05)
- Freemium tier support (default: 'free' tier)

## Architecture

### Backend Components

1. **Firebase Admin SDK Integration** (`app/main.py`)
   - Initializes Firebase Admin SDK on startup
   - Uses Application Default Credentials (Workload Identity in Cloud Run)
   - Gracefully handles initialization failures

2. **Firebase Auth Service** (`app/services/firebase_auth_service.py`)
   - Verifies Firebase ID tokens
   - Creates/migrates user profiles
   - Enforces email verification
   - Converts Firebase tokens to session cookies

3. **Token Verification Endpoint** (`POST /auth/firebase/token`)
   - Accepts Firebase ID tokens from frontend
   - Validates token and email verification
   - Creates session cookie compatible with OAuth flow
   - Returns user profile with tier information

4. **Configuration** (`app/config.py`)
   - `FIREBASE_AUTH_ENABLED`: Enable/disable Firebase auth
   - `FIREBASE_REQUIRE_EMAIL_VERIFICATION`: Enforce email verification
   - `FIREBASE_PROJECT_ID`: Firebase project ID (defaults to GCP project)

### Frontend Components

1. **Firebase Auth Module** (`static/firebase-auth.js`)
   - Firebase SDK integration
   - Email/password authentication
   - Google Sign-In
   - Automatic token refresh (every 50 minutes)
   - Session cookie management

2. **Usage Example**:
```javascript
import {
    initializeFirebaseAuth,
    signInWithGoogle,
    signInWithEmail,
    signUpWithEmail
} from './firebase-auth.js';

// Initialize Firebase
await initializeFirebaseAuth({
    apiKey: "YOUR_API_KEY",
    authDomain: "your-project.firebaseapp.com",
    projectId: "your-project-id",
});

// Sign in with Google
const user = await signInWithGoogle();

// Or sign in with email/password
const user = await signInWithEmail('user@example.com', 'password');
```

## Deployment Steps

### 1. Enable Firebase Authentication on GCP Project

```bash
# Enable Firebase Authentication API
gcloud services enable firebase.googleapis.com --project=coherent-answer-479115-e1
gcloud services enable firebaseauth.googleapis.com --project=coherent-answer-479115-e1

# Enable Identity Toolkit API (required by Firebase Auth)
gcloud services enable identitytoolkit.googleapis.com --project=coherent-answer-479115-e1
```

### 2. Configure Firebase Authentication

1. Go to Firebase Console: https://console.firebase.google.com/
2. Select project: `coherent-answer-479115-e1`
3. Navigate to Authentication > Sign-in method
4. Enable:
   - Email/Password authentication
   - Google authentication
5. Add authorized domains:
   - `ai4joy.org`
   - `localhost` (for development)

### 3. Update Environment Variables

Add to `.env.local` (development) and Cloud Run environment (production):

```bash
# Enable Firebase Authentication
FIREBASE_AUTH_ENABLED=true

# Enforce email verification (recommended)
FIREBASE_REQUIRE_EMAIL_VERIFICATION=true

# Firebase project ID (uses GCP project by default)
FIREBASE_PROJECT_ID=coherent-answer-479115-e1

# For local development only:
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs `firebase-admin>=6.5.0` which is required for token verification.

### 5. Update Frontend HTML

Add Firebase SDK to your HTML files (before loading `firebase-auth.js`):

```html
<!-- Firebase SDK v9 (modular) -->
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/9.23.0/firebase-auth-compat.js"></script>

<!-- Firebase Configuration -->
<script>
    const firebaseConfig = {
        apiKey: "YOUR_API_KEY",
        authDomain: "your-project.firebaseapp.com",
        projectId: "your-project-id",
        storageBucket: "your-project.appspot.com",
        messagingSenderId: "123456789",
        appId: "1:123456789:web:abc123def456"
    };

    // Initialize Firebase Auth module
    import('./firebase-auth.js').then(module => {
        module.initializeFirebaseAuth(firebaseConfig);
    });
</script>
```

**Security Note**: Firebase API keys are public and safe to include in frontend code. They identify your Firebase project but don't grant access without proper Firebase Security Rules.

### 6. Deploy to Cloud Run

```bash
# Deploy with Firebase auth enabled
cd terraform/
terraform apply -var="firebase_auth_enabled=true"

# Or update existing Cloud Run service
gcloud run services update improv-olympics \
    --update-env-vars FIREBASE_AUTH_ENABLED=true,FIREBASE_REQUIRE_EMAIL_VERIFICATION=true \
    --region us-central1 \
    --project coherent-answer-479115-e1
```

## User Migration Flow

Existing Google OAuth users are automatically migrated when they first sign in with Firebase:

1. User signs in with Google via Firebase
2. Backend checks for existing user by email
3. If found, updates `user_id` to Firebase UID
4. User retains existing tier and data
5. Migration timestamp recorded in Firestore

**Important**: OAuth users should be encouraged to migrate to Firebase for MFA support (Phase 2).

## Session Cookie Compatibility

Firebase ID tokens are converted to the same session cookie format as OAuth:

```python
{
    "sub": "firebase_uid",
    "email": "user@example.com",
    "name": "User Name",
    "email_verified": True,
    "auth_provider": "firebase",
    "created_at": 1234567890
}
```

This ensures:
- Existing middleware works without changes
- Session cookies remain httponly and secure
- 24-hour session expiration (same as OAuth)
- Backend doesn't need to distinguish auth method

## Freemium Tier Implementation

New Firebase users are automatically assigned the 'free' tier:

- **Free Tier**: Text-only access, no audio features
- **Regular Tier**: Text access (legacy tier)
- **Premium Tier**: Text + audio access

Admin API (Phase 2) will allow tier upgrades via:
- Manual admin promotion
- Stripe payment integration
- Promotional codes

## Email Verification Enforcement

Email verification is enforced by default (AC-AUTH-03):

1. User signs up with email/password
2. Verification email sent automatically
3. User must click verification link
4. Backend rejects unverified users at token verification
5. Frontend also checks `emailVerified` status

To disable (not recommended):
```bash
FIREBASE_REQUIRE_EMAIL_VERIFICATION=false
```

## Token Lifecycle

Firebase ID tokens expire after 1 hour:

1. **Client-side**: Frontend refreshes token every 50 minutes
2. **Server-side**: Backend validates token signature and expiration
3. **Session cookie**: Created with 24-hour expiration
4. **Token refresh**: Automatic before expiration

## Testing

### Test Email/Password Sign Up
```bash
curl -X POST http://localhost:8080/auth/firebase/token \
  -H "Content-Type: application/json" \
  -d '{"id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

### Test Existing User Migration
1. Create user via OAuth flow
2. Sign in with same email via Firebase
3. Verify `user_id` updated to Firebase UID
4. Verify tier preserved

## Security Considerations

1. **Token Expiration**: Firebase ID tokens expire after 1 hour
2. **Email Verification**: Enforced to prevent fake accounts
3. **Session Cookies**: httponly, secure, samesite=lax
4. **Workload Identity**: No service account keys in production
5. **HTTPS Only**: Secure cookies only in production

## Troubleshooting

### Firebase Admin SDK Initialization Fails
- Check `GOOGLE_APPLICATION_CREDENTIALS` in local dev
- Verify Workload Identity configured in Cloud Run
- Check Firebase APIs enabled in GCP project

### Email Verification Not Working
- Check Firebase Console > Authentication > Templates
- Verify authorized domains configured
- Check spam folder for verification emails

### Token Verification Fails
- Check token not expired (1 hour limit)
- Verify Firebase project ID matches
- Check backend logs for detailed error messages

### Existing Users Can't Sign In
- Migration happens automatically on first Firebase login
- User must use same email address
- OAuth users can continue using OAuth flow

## Next Steps (Phase 2)

- Multi-factor authentication (MFA) support
- Admin API for tier management
- Stripe payment integration
- Password reset UI
- User profile management
