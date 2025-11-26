"""IAP Authentication Middleware for Google Identity-Aware Proxy"""

from fastapi import Request, HTTPException, status
from typing import Optional, Dict
from functools import wraps

from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_authenticated_user(request: Request) -> Dict[str, str]:
    """
    Extract authenticated user information from IAP headers.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary containing user_email and user_id

    Raises:
        HTTPException: 401 if authentication headers are missing or invalid
    """
    iap_email_header = "X-Goog-Authenticated-User-Email"
    iap_id_header = "X-Goog-Authenticated-User-ID"

    user_email = request.headers.get(iap_email_header)
    user_id = request.headers.get(iap_id_header)

    if not user_email or not user_id:
        logger.warning(
            "Missing IAP authentication headers",
            path=request.url.path,
            has_email=bool(user_email),
            has_id=bool(user_id),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required - IAP headers missing",
        )

    user_email_clean = user_email.replace("accounts.google.com:", "")
    user_id_clean = user_id.replace("accounts.google.com:", "")

    logger.debug(
        "User authenticated via IAP",
        user_email=user_email_clean,
        user_id=user_id_clean,
        path=request.url.path,
    )

    return {"user_email": user_email_clean, "user_id": user_id_clean}


def require_auth(func):
    """
    Decorator to enforce authentication on endpoint functions.

    Extracts IAP headers and injects user info into request state.
    Returns 401 if authentication headers are missing or invalid.

    Usage:
        @router.get("/protected-endpoint")
        @require_auth
        async def protected_route(request: Request):
            user = get_authenticated_user(request)
            return {"user": user}
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = None

        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        if not request and "request" in kwargs:
            request = kwargs["request"]

        if not request:
            logger.error(
                "require_auth decorator used on function without Request parameter"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

        try:
            user_info = get_authenticated_user(request)
            request.state.user_email = user_info["user_email"]
            request.state.user_id = user_info["user_id"]

            logger.debug(
                "Authentication successful for endpoint",
                endpoint=func.__name__,
                user_email=user_info["user_email"],
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Unexpected error in authentication",
                endpoint=func.__name__,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
            )

        return await func(*args, **kwargs)

    return wrapper


class IAPAuthMiddleware:
    """
    ASGI middleware for IAP authentication validation.

    Validates presence of IAP headers on all requests except bypass paths.
    Returns 401 for missing or invalid authentication headers.
    """

    def __init__(self, app, bypass_paths: Optional[list] = None):
        self.app = app
        self.bypass_paths = bypass_paths or [
            "/health",
            "/ready",
            "/",
        ]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        if self._should_bypass_auth(request.url.path):
            logger.debug("Bypassing IAP auth check", path=request.url.path)
            await self.app(scope, receive, send)
            return

        try:
            user_info = get_authenticated_user(request)
            scope["state"] = {
                "user_email": user_info["user_email"],
                "user_id": user_info["user_id"],
            }

            await self.app(scope, receive, send)

        except HTTPException as e:
            from fastapi.responses import JSONResponse

            response = JSONResponse(
                status_code=e.status_code, content={"detail": e.detail}
            )
            await response(scope, receive, send)

    def _should_bypass_auth(self, path: str) -> bool:
        """Check if path should bypass authentication"""
        clean_path = path.split("?")[0].rstrip("/")
        bypass_paths_clean = [p.rstrip("/") for p in self.bypass_paths]
        return clean_path in bypass_paths_clean
