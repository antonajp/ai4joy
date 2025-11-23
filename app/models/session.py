"""Session Data Models"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    """Session lifecycle states"""
    INITIALIZED = "initialized"
    MC_PHASE = "mc_phase"
    ACTIVE = "active"
    SCENE_COMPLETE = "scene_complete"
    COACH_PHASE = "coach_phase"
    CLOSED = "closed"
    TIMEOUT = "timeout"


class SessionCreate(BaseModel):
    """Request model for creating new session"""
    location: str = Field(..., description="Scene location", min_length=1, max_length=200)
    user_name: Optional[str] = Field(None, description="Optional display name")


class Session(BaseModel):
    """Session state model"""
    session_id: str
    user_id: str
    user_email: str
    user_name: Optional[str] = None

    location: str
    status: SessionStatus = SessionStatus.INITIALIZED

    created_at: datetime
    updated_at: datetime
    expires_at: datetime

    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    current_phase: Optional[str] = None
    turn_count: int = 0

    class Config:
        use_enum_values = True


class SessionResponse(BaseModel):
    """API response model for session"""
    session_id: str
    status: str
    location: str
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
