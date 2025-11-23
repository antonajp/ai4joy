# Improv Olympics - ADK Application

AI-powered social gym backend application with OAuth authentication, rate limiting, and multi-agent orchestration.

## Architecture Overview

This application implements the foundational infrastructure for Improv Olympics:

### Core Components

1. **IAP Authentication Middleware** (`middleware/iap_auth.py`)
   - Extracts and validates IAP headers: `X-Goog-Authenticated-User-Email`, `X-Goog-Authenticated-User-ID`
   - Associates all sessions with authenticated users
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

4. **ADK Agent Skeleton** (`services/adk_agent.py`)
   - VertexAI Gemini integration (Flash and Pro models)
   - Workload Identity authentication (no API keys)
   - Async execution with retry logic
   - Chat session management

## Application Structure

```
app/
├── main.py                      # FastAPI application entry point
├── config.py                    # Configuration management
├── middleware/
│   └── iap_auth.py             # IAP header extraction
├── models/
│   └── session.py              # Data models (Session, Turn, etc.)
├── routers/
│   ├── health.py               # Health check endpoints
│   ├── sessions.py             # Session management API
│   └── agent.py                # ADK agent test endpoints
├── services/
│   ├── rate_limiter.py         # Per-user rate limiting
│   ├── session_manager.py      # Session persistence
│   └── adk_agent.py            # ADK agent integration
└── utils/
    └── logger.py               # Structured logging
```

## API Endpoints

### Health Checks (No Auth Required)

- `GET /health` - Basic health check (200 OK)
- `GET /ready` - Readiness check with dependency validation

### Session Management (IAP Auth Required)

- `POST /api/v1/session/start` - Create new session (rate limited)
- `GET /api/v1/session/{session_id}` - Get session info
- `POST /api/v1/session/{session_id}/close` - Close session
- `GET /api/v1/user/limits` - Get current rate limit status

### Agent Testing (IAP Auth Required)

- `GET /api/v1/agent/test` - Test VertexAI connectivity
- `GET /api/v1/agent/info` - Get agent configuration
- `POST /api/v1/agent/generate` - Test generation endpoint

## Environment Variables

```bash
# GCP Configuration
GCP_PROJECT_ID=improvOlympics
GCP_LOCATION=us-central1

# Firestore
FIRESTORE_DATABASE=(default)

# Rate Limits
RATE_LIMIT_DAILY_SESSIONS=10
RATE_LIMIT_CONCURRENT_SESSIONS=3

# Logging
LOG_LEVEL=INFO
```

## Local Development Setup

### Prerequisites

- Python 3.11+
- GCP project with APIs enabled:
  - Firestore API
  - VertexAI API
  - IAP API
- Service account with permissions:
  - `roles/datastore.user` (Firestore)
  - `roles/aiplatform.user` (VertexAI)

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
export GCP_PROJECT_ID="improvOlympics"
export GCP_LOCATION="us-central1"
export LOG_LEVEL="DEBUG"

# Run application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Testing Locally (Without IAP)

Since IAP headers are only present in production, you can test locally by:

1. **Option A**: Mock IAP headers in requests

```bash
curl -H "X-Goog-Authenticated-User-Email: accounts.google.com:test@example.com" \
     -H "X-Goog-Authenticated-User-ID: accounts.google.com:123456789" \
     http://localhost:8080/api/v1/user/limits
```

2. **Option B**: Temporarily disable IAP middleware

Comment out the middleware in `main.py`:
```python
# app.add_middleware(IAPAuthMiddleware)
```

### Testing Health Checks

```bash
# Health check (no auth)
curl http://localhost:8080/health

# Readiness check (no auth)
curl http://localhost:8080/ready

# Expected response:
# {"status":"healthy","timestamp":"2025-11-23T20:00:00Z","service":"Improv Olympics"}
```

### Testing Session Creation

```bash
# Create session (with mock IAP headers)
curl -X POST http://localhost:8080/api/v1/session/start \
  -H "Content-Type: application/json" \
  -H "X-Goog-Authenticated-User-Email: accounts.google.com:test@example.com" \
  -H "X-Goog-Authenticated-User-ID: accounts.google.com:123456789" \
  -d '{"location": "Mars Colony", "user_name": "Test User"}'

# Expected response:
# {
#   "session_id": "sess_abc123...",
#   "status": "initialized",
#   "location": "Mars Colony",
#   "created_at": "2025-11-23T20:00:00Z",
#   "expires_at": "2025-11-23T21:00:00Z",
#   "turn_count": 0
# }
```

