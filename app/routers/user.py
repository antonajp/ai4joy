"""User API Router - User Profile Endpoints

Provides endpoints for user profile management:
- GET /api/v1/user/me - Get current user's profile
"""

from fastapi import APIRouter, Request, HTTPException, status

from app.models.user import UserProfileResponse
from app.services.user_service import get_user_by_email, update_last_login
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/user", tags=["user"])


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user(request: Request) -> UserProfileResponse:
    """Get current authenticated user's profile.

    Returns:
        UserProfileResponse with user details including tier and audio usage

    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user is not authorized (not in Firestore)
    """
    # Check if user is authenticated
    if not hasattr(request.state, "user_email") or not request.state.user_email:
        logger.warning("Unauthenticated access attempt to /api/v1/user/me")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_email = request.state.user_email
    user_id = getattr(request.state, "user_id", None)

    # Look up user in Firestore
    user_profile = await get_user_by_email(user_email)

    if not user_profile:
        logger.warning(
            "Unauthorized user attempted to access profile",
            user_email=user_email,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not authorized for beta access",
        )

    # Update last login (fire and forget)
    try:
        await update_last_login(user_email)
    except Exception as e:
        logger.warning("Failed to update last login", error=str(e))

    # If we have OAuth user_id and it differs from stored, update it
    if user_id and user_profile.user_id != user_id:
        # Could update stored user_id here if needed
        pass

    logger.debug(
        "User profile retrieved",
        user_email=user_email,
        tier=user_profile.tier.value,
    )

    return UserProfileResponse.from_user_profile(user_profile)
