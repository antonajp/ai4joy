# Firestore Schema Documentation

Complete schema definition for the Improv Olympics application Firestore database, including OAuth user tracking and rate limiting.

## Database Configuration

**Database Name:** `(default)`
**Type:** Firestore Native Mode
**Region:** us-central1
**Backup Strategy:** Daily automated exports to Cloud Storage

---

## Collections

### 1. `sessions` Collection

Stores active and completed improv game sessions with full conversation history.

**Document ID:** Auto-generated UUID (e.g., `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)

**Document Structure:**

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "accounts.google.com:1234567890",
  "user_email": "user@example.com",
  "created_at": "2025-11-23T10:30:00Z",
  "updated_at": "2025-11-23T10:45:00Z",
  "status": "active",
  "current_phase": "PHASE_2_FALLIBLE",
  "turn_count": 12,
  "game_type": "worlds-worst-advice",
  "location": "A haunted library",
  "conversation_history": [
    {
      "turn": 1,
      "timestamp": "2025-11-23T10:30:15Z",
      "agent": "location_master",
      "role": "assistant",
      "content": "Welcome! Let's begin our improv session at: A haunted library",
      "latency_ms": 245
    },
    {
      "turn": 2,
      "timestamp": "2025-11-23T10:31:02Z",
      "agent": "player_1",
      "role": "user",
      "content": "I'm looking for a book on ghost hunting techniques.",
      "latency_ms": 0
    }
  ],
  "game_state": {
    "phase": "PHASE_2_FALLIBLE",
    "suggestion_count": 0,
    "successful_suggestions": 0,
    "failed_suggestions": 2,
    "current_performer": "player_1"
  },
  "metadata": {
    "source": "web",
    "build_id": "20251123-abc123",
    "cost_estimate": 0.42
  }
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | Unique session identifier (UUID) |
| `user_id` | string | Yes | OAuth user ID from IAP header (e.g., `accounts.google.com:1234567890`) |
| `user_email` | string | Yes | User email from IAP header for debugging/support |
| `created_at` | timestamp | Yes | Session creation timestamp (ISO 8601) |
| `updated_at` | timestamp | Yes | Last update timestamp (ISO 8601) |
| `status` | string | Yes | Session status: `active`, `completed`, `abandoned` |
| `current_phase` | string | Yes | Game phase: `PHASE_1_SUPPORT`, `PHASE_2_FALLIBLE` |
| `turn_count` | integer | Yes | Total number of turns taken |
| `game_type` | string | Yes | Game format (e.g., `worlds-worst-advice`) |
| `location` | string | Yes | Improv scene location |
| `conversation_history` | array | Yes | Full conversation history with timestamps |
| `game_state` | object | Yes | Current game state and counters |
| `metadata` | object | No | Additional metadata (source, build_id, cost_estimate) |

**Indexes:**

```
- user_id (ascending) + created_at (descending)
  Purpose: Query sessions by user, sorted by date

- status (ascending) + created_at (descending)
  Purpose: Query active sessions

- user_id (ascending) + status (ascending)
  Purpose: Query active sessions for specific user
```

**Security Rules:**

```javascript
match /sessions/{sessionId} {
  // Users can only read/write their own sessions
  allow read, write: if request.auth.token.email == resource.data.user_email;

  // Allow creation if user_id matches authenticated user
  allow create: if request.resource.data.user_id == request.auth.uid;
}
```

---

### 2. `user_limits` Collection

Tracks per-user rate limiting and cost management for OAuth users.

**Document ID:** OAuth user ID (e.g., `accounts.google.com:1234567890`)

**Document Structure:**

```json
{
  "user_id": "accounts.google.com:1234567890",
  "email": "user@example.com",
  "sessions_today": 7,
  "last_reset": "2025-11-23T00:00:00Z",
  "active_sessions": 2,
  "active_session_ids": [
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "f1e2d3c4-b5a6-9876-fedc-ba0987654321"
  ],
  "total_sessions": 42,
  "total_cost_estimate": 89.45,
  "daily_cost_today": 14.20,
  "first_session_at": "2025-11-15T14:22:00Z",
  "last_session_at": "2025-11-23T10:30:00Z",
  "rate_limit_overrides": {
    "daily_limit": 10,
    "concurrent_limit": 3
  },
  "flags": {
    "is_admin": false,
    "is_tester": true,
    "unlimited_sessions": false
  }
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | Yes | OAuth user ID from IAP (document ID) |
| `email` | string | Yes | User email for support/debugging |
| `sessions_today` | integer | Yes | Number of sessions created today |
| `last_reset` | timestamp | Yes | Last daily reset timestamp (midnight UTC) |
| `active_sessions` | integer | Yes | Number of currently active sessions |
| `active_session_ids` | array | Yes | List of active session IDs |
| `total_sessions` | integer | Yes | Total sessions created (all-time) |
| `total_cost_estimate` | float | Yes | Estimated total cost in USD |
| `daily_cost_today` | float | Yes | Estimated cost today in USD |
| `first_session_at` | timestamp | Yes | First session creation timestamp |
| `last_session_at` | timestamp | Yes | Most recent session creation timestamp |
| `rate_limit_overrides` | object | No | Custom rate limits for this user (admin only) |
| `flags` | object | No | User flags (admin, tester, unlimited_sessions) |

**Default Rate Limits:**

```python
DEFAULT_DAILY_SESSION_LIMIT = 10      # Max sessions per user per day
DEFAULT_CONCURRENT_LIMIT = 3          # Max concurrent active sessions
MAX_COST_PER_USER_PER_DAY = 2.00      # USD (10 sessions × $0.20)
```

**Indexes:**

```
- email (ascending)
  Purpose: Look up user by email

- sessions_today (descending) + last_reset (descending)
  Purpose: Identify heavy users

- daily_cost_today (descending)
  Purpose: Cost monitoring and alerts
```

**Security Rules:**

```javascript
match /user_limits/{userId} {
  // Users can read their own limits
  allow read: if request.auth.uid == userId;

  // Only backend service account can write
  allow write: if request.auth.token.email.endsWith('@gcp-sa-iap.iam.gserviceaccount.com');
}
```

---

### 3. `admin_config` Collection (Optional)

Global configuration for rate limits and feature flags.

**Document ID:** `rate_limits`

**Document Structure:**

```json
{
  "default_daily_session_limit": 10,
  "default_concurrent_session_limit": 3,
  "max_cost_per_user_per_day": 2.00,
  "emergency_circuit_breaker": {
    "enabled": false,
    "daily_cost_threshold": 250.00,
    "message": "Service temporarily unavailable due to high demand. Please try again later."
  },
  "feature_flags": {
    "rate_limiting_enabled": true,
    "cost_tracking_enabled": true,
    "allow_new_users": true
  },
  "updated_at": "2025-11-23T10:00:00Z",
  "updated_by": "admin@ai4joy.org"
}
```

---

## Initialization Script

### Create Collections and Initial Documents

```bash
# Set project
PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# Create user_limits document for admin user
cat <<'EOF' > /tmp/admin_limits.json
{
  "user_id": "accounts.google.com:ADMIN_USER_ID",
  "email": "admin@ai4joy.org",
  "sessions_today": 0,
  "last_reset": "2025-11-23T00:00:00Z",
  "active_sessions": 0,
  "active_session_ids": [],
  "total_sessions": 0,
  "total_cost_estimate": 0.0,
  "daily_cost_today": 0.0,
  "first_session_at": null,
  "last_session_at": null,
  "rate_limit_overrides": {
    "daily_limit": 100,
    "concurrent_limit": 10
  },
  "flags": {
    "is_admin": true,
    "is_tester": true,
    "unlimited_sessions": false
  }
}
EOF

# Import via gcloud (requires firebase CLI)
# npm install -g firebase-tools
# firebase firestore:import /tmp --project $PROJECT_ID

# Or use Firestore REST API
# See: https://cloud.google.com/firestore/docs/reference/rest
```

### Initialize Rate Limit Config

```bash
# Create admin_config/rate_limits document
cat <<'EOF' > /tmp/rate_limits.json
{
  "default_daily_session_limit": 10,
  "default_concurrent_session_limit": 3,
  "max_cost_per_user_per_day": 2.00,
  "emergency_circuit_breaker": {
    "enabled": false,
    "daily_cost_threshold": 250.00,
    "message": "Service temporarily unavailable. Please try again later."
  },
  "feature_flags": {
    "rate_limiting_enabled": true,
    "cost_tracking_enabled": true,
    "allow_new_users": true
  },
  "updated_at": "2025-11-23T00:00:00Z",
  "updated_by": "system"
}
EOF
```

---

## Rate Limiting Implementation

### Check Rate Limits (Application Code)

```python
from datetime import datetime, timedelta
from google.cloud import firestore

def check_rate_limits(user_id: str, user_email: str) -> tuple[bool, str]:
    """
    Check if user has exceeded rate limits.

    Returns:
        (allowed, message): Tuple of boolean and error message
    """
    db = firestore.Client()

    # Get or create user limits document
    user_limits_ref = db.collection('user_limits').document(user_id)
    user_limits = user_limits_ref.get()

    if not user_limits.exists:
        # First session for this user
        user_limits_ref.set({
            'user_id': user_id,
            'email': user_email,
            'sessions_today': 1,
            'last_reset': datetime.utcnow().replace(hour=0, minute=0, second=0),
            'active_sessions': 1,
            'active_session_ids': [],
            'total_sessions': 1,
            'total_cost_estimate': 0.0,
            'daily_cost_today': 0.0,
            'first_session_at': datetime.utcnow(),
            'last_session_at': datetime.utcnow(),
            'flags': {'is_admin': False, 'is_tester': False}
        })
        return True, ""

    limits = user_limits.to_dict()

    # Check if daily reset needed
    last_reset = limits['last_reset']
    if datetime.utcnow() - last_reset > timedelta(days=1):
        # Reset daily counters
        user_limits_ref.update({
            'sessions_today': 0,
            'daily_cost_today': 0.0,
            'last_reset': datetime.utcnow().replace(hour=0, minute=0, second=0)
        })
        limits['sessions_today'] = 0

    # Get rate limits (use overrides if present)
    daily_limit = limits.get('rate_limit_overrides', {}).get('daily_limit', 10)
    concurrent_limit = limits.get('rate_limit_overrides', {}).get('concurrent_limit', 3)

    # Check unlimited flag
    if limits.get('flags', {}).get('unlimited_sessions', False):
        return True, ""

    # Check daily limit
    if limits['sessions_today'] >= daily_limit:
        return False, f"Daily session limit reached ({limits['sessions_today']}/{daily_limit}). Try again tomorrow."

    # Check concurrent limit
    if limits['active_sessions'] >= concurrent_limit:
        return False, f"Concurrent session limit reached ({limits['active_sessions']}/{concurrent_limit}). Complete an existing session first."

    return True, ""
```

### Update Session Counters

```python
def increment_session_counter(user_id: str):
    """Increment session counters when new session starts."""
    db = firestore.Client()
    user_limits_ref = db.collection('user_limits').document(user_id)

    user_limits_ref.update({
        'sessions_today': firestore.Increment(1),
        'active_sessions': firestore.Increment(1),
        'total_sessions': firestore.Increment(1),
        'last_session_at': datetime.utcnow()
    })

def decrement_active_sessions(user_id: str):
    """Decrement active session count when session completes."""
    db = firestore.Client()
    user_limits_ref = db.collection('user_limits').document(user_id)

    user_limits_ref.update({
        'active_sessions': firestore.Increment(-1)
    })
```

---

## Backup Strategy

### Daily Automated Backups

Configured in Terraform (`main.tf`):

```terraform
resource "google_cloud_scheduler_job" "firestore_backup" {
  name        = "firestore-daily-backup"
  schedule    = "0 2 * * *"  # 2 AM UTC daily
  time_zone   = "UTC"

  http_target {
    http_method = "POST"
    uri         = "https://firestore.googleapis.com/v1/projects/${var.project_id}/databases/(default):exportDocuments"

    body = base64encode(jsonencode({
      outputUriPrefix = "gs://${var.project_id}-backups/firestore/${formatdate("YYYY-MM-DD", timestamp())}"
    }))
  }
}
```

### Manual Backup

```bash
# Export all collections
gcloud firestore export \
  gs://your-gcp-project-id-backups/firestore/manual-$(date +%Y%m%d) \
  --project=your-gcp-project-id

# Export specific collection
gcloud firestore export \
  gs://your-gcp-project-id-backups/firestore/sessions-$(date +%Y%m%d) \
  --collection-ids=sessions \
  --project=your-gcp-project-id
```

### Restore from Backup

```bash
# Restore all collections
gcloud firestore import \
  gs://your-gcp-project-id-backups/firestore/2025-11-23 \
  --project=your-gcp-project-id

# Restore specific collection
gcloud firestore import \
  gs://your-gcp-project-id-backups/firestore/2025-11-23 \
  --collection-ids=sessions \
  --project=your-gcp-project-id
```

---

## Monitoring Queries

### Query High-Usage Users

```bash
# Get users with most sessions today
gcloud firestore documents list user_limits \
  --filter="sessions_today>5" \
  --order-by=sessions_today \
  --project=your-gcp-project-id
```

### Query Cost by User

```python
from google.cloud import firestore

db = firestore.Client()
user_limits = db.collection('user_limits') \
    .order_by('daily_cost_today', direction=firestore.Query.DESCENDING) \
    .limit(10) \
    .stream()

print("Top 10 users by cost today:")
for user in user_limits:
    data = user.to_dict()
    print(f"{data['email']}: ${data['daily_cost_today']:.2f}")
```

---

## Best Practices

1. **Always check rate limits before creating sessions**
2. **Update user_limits atomically using Firestore transactions**
3. **Reset daily counters at midnight UTC**
4. **Track cost estimates for budget monitoring**
5. **Use indexes for efficient queries**
6. **Back up database daily**
7. **Monitor high-usage users**
8. **Implement emergency circuit breaker for cost protection**

---

**Document Version:** 1.0
**Last Updated:** 2025-11-23
**Maintained by:** ai4joy.org team