### Testing Rate Limits

```bash
# Check current limits
curl http://localhost:8080/api/v1/user/limits \
  -H "X-Goog-Authenticated-User-Email: accounts.google.com:test@example.com" \
  -H "X-Goog-Authenticated-User-ID: accounts.google.com:123456789"

# Create 11 sessions to trigger daily limit
for i in {1..11}; do
  curl -X POST http://localhost:8080/api/v1/session/start \
    -H "Content-Type: application/json" \
    -H "X-Goog-Authenticated-User-Email: accounts.google.com:test@example.com" \
    -H "X-Goog-Authenticated-User-ID: accounts.google.com:123456789" \
    -d "{\"location\": \"Test Location $i\"}"
done

# 11th request should return:
# {
#   "detail": "Rate limit exceeded: Daily limit (10 sessions). Resets at 2025-11-24T00:00:00Z"
# }
```

### Testing Gemini Integration

```bash
# Test VertexAI connectivity
curl http://localhost:8080/api/v1/agent/test \
  -H "X-Goog-Authenticated-User-Email: accounts.google.com:test@example.com" \
  -H "X-Goog-Authenticated-User-ID: accounts.google.com:123456789"

# Test generation
curl -X POST "http://localhost:8080/api/v1/agent/generate?prompt=Hello%20World" \
  -H "X-Goog-Authenticated-User-Email: accounts.google.com:test@example.com" \
  -H "X-Goog-Authenticated-User-ID: accounts.google.com:123456789"
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
  -e GCP_PROJECT_ID="improvOlympics" \
  -e GCP_LOCATION="us-central1" \
  -e LOG_LEVEL="INFO" \
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
  "user_id": "1234567890",
  "user_email": "user@example.com",
  "user_name": "Test User",
  "location": "Mars Colony",
  "status": "active",
  "created_at": "2025-11-23T15:00:00Z",
  "updated_at": "2025-11-23T15:30:00Z",
  "expires_at": "2025-11-23T16:00:00Z",
  "conversation_history": [],
  "metadata": {},
  "current_phase": "PHASE_1",
  "turn_count": 5
}
```

#### `user_limits`
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

### Required Indexes

No composite indexes required for MVP. Firestore will auto-create single-field indexes.

## Logging and Observability

### Structured Logging

All logs are JSON-formatted for Cloud Logging:

```json
{
  "severity": "INFO",
  "timestamp": "2025-11-23T20:00:00Z",
  "message": "Session created successfully",
  "session_id": "sess_abc123",
  "user_id": "1234567890",
  "user_email": "user@example.com"
}
```

### Key Log Events

- IAP header extraction
- Rate limit checks and violations
- Session creation/closure
- Agent initialization
- Model generation requests
- Errors and exceptions

### Debugging in Chrome Dev Console

Logs are compatible with Chrome DevTools console. Use Cloud Logging filters:

```
resource.type="cloud_run_revision"
resource.labels.service_name="improv-olympics-app"
severity>=WARNING
```

## Security Considerations

### IAP Headers

- **Never trust client-provided headers in production**
- IAP headers are injected by GCP infrastructure, not the client
- Validate headers are present before processing requests

### Rate Limiting

- Limits are enforced at application layer (defense in depth)
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

### Issue: "IAP headers missing"

**Cause**: Request not passing through IAP
**Solution**: Ensure load balancer has IAP enabled and user is authenticated

### Issue: "Rate limit exceeded"

**Cause**: User hit daily or concurrent session limit
**Solution**: Wait for reset (shown in error message) or increase limits

### Issue: "VertexAI initialization failed"

**Cause**: Missing service account permissions
**Solution**: Grant `roles/aiplatform.user` to Cloud Run service account

### Issue: "Firestore connection timeout"

**Cause**: Firestore API not enabled or network issue
**Solution**: Enable Firestore API, check VPC connector

## Next Steps

### Phase 2: Multi-Agent Orchestration

- Implement MC, TheRoom, DynamicScenePartner, and Coach agents
- Add LLM orchestrator pattern for agent routing
- Implement sequential and parallel workflows

### Phase 3: Custom Tools

- GameDatabase tool for improv games
- SentimentGauge for real-time engagement analysis
- DemographicGenerator for audience personas

### Phase 4: Performance Optimization

- Streaming responses for lower perceived latency
- Parallel agent execution where possible
- Context compaction for long sessions

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

**Application Version**: 1.0.0
**Last Updated**: 2025-11-23
**Maintained by**: ai4joy.org team
