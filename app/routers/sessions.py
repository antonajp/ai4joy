"""Session Management API Endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from datetime import datetime, timezone
from typing import Dict, Any

from app.models.session import SessionCreate, SessionResponse, TurnInput, TurnResponse
from app.services.session_manager import SessionManager, get_session_manager
from app.services.rate_limiter import RateLimiter, get_rate_limiter, RateLimitExceeded
from app.middleware.iap_auth import get_authenticated_user
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1", tags=["sessions"])
logger = get_logger(__name__)


@router.post("/session/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    session_data: SessionCreate,
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
) -> SessionResponse:
    """
    Create new session with rate limiting.

    Checks:
    1. Daily session limit (10 per day)
    2. Concurrent session limit (3 active)
    3. Creates session associated with authenticated user
    """
    user_info = get_authenticated_user(request)
    user_id = user_info["user_id"]
    user_email = user_info["user_email"]

    logger.info(
        "Session creation requested",
        user_id=user_id,
        user_email=user_email,
        location=session_data.location
    )

    try:
        await rate_limiter.check_and_increment_daily_limit(user_id)
    except RateLimitExceeded as e:
        logger.warning(
            "Session creation blocked by daily rate limit",
            user_id=user_id,
            user_email=user_email
        )
        raise e

    session = await session_manager.create_session(
        user_id=user_id,
        user_email=user_email,
        session_data=session_data
    )

    try:
        await rate_limiter.check_and_increment_concurrent_limit(user_id, session.session_id)
    except RateLimitExceeded as e:
        logger.warning(
            "Session creation blocked by concurrent rate limit",
            user_id=user_id,
            session_id=session.session_id
        )
        await session_manager.close_session(session.session_id)
        raise e

    logger.info(
        "Session created successfully",
        session_id=session.session_id,
        user_id=user_id,
        user_email=user_email
    )

    return SessionResponse(
        session_id=session.session_id,
        status=session.status.value,
        location=session.location,
        created_at=session.created_at,
        expires_at=session.expires_at,
        turn_count=session.turn_count
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session_info(
    session_id: str,
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager)
) -> SessionResponse:
    """Get session information"""
    user_info = get_authenticated_user(request)
    user_id = user_info["user_id"]

    session = await session_manager.get_session(session_id)

    if not session:
        logger.warning("Session not found", session_id=session_id, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired"
        )

    if session.user_id != user_id:
        logger.warning(
            "Unauthorized session access attempt",
            session_id=session_id,
            requesting_user=user_id,
            session_owner=session.user_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )

    return SessionResponse(
        session_id=session.session_id,
        status=session.status.value,
        location=session.location,
        created_at=session.created_at,
        expires_at=session.expires_at,
        turn_count=session.turn_count
    )


@router.post("/session/{session_id}/close")
async def close_session(
    session_id: str,
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager),
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
) -> Dict[str, str]:
    """
    Close session and decrement concurrent counter.
    """
    user_info = get_authenticated_user(request)
    user_id = user_info["user_id"]

    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to close this session"
        )

    await session_manager.close_session(session_id)
    await rate_limiter.decrement_concurrent_sessions(user_id, session_id)

    logger.info(
        "Session closed",
        session_id=session_id,
        user_id=user_id
    )

    return {"status": "closed", "session_id": session_id}


@router.get("/user/limits")
async def get_user_limits(
    request: Request,
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
) -> Dict[str, Any]:
    """
    Get current rate limit status for authenticated user.
    """
    user_info = get_authenticated_user(request)
    user_id = user_info["user_id"]

    limits = await rate_limiter.get_user_limits_status(user_id)

    return {
        "user_id": user_id,
        "limits": limits
    }
