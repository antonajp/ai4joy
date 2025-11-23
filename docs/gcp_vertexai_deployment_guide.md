# Improv Olympics: GCP VertexAI Deployment Architecture Guide

## Executive Summary

This document provides comprehensive technical guidance for deploying the Improv Olympics multi-agent system to Google Cloud Platform (GCP) using VertexAI. The system is a production-grade agentic AI application built with Google Agent Development Kit (ADK), featuring a hub-and-spoke architecture with five specialized agents.

**Current State**: Design phase with ADK dependencies installed, no implementation code yet.

**Target State**: Production deployment on GCP ImprovOlympics project, hosted on ai4joy.org domain.

**Key Technologies**: ADK, Gemini 1.5 Pro/Flash, Cloud Run, Firestore, VertexAI, WebSockets (future).

---

## 1. ADK Containerization Strategy for VertexAI

### 1.1 Current ADK Installation Analysis

Your environment has Google ADK 1.19.0 installed with the full VertexAI stack:
- `google-adk==1.19.0`
- `google-cloud-aiplatform==1.128.0`
- Supporting GCP services (Secret Manager, Logging, Monitoring, BigQuery, Bigtable)

### 1.2 Containerization Approach

**Recommended Strategy: Cloud Run with ADK Custom Container**

ADK applications are best deployed as containerized services on Cloud Run because:
1. ADK agents are stateless HTTP services with variable traffic
2. Auto-scaling matches the unpredictable nature of user interactions
3. Pay-per-use pricing aligns with educational/training use cases
4. Native integration with VertexAI and GCP services
5. WebSocket support for future real-time voice features

### 1.3 Dockerfile Architecture

```dockerfile
# /Users/jpantona/Documents/code/ai4joy/Dockerfile

# Use official Python 3.13 slim image for minimal attack surface
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies for ADK and potential native extensions
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt .

# Install Python dependencies with layer caching
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port for Cloud Run (Cloud Run uses PORT env var)
ENV PORT=8080
EXPOSE 8080

# Health check endpoint for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run the ADK application
CMD ["python", "-m", "src.main"]
```

### 1.4 Requirements Configuration

```txt
# /Users/jpantona/Documents/code/ai4joy/requirements.txt

# Core ADK and VertexAI
google-adk==1.19.0
google-cloud-aiplatform==1.128.0

# GCP Service Integrations
google-cloud-logging==3.12.1
google-cloud-monitoring==2.28.0
google-cloud-secret-manager==2.25.0
google-cloud-firestore==2.20.0

# Web framework for ADK HTTP server
flask==3.1.0
gunicorn==23.0.0

# For future WebSocket support
flask-socketio==5.4.2
python-socketio==5.12.0

# Observability and reliability
opentelemetry-api==1.31.0
opentelemetry-sdk==1.31.0
opentelemetry-exporter-gcp-trace==1.8.0
tenacity==9.0.0  # For retry logic

# Testing and development
pytest==8.3.0
pytest-asyncio==0.24.0
```

### 1.5 Build and Push Strategy

```bash
# /Users/jpantona/Documents/code/ai4joy/scripts/build_and_push.sh

#!/bin/bash
set -e

PROJECT_ID="ImprovOlympics"
REGION="us-central1"
SERVICE_NAME="improv-olympics-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Authenticate with GCP
gcloud auth configure-docker

# Build the container with Cloud Build (recommended for GCP)
gcloud builds submit \
  --project=${PROJECT_ID} \
  --config=cloudbuild.yaml \
  --region=${REGION} \
  --substitutions=_IMAGE_NAME=${IMAGE_NAME}

echo "Build complete: ${IMAGE_NAME}:latest"
```

```yaml
# /Users/jpantona/Documents/code/ai4joy/cloudbuild.yaml

steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/improv-olympics-api:$COMMIT_SHA'
      - '-t'
      - 'gcr.io/$PROJECT_ID/improv-olympics-api:latest'
      - '.'
    timeout: 1200s

  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'gcr.io/$PROJECT_ID/improv-olympics-api:$COMMIT_SHA'

  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'gcr.io/$PROJECT_ID/improv-olympics-api:latest'

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'improv-olympics-api'
      - '--image=gcr.io/$PROJECT_ID/improv-olympics-api:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=2Gi'
      - '--cpu=2'
      - '--max-instances=100'
      - '--min-instances=1'
      - '--timeout=300s'
      - '--concurrency=80'
      - '--set-env-vars=PROJECT_ID=$PROJECT_ID,REGION=us-central1'

images:
  - 'gcr.io/$PROJECT_ID/improv-olympics-api:$COMMIT_SHA'
  - 'gcr.io/$PROJECT_ID/improv-olympics-api:latest'

timeout: 1800s
```

---

## 2. Agent Orchestration Deployment Architecture

### 2.1 Multi-Agent Pattern Analysis

Your design uses a **Hub-and-Spoke (Central Orchestrator)** pattern with a simplified execution loop. This is optimal for the following reasons:

**Strengths**:
- Centralized state management reduces synchronization complexity
- Predictable turn-based interaction (no chatroom chaos)
- Efficient API usage (3 agents per turn vs 7 in naive parallel)
- Clear phase transitions (Phase 1: Support → Phase 2: Fallibility)

**Deployment Implications**:
- Single Cloud Run service hosts all agents (monolithic)
- State managed in Firestore (session-based)
- No inter-service communication overhead
- Simplified observability and debugging

### 2.2 Agent Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloud Run Service                         │
│                 (improv-olympics-api)                        │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │        Stage Manager (Root Agent)                     │ │
│  │  - Session State Management                           │ │
│  │  - Phase Logic (PHASE_1_SUPPORT → PHASE_2_FALLIBLE)  │ │
│  │  - Turn Counter & Metrics                            │ │
│  │  - Agent Routing & Orchestration                     │ │
│  └───────────────┬───────────────────────────────────────┘ │
│                  │                                          │
│       ┌──────────┼──────────┬──────────┬──────────┐        │
│       ▼          ▼          ▼          ▼          ▼        │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │
│  │   MC   │ │  Room  │ │Partner │ │ Coach  │ │ Tools  │  │
│  │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │ │        │  │
│  │(Flash) │ │(Flash) │ │ (Pro)  │ │(Flash) │ │        │  │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘  │
│      │          │          │          │          │        │
└──────┼──────────┼──────────┼──────────┼──────────┼────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
  ┌────────────────────────────────────────────────────┐
  │            Gemini via VertexAI                      │
  │  - gemini-1.5-flash (MC, Room, Coach)              │
  │  - gemini-1.5-pro (Dynamic Scene Partner)          │
  └────────────────────────────────────────────────────┘
```

### 2.3 Proposed Project Structure

```
/Users/jpantona/Documents/code/ai4joy/
├── src/
│   ├── __init__.py
│   ├── main.py                          # Flask app entry point
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── stage_manager.py            # Root orchestrator
│   │   ├── mc_agent.py                 # MC (Flash)
│   │   ├── room_agent.py               # Audience aggregator (Flash)
│   │   ├── partner_agent.py            # Dynamic partner (Pro)
│   │   ├── coach_agent.py              # Post-game analysis (Flash)
│   │   └── base_agent.py               # Shared ADK agent interface
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── game_database.py            # Game rules retrieval
│   │   ├── demographic_generator.py     # Audience archetypes
│   │   ├── sentiment_gauge.py          # Conversation temperature
│   │   └── improv_expert_database.py   # Coaching knowledge base
│   ├── state/
│   │   ├── __init__.py
│   │   ├── session_manager.py          # Firestore session state
│   │   └── models.py                   # Pydantic models for state
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                   # HTTP endpoints
│   │   └── websocket_handler.py        # Future WebSocket support
│   └── utils/
│       ├── __init__.py
│       ├── observability.py            # Logging, tracing, metrics
│       ├── retry_logic.py              # Exponential backoff
│       └── config.py                   # Environment configuration
├── config/
│   ├── prompts/
│   │   ├── mc_system_prompt.txt
│   │   ├── room_system_prompt.txt
│   │   ├── partner_phase1_prompt.txt
│   │   ├── partner_phase2_prompt.txt
│   │   └── coach_system_prompt.txt
│   └── games/
│       └── games_database.json         # Short Form/Long Form games
├── tests/
│   ├── unit/
│   │   ├── test_agents.py
│   │   ├── test_tools.py
│   │   └── test_state_management.py
│   ├── integration/
│   │   ├── test_orchestration.py
│   │   └── test_api_endpoints.py
│   └── fixtures/
│       └── sample_sessions.json
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── modules/
│   │   │   ├── cloud_run/
│   │   │   ├── firestore/
│   │   │   ├── secrets/
│   │   │   └── monitoring/
│   └── scripts/
│       ├── deploy.sh
│       └── setup_gcp_project.sh
├── Dockerfile
├── requirements.txt
├── cloudbuild.yaml
├── .dockerignore
├── .gcloudignore
└── README.md
```

### 2.4 ADK Agent Implementation Pattern

```python
# /Users/jpantona/Documents/code/ai4joy/src/agents/base_agent.py

