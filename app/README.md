# Improv Olympics - Application Backend

AI-powered social gym backend with Google OAuth 2.0 authentication, rate limiting, and multi-agent orchestration.

## Architecture Overview

This FastAPI application provides the backend infrastructure for Improv Olympics:

### Core Components

1. **OAuth 2.0 Authentication** (`middleware/oauth_auth.py`)
   - Application-level Google Sign-In using secure session cookies
   - Email whitelist access control via `ALLOWED_USERS` environment variable
   - Session management with httponly, secure cookies (XSS/CSRF protection)
   - Bypasses authentication for health check endpoints

2. **Rate Limiting Service** (`services/rate_limiter.py`)
   - **Daily Limit**: 10 sessions per user per day (resets at midnight UTC)
   - **Concurrent Limit**: 3 active sessions per user at any time
   - Firestore-backed persistence with transactional updates
   - Returns 429 error when limits exceeded

3. **Session Management** (`services/session_manager.py`)
   - Firestore persistence with user_id association
   - Automatic session expiration (60 minutes default)
   - Conversation history tracking
   - Phase transition management

4. **ADK Multi-Agent System** (`agents/`)
   - Stage Manager (Orchestrator with 4 sub-agents)
   - MC Agent (Game introduction and context)
   - Partner Agent (Phase-aware improv scene partner)
   - Room Agent (Audience simulation)
   - Coach Agent (Improv expert with knowledge base tools)
   - ADK-first architecture using DatabaseSessionService and InMemoryRunner

## Application Structure

```
app/
├── main.py                      # FastAPI application entry point
├── config.py                    # Configuration management
├── middleware/
│   ├── oauth_auth.py           # OAuth session middleware
│   └── performance.py          # Performance tracking middleware
├── models/
│   └── session.py              # Data models (Session, Turn, etc.)
├── routers/
│   ├── auth.py                 # OAuth endpoints (/auth/login, /callback, /logout)
│   ├── health.py               # Health check endpoints
│   ├── sessions.py             # Session management API
│   ├── user.py                 # User profile endpoints
│   ├── static.py               # Static file serving
│   ├── audio_poc.py            # Audio PoC endpoints
│   └── audio.py                # Production audio endpoints
├── agents/
│   ├── stage_manager.py        # Orchestrator agent
│   ├── mc_agent.py             # MC agent
│   ├── partner_agent.py        # Phase-aware scene partner
│   ├── room_agent.py           # Audience simulation
│   └── coach_agent.py          # Improv expert coach
├── services/
│   ├── rate_limiter.py         # Per-user rate limiting
│   ├── session_manager.py      # Session persistence
│   ├── adk_session_service.py  # ADK DatabaseSessionService integration
│   ├── adk_memory_service.py   # ADK MemoryService for RAG
│   └── turn_orchestrator.py    # Turn execution with ADK Runner
└── utils/
    └── logger.py               # Structured logging
```

## API Endpoints

### Health Checks (No Auth Required)

- `GET /health` - Basic health check (200 OK)
- `GET /ready` - Readiness check with dependency validation

### Authentication (OAuth 2.0)

- `GET /auth/login` - Initiate OAuth login flow
- `GET /auth/callback` - OAuth callback endpoint
- `GET /auth/logout` - Clear session and logout
- `GET /auth/user` - Get current authenticated user info
- `GET /auth/ws-token` - Get WebSocket authentication token

### User Profile (OAuth Required)

- `GET /api/v1/user/me` - Get current user profile

### Session Management (OAuth Required)

- `GET /api/v1/games` - List available improv games
- `POST /api/v1/session/start` - Create new session (rate limited)
- `GET /api/v1/session/{session_id}` - Get session info
- `POST /api/v1/session/{session_id}/welcome` - Execute MC welcome phase
- `POST /api/v1/session/{session_id}/turn` - Execute a turn in the scene
- `POST /api/v1/session/{session_id}/close` - Close session
- `GET /api/v1/user/limits` - Get current rate limit status

### Static Files

- `GET /` - Serve index.html
- `GET /static/{file_path}` - Serve static assets

## Environment Variables

```bash
# GCP Configuration
GCP_PROJECT_ID=coherent-answer-479115-e1
GCP_LOCATION=us-central1

# Firestore
FIRESTORE_DATABASE=(default)

# OAuth Configuration (from Secret Manager)
OAUTH_CLIENT_ID=<from-secret-manager>
OAUTH_CLIENT_SECRET=<from-secret-manager>
SESSION_SECRET_KEY=<from-secret-manager>

# Access Control
ALLOWED_USERS=user1@example.com,user2@example.com

# Rate Limits
RATE_LIMIT_DAILY_SESSIONS=10
RATE_LIMIT_CONCURRENT_SESSIONS=3

# Logging
LOG_LEVEL=INFO

# Observability
OTEL_ENABLED=true
```

