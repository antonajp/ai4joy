# Improv Olympics API Documentation

**Version**: 1.0
**Last Updated**: 2025-11-24
**Base URL**: `https://YOUR-SERVICE-URL.run.app`

This document provides comprehensive documentation for the Improv Olympics REST API endpoints.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Error Handling](#error-handling)
3. [Rate Limiting](#rate-limiting)
4. [Endpoints](#endpoints)
   - [Health & Readiness](#health--readiness)
   - [Authentication Endpoints](#authentication-endpoints)
   - [Session Management](#session-management)
   - [Rate Limit Status](#rate-limit-status)
5. [Data Models](#data-models)
6. [Example Workflows](#example-workflows)
7. [Testing](#testing)

---

## Authentication

The Improv Olympics API uses **OAuth 2.0** for authentication with Google as the identity provider.

### Authentication Flow

1. **Initiate Login**: Navigate to `/auth/login`
2. **Google OAuth**: User authenticates with Google
3. **Callback**: Google redirects to `/auth/callback` with authorization code
4. **Session Cookie**: Server sets secure session cookie
5. **API Access**: Subsequent requests include session cookie automatically

### Authentication Headers

For programmatic access (integration tests), you can mock IAP headers:

```
X-Goog-Authenticated-User-Id: <user-id>
X-Goog-Authenticated-User-Email: <user-email>
```

**Note**: In production, these headers are set by Google Identity-Aware Proxy (IAP) and cannot be spoofed.

### Access Control

Access is restricted to users in the **allowed users list** configured via the `ALLOWED_USERS` environment variable.

---

## Error Handling

### Error Response Format

All errors return a JSON object with the following structure:

```json
{
  "detail": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | User not authorized for this resource |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error occurred |
| 503 | Service Unavailable | Service temporarily unavailable |
| 504 | Gateway Timeout | Request timed out |

### Common Error Scenarios

**Rate Limit Exceeded (429)**:
```json
{
  "detail": "Daily session limit of 10 sessions reached. Try again tomorrow."
}
```

**Session Not Found (404)**:
```json
{
  "detail": "Session not found or expired"
}
```

**Unauthorized Access (403)**:
```json
{
  "detail": "Not authorized to access this session"
}
```

**Turn Sequence Error (400)**:
```json
{
  "detail": "Expected turn 3, got 5"
}
```

---

## Rate Limiting

### Limits

| Limit Type | Default Value | Scope |
|------------|---------------|-------|
| Daily Sessions | 10 | Per user per day |
| Concurrent Sessions | 3 | Per user |
| Request Timeout | 300s | Per request |

### Rate Limit Headers

Rate limit information is included in API responses:

```
X-RateLimit-Daily-Limit: 10
X-RateLimit-Daily-Remaining: 7
X-RateLimit-Concurrent-Limit: 3
X-RateLimit-Concurrent-Used: 1
```

### Checking Rate Limits

Use `GET /api/v1/user/limits` to check current rate limit status.

---

## Endpoints

### Health & Readiness

#### GET /health

Check if the service is healthy.

**Authentication**: None required

**Request**:
```bash
curl https://YOUR-SERVICE-URL.run.app/health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-11-24T16:30:00Z"
}
```

---

#### GET /ready

Check if the service is ready to accept requests.

**Authentication**: None required

**Request**:
```bash
curl https://YOUR-SERVICE-URL.run.app/ready
```

**Response** (200 OK):
```json
{
  "status": "ready",
  "timestamp": "2025-11-24T16:30:00Z"
}
```

---

### Authentication Endpoints

#### GET /auth/login

Initiate OAuth login flow.

**Authentication**: None required

**Request**:
```bash
curl -L https://YOUR-SERVICE-URL.run.app/auth/login
```

**Response**: Redirect to Google OAuth consent screen

---

#### GET /auth/callback

OAuth callback endpoint (handled automatically by browser).

**Authentication**: None required

**Query Parameters**:
- `code` (string, required): Authorization code from Google
- `state` (string, required): CSRF protection token

**Response**: Redirect to application home with session cookie set

---

#### GET /auth/logout

Log out and clear session.

**Authentication**: Session cookie required

**Request**:
```bash
curl -X GET https://YOUR-SERVICE-URL.run.app/auth/logout \
  -b "session_id=<session-cookie>"
```

**Response**: Redirect to home page with session cleared

---

### Session Management

#### POST /api/v1/session/start

Create a new improv session.

**Authentication**: Required

**Rate Limits**:
- Daily: 10 sessions per user per day
- Concurrent: 3 active sessions per user

**Request Body**:
```json
{
  "location": "Spaceship Bridge",
  "user_name": "Captain Rodriguez"
}
```

**Parameters**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| location | string | Yes | 1-200 chars | Scene location/setting |
| user_name | string | No | 1-100 chars | Optional display name |

**Request Example**:
```bash
curl -X POST https://YOUR-SERVICE-URL.run.app/api/v1/session/start \
  -H "Content-Type: application/json" \
  -H "X-Goog-Authenticated-User-Id: user123" \
  -H "X-Goog-Authenticated-User-Email: user@example.com" \
  -d '{
    "location": "Spaceship Bridge",
    "user_name": "Captain Rodriguez"
  }'
```

**Response** (201 Created):
```json
{
  "session_id": "sess_a1b2c3d4e5f6g7h8",
  "status": "initialized",
  "location": "Spaceship Bridge",
  "created_at": "2025-11-24T16:00:00Z",
  "expires_at": "2025-11-24T17:00:00Z",
  "turn_count": 0
}
```

**Errors**:
- 400: Invalid location (empty or too long)
- 401: Not authenticated
- 429: Rate limit exceeded

---

#### GET /api/v1/session/{session_id}

Retrieve session information.

**Authentication**: Required (must be session owner)

**Path Parameters**:
- `session_id` (string, required): Session identifier

**Request Example**:
```bash
curl https://YOUR-SERVICE-URL.run.app/api/v1/session/sess_a1b2c3d4e5f6g7h8 \
  -H "X-Goog-Authenticated-User-Id: user123" \
  -H "X-Goog-Authenticated-User-Email: user@example.com"
```

**Response** (200 OK):
```json
{
  "session_id": "sess_a1b2c3d4e5f6g7h8",
  "status": "active",
  "location": "Spaceship Bridge",
  "created_at": "2025-11-24T16:00:00Z",
  "expires_at": "2025-11-24T17:00:00Z",
  "turn_count": 5
}
```

**Errors**:
- 401: Not authenticated
- 403: Not authorized (not session owner)
- 404: Session not found or expired

---

#### POST /api/v1/session/{session_id}/turn

Execute a turn in the improv session.

**Authentication**: Required (must be session owner)

**Path Parameters**:
- `session_id` (string, required): Session identifier

**Request Body**:
```json
{
  "user_input": "Captain's log, stardate 2345.6. We've entered orbit around Mars.",
  "turn_number": 1
}
```

**Parameters**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| user_input | string | Yes | 1-1000 chars | User's scene contribution |
| turn_number | integer | Yes | >= 1 | Turn number (must be sequential) |

**Request Example**:
```bash
curl -X POST https://YOUR-SERVICE-URL.run.app/api/v1/session/sess_a1b2c3d4e5f6g7h8/turn \
  -H "Content-Type: application/json" \
  -H "X-Goog-Authenticated-User-Id: user123" \
  -H "X-Goog-Authenticated-User-Email: user@example.com" \
  -d '{
    "user_input": "Captain'\''s log, stardate 2345.6. We'\''ve entered orbit around Mars.",
    "turn_number": 1
  }'
```

**Response** (200 OK):
```json
{
  "turn_number": 1,
  "partner_response": "Acknowledged, Captain. All systems nominal. Shall I initiate landing sequence?",
  "room_vibe": {
    "analysis": "The audience is engaged and curious about the mission.",
    "energy": "positive",
    "engagement_level": "high"
  },
  "current_phase": 1,
  "timestamp": "2025-11-24T16:05:00Z",
  "coach_feedback": null
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| turn_number | integer | Turn number executed |
| partner_response | string | Partner agent's scene contribution |
| room_vibe | object | Audience sentiment analysis |
| room_vibe.analysis | string | Qualitative audience analysis |
| room_vibe.energy | string | Audience energy level |
| room_vibe.engagement_level | string | Audience engagement rating |
| current_phase | integer | Current partner phase (1 or 2) |
| timestamp | string (ISO 8601) | Turn completion timestamp |
| coach_feedback | string \| null | Coach feedback (only at turn 15+) |

**Phase Transitions**:
- **Phase 1** (Turns 1-4): Partner is supportive and helpful
- **Phase 2** (Turns 5+): Partner becomes more fallible and human

**Coach Feedback**:
- Appears starting at turn 15
- Provides constructive feedback on improv techniques
- Highlights strengths and areas for improvement

**Errors**:
- 400: Invalid turn number (out of sequence)
- 401: Not authenticated
- 403: Not authorized (not session owner)
- 404: Session not found
- 422: Content policy violation (offensive content or prompt injection)
- 504: Agent execution timeout (>30s)

---

#### POST /api/v1/session/{session_id}/close

Close an active session.

**Authentication**: Required (must be session owner)

**Path Parameters**:
- `session_id` (string, required): Session identifier

**Request Example**:
```bash
curl -X POST https://YOUR-SERVICE-URL.run.app/api/v1/session/sess_a1b2c3d4e5f6g7h8/close \
  -H "X-Goog-Authenticated-User-Id: user123" \
  -H "X-Goog-Authenticated-User-Email: user@example.com"
```

**Response** (200 OK):
```json
{
  "status": "closed",
  "session_id": "sess_a1b2c3d4e5f6g7h8"
}
```

**Errors**:
- 401: Not authenticated
- 403: Not authorized (not session owner)
- 404: Session not found

---

### Rate Limit Status

#### GET /api/v1/user/limits

Get current rate limit status for authenticated user.

**Authentication**: Required

**Request Example**:
```bash
curl https://YOUR-SERVICE-URL.run.app/api/v1/user/limits \
  -H "X-Goog-Authenticated-User-Id: user123" \
  -H "X-Goog-Authenticated-User-Email: user@example.com"
```

**Response** (200 OK):
```json
{
  "user_id": "user123",
  "limits": {
    "daily_sessions_limit": 10,
    "daily_sessions_used": 3,
    "daily_sessions_remaining": 7,
    "concurrent_sessions_limit": 3,
    "concurrent_sessions_count": 1,
    "concurrent_sessions_remaining": 2,
    "daily_reset_at": "2025-11-25T00:00:00Z"
  }
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| user_id | string | Authenticated user ID |
| daily_sessions_limit | integer | Max sessions per day |
| daily_sessions_used | integer | Sessions used today |
| daily_sessions_remaining | integer | Sessions remaining today |
| concurrent_sessions_limit | integer | Max concurrent sessions |
| concurrent_sessions_count | integer | Current active sessions |
| concurrent_sessions_remaining | integer | Concurrent slots available |
| daily_reset_at | string (ISO 8601) | When daily counter resets |

**Errors**:
- 401: Not authenticated

---

## Data Models

### SessionCreate

```json
{
  "location": "string (1-200 chars, required)",
  "user_name": "string (1-100 chars, optional)"
}
```

### SessionResponse

```json
{
  "session_id": "string",
  "status": "initialized|active|closed|timeout",
  "location": "string",
  "created_at": "ISO 8601 datetime",
  "expires_at": "ISO 8601 datetime",
  "turn_count": "integer"
}
```

### TurnInput

```json
{
  "user_input": "string (1-1000 chars, required)",
  "turn_number": "integer (>= 1, required)"
}
```

### TurnResponse

```json
{
  "turn_number": "integer",
  "partner_response": "string",
  "room_vibe": {
    "analysis": "string",
    "energy": "string",
    "engagement_level": "string"
  },
  "current_phase": "integer (1 or 2)",
  "timestamp": "ISO 8601 datetime",
  "coach_feedback": "string | null"
}
```

---

## Example Workflows

### Complete Session Workflow

```bash
# Step 1: Start session
SESSION_RESPONSE=$(curl -s -X POST https://YOUR-SERVICE-URL.run.app/api/v1/session/start \
  -H "Content-Type: application/json" \
  -H "X-Goog-Authenticated-User-Id: user123" \
  -H "X-Goog-Authenticated-User-Email: user@example.com" \
  -d '{"location": "Mars Research Station"}')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Session created: $SESSION_ID"

# Step 2: Execute turns 1-15
for i in {1..15}; do
  echo "Executing turn $i..."

  TURN_RESPONSE=$(curl -s -X POST \
    https://YOUR-SERVICE-URL.run.app/api/v1/session/$SESSION_ID/turn \
    -H "Content-Type: application/json" \
    -H "X-Goog-Authenticated-User-Id: user123" \
    -H "X-Goog-Authenticated-User-Email: user@example.com" \
    -d "{
      \"user_input\": \"This is my improvisation for turn $i\",
      \"turn_number\": $i
    }")

  PARTNER_RESPONSE=$(echo $TURN_RESPONSE | jq -r '.partner_response')
  echo "Partner: $PARTNER_RESPONSE"

  # Check for coach feedback at turn 15
  if [ $i -eq 15 ]; then
    COACH_FEEDBACK=$(echo $TURN_RESPONSE | jq -r '.coach_feedback')
    echo "Coach: $COACH_FEEDBACK"
  fi

  sleep 1
done

# Step 3: Close session
curl -X POST https://YOUR-SERVICE-URL.run.app/api/v1/session/$SESSION_ID/close \
  -H "X-Goog-Authenticated-User-Id: user123" \
  -H "X-Goog-Authenticated-User-Email: user@example.com"

echo "Session completed!"
```

### Check Rate Limits

```bash
curl https://YOUR-SERVICE-URL.run.app/api/v1/user/limits \
  -H "X-Goog-Authenticated-User-Id: user123" \
  -H "X-Goog-Authenticated-User-Email: user@example.com" \
  | jq '.'
```

### Retrieve Session Info

```bash
curl https://YOUR-SERVICE-URL.run.app/api/v1/session/sess_a1b2c3d4e5f6g7h8 \
  -H "X-Goog-Authenticated-User-Id: user123" \
  -H "X-Goog-Authenticated-User-Email: user@example.com" \
  | jq '.'
```

---

## Testing

### Smoke Tests

Run the automated smoke test suite:

```bash
python scripts/smoke_test.py --url https://YOUR-SERVICE-URL.run.app
```

### Manual Testing

Use tools like Postman, Insomnia, or curl to manually test endpoints.

**Postman Collection**: Available at `docs/postman_collection.json` (if created)

### Integration Tests

Integration tests require real infrastructure:

```bash
pytest tests/integration/ --run-integration
```

---

## Additional Notes

### Session Lifecycle

1. **initialized**: Session created, no turns executed
2. **active**: At least one turn executed
3. **closed**: Manually closed by user
4. **timeout**: Expired after 60 minutes of inactivity

### Security Features

- **Content Filtering**: Offensive content is blocked (HTTP 400)
- **PII Detection**: Personal information is redacted from logs
- **Prompt Injection Protection**: Injection attempts are blocked (HTTP 422)
- **Rate Limiting**: Prevents abuse via daily and concurrent limits
- **Access Control**: Only allowed users can access the API

### Performance

- **Turn Execution**: Typically 5-8 seconds (ADK agent execution)
- **Timeout**: 30 seconds per turn
- **Session Timeout**: 60 minutes of inactivity
- **Request Timeout**: 300 seconds maximum

### Best Practices

1. **Handle Errors Gracefully**: Always check HTTP status codes
2. **Respect Rate Limits**: Check `/user/limits` before creating sessions
3. **Sequential Turns**: Always send turns in sequence (1, 2, 3...)
4. **Close Sessions**: Call `/close` when done to free concurrent slots
5. **Timeout Handling**: Be prepared for 504 timeouts on slow ADK execution

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-24
**Contact**: See DEPLOYMENT_RUNBOOK.md for support contacts
