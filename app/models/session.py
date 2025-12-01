"""Session Data Models"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    """Session lifecycle states"""

    INITIALIZED = "initialized"
    MC_WELCOME = "mc_welcome"  # MC introducing and welcoming user
    GAME_SELECT = "game_select"  # User selecting game or MC suggesting
    SUGGESTION_PHASE = "suggestion_phase"  # Collecting audience suggestion
    MC_PHASE = "mc_phase"  # Legacy - kept for compatibility
    ACTIVE = "active"  # Scene work in progress
    SCENE_COMPLETE = "scene_complete"
    COACH_PHASE = "coach_phase"
    CLOSED = "closed"
    TIMEOUT = "timeout"


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