## Local Development Setup

### Prerequisites

- Python 3.11+
- GCP project with APIs enabled:
  - Firestore API
  - VertexAI API
- Service account with permissions:
  - `roles/datastore.user` (Firestore)
  - `roles/aiplatform.user` (VertexAI)
- OAuth 2.0 credentials configured (see [OAUTH_GUIDE.md](../docs/OAUTH_GUIDE.md))

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set GCP credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Set environment variables
export GCP_PROJECT_ID="coherent-answer-479115-e1"
export GCP_LOCATION="us-central1"
export LOG_LEVEL="DEBUG"
export ALLOWED_USERS="test@example.com"

# Run application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Testing Locally (Without OAuth)

For local development, you can temporarily disable OAuth middleware:

**Option A**: Comment out OAuth middleware in `main.py`:
```python
# app.add_middleware(OAuthSessionMiddleware)
```

**Option B**: Use the test user bypass in development mode (if implemented)

### Testing Health Checks

```bash
# Health check (no auth)
curl http://localhost:8080/health

# Readiness check (no auth)
curl http://localhost:8080/ready

# Expected response:
# {"status":"healthy","timestamp":"2025-11-30T20:00:00Z"}
```

### Testing OAuth Flow

```bash
# 1. Visit login endpoint in browser
open http://localhost:8080/auth/login

# 2. Authenticate with Google (must use email in ALLOWED_USERS)

# 3. After callback, you'll have a session cookie

# 4. Test authenticated endpoint
curl http://localhost:8080/auth/user

# Expected response:
# {"email":"test@example.com","user_id":"...","name":"..."}
```

### Testing Session Creation

```bash
# Create session (requires authenticated session cookie)
# Get session cookie from browser DevTools after OAuth login

curl -X POST http://localhost:8080/api/v1/session/start \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your-session-cookie>" \
  -d '{"location": "Mars Colony"}'

# Expected response:
# {
#   "session_id": "sess_abc123...",
#   "status": "initialized",
#   "location": "Mars Colony",
#   "created_at": "2025-11-30T20:00:00Z",
#   "expires_at": "2025-11-30T21:00:00Z",
#   "turn_count": 0
# }
```

### Testing Rate Limits

```bash
# Check current limits
curl http://localhost:8080/api/v1/user/limits \
  -H "Cookie: session=<your-session-cookie>"

# Create 11 sessions to trigger daily limit
for i in {1..11}; do
  curl -X POST http://localhost:8080/api/v1/session/start \
    -H "Content-Type: application/json" \
    -H "Cookie: session=<your-session-cookie>" \
    -d "{\"location\": \"Test Location $i\"}"
done

# 11th request should return:
# {
#   "detail": "Rate limit exceeded: Daily limit (10 sessions). Resets at 2025-12-01T00:00:00Z"
# }
```

### Testing Turn Execution

```bash
# Execute a turn (requires active session)
curl -X POST "http://localhost:8080/api/v1/session/{session_id}/turn" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your-session-cookie>" \
  -d '{"user_input": "Yes and... I love this spaceship!", "turn_number": 1}'

# Expected response:
# {
#   "turn_number": 1,
#   "partner_response": "...",
#   "room_vibe": {...},
#   "current_phase": 1,
#   "timestamp": "..."
# }
```

## Docker Build and Test

### Build Container

```bash
# Build with build args
docker build \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg GIT_COMMIT=$(git rev-parse HEAD) \
  -t improv-olympics:latest .

# Verify build
docker images | grep improv-olympics
```

### Run Container Locally

```bash
# Run with environment variables
docker run -p 8080:8080 \
  -e GCP_PROJECT_ID="coherent-answer-479115-e1" \
  -e GCP_LOCATION="us-central1" \
  -e LOG_LEVEL="INFO" \
  -e ALLOWED_USERS="test@example.com" \
  -v /path/to/service-account-key.json:/app/gcp-key.json \
  -e GOOGLE_APPLICATION_CREDENTIALS="/app/gcp-key.json" \
  improv-olympics:latest

# Test health check
curl http://localhost:8080/health
```

## Firestore Schema

### Collections

#### `sessions`
```json
{
  "session_id": "sess_abc123",
  "user_id": "google-oauth2|1234567890",
  "user_email": "user@example.com",
  "location": "Mars Colony",
  "status": "active",
  "created_at": "2025-11-30T15:00:00Z",
  "updated_at": "2025-11-30T15:30:00Z",
  "expires_at": "2025-11-30T16:00:00Z",
  "conversation_history": [],
  "metadata": {},
  "current_phase": 1,
  "turn_count": 5
}
```

