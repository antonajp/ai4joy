"""Session Management API Endpoints"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Dict, Any

from app.models.session import SessionCreate, SessionResponse, TurnInput, TurnResponse
from app.services.session_manager import SessionManager, get_session_manager
from app.services.rate_limiter import RateLimiter, get_rate_limiter, RateLimitExceeded
from app.services.turn_orchestrator import get_turn_orchestrator
from app.services.content_filter import get_content_filter
from app.services.pii_detector import get_pii_detector
from app.services.prompt_injection_guard import get_prompt_injection_guard
from app.services.adk_session_service import get_adk_session
from app.services.adk_memory_service import save_session_to_memory
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
        status=session.status,
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
        status=session.status,
        location=session.location,
        created_at=session.created_at,
        expires_at=session.expires_at,
        turn_count=session.turn_count
    )


@router.post("/session/{session_id}/turn", response_model=TurnResponse)
async def execute_turn(
    session_id: str,
    turn_input: TurnInput,
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager)
) -> TurnResponse:
    """
    Execute a turn in the improv session.

    Coordinates Stage Manager and sub-agents (Partner, Room, Coach) to:
    1. Generate Partner response to user input
    2. Provide Room audience vibe analysis
    3. Offer Coach feedback (if turn >= 15)
    4. Update session state and conversation history
    """
    user_info = get_authenticated_user(request)
    user_id = user_info["user_id"]

    # Security checks on user input
    content_filter = get_content_filter()
    pii_detector = get_pii_detector()
    injection_guard = get_prompt_injection_guard()

    # Check for prompt injection attempts
    injection_result = injection_guard.check_injection(turn_input.user_input)
    if not injection_result.is_safe:
        logger.warning(
            "Prompt injection attempt blocked",
            session_id=session_id,
            user_id=user_id,
            threat_level=injection_result.threat_level,
            detections=injection_result.detections
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Input contains patterns that violate content policy. Please rephrase your input."
        )

    # Check for offensive content
    content_result = content_filter.filter_input(turn_input.user_input)
    if not content_result.is_allowed:
        logger.warning(
            "Offensive content blocked",
            session_id=session_id,
            user_id=user_id,
            severity=content_result.severity
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input contains inappropriate content. Please keep the scene collaborative and respectful."
        )

    # Detect and redact PII for logging
    pii_result = pii_detector.detect_pii(turn_input.user_input)
    if pii_result.has_pii:
        logger.warning(
            "PII detected in user input",
            session_id=session_id,
            user_id=user_id,
            pii_types=[d.pii_type for d in pii_result.detections]
        )

    # Use redacted version for all logging from this point forward
    sanitized_input = pii_result.redacted_text

    # Retrieve session
    session = await session_manager.get_session(session_id)

    if not session:
        logger.warning("Turn requested for non-existent session", session_id=session_id, user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or expired"
        )

    # Verify ownership
    if session.user_id != user_id:
        logger.warning(
            "Unauthorized turn attempt",
            session_id=session_id,
            requesting_user=user_id,
            session_owner=session.user_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )

    # Validate turn number matches session state
    expected_turn = session.turn_count + 1
    if turn_input.turn_number != expected_turn:
        logger.warning(
            "Turn number mismatch",
            session_id=session_id,
            expected=expected_turn,
            received=turn_input.turn_number
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected turn {expected_turn}, got {turn_input.turn_number}"
        )

    # Execute turn with orchestrator
    orchestrator = get_turn_orchestrator(session_manager)

    try:
        # Use original input for agent execution, sanitized for logging
        turn_response_data = await orchestrator.execute_turn(
            session=session,
            user_input=turn_input.user_input,
            turn_number=turn_input.turn_number
        )

        logger.info(
            "Turn completed successfully",
            session_id=session_id,
            turn_number=turn_input.turn_number,
            user_id=user_id
        )

        phase_int = turn_response_data["current_phase"]
        turn_response_data["current_phase"] = f"Phase {phase_int} ({'Supportive' if phase_int == 1 else 'Fallible'})"

        return TurnResponse(**turn_response_data)

    except asyncio.TimeoutError:
        logger.error(
            "Turn execution timed out",
            session_id=session_id,
            turn_number=turn_input.turn_number
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Agent execution timed out. Please try again."
        )
    except Exception as e:
        logger.error(
            "Turn execution failed",
            session_id=session_id,
            turn_number=turn_input.turn_number,
            error=str(e),
            error_type=type(e).__name__
        )
        # Sanitize error message - don't leak internal details
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while executing the turn. Please try again or contact support."
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

    try:
        adk_session = await get_adk_session(session_id=session_id, user_id=user_id)
        if adk_session:
            memory_saved = await save_session_to_memory(adk_session)
            if memory_saved:
                logger.info(
                    "Session memories saved",
                    session_id=session_id,
                    user_id=user_id
                )
        else:
            logger.warning(
                "ADK session not found for memory save",
                session_id=session_id,
                user_id=user_id
            )
    except Exception as e:
        logger.error(
            "Failed to save session to memory, continuing with close",
            session_id=session_id,
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__
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
