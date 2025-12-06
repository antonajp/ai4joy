"""MFA Enforcement Middleware

This middleware enforces MFA verification on sensitive endpoints
for Phase 2 of IQS-65.

Features:
- Check MFA enrollment status for authenticated users
- Require MFA verification on sensitive endpoints
- Bypass MFA checks for public and MFA enrollment endpoints
- Integration with existing session cookie system

Acceptance Criteria:
- AC-MFA-01: MFA enrollment mandatory during signup
- AC-MFA-06: MFA verification required on every login
"""

from fastapi import Request, HTTPException, status
from typing import Optional, List
from functools import wraps

from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


# Endpoints that require MFA verification (if user has MFA enabled)
MFA_PROTECTED_ENDPOINTS = [
    "/api/v1/sessions",  # Creating new improv sessions
    "/api/v1/user/me",  # Viewing user profile
    "/api/v1/turn",  # Executing turns
]

# Endpoints that bypass MFA check (public, auth, and MFA enrollment)
MFA_BYPASS_ENDPOINTS = [
    "/health",
    "/ready",
    "/auth/login",
    "/auth/callback",
    "/auth/logout",
    "/auth/user",
    "/auth/ws-token",
    "/auth/firebase/token",
    "/auth/mfa/enroll",  # MFA enrollment endpoints
    "/auth/mfa/verify",  # MFA verification endpoints
    "/auth/mfa/recovery",  # Recovery code endpoints
    "/auth/mfa/generate-recovery",
    "/auth/mfa/status",
    "/",
    "/static/",
]


async def check_mfa_status(request: Request) -> bool:
    """Check if user has completed MFA verification.

    Args:
        request: FastAPI request object

    Returns:
        True if user has completed MFA verification or MFA not required
        False if user needs MFA verification

    Checks:
    1. Is user authenticated?
    2. Does user have MFA enabled?
    3. Has user verified MFA in this session?
    """
    # Get user from request state (set by auth middleware)
    user_email = getattr(request.state, "user_email", None)

    if not user_email:
        # User not authenticated, let auth middleware handle it
        return True

    # Check if user has MFA enabled in Firestore
    from app.services.user_service import get_user_by_email

    try:
        user_profile = await get_user_by_email(user_email)

        if not user_profile:
            logger.warning(
                "User profile not found for MFA check", user_email=user_email
            )
            return True  # Let other middleware handle missing profile

        # If user has MFA enabled, check if they've verified in this session
        if user_profile.mfa_enabled:
            # Check session cookie for MFA verification flag
            from app.middleware.oauth_auth import OAuthSessionMiddleware

            session_middleware = OAuthSessionMiddleware(app=None)
            session_cookie = request.cookies.get("session")

            if not session_cookie:
                logger.warning("No session cookie found for MFA check")
                return False

            try:
                # Validate and deserialize session cookie
                session_data = session_middleware.serializer.loads(
                    session_cookie, max_age=session_middleware.max_age
                )

                # Check if MFA was verified in this session
                mfa_verified = session_data.get("mfa_verified", False)

                if not mfa_verified:
                    logger.warning(
                        "User has MFA enabled but not verified in session",
                        user_email=user_email,
                    )
                    return False

                logger.debug("MFA verified in session", user_email=user_email)
                return True

            except Exception as e:
                logger.error("Failed to validate session for MFA check", error=str(e))
                return False

        # User doesn't have MFA enabled, allow access
        return True

    except Exception as e:
        logger.error("Error checking MFA status", error=str(e), user_email=user_email)
        # Fail open to prevent accidental lockout
        return True


def should_enforce_mfa(path: str) -> bool:
    """Determine if MFA should be enforced for this path.

    Args:
        path: Request path

    Returns:
        True if MFA should be enforced, False otherwise
    """
    # Remove query string and trailing slash
    clean_path = path.split("?")[0].rstrip("/")

    # Check bypass list first
    for bypass_path in MFA_BYPASS_ENDPOINTS:
        if clean_path.startswith(bypass_path.rstrip("/")):
            return False

    # Check if path is in protected list
    for protected_path in MFA_PROTECTED_ENDPOINTS:
        if clean_path.startswith(protected_path.rstrip("/")):
            return True

    # Default: don't enforce MFA (fail open)
    return False


def require_mfa(func):
    """Decorator to enforce MFA verification on endpoint.

    Usage:
        @router.get("/protected-endpoint")
        @require_mfa
        async def protected_route(request: Request):
            return {"data": "sensitive"}
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Find Request object in args or kwargs
        request = None

        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        if not request and "request" in kwargs:
            request = kwargs["request"]

        if not request:
            logger.error(
                "require_mfa decorator used on function without Request parameter"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

        # Check MFA status
        mfa_ok = await check_mfa_status(request)

        if not mfa_ok:
            logger.warning(
                "MFA verification required",
                endpoint=func.__name__,
                user_email=getattr(request.state, "user_email", "unknown"),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Multi-factor authentication verification required. Please complete MFA verification.",
            )

        # MFA check passed, continue to endpoint
        return await func(*args, **kwargs)

    return wrapper


class MFAEnforcementMiddleware:
    """ASGI middleware for MFA enforcement on protected endpoints.

    This middleware:
    1. Checks if endpoint requires MFA
    2. Verifies user has completed MFA if required
    3. Returns 403 if MFA verification needed
    4. Bypasses MFA check for public and enrollment endpoints
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        # Check if MFA should be enforced for this path
        if should_enforce_mfa(path):
            logger.debug("Checking MFA enforcement", path=path)

            # Check MFA status
            mfa_ok = await check_mfa_status(request)

            if not mfa_ok:
                logger.warning(
                    "MFA verification required for protected endpoint",
                    path=path,
                    user_email=getattr(request.state, "user_email", "unknown"),
                )

                from fastapi.responses import JSONResponse

                response = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "Multi-factor authentication verification required",
                        "mfa_required": True,
                        "redirect_to": "/auth/mfa/verify",
                    },
                )

                await response(scope, receive, send)
                return

        # MFA not required or check passed, continue
        await self.app(scope, receive, send)