#### `user_limits`
```json
{
  "user_id": "google-oauth2|1234567890",
  "email": "user@example.com",
  "sessions_today": 5,
  "last_reset": "2025-11-30T00:00:00Z",
  "active_sessions": 2,
  "active_session_ids": ["sess_1", "sess_2"]
}
```

### Required Indexes

No composite indexes required for MVP. Firestore will auto-create single-field indexes.

## Logging and Observability

### Structured Logging

All logs are JSON-formatted for Cloud Logging:

```json
{
  "severity": "INFO",
  "timestamp": "2025-11-30T20:00:00Z",
  "message": "Session created successfully",
  "session_id": "sess_abc123",
  "user_id": "google-oauth2|123",
  "user_email": "user@example.com"
}
```

### Key Log Events

- OAuth authentication flow
- Rate limit checks and violations
- Session creation/closure
- Agent initialization
- Model generation requests
- Errors and exceptions

### Cloud Trace Integration

The application uses OpenTelemetry with Cloud Trace exporter:

```
resource.type="cloud_run_revision"
resource.labels.service_name="improv-olympics-app"
severity>=WARNING
```

## Security Considerations

### OAuth Session Cookies

- **httponly**: Prevents XSS attacks
- **secure**: HTTPS-only transmission
- **samesite=lax**: CSRF protection
- **signed**: Uses SESSION_SECRET_KEY from Secret Manager
- **24-hour expiration**: Automatic timeout

### Access Control

- Email whitelist via `ALLOWED_USERS` environment variable
- Checked after successful Google OAuth
- Unauthorized users get "Access denied" message

### Rate Limiting

- Limits enforced at application layer (defense in depth)
- Cloud Armor provides additional network-level rate limiting
- Per-user limits prevent cost abuse

### Workload Identity

- No API keys stored in code or environment variables
- Service account permissions granted via IAM
- Credentials automatically refreshed by GCP

## Performance Optimization

### Cold Start Mitigation

- Multi-stage Docker build reduces image size
- Health checks prevent premature instance shutdown
- Set `min_instances=1` in production for instant response

### Async Execution

- All agent calls use async patterns
- Retry logic with exponential backoff
- Concurrent operations where possible

### Firestore Optimization

- Transactional updates for rate limiting
- Document-based queries (no table scans)
- Batch operations for efficiency

## Troubleshooting

### Issue: "Unauthorized" or no session cookie

**Cause**: User not authenticated via OAuth
**Solution**: Visit `/auth/login` to authenticate with Google

### Issue: "Access denied" after OAuth login

**Cause**: User email not in `ALLOWED_USERS` list
**Solution**: Add user's email to `ALLOWED_USERS` environment variable

### Issue: "Rate limit exceeded"

**Cause**: User hit daily or concurrent session limit
**Solution**: Wait for reset (shown in error message) or increase limits

### Issue: "VertexAI initialization failed"

**Cause**: Missing service account permissions
**Solution**: Grant `roles/aiplatform.user` to Cloud Run service account

### Issue: "Firestore connection timeout"

**Cause**: Firestore API not enabled or network issue
**Solution**: Enable Firestore API, check VPC connector

## ADK-First Architecture (Complete)

The application uses Google's Agent Development Kit (ADK) for all agent functionality:

- **DatabaseSessionService**: Persistent sessions via SQLite backend
- **MemoryService**: RAG-based cross-session learning via VertexAI
- **CloudTraceCallback**: Native observability integration
- **InMemoryRunner**: Singleton pattern for efficient agent execution
- **Evaluation Framework**: Agent quality testing with ADK evaluators

## Multi-Agent Orchestration (Complete)

- **Stage Manager**: Orchestrator routing to specialized sub-agents
- **MC Agent**: Game introduction and context setting
- **Partner Agent**: Phase-aware improv scene partner (supportive→fallible)
- **Room Agent**: Audience simulation with reactions
- **Coach Agent**: Improv expert with knowledge base tools

## Future Enhancements

- Streaming responses for lower perceived latency
- Enhanced memory retrieval patterns
- Additional game types and scenarios
- WebSocket support for real-time audio

## Contributing

When adding new features:

1. Follow existing code structure and naming conventions
2. Add comprehensive logging for observability
3. Include error handling with retries
4. Update this README with new endpoints/features
5. Test locally before container build

## License

See LICENSE file for details.

---

**Application Version**: 2.0.0 (ADK-First + OAuth 2.0)
**Last Updated**: 2025-11-30
**Maintained by**: ai4joy.org team
