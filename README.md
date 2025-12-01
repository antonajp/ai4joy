# Improv Olympics (ai4joy)

**An AI-Powered Social Gym for Improvisational Comedy Practice**

> **Note:** This project uses **Application-Level OAuth 2.0** for authentication with Google Sign-In and email whitelist access control.

Improv Olympics is a multi-agent AI application that enables users to practice improvisational comedy skills through interactive text-based sessions with specialized AI agents. Built on Google Cloud Platform with Application-Level OAuth 2.0 authentication and per-user rate limiting to support a pilot launch for 10-50 early adopters.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Deployment](#deployment)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Overview

### What is Improv Olympics?

Improv Olympics provides an interactive learning environment where users practice improvisational comedy through AI-powered sessions. Five specialized agents orchestrate the experience using Google's Agent Development Kit (ADK):

- **Stage Manager Agent** - Orchestrates the multi-agent experience across all sub-agents
- **Partner Agent** - Phase-aware scene partner that adapts behavior based on user skill level
- **Room Agent** - Simulates audience reactions and collective vibe using sentiment analysis
- **Coach Agent** - Delivers actionable feedback using improv principles database
- **MC Agent** - (Future) Introduces games and guides session flow

### Technology Stack

- **Backend**: FastAPI (Python)
- **AI Models**: Google Gemini 2.0 Flash Exp via VertexAI
- **Agent Framework**: Google Agent Developer Toolkit (ADK)
  - `DatabaseSessionService` for session persistence (SQLite)
  - `VertexAiRagMemoryService` for cross-session learning
  - `CloudTraceCallback` for native observability
  - `InMemoryRunner` singleton pattern for efficient execution
- **Database**: Google Cloud Firestore (rate limits), SQLite (ADK sessions)
- **Hosting**: Google Cloud Run (serverless containers)
- **Authentication**: Application-Level OAuth 2.0 with Google Sign-In (authlib, itsdangerous)
- **Infrastructure**: Terraform
- **CI/CD**: Cloud Build
- **Monitoring**: Cloud Logging, Cloud Monitoring, Cloud Trace

## Architecture

### High-Level Architecture

```
┌─────────────┐
│   User      │
│   Browser   │
└──────┬──────┘
       │ HTTPS
       ▼
┌──────────────────┐
│  Cloud Load      │
│  Balancer        │◄─── Google-managed SSL
└────────┬─────────┘
         │
         ▼
┌─────────────────────┐
│   Cloud Run         │
│   (FastAPI App)     │
│   ┌───────────────┐ │
│   │ OAuth Session │ │
│   │ Middleware    │ │◄─── Application-Level OAuth 2.0
│   ├───────────────┤ │     (session cookies)
│   │ Rate Limiter  │ │
│   ├───────────────┤ │
│   │ Session Mgr   │ │
│   ├───────────────┤ │
│   │ ADK Agents    │ │
│   └───────────────┘ │
└────────┬────────────┘
         │
         ├──────────► Firestore (sessions, rate limits)
         │
         └──────────► VertexAI (Gemini models)
```

### ADK-First Multi-Agent Orchestration

```
User Input
    │
    ▼
┌──────────────────┐
│ Stage Manager    │ (Gemini 2.0 Flash Exp)
│ (ADK LlmAgent)   │ [Orchestrates 3 sub-agents]
└────────┬─────────┘
         │
         ├────► Partner Agent (Phase-aware improv partner)
         │      - Phase 1: Supportive "Yes, and..."
         │      - Phase 2: Fallible, realistic friction
         │
         ├────► Room Agent (Audience sentiment & vibe)
         │      - Sentiment analysis tools
         │      - Demographic simulation
         │
         └────► Coach Agent (Expert feedback)
                - Improv principles database
                - Constructive coaching

All agents backed by:
- ADK DatabaseSessionService (session persistence)
- ADK MemoryService (cross-session learning)
- ADK CloudTraceCallback (observability)
- Singleton InMemoryRunner (efficient execution)
```

## Key Features

### Production-Ready Infrastructure

- **Application-Level OAuth 2.0**: Google Sign-In with secure httponly cookies (no IAP required)
- **Per-User Rate Limiting**: 10 sessions/day, 3 concurrent sessions
- **ADK Session Persistence**: `DatabaseSessionService` with SQLite backend
- **Cross-Session Memory**: `VertexAiRagMemoryService` for personalized learning
- **Native Observability**: ADK `CloudTraceCallback` auto-instrumentation
- **Efficient Agent Execution**: Singleton `InMemoryRunner` pattern
- **Health Checks**: Load balancer integration with readiness probes
- **Structured Logging**: Cloud Logging-compatible JSON logs
- **Auto-Scaling**: Serverless Cloud Run with automatic scaling
- **Security**: Workload Identity for service-to-service auth (no API keys)

### Cost Control

- **OAuth Gating**: Prevents anonymous abuse of LLM services
- **Rate Limiting**: Per-user session limits prevent runaway costs
- **Model Optimization**: Strategic use of Gemini Flash vs Pro
- **Budget Target**: <$200/month for pilot (10-50 users)

### Reliability Features

- **Secure Session Management**: Signed, httponly session cookies with 24-hour expiration
- **Transactional Updates**: Race-condition-safe Firestore operations
- **Retry Logic**: Exponential backoff for VertexAI calls
- **Graceful Degradation**: Clear error messages for quota/timeout issues

## Quick Start

### Prerequisites

- Google Cloud Platform account with billing enabled
- Domain name (e.g., ai4joy.org)
- gcloud CLI installed
- Terraform >= 1.5
- Python >= 3.11

### Deploy to GCP

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/ai4joy.git
cd ai4joy

# 2. Set environment variables
export PROJECT_ID="your-gcp-project-id"
export BILLING_ACCOUNT_ID="your-billing-account-id"

# 3. Run setup script
./scripts/setup.sh

# 4. Create OAuth 2.0 credentials and secrets (manual step)
# Visit: https://console.cloud.google.com/apis/credentials
# Create OAuth client ID, add credentials to Secret Manager
# See docs/OAUTH_GUIDE.md for detailed instructions

# 5. Configure Terraform variables
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings

# 6. Deploy infrastructure
terraform init
terraform apply

# 7. Configure DNS at your domain registrar
# Use nameservers from: terraform output dns_nameservers

# 8. Build and deploy application (after DNS propagates)
cd ../..
./scripts/deploy.sh
```

### Local Development

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
cp .env.example .env
# Edit .env with your local configuration

# 4. Run Firestore emulator (optional)
gcloud emulators firestore start

# 5. Run application
cd app
uvicorn main:app --reload --port 8080

# 6. Test authentication flow
# Visit http://localhost:8080/auth/login to test OAuth
curl http://localhost:8080/health  # No auth required for health
```

## Project Structure

```
ai4joy/
├── app/                        # FastAPI application
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration management
│   ├── middleware/             # OAuth session middleware
│   │   └── oauth_auth.py       # OAuthSessionMiddleware
│   ├── models/                 # Pydantic data models
│   ├── routers/                # API endpoints
│   │   ├── auth.py             # OAuth endpoints (/auth/login, /callback, /logout)
│   │   └── sessions.py         # Session management
│   ├── services/               # Business logic
│   │   ├── rate_limiter.py     # Per-user rate limiting
│   │   ├── session_manager.py  # Session persistence
│   │   └── adk_agent.py        # ADK agent integration
│   └── utils/                  # Utilities (logging, etc.)
│
├── infrastructure/
│   └── terraform/              # Terraform IaC
│       ├── main.tf             # Infrastructure definition
│       ├── variables.tf        # Input variables
│       └── outputs.tf          # Output values
│
├── tests/                      # Test suites
│   ├── test_oauth.py           # Application-level OAuth tests
│   ├── test_rate_limiting.py   # Rate limit tests
│   └── test_infrastructure.py  # Infrastructure validation
│
├── scripts/                    # Operational scripts
│   ├── setup.sh                # Initial GCP setup
│   ├── deploy.sh               # Application deployment
│   ├── rollback.sh             # Rollback to previous revision
│   ├── seed_firestore_tool_data.py  # Seed Firestore with tool data
│   ├── manage_users.py         # User tier management
│   ├── reset_limits.py         # Reset user rate limits
│   ├── logs.sh                 # View application logs
│   ├── smoke_test.py           # Post-deployment validation
│   ├── test_local_app.sh       # Local testing script
│   └── test_turn.py            # Turn execution testing
│
├── docs/                       # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── DEPLOYMENT.md
│   ├── design_overview.md
│   ├── FIRESTORE_SCHEMA.md
│   └── OAUTH_GUIDE.md
│
├── .claude/                    # Claude Code configuration
│   ├── agents/                 # Specialized agents
│   └── commands/               # Custom slash commands
│
├── Dockerfile                  # Container definition
├── cloudbuild.yaml             # CI/CD pipeline
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Documentation

### Core Documentation

- **[Application README](app/README.md)** - Backend application, API endpoints, local development setup
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete deployment procedures and infrastructure setup
- **[OAuth Guide](docs/OAUTH_GUIDE.md)** - OAuth 2.0 setup and user access management
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference
- **[Firestore Schema](docs/FIRESTORE_SCHEMA.md)** - Database schema documentation
- **[Design Overview](docs/design_overview.md)** - Original vision and design philosophy
- **[Terraform README](infrastructure/terraform/README.md)** - Infrastructure as code configuration

### Testing Documentation

- **[Testing Summary](tests/TESTING_SUMMARY.md)** - Test strategy and results
- **[Manual Test Procedures](tests/OAUTH_MANUAL_TEST_PROCEDURES.md)** - Manual testing steps
- **[Tests README](tests/README.md)** - Testing guide and execution

## Deployment

### Production Deployment

The application is deployed to Google Cloud Run with the following components:

1. **Cloud Load Balancer** - HTTPS termination and routing
2. **Cloud Run** - Serverless container hosting with OAuth middleware
3. **Cloud Firestore** - Session and rate limit storage
4. **VertexAI** - Gemini model access
5. **Cloud DNS** - Domain management
6. **Cloud Armor** - Security policies
7. **Secret Manager** - OAuth credentials and session secrets

### CI/CD Pipeline

The `cloudbuild.yaml` defines a fully automated pipeline:

1. Run automated tests
2. Build Docker container
3. Scan for vulnerabilities
4. Deploy to Cloud Run
5. Run smoke tests
6. Gradual rollout (25% → 50% → 100%)
7. Automatic rollback on failure

### Manual Deployment

```bash
# Build container
docker build -t gcr.io/${PROJECT_ID}/improv-olympics:latest .

# Push to Container Registry
docker push gcr.io/${PROJECT_ID}/improv-olympics:latest

# Deploy to Cloud Run
gcloud run deploy improv-olympics \
  --image gcr.io/${PROJECT_ID}/improv-olympics:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \  # OAuth handled by application middleware
  --set-secrets OAUTH_CLIENT_ID=oauth-client-id:latest,OAUTH_CLIENT_SECRET=oauth-client-secret:latest
```

## Development

### Setting Up Development Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install pytest pytest-asyncio black flake8 mypy

# Format code
black app/

# Lint code
flake8 app/

# Type check
mypy app/
```

### Environment Variables

Required environment variables (see `.env.example`):

- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_REGION` - Deployment region (default: us-central1)
- `FIRESTORE_DATABASE` - Firestore database name
- `MODEL_NAME` - Default Gemini model (gemini-1.5-flash)
- `RATE_LIMIT_DAILY` - Daily session limit per user (default: 10)
- `RATE_LIMIT_CONCURRENT` - Concurrent session limit (default: 3)
- `OAUTH_CLIENT_ID` - Google OAuth 2.0 client ID (from Secret Manager)
- `OAUTH_CLIENT_SECRET` - Google OAuth 2.0 client secret (from Secret Manager)
- `SESSION_SECRET_KEY` - Secret key for signing session cookies (from Secret Manager)
- `ALLOWED_USERS` - Comma-separated list of allowed user emails

### API Endpoints

Key endpoints:

- `GET /health` - Health check (no auth required)
- `GET /ready` - Readiness check (validates dependencies)
- `GET /auth/login` - Initiate OAuth login flow
- `GET /auth/callback` - OAuth callback endpoint
- `GET /auth/logout` - Clear session and logout
- `GET /auth/user` - Get current user info (protected)
- `POST /api/v1/session/start` - Create new session (protected)
- `POST /api/v1/session/{id}/message` - Send message to agent (protected)
- `GET /api/v1/session/{id}` - Retrieve session state (protected)
- `POST /api/v1/session/{id}/close` - Close session (protected)

See [app/README.md](app/README.md) for complete API documentation.

## Testing

### Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/test_oauth.py

# Run with coverage
pytest --cov=app tests/
```

### Test Suites

- **Unit Tests** - Individual component testing
- **Integration Tests** - OAuth flow, rate limiting, Firestore
- **Infrastructure Tests** - Terraform validation, resource checks
- **Manual Tests** - End-to-end OAuth flow, production verification

### Testing OAuth Locally

```bash
# Test OAuth login flow
open http://localhost:8080/auth/login

# After authenticating, test protected endpoint with session cookie
curl http://localhost:8080/api/v1/session/start \
  -H "Cookie: session=<your-session-cookie>" \
  -H "Content-Type: application/json" \
  -d '{"location": "Mars Colony"}'

# Get current user info
curl http://localhost:8080/auth/user \
  -H "Cookie: session=<your-session-cookie>"
```

## Operational Scripts

The `scripts/` directory contains operational utilities for deployment and maintenance. See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete documentation.

### Quick Reference

```bash
# Setup & Initialization
./scripts/setup.sh                                    # One-time GCP setup
python scripts/seed_firestore_tool_data.py            # Seed Firestore with tool data

# Deployment
./scripts/deploy.sh                                   # Deploy application
./scripts/rollback.sh                                 # Rollback deployment

# User Management
python scripts/manage_users.py add user@example.com premium
python scripts/manage_users.py list
python scripts/manage_users.py remove user@example.com

# Operations
python scripts/reset_limits.py user_id                # Reset rate limits
./scripts/logs.sh tail                                # View logs
python scripts/smoke_test.py --url https://ai4joy.org # Post-deployment tests
```

See [Deployment Scripts Documentation](docs/DEPLOYMENT.md#deployment-scripts) for detailed usage.

## Current Status

### Completed Features

**Authentication & Infrastructure (IQS-45)**
- Application-Level OAuth 2.0 authentication with Google Sign-In
- Secure session management with httponly cookies and Secret Manager
- Per-user rate limiting (10 sessions/day, 3 concurrent)
- Health check endpoints
- Structured JSON logging
- Complete Terraform infrastructure
- Automated testing suite

**Multi-Agent System (IQS-46 to IQS-48)**
- 5 specialized ADK agents (Stage Manager, Partner, Room, Coach, MC)
- Phase-aware Partner Agent behavior
- Multi-agent orchestration via Stage Manager
- Sentiment analysis and audience simulation
- Improv coaching with principles database

**ADK-First Architecture (IQS-49 to IQS-54)**
- ADK `DatabaseSessionService` for session persistence
- ADK `VertexAiRagMemoryService` for cross-session learning
- ADK `CloudTraceCallback` native observability
- Singleton `InMemoryRunner` pattern for efficiency
- ADK evaluation framework for agent quality testing
- All agents using `google.adk.agents.Agent`
- Comprehensive documentation updates

### Roadmap

**Phase 1: MVP Launch** (Completed - IQS-45)
- OAuth authentication and rate limiting
- Infrastructure automation
- Single-agent skeleton deployment

**Phase 2: Multi-Agent Implementation** (Completed - IQS-46 to IQS-48)
- Stage Manager (multi-agent orchestrator)
- Partner Agent (phase-aware scene partner)
- Room Agent (audience simulation with sentiment tools)
- Coach Agent (feedback with improv principles)
- MC Agent (game introduction and context)

**Phase 3: ADK-First Architecture** (Completed - IQS-49 to IQS-54)
- ADK `DatabaseSessionService` for session persistence
- ADK `MemoryService` for cross-session learning
- ADK `CloudTraceCallback` for native observability
- Singleton `InMemoryRunner` pattern
- ADK evaluation framework for agent quality testing

**Phase 4: Production Optimization** (Future)
- Streaming responses for real-time feedback
- Context compaction for long sessions
- Performance optimization and caching
- Advanced coaching features
- Mid-scene coaching options

## Contributing

This is currently a private project for pilot testing. Contribution guidelines will be published when the project enters public beta.

## Support

For issues or questions:

- **Documentation**: See the [docs/](docs/) directory
- **Issues**: Create a GitHub issue (when repository is public)
- **Contact**: support@ai4joy.org

## License

Copyright 2025 JP Antona. All rights reserved.

---

**Project Status**: 🟢 Production Ready (ADK-First Architecture Complete)
**Last Updated**: 2025-11-25
**Version**: 2.0.0 (ADK-First)
