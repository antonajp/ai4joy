"""Session Data Models"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    """Session lifecycle states.

    TEXT MODE (Freemium) FLOW:
    INITIALIZED -> MC_WELCOME -> GAME_SELECT -> SUGGESTION_PHASE -> ACTIVE ->
    SCENE_COMPLETE -> COACH_PHASE -> CLOSED

    TEXT MODE (With Pre-selected Game):
    INITIALIZED -> GAME_SELECT (skips MC_WELCOME) -> SUGGESTION_PHASE -> ACTIVE ->
    SCENE_COMPLETE -> COACH_PHASE -> CLOSED

    AUDIO MODE (Premium) FLOW:
    INITIALIZED -> ACTIVE -> CLOSED
    (Direct ADK orchestration via WebSocket, stateless design)

    LEGACY STATUSES:
    - MC_PHASE: Deprecated, kept for backwards compatibility only. Not used in current flows.

    TIMEOUT:
    - Terminal status when session expires (>60min since creation)
    """

    INITIALIZED = "initialized"  # Session created, awaiting first interaction
    MC_WELCOME = "mc_welcome"  # TEXT MODE: MC introducing and welcoming user
    GAME_SELECT = "game_select"  # TEXT MODE: User selecting game or MC suggesting
    SUGGESTION_PHASE = "suggestion_phase"  # TEXT MODE: Collecting audience suggestion
    MC_PHASE = "mc_phase"  # LEGACY: Deprecated, kept for backwards compatibility
    ACTIVE = "active"  # Scene work in progress (both TEXT and AUDIO modes)
    SCENE_COMPLETE = "scene_complete"  # TEXT MODE: Scene ended, awaiting coach feedback
    COACH_PHASE = "coach_phase"  # TEXT MODE: Coach providing feedback
    CLOSED = "closed"  # Terminal status: Session completed normally
    TIMEOUT = "timeout"  # Terminal status: Session expired due to timeout


class SessionCreate(BaseModel):
    """Request model for creating new session"""

    user_name: Optional[str] = Field(None, description="Optional display name")
    selected_game_id: Optional[str] = Field(None, description="Pre-selected game ID")
    selected_game_name: Optional[str] = Field(
        None, description="Pre-selected game name"
    )


class Session(BaseModel):
    """Session state model"""

    session_id: str
    user_id: str
    user_email: str
    user_name: Optional[str] = None

    status: SessionStatus = SessionStatus.INITIALIZED

    created_at: datetime
    updated_at: datetime
    expires_at: datetime

    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    current_phase: Optional[str] = None
    turn_count: int = 0

    # MC Welcome Phase fields
    selected_game_id: Optional[str] = None
    selected_game_name: Optional[str] = None
    audience_suggestion: Optional[str] = None
    mc_welcome_complete: bool = False

    class Config:
        use_enum_values = True


class SessionResponse(BaseModel):
    """API response model for session"""

    session_id: str
    status: str
    created_at: datetime
    expires_at: datetime
    turn_count: int = 0


class TurnInput(BaseModel):
    """User input for a turn"""

    user_input: str = Field(..., min_length=1, max_length=1000)
    turn_number: int = Field(..., ge=1)


class TurnResponse(BaseModel):
    """Response for a turn"""

    turn_number: int
    partner_response: str
    room_vibe: Dict[str, Any]
    current_phase: str
    timestamp: datetime
    coach_feedback: Optional[str] = None