from google.genai import types
from google.adk.genai import Agent, tool
from typing import Optional, Dict, Any
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class BaseImprovAgent:
    """Base class for all Improv Olympics agents with built-in observability and retry logic."""

    def __init__(
        self,
        model_name: str,
        system_instruction: str,
        temperature: float = 0.7,
        tools: Optional[list] = None
    ):
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.temperature = temperature
        self.tools = tools or []

        # ADK Agent configuration with built-in features
        self.agent = Agent(
            model=model_name,
            system_instruction=system_instruction,
            generation_config=types.GenerationConfig(
                temperature=temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048,
            ),
            tools=self.tools,
            # Enable ADK retry logic for transient failures
            retry_options=types.RetryOptions(
                initial_delay_seconds=1,
                max_delay_seconds=32,
                delay_multiplier=2,
                max_attempts=5,
                retryable_error_codes=[429, 503, 500]  # Rate limit, service unavailable
            ),
            # Enable observability
            enable_prompt_logging=True,
            enable_response_logging=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def generate_response(
        self,
        user_input: str,
        session_context: Dict[str, Any],
        tool_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate agent response with retry logic and comprehensive logging.

        Args:
            user_input: User's message
            session_context: Current session state (turn count, phase, history)
            tool_context: Additional context for tool execution

        Returns:
            Agent's text response
        """
        try:
            logger.info(f"Agent {self.__class__.__name__} generating response", extra={
                "model": self.model_name,
                "temperature": self.temperature,
                "session_id": session_context.get("session_id"),
                "turn_count": session_context.get("turn_count")
            })

            # Construct messages with conversation history
            messages = self._build_message_history(session_context)
            messages.append({"role": "user", "content": user_input})

            # Call ADK agent with tool context
            response = await self.agent.generate_content(
                messages=messages,
                tool_context=tool_context
            )

            logger.info(f"Agent {self.__class__.__name__} response generated successfully", extra={
                "response_length": len(response.text),
                "tokens_used": response.usage_metadata.total_token_count if response.usage_metadata else None
            })

            return response.text

        except Exception as e:
            logger.error(f"Agent {self.__class__.__name__} failed to generate response", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "session_id": session_context.get("session_id")
            })
            raise

    def _build_message_history(self, session_context: Dict[str, Any]) -> list:
        """Build conversation history from session context for context window."""
        history = session_context.get("conversation_history", [])
        # ADK context compaction: Keep last N turns to prevent token overflow
        max_history_turns = 10
        return history[-max_history_turns * 2:] if len(history) > max_history_turns * 2 else history
```

---

## 3. Session Management and State Persistence

### 3.1 Session Architecture

**Challenge**: Improv scenes span 10-15 turns and require:
- Conversation history preservation
- Phase state tracking (PHASE_1 → PHASE_2 transition)
- Audience archetype persistence
- Sentiment trend analysis

**Solution**: Firestore with TTL-based session expiration

### 3.2 Firestore Schema Design

```python
# /Users/jpantona/Documents/code/ai4joy/src/state/models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime, timedelta

class Phase(str, Enum):
    INITIALIZATION = "INITIALIZATION"
    MC_WARMUP = "MC_WARMUP"
    PHASE_1_SUPPORT = "PHASE_1_SUPPORT"
    PHASE_2_FALLIBLE = "PHASE_2_FALLIBLE"
    COACH_ANALYSIS = "COACH_ANALYSIS"
    COMPLETE = "COMPLETE"

class SentimentLevel(str, Enum):
    WITH_YOU = "WITH_YOU"
    ENGAGED = "ENGAGED"
    NEUTRAL = "NEUTRAL"
    BORED = "BORED"
    CONFUSED = "CONFUSED"
    TENSE = "TENSE"

class Message(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str
    agent_name: Optional[str] = None  # Which agent generated this
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AudienceArchetype(BaseModel):
    name: str  # "Grumpy New Yorker", "Giggling Teen"
    description: str
    spotlight_count: int = 0  # How many times they've interrupted

class SessionState(BaseModel):
    session_id: str
    user_id: str
    current_phase: Phase = Phase.INITIALIZATION
    turn_count: int = 0

    # Scene configuration
    location: str  # "Mars Colony Breakroom"
    relationship: Optional[str] = None  # "Co-workers defusing a bomb"
    selected_game: Optional[str] = None  # "World's Worst Advice"

    # Conversation history
    conversation_history: List[Message] = Field(default_factory=list)

    # Audience state
    audience_archetypes: List[AudienceArchetype] = Field(default_factory=list)
    current_sentiment: SentimentLevel = SentimentLevel.NEUTRAL
    sentiment_history: List[SentimentLevel] = Field(default_factory=list)

    # Phase transition tracking
    phase_1_stability_count: int = 0  # Consecutive turns of stable sentiment
    phase_transition_turn: Optional[int] = None

    # Metrics
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=2)
    )

    # Observability
    total_tokens_used: int = 0
    latencies: Dict[str, List[float]] = Field(default_factory=dict)  # Agent name -> latencies
```

### 3.3 Firestore Session Manager Implementation

```python
# /Users/jpantona/Documents/code/ai4joy/src/state/session_manager.py

from google.cloud import firestore
from typing import Optional
import logging
from .models import SessionState, Message, Phase, SentimentLevel

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages session state persistence in Firestore with ADK integration."""

    def __init__(self, project_id: str):
        self.db = firestore.Client(project=project_id)
        self.sessions_collection = self.db.collection("improv_sessions")

    async def create_session(self, user_id: str, location: str) -> SessionState:
        """Create a new improv session."""
        session = SessionState(
            session_id=self.db.collection("_").document().id,  # Generate unique ID
            user_id=user_id,
            location=location
        )

        # Store in Firestore
        self.sessions_collection.document(session.session_id).set(
            session.model_dump(mode='json')
        )

        logger.info(f"Created session {session.session_id} for user {user_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve session state from Firestore."""
        doc = self.sessions_collection.document(session_id).get()

        if not doc.exists:
            logger.warning(f"Session {session_id} not found")
            return None

        return SessionState(**doc.to_dict())

    async def update_session(self, session: SessionState) -> None:
        """Update session state in Firestore."""
        from datetime import datetime
        session.updated_at = datetime.utcnow()

        self.sessions_collection.document(session.session_id).set(
            session.model_dump(mode='json'),
            merge=True
        )

        logger.debug(f"Updated session {session.session_id}")

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> None:
        """Add a message to the conversation history."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message = Message(
            role=role,
            content=content,
            agent_name=agent_name,
            metadata=metadata or {}
        )

        session.conversation_history.append(message)
        session.turn_count += 1

        await self.update_session(session)

    async def transition_phase(
        self,
        session_id: str,
        new_phase: Phase,
        reason: str = ""
    ) -> None:
        """Transition session to a new phase with logging."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        old_phase = session.current_phase
        session.current_phase = new_phase

        if new_phase == Phase.PHASE_2_FALLIBLE:
            session.phase_transition_turn = session.turn_count

        await self.update_session(session)

        logger.info(f"Session {session_id} transitioned: {old_phase} → {new_phase}", extra={
            "reason": reason,
            "turn_count": session.turn_count
        })

    async def update_sentiment(
        self,
        session_id: str,
        sentiment: SentimentLevel
    ) -> None:
        """Update current sentiment and track history."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.current_sentiment = sentiment
        session.sentiment_history.append(sentiment)

        # Track stability for phase transition logic
        if sentiment in [SentimentLevel.WITH_YOU, SentimentLevel.ENGAGED]:
            session.phase_1_stability_count += 1
        else:
            session.phase_1_stability_count = 0

        await self.update_session(session)

    async def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions (run as scheduled job)."""
        from datetime import datetime
        now = datetime.utcnow()

        expired_query = self.sessions_collection.where("expires_at", "<", now).stream()

        count = 0
        for doc in expired_query:
            doc.reference.delete()
            count += 1

        logger.info(f"Cleaned up {count} expired sessions")
        return count
```

### 3.4 ADK Session Integration

ADK provides built-in session management, but for your use case, Firestore is better because:

**Why Firestore over ADK Sessions**:
1. **Persistence across restarts**: Cloud Run instances are ephemeral
2. **Multi-turn complexity**: 10-15 turns with phase transitions
3. **Rich state**: Audience archetypes, sentiment history, metrics
4. **Observability**: Query sessions for analytics and debugging
5. **TTL management**: Automatic cleanup of old sessions

**ADK ToolContext Integration**:
```python
# Use ADK's ToolContext to pass session state to tools
tool_context = {
    "session_id": session.session_id,
    "current_phase": session.current_phase,
    "turn_count": session.turn_count,
    "audience_archetypes": [a.model_dump() for a in session.audience_archetypes],
    "sentiment": session.current_sentiment
}

response = await agent.generate_content(
    messages=messages,
    tool_context=tool_context  # Available to all tools
)
```

---

## 4. Model Integration Patterns for Gemini 1.5 Pro/Flash

### 4.1 Model Selection Strategy

Your design correctly uses:
- **Gemini 1.5 Flash** (faster, cheaper): MC, Room, Coach (orchestration tasks)
- **Gemini 1.5 Pro** (smarter, creative): Dynamic Scene Partner (complex reasoning)

### 4.2 VertexAI Configuration

```python
# /Users/jpantona/Documents/code/ai4joy/src/utils/config.py

import os
from google.auth import default
from google.auth.transport.requests import Request

class Config:
    """GCP and VertexAI configuration from environment."""

    # GCP Project
    PROJECT_ID = os.getenv("PROJECT_ID", "ImprovOlympics")
    REGION = os.getenv("REGION", "us-central1")

    # VertexAI Models (unified API, not legacy)
    GEMINI_FLASH_MODEL = "gemini-1.5-flash-002"
    GEMINI_PRO_MODEL = "gemini-1.5-pro-002"

    # Model parameters by agent
    MC_TEMPERATURE = 0.8  # High creativity for game selection
    ROOM_TEMPERATURE = 0.6  # Moderate for sentiment analysis
    PARTNER_PHASE1_TEMPERATURE = 0.9  # Maximum creativity
    PARTNER_PHASE2_TEMPERATURE = 0.7  # Slightly lower for coherent "stumbles"
    COACH_TEMPERATURE = 0.5  # Lower for consistent pedagogical feedback

    # Session management
    FIRESTORE_COLLECTION = "improv_sessions"
    SESSION_TTL_HOURS = 2

    # Rate limiting and retry
    MAX_RETRIES = 5
    INITIAL_RETRY_DELAY = 1.0
    MAX_RETRY_DELAY = 32.0

    # Observability
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_TRACING = os.getenv("ENABLE_TRACING", "true").lower() == "true"

    # WebSocket (future)
    ENABLE_WEBSOCKET = os.getenv("ENABLE_WEBSOCKET", "false").lower() == "true"

    @classmethod
    def get_credentials(cls):
        """Get GCP credentials for VertexAI authentication."""
        credentials, project = default()
        credentials.refresh(Request())
        return credentials
```

### 4.3 Agent-Specific Model Initialization

```python
# /Users/jpantona/Documents/code/ai4joy/src/agents/mc_agent.py

from .base_agent import BaseImprovAgent
from ..utils.config import Config

class MCAgent(BaseImprovAgent):
    """MC Agent - High-energy host using Gemini Flash."""

    def __init__(self):
        with open("config/prompts/mc_system_prompt.txt") as f:
            system_instruction = f.read()

        super().__init__(
            model_name=f"publishers/google/models/{Config.GEMINI_FLASH_MODEL}",
            system_instruction=system_instruction,
            temperature=Config.MC_TEMPERATURE,
            tools=[self._get_game_database_tool()]
        )

    def _get_game_database_tool(self):
        """Register GameDatabase tool for MC agent."""
        from ..tools.game_database import game_database_tool
        return game_database_tool
```

```python
# /Users/jpantona/Documents/code/ai4joy/src/agents/partner_agent.py

from .base_agent import BaseImprovAgent
from ..utils.config import Config
from ..state.models import Phase

class DynamicPartnerAgent(BaseImprovAgent):
    """
    Dynamic Scene Partner using Gemini Pro.

    Operates in two modes:
    - Phase 1 (PHASE_1_SUPPORT): Hyper-competent, validates user perfectly
    - Phase 2 (PHASE_2_FALLIBLE): Strategic fallibility, forces user to lead
    """

    def __init__(self):
        # Start with Phase 1 prompt
        with open("config/prompts/partner_phase1_prompt.txt") as f:
            self.phase1_prompt = f.read()

        with open("config/prompts/partner_phase2_prompt.txt") as f:
            self.phase2_prompt = f.read()

        super().__init__(
            model_name=f"publishers/google/models/{Config.GEMINI_PRO_MODEL}",
            system_instruction=self.phase1_prompt,
            temperature=Config.PARTNER_PHASE1_TEMPERATURE,
            tools=[]
        )

    async def generate_response(self, user_input: str, session_context: dict, tool_context=None):
        """Override to dynamically switch prompts based on phase."""
        current_phase = session_context.get("current_phase")

        # Dynamically adjust system instruction and temperature
        if current_phase == Phase.PHASE_2_FALLIBLE:
            self.agent.system_instruction = self.phase2_prompt
            self.agent.generation_config.temperature = Config.PARTNER_PHASE2_TEMPERATURE
        else:
            self.agent.system_instruction = self.phase1_prompt
            self.agent.generation_config.temperature = Config.PARTNER_PHASE1_TEMPERATURE

        return await super().generate_response(user_input, session_context, tool_context)
```

### 4.4 Cost Optimization Strategy

**Gemini Pricing (as of Dec 2024)**:
- **Flash**: $0.075 per 1M input tokens, $0.30 per 1M output tokens
- **Pro**: $1.25 per 1M input tokens, $5.00 per 1M output tokens

**Per-Session Cost Estimate**:
- 15 turns average
- 3 agents per turn (MC, Partner, Room)
- 500 tokens average input, 300 tokens output per agent

Flash agents (MC, Room, Coach):
- 15 turns × 2 agents × (500 input + 300 output) = 24,000 tokens
- Cost: ~$0.009 per session

Pro agent (Partner):
- 15 turns × (500 input + 300 output) = 12,000 tokens
- Cost: ~$0.075 per session

**Total per session: ~$0.084**
**100 sessions/day: ~$8.40/day = $252/month**

**Optimization Strategies**:
1. **Context compaction**: Limit history to last 10 turns
2. **Prompt caching**: Store common prompts in Secret Manager
3. **Semantic caching**: Cache similar user inputs (future)
4. **Batch processing**: Process multiple turns in one API call (Phase 2 optimization)

---

## 5. Custom Tools Integration and Deployment

### 5.1 ADK Tool Implementation Pattern

```python
# /Users/jpantona/Documents/code/ai4joy/src/tools/game_database.py

from google.adk.genai import tool
from typing import List, Dict
import json
import logging

logger = logging.getLogger(__name__)

class GameDatabase:
    """Retrieval tool for improv game rules."""

    def __init__(self, games_file: str = "config/games/games_database.json"):
        with open(games_file) as f:
            self.games = json.load(f)
        logger.info(f"Loaded {len(self.games)} games from database")

    @tool
    def search_games(
        self,
        category: str = None,  # "short_form" or "long_form"
        difficulty: str = None,  # "beginner", "intermediate", "advanced"
        constraints: List[str] = None  # ["verbal", "physical", "group"]
    ) -> List[Dict[str, str]]:
        """
        Search improv games by category, difficulty, and constraints.

        Args:
            category: Game category (short_form or long_form)
            difficulty: Skill level required
            constraints: List of constraint types

        Returns:
            List of matching games with rules and examples
        """
        results = self.games

        if category:
            results = [g for g in results if g.get("category") == category]

        if difficulty:
            results = [g for g in results if g.get("difficulty") == difficulty]

        if constraints:
            results = [
                g for g in results
                if any(c in g.get("constraints", []) for c in constraints)
            ]

        logger.info(f"Game search returned {len(results)} results", extra={
            "category": category,
            "difficulty": difficulty,
            "constraints": constraints
        })

        return results

    @tool
    def get_game_by_name(self, game_name: str) -> Dict[str, str]:
        """
        Retrieve specific game details by name.

        Args:
            game_name: Name of the improv game

        Returns:
            Game details including rules, examples, and coaching tips
        """
        game = next((g for g in self.games if g["name"].lower() == game_name.lower()), None)

        if not game:
            logger.warning(f"Game '{game_name}' not found")
            return {"error": f"Game '{game_name}' not found"}

        return game

# Instantiate for use by agents
game_database = GameDatabase()
game_database_tool = game_database.search_games
```

```python
# /Users/jpantona/Documents/code/ai4joy/src/tools/sentiment_gauge.py

from google.adk.genai import tool
from typing import List, Dict
from ..state.models import SentimentLevel
import logging

logger = logging.getLogger(__name__)

class SentimentGauge:
    """Analyzes conversation temperature and sentiment."""

    @tool
    def analyze_sentiment(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        turn_count: int
    ) -> Dict[str, any]:
        """
        Analyze the emotional temperature of the conversation.

        This tool performs lightweight sentiment analysis to determine
        the room's vibe without requiring a full LLM call.

        Args:
            user_input: Latest user message
            conversation_history: Recent conversation turns
            turn_count: Current turn number

        Returns:
            Sentiment analysis with level and reasoning
        """
        # Simple heuristic-based sentiment (could be enhanced with ML)
        input_lower = user_input.lower()

        # Positive indicators
        positive_signals = ["yes", "and", "great", "love", "awesome", "perfect", "exactly"]
        negative_signals = ["no", "but", "confused", "wait", "what", "huh", "stop"]
        engagement_signals = ["!", "?", "really", "wow", "oh"]

        positive_count = sum(1 for signal in positive_signals if signal in input_lower)
        negative_count = sum(1 for signal in negative_signals if signal in input_lower)
        engagement_count = sum(1 for signal in engagement_signals if signal in input_lower)

        # Determine sentiment level
        if positive_count >= 2 and negative_count == 0:
            sentiment = SentimentLevel.WITH_YOU
        elif engagement_count >= 2:
            sentiment = SentimentLevel.ENGAGED
        elif negative_count >= 2:
            sentiment = SentimentLevel.CONFUSED
        elif len(user_input) < 20 and turn_count > 5:
            sentiment = SentimentLevel.BORED
        else:
            sentiment = SentimentLevel.NEUTRAL

        logger.info(f"Sentiment analysis: {sentiment}", extra={
            "turn_count": turn_count,
            "input_length": len(user_input),
            "positive_signals": positive_count,
            "negative_signals": negative_count
        })

        return {
            "sentiment": sentiment,
            "confidence": 0.7,  # Placeholder for ML-based confidence
            "reasoning": f"Detected {positive_count} positive, {negative_count} negative signals"
        }

sentiment_gauge = SentimentGauge()
sentiment_gauge_tool = sentiment_gauge.analyze_sentiment
```

### 5.2 Tool Deployment Strategy

**Tools as Python Modules** (Recommended):
- Tools are just Python functions decorated with `@tool`
- Deployed within the same Cloud Run container
- No separate deployment needed
- Direct access to Firestore, Secret Manager, etc.

**Alternative: Tools as Cloud Functions** (For future scaling):
- Deploy tools as separate Cloud Functions
- Call via HTTP from agents
- Enables independent scaling and versioning
- Use for expensive tools (e.g., vector search with embeddings)

---

## 6. Scalability Considerations for Hub-and-Spoke Pattern

### 6.1 Current Architecture Scalability Analysis

**Strengths**:
- Stateless HTTP service (Cloud Run handles scaling)
- Firestore auto-scales reads/writes
- Gemini API has high throughput (managed by Google)
- Single deployment unit (no microservice complexity)

**Potential Bottlenecks**:
1. **Cold start latency**: First request to Cloud Run instance
2. **Sequential agent calls**: 3 agents per turn = 3× latency
3. **Firestore write contention**: Multiple updates per turn
4. **Gemini rate limits**: 60 requests/minute (Flash), 10 requests/minute (Pro)

### 6.2 Scalability Recommendations

#### 6.2.1 Cloud Run Configuration

```bash
# Optimized Cloud Run deployment
gcloud run deploy improv-olympics-api \
  --image=gcr.io/ImprovOlympics/improv-olympics-api:latest \
  --region=us-central1 \
  --platform=managed \
  \
  # Compute resources
  --memory=2Gi \
  --cpu=2 \
  --max-instances=100 \
  --min-instances=1 \  # Keep 1 instance warm to prevent cold starts
  --concurrency=80 \  # 80 concurrent requests per instance
  \
  # Timeouts
  --timeout=300s \  # 5 minutes for long improv scenes
  --cpu-throttling \  # Throttle CPU when idle (cost optimization)
  \
  # Scaling
  --cpu-utilization=70 \  # Scale up at 70% CPU
  --request-timeout=60s  # Individual request timeout
```

#### 6.2.2 Parallel Agent Execution (Future Optimization)

Current design: Sequential (MC → Partner → Room)
```
Turn latency = MC_latency + Partner_latency + Room_latency
             = 1s + 2s + 1s = 4s per turn
```

Optimized: Parallel where possible
```python
# /Users/jpantona/Documents/code/ai4joy/src/agents/stage_manager.py

import asyncio

class StageManager:
    """Root orchestrator for the improv scene."""

    async def process_turn_optimized(self, session_id: str, user_input: str):
        """Process a turn with parallel agent execution where possible."""
        session = await self.session_manager.get_session(session_id)

        # Phase 1: Partner response (must complete first)
        partner_response = await self.partner_agent.generate_response(
            user_input=user_input,
            session_context=session.model_dump()
        )

        # Phase 2: Room and sentiment analysis in parallel
        room_task = asyncio.create_task(
            self.room_agent.generate_response(
                user_input=f"Student: {user_input}\nPartner: {partner_response}",
                session_context=session.model_dump()
            )
        )

        sentiment_task = asyncio.create_task(
            self.sentiment_gauge.analyze_sentiment(
                user_input=user_input,
                conversation_history=session.conversation_history,
                turn_count=session.turn_count
            )
        )

        # Wait for both to complete
        room_response, sentiment_result = await asyncio.gather(room_task, sentiment_task)

        # Update session
        await self.session_manager.add_message(session_id, "assistant", partner_response, "Partner")
        await self.session_manager.add_message(session_id, "system", room_response, "Room")
        await self.session_manager.update_sentiment(session_id, sentiment_result["sentiment"])

        return {
            "partner_response": partner_response,
            "room_reaction": room_response,
            "sentiment": sentiment_result["sentiment"]
        }
```

**Improved latency**: 1s (Partner) + max(2s Room, 0.5s Sentiment) = 3s per turn (25% reduction)

#### 6.2.3 Firestore Optimization

```python
# Batch writes to reduce round trips
async def update_session_batch(self, session: SessionState, messages: List[Message], sentiment: SentimentLevel):
    """Batch multiple updates into a single Firestore transaction."""
    batch = self.db.batch()

    session_ref = self.sessions_collection.document(session.session_id)

    # Update session fields
    batch.update(session_ref, {
        "current_sentiment": sentiment,
        "sentiment_history": firestore.ArrayUnion([sentiment]),
        "turn_count": firestore.Increment(1),
        "updated_at": firestore.SERVER_TIMESTAMP
    })

    # Add messages
    for msg in messages:
        batch.update(session_ref, {
            "conversation_history": firestore.ArrayUnion([msg.model_dump()])
        })

    await batch.commit()
```

#### 6.2.4 Gemini Rate Limit Handling

```python
# /Users/jpantona/Documents/code/ai4joy/src/utils/retry_logic.py

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
import logging

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    """Custom exception for rate limit exceeded."""
    pass

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=1, max=32),
    retry=retry_if_exception_type((ResourceExhausted, ServiceUnavailable, RateLimitError)),
    reraise=True
)
async def call_gemini_with_retry(agent, messages, tool_context=None):
    """
    Call Gemini API with exponential backoff for rate limits.

    Rate limits (per project):
    - Flash: 60 RPM, 15 concurrent requests
    - Pro: 10 RPM, 5 concurrent requests
    """
    try:
        response = await agent.generate_content(
            messages=messages,
            tool_context=tool_context
        )
        return response

    except ResourceExhausted as e:
        logger.warning(f"Rate limit exceeded: {e}. Retrying with exponential backoff.")
        raise RateLimitError(f"Gemini rate limit exceeded: {e}")

    except ServiceUnavailable as e:
        logger.warning(f"Gemini service unavailable: {e}. Retrying.")
        raise
```

### 6.3 Load Testing Recommendations

```python
# /Users/jpantona/Documents/code/ai4joy/tests/load/locustfile.py

from locust import HttpUser, task, between
import json

class ImprovOlympicsUser(HttpUser):
    wait_time = between(5, 15)  # Simulate realistic user pauses

    def on_start(self):
        """Create a session when user starts."""
        response = self.client.post("/api/sessions", json={
            "user_id": f"loadtest_{self.user_id}",
            "location": "Mars Colony Breakroom"
        })
        self.session_id = response.json()["session_id"]

    @task(3)
    def send_message(self):
        """Send a message in the improv scene."""
        self.client.post(f"/api/sessions/{self.session_id}/message", json={
            "message": "Yes! And let's defuse this bomb together!"
        })

    @task(1)
    def get_session_state(self):
        """Check session state."""
        self.client.get(f"/api/sessions/{self.session_id}")

# Run: locust -f tests/load/locustfile.py --host=https://ai4joy.org
# Target: 100 concurrent users, 500 total sessions
```

---

## 7. Monitoring and Observability Setup

### 7.1 Observability Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Cloud Run Service                          │
│  - Structured JSON logs                                      │
│  - Custom metrics (Prometheus format)                        │
│  - OpenTelemetry tracing                                     │
└──────────────────┬──────────────────────────────────────────┘
                   │
       ┌───────────┼───────────┬──────────────┐
       ▼           ▼           ▼              ▼
  ┌─────────┐ ┌─────────┐ ┌─────────┐  ┌──────────┐
  │ Cloud   │ │ Cloud   │ │ Cloud   │  │ Cloud    │
  │ Logging │ │Monitori│ │ Trace   │  │ Error    │
  │         │ │   ng    │ │         │  │Reporting │
  └─────────┘ └─────────┘ └─────────┘  └──────────┘
```

### 7.2 Structured Logging Implementation

```python
# /Users/jpantona/Documents/code/ai4joy/src/utils/observability.py

import logging
import json
from google.cloud import logging as cloud_logging
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from typing import Dict, Any

class StructuredLogger:
    """Cloud Logging integration with structured JSON logs."""

    def __init__(self, project_id: str, service_name: str):
        # Initialize Cloud Logging client
        self.logging_client = cloud_logging.Client(project=project_id)
        self.logging_client.setup_logging()

        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.INFO)

        # Add structured log handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '{"severity": "%(levelname)s", "message": "%(message)s", '
            '"timestamp": "%(asctime)s", "extra": %(extra)s}'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_agent_call(
        self,
        agent_name: str,
        model_name: str,
        session_id: str,
        turn_count: int,
        latency_ms: float,
        tokens_used: int,
        success: bool,
        error: str = None
    ):
        """Log structured agent invocation data."""
        self.logger.info(
            f"Agent {agent_name} completed",
            extra={
                "agent_name": agent_name,
                "model_name": model_name,
                "session_id": session_id,
                "turn_count": turn_count,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "success": success,
                "error": error,
                "log_type": "agent_call"
            }
        )

    def log_phase_transition(
        self,
        session_id: str,
        old_phase: str,
        new_phase: str,
        turn_count: int,
        reason: str
    ):
        """Log phase transitions for pedagogical analysis."""
        self.logger.info(
            f"Phase transition: {old_phase} → {new_phase}",
            extra={
                "session_id": session_id,
                "old_phase": old_phase,
                "new_phase": new_phase,
                "turn_count": turn_count,
                "reason": reason,
                "log_type": "phase_transition"
            }
        )

class TracingManager:
    """OpenTelemetry distributed tracing integration."""

    def __init__(self, project_id: str):
        # Set up Cloud Trace exporter
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()

        cloud_trace_exporter = CloudTraceSpanExporter(project_id=project_id)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(cloud_trace_exporter)
        )

        self.tracer = trace.get_tracer(__name__)

    def trace_agent_execution(self, agent_name: str, session_id: str):
        """Context manager for tracing agent execution."""
        return self.tracer.start_as_current_span(
            f"agent.{agent_name}",
            attributes={
                "agent.name": agent_name,
                "session.id": session_id
            }
        )
```

### 7.3 Custom Metrics for Multi-Agent Systems

```python
# /Users/jpantona/Documents/code/ai4joy/src/utils/metrics.py

from prometheus_client import Counter, Histogram, Gauge
from google.cloud import monitoring_v3
import time

# Prometheus metrics (exposed via /metrics endpoint)
AGENT_CALLS_TOTAL = Counter(
    'improv_agent_calls_total',
    'Total number of agent invocations',
    ['agent_name', 'model', 'status']
)

AGENT_LATENCY_SECONDS = Histogram(
    'improv_agent_latency_seconds',
    'Agent response latency in seconds',
    ['agent_name', 'model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

ACTIVE_SESSIONS = Gauge(
    'improv_active_sessions',
    'Number of active improv sessions'
)

PHASE_TRANSITIONS_TOTAL = Counter(
    'improv_phase_transitions_total',
    'Total phase transitions',
    ['from_phase', 'to_phase']
)

SENTIMENT_DISTRIBUTION = Counter(
    'improv_sentiment_distribution',
    'Distribution of sentiment levels',
    ['sentiment']
)

TOKENS_USED_TOTAL = Counter(
    'improv_tokens_used_total',
    'Total tokens consumed',
    ['model', 'token_type']
)

class MetricsCollector:
    """Collect and export metrics to Cloud Monitoring."""

    def __init__(self, project_id: str):
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{project_id}"

    def record_agent_call(
        self,
        agent_name: str,
        model: str,
        latency_seconds: float,
        success: bool,
        tokens_used: int
    ):
        """Record metrics for a single agent call."""
        status = "success" if success else "error"

        AGENT_CALLS_TOTAL.labels(
            agent_name=agent_name,
            model=model,
            status=status
        ).inc()

        AGENT_LATENCY_SECONDS.labels(
            agent_name=agent_name,
            model=model
        ).observe(latency_seconds)

        # Split tokens by type
        TOKENS_USED_TOTAL.labels(
            model=model,
            token_type="total"
        ).inc(tokens_used)

    def record_phase_transition(self, from_phase: str, to_phase: str):
        """Record phase transition event."""
        PHASE_TRANSITIONS_TOTAL.labels(
            from_phase=from_phase,
            to_phase=to_phase
        ).inc()

    def record_sentiment(self, sentiment: str):
        """Record sentiment distribution."""
        SENTIMENT_DISTRIBUTION.labels(sentiment=sentiment).inc()

    def update_active_sessions(self, count: int):
        """Update active session gauge."""
        ACTIVE_SESSIONS.set(count)
```

### 7.4 Cloud Monitoring Dashboards

```json
{
  "displayName": "Improv Olympics - Multi-Agent Performance",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Agent Call Success Rate",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "metric.type=\"custom.googleapis.com/improv_agent_calls_total\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE"
                    }
                  }
                },
                "plotType": "LINE"
              }
            ]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "xPos": 6,
        "widget": {
          "title": "Agent Latency (P50, P95, P99)",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "metric.type=\"custom.googleapis.com/improv_agent_latency_seconds\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_DELTA",
                      "crossSeriesReducer": "REDUCE_PERCENTILE_50"
                    }
                  }
                }
              }
            ]
          }
        }
      },
      {
        "width": 12,
        "height": 4,
        "yPos": 4,
        "widget": {
          "title": "Phase Transition Frequency",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "metric.type=\"custom.googleapis.com/improv_phase_transitions_total\"",
                    "aggregation": {
                      "alignmentPeriod": "300s",
                      "perSeriesAligner": "ALIGN_RATE"
                    }
                  }
                }
              }
            ]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "yPos": 8,
        "widget": {
          "title": "Sentiment Distribution",
          "pieChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "metric.type=\"custom.googleapis.com/improv_sentiment_distribution\""
                  }
                }
              }
            ]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "xPos": 6,
        "yPos": 8,
        "widget": {
          "title": "Token Usage by Model",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "metric.type=\"custom.googleapis.com/improv_tokens_used_total\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE",
                      "groupByFields": ["metric.label.model"]
                    }
                  }
                }
              }
            ]
          }
        }
      }
    ]
  }
}
```

### 7.5 Alerting Policies

```yaml
# /Users/jpantona/Documents/code/ai4joy/infrastructure/monitoring/alert_policies.yaml

alertPolicies:
  - displayName: "High Agent Error Rate"
    conditions:
      - displayName: "Agent error rate > 5%"
        conditionThreshold:
          filter: 'metric.type="custom.googleapis.com/improv_agent_calls_total" AND metric.label.status="error"'
          comparison: COMPARISON_GT
          thresholdValue: 0.05
          duration: 300s
          aggregations:
            - alignmentPeriod: 60s
              perSeriesAligner: ALIGN_RATE
    notificationChannels:
      - projects/ImprovOlympics/notificationChannels/email-ops-team
    alertStrategy:
      autoClose: 1800s

  - displayName: "Agent Latency P95 > 10s"
    conditions:
      - displayName: "P95 latency exceeds 10 seconds"
        conditionThreshold:
          filter: 'metric.type="custom.googleapis.com/improv_agent_latency_seconds"'
          comparison: COMPARISON_GT
          thresholdValue: 10.0
          duration: 300s
          aggregations:
            - alignmentPeriod: 60s
              perSeriesAligner: ALIGN_DELTA
              crossSeriesReducer: REDUCE_PERCENTILE_95
    notificationChannels:
      - projects/ImprovOlympics/notificationChannels/email-ops-team

  - displayName: "Firestore Write Errors"
    conditions:
      - displayName: "Firestore write failures"
        conditionThreshold:
          filter: 'resource.type="cloud_firestore_database" AND metric.type="firestore.googleapis.com/document/write_count" AND metric.label.error_code!="OK"'
          comparison: COMPARISON_GT
          thresholdValue: 10
          duration: 120s
    notificationChannels:
      - projects/ImprovOlympics/notificationChannels/pagerduty-critical

  - displayName: "Active Sessions Spike"
    conditions:
      - displayName: "Active sessions > 1000"
        conditionThreshold:
          filter: 'metric.type="custom.googleapis.com/improv_active_sessions"'
          comparison: COMPARISON_GT
          thresholdValue: 1000
          duration: 60s
    notificationChannels:
      - projects/ImprovOlympics/notificationChannels/slack-engineering
```

---

## 8. WebSocket Architecture for Real-Time Voice (Future)

### 8.1 Current vs Future Architecture

**Current (Text-Based)**:
```
User → HTTP POST /api/sessions/{id}/message → Cloud Run → Agents → HTTP Response
```

**Future (Real-Time Voice)**:
```
User ↔ WebSocket Connection ↔ Cloud Run ↔ Agents
                                   ↕
                              Voice Activity Detection (VAD)
                                   ↕
                         Speech-to-Text / Text-to-Speech
```

### 8.2 WebSocket Implementation Strategy

```python
# /Users/jpantona/Documents/code/ai4joy/src/api/websocket_handler.py

from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import Flask, request
import asyncio
import logging

logger = logging.getLogger(__name__)

class ImprovWebSocketHandler:
    """WebSocket handler for real-time voice interaction."""

    def __init__(self, app: Flask, stage_manager):
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='threading',
            ping_timeout=60,
            ping_interval=25
        )
        self.stage_manager = stage_manager
        self._register_handlers()

    def _register_handlers(self):
        """Register WebSocket event handlers."""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle new WebSocket connection."""
            logger.info(f"Client connected: {request.sid}")
            emit('connected', {'status': 'ready'})

        @self.socketio.on('join_session')
        async def handle_join_session(data):
            """Join an existing improv session."""
            session_id = data.get('session_id')

            if not session_id:
                emit('error', {'message': 'session_id required'})
                return

            # Join Socket.IO room for this session
            join_room(session_id)

            # Load session state
            session = await self.stage_manager.session_manager.get_session(session_id)

            if not session:
                emit('error', {'message': 'Session not found'})
                return

            emit('session_joined', {
                'session_id': session_id,
                'current_phase': session.current_phase,
                'turn_count': session.turn_count
            })

            logger.info(f"Client {request.sid} joined session {session_id}")

        @self.socketio.on('audio_chunk')
        async def handle_audio_chunk(data):
            """
            Handle incoming audio chunk from client.

            Audio format: base64-encoded PCM16, 16kHz, mono
            """
            session_id = data.get('session_id')
            audio_data = data.get('audio')  # Base64 encoded
            is_final = data.get('is_final', False)  # VAD detected end of speech

            if not session_id or not audio_data:
                emit('error', {'message': 'session_id and audio required'})
                return

            # TODO: Implement speech-to-text (Vertex AI Speech-to-Text)
            # For now, emit acknowledgment
            emit('audio_received', {'chunk_id': data.get('chunk_id')})

            if is_final:
                # Process the complete utterance
                # transcribed_text = await self._transcribe_audio(audio_data)
                # response = await self.stage_manager.process_turn(session_id, transcribed_text)
                # audio_response = await self._synthesize_speech(response['partner_response'])
                # emit('agent_response', {'audio': audio_response, 'text': response['partner_response']})
                pass

        @self.socketio.on('text_message')
        async def handle_text_message(data):
            """
            Handle text message (fallback or mixed-mode interaction).
            """
            session_id = data.get('session_id')
            message = data.get('message')

            if not session_id or not message:
                emit('error', {'message': 'session_id and message required'})
                return

            # Process turn through stage manager
            response = await self.stage_manager.process_turn(session_id, message)

            # Emit response to client
            emit('agent_response', {
                'partner_response': response['partner_response'],
                'room_reaction': response.get('room_reaction'),
                'sentiment': response.get('sentiment')
            })

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {request.sid}")
```

### 8.3 Voice Activity Detection (VAD) Integration

```python
# /Users/jpantona/Documents/code/ai4joy/src/utils/vad.py

import numpy as np
from typing import Optional

class VoiceActivityDetector:
    """
    Simple energy-based VAD for detecting speech boundaries.

    For production, use Vertex AI Speech-to-Text streaming with VAD.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        energy_threshold: float = 0.02,
        silence_duration_ms: int = 500
    ):
        self.sample_rate = sample_rate
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.energy_threshold = energy_threshold
        self.silence_frames = int(silence_duration_ms / frame_duration_ms)

        self.consecutive_silence = 0
        self.is_speaking = False

    def process_frame(self, audio_frame: bytes) -> dict:
        """
        Process a single audio frame and detect voice activity.

        Args:
            audio_frame: Raw PCM16 audio bytes

        Returns:
            dict with 'is_speech' and 'is_final' flags
        """
        # Convert bytes to numpy array
        audio_int16 = np.frombuffer(audio_frame, dtype=np.int16)
        audio_float = audio_int16.astype(np.float32) / 32768.0

        # Calculate frame energy
        energy = np.sqrt(np.mean(audio_float ** 2))

        # Detect speech
        if energy > self.energy_threshold:
            self.is_speaking = True
            self.consecutive_silence = 0
        else:
            self.consecutive_silence += 1

        # Detect end of speech
        is_final = False
        if self.is_speaking and self.consecutive_silence >= self.silence_frames:
            is_final = True
            self.is_speaking = False
            self.consecutive_silence = 0

        return {
            'is_speech': energy > self.energy_threshold,
            'is_final': is_final,
            'energy': float(energy)
        }
```

### 8.4 WebSocket Deployment Considerations

**Cloud Run WebSocket Support**:
- Cloud Run fully supports WebSockets
- Use `--timeout=3600s` for long-lived connections (max 1 hour)
- Enable session affinity with `--session-affinity`
- Set `--min-instances=3` to ensure availability

**Alternative: Cloud Run + Pub/Sub for async processing**:
```
WebSocket Client ↔ Cloud Run (WebSocket Server)
                        ↓ (publish)
                   Pub/Sub Topic
                        ↓ (subscribe)
         Cloud Run (Agent Processor, stateless)
                        ↓
              Firestore (State Storage)
                        ↓ (Firestore triggers)
              Cloud Run (Response Handler)
                        ↓ (WebSocket broadcast)
                   WebSocket Client
```

**Latency Optimization**:
- Stream partial responses from agents (SSE-style)
- Use Gemini streaming API for incremental responses
- Implement audio buffering on client side
- Pre-warm agent models with keep-alive requests

---

## 9. Technical Risks and Mitigation Strategies

### 9.1 Risk Matrix

| Risk | Impact | Probability | Mitigation Strategy |
|------|--------|-------------|---------------------|
| **Cold start latency (>5s)** | High | Medium | Min instances = 1, pre-warming, async loading |
| **Gemini rate limit exceeded** | High | High | Retry with exponential backoff, request queuing, multi-project setup |
| **Firestore write contention** | Medium | Low | Batch writes, eventual consistency model |
| **Session state loss** | High | Low | Firestore replication, regular backups, graceful degradation |
| **Agent hallucination (factually incorrect improv coaching)** | Medium | Medium | Ground truth validation with ImprovExpertDatabase tool, human review |
| **Context window overflow (>1M tokens)** | Medium | Medium | Context compaction after 10 turns, summarization |
| **WebSocket connection drop** | Medium | High | Automatic reconnection, state persistence, resume logic |
| **Cost overrun (>$1000/month)** | High | Low | Budget alerts, rate limiting, usage quotas |
| **Domain (ai4joy.org) not routing to Cloud Run** | High | Low | Cloud Load Balancer + Cloud CDN, DNS verification |
| **Multi-agent coordination failure** | Medium | Medium | Comprehensive observability, circuit breakers, fallback logic |

### 9.2 Mitigation Implementation

#### 9.2.1 Cold Start Mitigation

```bash
# Deploy with minimum 1 instance to keep service warm
gcloud run deploy improv-olympics-api \
  --min-instances=1 \
  --max-instances=100 \
  --cpu-boost  # Allocate extra CPU during startup
```

```python
# /Users/jpantona/Documents/code/ai4joy/src/main.py

# Pre-load models and tools during startup (not per-request)
@app.before_first_request
async def initialize_agents():
    """Initialize all agents during startup to reduce first-request latency."""
    global stage_manager

    logger.info("Initializing agents...")
    stage_manager = StageManager(
        project_id=Config.PROJECT_ID,
        region=Config.REGION
    )

    # Pre-warm Gemini connections
    await stage_manager.mc_agent.generate_response("warm up", {})
    logger.info("Agents initialized successfully")
```

#### 9.2.2 Rate Limit Queue System

```python
# /Users/jpantona/Documents/code/ai4joy/src/utils/rate_limiter.py

import asyncio
from collections import deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for Gemini API calls.

    Rate limits:
    - Flash: 60 requests/minute
    - Pro: 10 requests/minute
    """

    def __init__(self, requests_per_minute: int, burst_size: int = None):
        self.rpm = requests_per_minute
        self.burst_size = burst_size or requests_per_minute
        self.tokens = self.burst_size
        self.last_update = datetime.utcnow()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire a token, blocking if rate limit is exceeded."""
        async with self.lock:
            now = datetime.utcnow()
            time_passed = (now - self.last_update).total_seconds()

            # Refill tokens based on time passed
            tokens_to_add = time_passed * (self.rpm / 60.0)
            self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
            self.last_update = now

            # If no tokens available, wait
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / (self.rpm / 60.0)
                logger.warning(f"Rate limit reached. Waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 1

            self.tokens -= 1

# Global rate limiters for each model
flash_rate_limiter = TokenBucketRateLimiter(requests_per_minute=60)
pro_rate_limiter = TokenBucketRateLimiter(requests_per_minute=10)

async def call_gemini_with_rate_limit(agent, model_type: str, messages, tool_context=None):
    """Wrap Gemini calls with rate limiting."""
    limiter = flash_rate_limiter if model_type == "flash" else pro_rate_limiter

    await limiter.acquire()

    try:
        response = await agent.generate_content(messages=messages, tool_context=tool_context)
        return response
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise
```

#### 9.2.3 Circuit Breaker for Agent Failures

```python
# /Users/jpantona/Documents/code/ai4joy/src/utils/circuit_breaker.py

from enum import Enum
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"      # Failing, reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing recovery

class CircuitBreaker:
    """
    Circuit breaker pattern for agent reliability.

    If an agent fails repeatedly, stop calling it temporarily
    to prevent cascading failures.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        expected_exception = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout_seconds):
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception(f"Circuit breaker OPEN. Agent temporarily unavailable.")

        try:
            result = await func(*args, **kwargs)

            # Success - reset failure count
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                logger.info("Circuit breaker CLOSED (recovered)")

            self.failure_count = 0
            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(f"Circuit breaker OPEN after {self.failure_count} failures")

            raise
```

#### 9.2.4 Graceful Degradation Strategy

```python
# /Users/jpantona/Documents/code/ai4joy/src/agents/stage_manager.py

class StageManager:
    """Root orchestrator with graceful degradation."""

    async def process_turn_with_fallback(self, session_id: str, user_input: str) -> dict:
        """Process turn with fallback strategies if agents fail."""
        session = await self.session_manager.get_session(session_id)

        try:
            # Try primary flow: Partner + Room + Sentiment
            response = await self._process_turn_normal(session_id, user_input)
            return response

        except Exception as e:
            logger.error(f"Primary agent flow failed: {e}. Attempting fallback.")

            # Fallback 1: Partner only (skip Room)
            try:
                partner_response = await self.partner_agent.generate_response(
                    user_input=user_input,
                    session_context=session.model_dump()
                )

                return {
                    "partner_response": partner_response,
                    "room_reaction": None,  # Skip audience
                    "sentiment": session.current_sentiment,  # Use previous sentiment
                    "degraded": True,
                    "degradation_reason": "Room agent unavailable"
                }

            except Exception as e2:
                logger.error(f"Fallback 1 failed: {e2}. Attempting Fallback 2.")

                # Fallback 2: Canned response with apology
                return {
                    "partner_response": "I'm having trouble connecting right now. Let's try that again!",
                    "room_reaction": "[Technical difficulties]",
                    "sentiment": session.current_sentiment,
                    "degraded": True,
                    "degradation_reason": "All agents unavailable",
                    "error": str(e2)
                }
```

---

## 10. Implementation Approach and Phasing

### 10.1 Recommended Phasing Strategy

```
Phase 1: MVP (Weeks 1-4)
├── Core infrastructure setup
├── Single-agent proof of concept
├── Basic HTTP API
└── Manual testing

Phase 2: Multi-Agent Orchestration (Weeks 5-8)
├── All 5 agents implemented
├── Firestore session management
├── Phase transition logic
├── Integration testing

Phase 3: Production Hardening (Weeks 9-12)
├── Observability (logging, metrics, tracing)
├── Error handling and retries
├── Load testing and optimization
├── Domain configuration (ai4joy.org)

Phase 4: WebSocket/Voice (Weeks 13-16)
├── WebSocket server implementation
├── Speech-to-Text integration
├── Text-to-Speech integration
├── Voice Activity Detection
```

### 10.2 Phase 1: MVP Implementation Checklist

**Week 1: Infrastructure Setup**
- [ ] GCP project setup (ImprovOlympics)
- [ ] Enable required APIs:
  ```bash
  gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    firestore.googleapis.com \
    secretmanager.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    aiplatform.googleapis.com
  ```
- [ ] Create Firestore database (Native mode, us-central1)
- [ ] Set up Secret Manager for API keys
- [ ] Configure IAM service accounts:
  - `improv-olympics-api@ImprovOlympics.iam.gserviceaccount.com`
  - Roles: Firestore User, Secret Manager Accessor, Vertex AI User

**Week 2: Single-Agent PoC**
- [ ] Create project structure
- [ ] Implement BaseImprovAgent class
- [ ] Implement MC Agent (simplest agent)
- [ ] Create Flask HTTP server
- [ ] Implement `/health` endpoint
- [ ] Implement `/api/test/mc` endpoint for testing
- [ ] Containerize with Dockerfile
- [ ] Deploy to Cloud Run
- [ ] Verify Gemini API connectivity

**Week 3: Session Management**
- [ ] Define SessionState Pydantic models
- [ ] Implement SessionManager with Firestore
- [ ] Create `/api/sessions` (POST) - create session
- [ ] Create `/api/sessions/{id}` (GET) - get session state
- [ ] Create `/api/sessions/{id}/message` (POST) - send message
- [ ] Test session persistence across requests

**Week 4: Testing & Documentation**
- [ ] Write unit tests for SessionManager
- [ ] Write integration tests for MC Agent
- [ ] Document API endpoints (OpenAPI spec)
- [ ] Create deployment runbook
- [ ] Set up basic Cloud Monitoring dashboard

### 10.3 Phase 2: Multi-Agent Implementation

**Week 5: Remaining Agents**
- [ ] Implement Room Agent (audience aggregator)
- [ ] Implement Dynamic Partner Agent
- [ ] Implement Coach Agent
- [ ] Create tools: GameDatabase, DemographicGenerator
- [ ] Create tools: SentimentGauge, ImprovExpertDatabase

**Week 6: Orchestration Logic**
- [ ] Implement StageManager class
- [ ] Implement turn-based loop (Steps A-E from design)
- [ ] Implement phase transition logic (PHASE_1 → PHASE_2)
- [ ] Add conversation history management
- [ ] Add sentiment tracking

**Week 7: Integration Testing**
- [ ] End-to-end scene simulation (15 turns)
- [ ] Verify phase transitions occur correctly
- [ ] Test audience archetype generation
- [ ] Test Coach post-game analysis
- [ ] Performance testing (single user)

**Week 8: Optimization**
- [ ] Implement parallel agent execution
- [ ] Add context compaction (10-turn limit)
- [ ] Optimize Firestore batch writes
- [ ] Add basic caching (prompt templates)

### 10.4 Phase 3: Production Hardening

**Week 9: Observability**
- [ ] Implement StructuredLogger
- [ ] Implement TracingManager (OpenTelemetry)
- [ ] Implement MetricsCollector (Prometheus)
- [ ] Create Cloud Monitoring dashboards
- [ ] Set up alerting policies

**Week 10: Reliability**
- [ ] Implement retry logic with exponential backoff
- [ ] Implement rate limiting (TokenBucket)
- [ ] Implement circuit breakers
- [ ] Add graceful degradation logic
- [ ] Test failure scenarios (agent timeout, Firestore unavailable)

**Week 11: Load Testing**
- [ ] Create Locust load test scripts
- [ ] Run load tests (10, 50, 100 concurrent users)
- [ ] Identify bottlenecks
- [ ] Optimize Cloud Run configuration (CPU, memory, concurrency)
- [ ] Implement auto-scaling policies

**Week 12: Domain & Launch**
- [ ] Configure Cloud Load Balancer
- [ ] Map ai4joy.org domain to Load Balancer
- [ ] Set up SSL certificate (Certificate Manager)
- [ ] Configure Cloud CDN for static assets
- [ ] Production smoke tests
- [ ] Soft launch (10 beta users)

### 10.5 Phase 4: WebSocket/Voice (Stretch Goal)

**Week 13: WebSocket Server**
- [ ] Implement Flask-SocketIO handlers
- [ ] Add `connect`, `disconnect`, `join_session` events
- [ ] Add `text_message` event (text fallback)
- [ ] Test WebSocket connection stability
- [ ] Deploy with session affinity

**Week 14: Speech Integration**
- [ ] Integrate Vertex AI Speech-to-Text (streaming)
- [ ] Integrate Vertex AI Text-to-Speech
- [ ] Test audio encoding/decoding (PCM16, Opus)
- [ ] Implement audio buffering

**Week 15: VAD & Real-Time Processing**
- [ ] Implement VoiceActivityDetector
- [ ] Add `audio_chunk` event handler
- [ ] Test end-of-speech detection
- [ ] Optimize latency (target <2s end-to-end)

**Week 16: Voice Launch**
- [ ] Client-side WebSocket implementation (web app)
- [ ] Microphone access and audio streaming
- [ ] Audio playback and visualization
- [ ] End-to-end voice testing
- [ ] Voice feature launch

---

## 11. Infrastructure as Code (Terraform)

### 11.1 Terraform Module Structure

```hcl
# /Users/jpantona/Documents/code/ai4joy/infrastructure/terraform/main.tf

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "improvollympics-terraform-state"
    prefix = "prod/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "firestore.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "aiplatform.googleapis.com",
    "compute.googleapis.com",
    "certificatemanager.googleapis.com"
  ])

  service = each.key
  disable_on_destroy = false
}

# Modules
module "firestore" {
  source = "./modules/firestore"

  project_id = var.project_id
  region     = var.region
}

module "cloud_run" {
  source = "./modules/cloud_run"

  project_id    = var.project_id
  region        = var.region
  service_name  = "improv-olympics-api"
  image         = var.cloud_run_image

  min_instances = 1
  max_instances = 100

  environment_vars = {
    PROJECT_ID = var.project_id
    REGION     = var.region
    LOG_LEVEL  = "INFO"
  }
}

module "load_balancer" {
  source = "./modules/load_balancer"

  project_id    = var.project_id
  region        = var.region
  domain        = "ai4joy.org"

  backend_service = module.cloud_run.service_name
}

module "monitoring" {
  source = "./modules/monitoring"

  project_id   = var.project_id
  service_name = module.cloud_run.service_name
}

module "secrets" {
  source = "./modules/secrets"

  project_id = var.project_id
}
```

```hcl
# /Users/jpantona/Documents/code/ai4joy/infrastructure/terraform/modules/cloud_run/main.tf

resource "google_cloud_run_service" "api" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.cloud_run_sa.email

      containers {
        image = var.image

        resources {
          limits = {
            cpu    = "2000m"
            memory = "2Gi"
          }
        }

        dynamic "env" {
          for_each = var.environment_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        ports {
          container_port = 8080
        }
      }

      container_concurrency = 80
      timeout_seconds       = 300
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.min_instances
        "autoscaling.knative.dev/maxScale" = var.max_instances
        "run.googleapis.com/cpu-throttling" = "true"
        "run.googleapis.com/startup-cpu-boost" = "true"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_service_account" "cloud_run_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name}"
}

resource "google_project_iam_member" "cloud_run_permissions" {
  for_each = toset([
    "roles/firestore.user",
    "roles/secretmanager.secretAccessor",
    "roles/aiplatform.user",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent"
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Allow unauthenticated access (or configure IAM for authenticated)
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_service.api.name
  location = google_cloud_run_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "service_url" {
  value = google_cloud_run_service.api.status[0].url
}

output "service_name" {
  value = google_cloud_run_service.api.name
}
```

### 11.2 Deployment Script

```bash
# /Users/jpantona/Documents/code/ai4joy/infrastructure/scripts/deploy.sh

#!/bin/bash
set -e

PROJECT_ID="ImprovOlympics"
REGION="us-central1"
SERVICE_NAME="improv-olympics-api"

echo "=== Improv Olympics Deployment Script ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Build and push container
echo "[1/4] Building container image..."
gcloud builds submit \
  --project=$PROJECT_ID \
  --config=cloudbuild.yaml \
  --region=$REGION \
  --substitutions=_IMAGE_NAME=gcr.io/$PROJECT_ID/$SERVICE_NAME

# Step 2: Apply Terraform infrastructure
echo "[2/4] Applying Terraform infrastructure..."
cd infrastructure/terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Step 3: Verify deployment
echo "[3/4] Verifying deployment..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --project=$PROJECT_ID \
  --region=$REGION \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Health check
echo "Performing health check..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL/health)

if [ "$HEALTH_STATUS" == "200" ]; then
  echo "✓ Health check passed"
else
  echo "✗ Health check failed (HTTP $HEALTH_STATUS)"
  exit 1
fi

# Step 4: Run smoke tests
echo "[4/4] Running smoke tests..."
python tests/smoke/test_api.py --url=$SERVICE_URL

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: $SERVICE_URL"
echo "Logs: gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit 50"
echo "Metrics: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics?project=$PROJECT_ID"
```

---

## 12. Cost Estimate and Optimization

### 12.1 Monthly Cost Breakdown (100 sessions/day)

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|-------------|
| **Cloud Run** | 100 sessions × 15 turns × 3s = 4,500 req-sec/day | $0.00002400/req-sec | $3.24 |
| **Firestore** | 100 sessions × 50 writes/session = 5,000 writes/day | $0.18/100K writes | $2.70 |
| **Firestore** | 100 sessions × 150 reads/session = 15,000 reads/day | $0.06/100K reads | $2.70 |
| **Gemini Flash** | 70% of calls, 24K tokens/session | $0.075/1M input + $0.30/1M output | $162 |
| **Gemini Pro** | 30% of calls, 12K tokens/session | $1.25/1M input + $5.00/1M output | $90 |
| **Cloud Logging** | 1GB/month | $0.50/GB | $0.50 |
| **Cloud Monitoring** | Standard metrics | Free tier | $0 |
| **Load Balancer** | 100GB egress | $0.12/GB | $12 |
| **Cloud Storage** (backups) | 10GB | $0.02/GB | $0.20 |
| **Total** | | | **$273.34/month** |

### 12.2 Cost Optimization Strategies

1. **Committed Use Discounts** (CUD):
   - If usage is predictable, commit to 1-year Gemini usage for 25% discount
   - Saves ~$63/month on Gemini costs

2. **Context Compaction**:
   - Limit history to 10 turns → reduce tokens by 30%
   - Saves ~$75/month on Gemini costs

3. **Semantic Caching** (future):
   - Cache similar user inputs and responses
   - Potential 20-40% reduction in Gemini calls

4. **Firestore Optimization**:
   - Batch writes (already planned)
   - Use Firestore offline persistence on client (future mobile app)

5. **Cloud Run Right-Sizing**:
   - Monitor CPU/memory usage
   - Potentially reduce to 1 CPU, 1Gi memory → saves ~$1/month

**Optimized Monthly Cost: ~$210/month (100 sessions/day)**

---

## 13. Summary and Next Steps

### 13.1 Key Architectural Decisions

1. **Deployment Platform**: Cloud Run (serverless, auto-scaling, WebSocket support)
2. **State Management**: Firestore (persistence, TTL, observability)
3. **Orchestration Pattern**: Hub-and-Spoke with simplified turn-based loop
4. **Model Selection**: Gemini Flash (MC, Room, Coach) + Pro (Partner)
5. **Agent Coordination**: Sequential with parallel optimization opportunities
6. **Observability**: Cloud Logging + Monitoring + OpenTelemetry traces
7. **Reliability**: Retry logic, rate limiting, circuit breakers, graceful degradation

### 13.2 Implementation Roadmap

**Immediate Next Steps (Week 1)**:
1. Set up GCP project and enable APIs
2. Create project structure with recommended file organization
3. Implement BaseImprovAgent and MC Agent
4. Deploy MVP to Cloud Run
5. Verify Gemini API connectivity

**Short-Term (Weeks 2-4)**:
1. Implement Firestore session management
2. Create HTTP API endpoints
3. Write unit and integration tests
4. Deploy to production with monitoring

**Medium-Term (Weeks 5-12)**:
1. Implement all 5 agents
2. Add phase transition logic
3. Production hardening (observability, reliability)
4. Load testing and optimization
5. Domain configuration (ai4joy.org)

**Long-Term (Weeks 13-16+)**:
1. WebSocket server for real-time interaction
2. Speech-to-Text and Text-to-Speech integration
3. Voice Activity Detection
4. Mobile app (iOS/Android)
5. Analytics dashboard for coaches

### 13.3 Success Criteria

**Technical**:
- [ ] Latency: P95 < 5s per turn (HTTP), P95 < 2s (WebSocket)
- [ ] Availability: 99.9% uptime (SLA)
- [ ] Error rate: < 1% agent failures
- [ ] Cost: < $300/month for 100 sessions/day

**Product**:
- [ ] Session completion rate > 80% (users finish 10+ turns)
- [ ] Phase transition logic works correctly (Phase 1 → Phase 2)
- [ ] Coach feedback is actionable and aligned with improv principles
- [ ] User satisfaction: NPS > 50

### 13.4 Open Questions for Product Team

1. **Authentication**: Should users have accounts, or anonymous sessions?
2. **Pricing Model**: Free tier limits? Premium features?
3. **Data Retention**: How long to keep session data for analytics?
4. **Content Moderation**: Safety filters for user inputs?
5. **Internationalization**: Support for non-English languages?

---

## Appendix A: Quick Reference Commands

```bash
# Deploy infrastructure
cd infrastructure/terraform
terraform init
terraform apply

# Build and deploy Cloud Run
gcloud builds submit --config=cloudbuild.yaml

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Monitor metrics
gcloud monitoring dashboards list

# Test API
curl -X POST https://ai4joy.org/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "location": "Mars Colony"}'

# SSH into Cloud Shell (for debugging)
gcloud cloud-shell ssh

# Scale Cloud Run manually
gcloud run services update improv-olympics-api \
  --min-instances=5 \
  --max-instances=200
```

## Appendix B: Useful Resources

- **ADK Documentation**: https://cloud.google.com/vertex-ai/docs/agent-builder
- **Cloud Run Documentation**: https://cloud.google.com/run/docs
- **Firestore Documentation**: https://cloud.google.com/firestore/docs
- **Gemini API Documentation**: https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini
- **Terraform GCP Provider**: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- **OpenTelemetry Python**: https://opentelemetry.io/docs/instrumentation/python/

---

**Document Version**: 1.0
**Last Updated**: 2025-11-23
**Author**: Agentic ML Architect + GCP Admin Deployer
**Project**: Improv Olympics
**Status**: Architecture Design Complete, Implementation Ready
