# Improv Olympics (ai4joy)

**An AI-Powered Social Gym for Improvisational Comedy Practice**

Improv Olympics is a multi-agent AI application that enables users to practice improvisational comedy skills through interactive text-based sessions with specialized AI agents. Built on Google Cloud Platform with OAuth authentication and per-user rate limiting to support a pilot launch for 10-50 early adopters.

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

Improv Olympics provides an interactive learning environment where users practice improvisational comedy through AI-powered sessions. Four specialized agents orchestrate the experience:

- **MC Agent** - Introduces games, provides context, and guides the session flow
- **The Room Agent** - Simulates audience reactions and feedback
- **Dynamic Scene Partner Agent** - Responds contextually as a scene partner
- **Coach Agent** - Delivers actionable feedback and coaching insights

### Technology Stack

- **Backend**: FastAPI (Python)
- **AI Models**: Google Gemini 1.5 Pro/Flash via VertexAI
- **Agent Framework**: Google Agent Developer Toolkit (ADK)
- **Database**: Google Cloud Firestore
- **Hosting**: Google Cloud Run (serverless containers)
- **Authentication**: Identity-Aware Proxy (IAP) with OAuth 2.0
- **Infrastructure**: Terraform
- **CI/CD**: Cloud Build
- **Monitoring**: Cloud Logging, Cloud Monitoring

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
│  + IAP (OAuth)   │◄─── OAuth consent screen
└────────┬─────────┘
         │
         ▼
┌─────────────────────┐
│   Cloud Run         │
│   (FastAPI App)     │
│   ┌───────────────┐ │
│   │ IAP Header    │ │
│   │ Validation    │ │
│   ├───────────────┤ │
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

### Multi-Agent Orchestration

```
User Input
    │
    ▼
┌─────────────┐
│ MC Agent    │ (Gemini 1.5 Flash)
│ Orchestrator│
└──────┬──────┘
       │
       ├────► The Room (audience feedback)
       │
       ├────► Dynamic Scene Partner (scene interaction)
       │
       └────► Coach (feedback & analysis)
```

## Key Features

### Production-Ready Infrastructure

- **OAuth Authentication**: Google Sign-In via Identity-Aware Proxy
- **Per-User Rate Limiting**: 10 sessions/day, 3 concurrent sessions
- **Session Persistence**: Firestore-backed session management
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

- **JWT Validation**: Defense-in-depth IAP header verification
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

# 4. Create OAuth consent screen (manual step)
# Follow instructions output by setup.sh
# Visit: https://console.cloud.google.com/apis/credentials/consent

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

# 6. Test with mock IAP headers
curl http://localhost:8080/health
```

## Project Structure

```
ai4joy/
├── app/                        # FastAPI application
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration management
│   ├── middleware/             # IAP authentication middleware
│   ├── models/                 # Pydantic data models
│   ├── routers/                # API endpoints
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
│   ├── test_oauth.py           # OAuth integration tests
│   ├── test_rate_limiting.py   # Rate limit tests
│   └── test_infrastructure.py  # Infrastructure validation
│
├── scripts/                    # Deployment scripts
│   ├── setup.sh                # Initial GCP setup
│   ├── deploy.sh               # Application deployment
│   └── rollback.sh             # Rollback script
│
├── docs/                       # Documentation
│   ├── gcp-deployment-architecture.md
│   ├── deployment-runbook.md
│   ├── FIRESTORE_SCHEMA.md
│   └── IAP_OAUTH_GUIDE.md
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

- **[Application README](app/README.md)** - Detailed API documentation, local development setup
- **[GCP Deployment Architecture](docs/gcp-deployment-architecture.md)** - Infrastructure design and rationale
- **[Deployment Runbook](docs/deployment-runbook.md)** - Step-by-step deployment procedures
- **[IAP OAuth Guide](docs/IAP_OAUTH_GUIDE.md)** - OAuth setup and user management
- **[Firestore Schema](docs/FIRESTORE_SCHEMA.md)** - Database schema documentation
- **[Terraform README](infrastructure/terraform/README.md)** - Infrastructure configuration

### Implementation Documentation

- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Complete implementation details for IQS-45
- **[Application README](APPLICATION_README.md)** - Application-specific implementation notes
- **[Deployment Summary](docs/DEPLOYMENT_SUMMARY_IQS45.md)** - Deployment details for IQS-45

### Testing Documentation

- **[Testing Summary](tests/TESTING_SUMMARY.md)** - Test strategy and results
- **[OAuth Test Report](tests/IQS45_OAUTH_TEST_REPORT.md)** - OAuth integration test results
- **[Manual Test Procedures](tests/OAUTH_MANUAL_TEST_PROCEDURES.md)** - Manual testing steps

## Deployment

### Production Deployment

The application is deployed to Google Cloud Run with the following components:

1. **Cloud Load Balancer** - HTTPS termination, IAP integration
2. **Cloud Run** - Serverless container hosting
3. **Cloud Firestore** - Session and rate limit storage
4. **VertexAI** - Gemini model access
5. **Cloud DNS** - Domain management
6. **Cloud Armor** - Security policies

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
  --allow-unauthenticated  # IAP handles auth at LB level
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

### API Endpoints

Key endpoints:

- `GET /health` - Health check (no auth required)
- `GET /ready` - Readiness check (validates dependencies)
- `POST /api/v1/session/start` - Create new session
- `POST /api/v1/session/{id}/message` - Send message to agent
- `GET /api/v1/session/{id}` - Retrieve session state
- `POST /api/v1/session/{id}/close` - Close session

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
# Mock IAP headers for local testing
curl http://localhost:8080/api/v1/session/start \
  -H "X-Goog-Authenticated-User-Email: accounts.google.com:test@example.com" \
  -H "X-Goog-Authenticated-User-ID: accounts.google.com:123456789" \
  -H "Content-Type: application/json" \
  -d '{"location": "Mars Colony"}'
```

## Current Status

### Completed Features (IQS-45)

- OAuth/IAP authentication at load balancer
- JWT signature validation in application
- Per-user rate limiting (10 sessions/day, 3 concurrent)
- Session management with Firestore persistence
- ADK agent skeleton with Gemini integration
- Health check endpoints
- Structured JSON logging
- Comprehensive documentation
- Automated testing suite
- Complete Terraform infrastructure

### Roadmap

**Phase 1: MVP Launch** (Completed)
- OAuth authentication and rate limiting
- Single-agent skeleton deployment
- Infrastructure automation

**Phase 2: Multi-Agent Implementation** (Planned)
- MC agent (session orchestrator)
- The Room agent (audience simulation)
- Dynamic Scene Partner agent
- Coach agent (feedback & analysis)
- LLM-based agent routing

**Phase 3: Production Optimization** (Future)
- Custom tools (GameDatabase, SentimentGauge)
- Streaming responses
- Context compaction for long sessions
- Performance optimization
- Advanced monitoring and alerting

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

**Project Status**: 🟢 Production Ready (MVP)
**Last Updated**: 2025-11-23
**Version**: 1.0.0
