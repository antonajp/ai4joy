"""Identity-Aware Proxy (IAP) Authentication Middleware"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional
import re

from app.config import get_settings
from app.utils.logger import get_logger

try:
    from google.auth.transport import requests
    from google.oauth2 import id_token
    JWT_VALIDATION_AVAILABLE = True
except ImportError:
    JWT_VALIDATION_AVAILABLE = False

logger = get_logger(__name__)
settings = get_settings()


class IAPAuthMiddleware:
    """
    Extracts and validates IAP headers from incoming requests.

    IAP injects two critical headers:
    - X-Goog-Authenticated-User-Email: accounts.google.com:user@example.com
    - X-Goog-Authenticated-User-ID: accounts.google.com:1234567890

    These headers are used for user authentication and session association.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        if self._should_bypass_auth(request.url.path):
            logger.debug("Bypassing IAP auth", path=request.url.path)
            await self.app(scope, receive, send)
            return

        try:
            if JWT_VALIDATION_AVAILABLE and settings.gcp_project_number:
                if not self._validate_iap_jwt(request):
                    logger.warning(
                        "IAP JWT validation failed",
                        path=request.url.path
                    )
                    response = JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "error": "Authentication failed",
                            "detail": "IAP JWT signature validation failed."
                        }
                    )
                    await response(scope, receive, send)
                    return
            elif not JWT_VALIDATION_AVAILABLE:
                logger.warning("JWT validation libraries not available - using header-only validation")
            elif not settings.gcp_project_number:
                logger.warning("GCP_PROJECT_NUMBER not configured - skipping JWT validation")

            user_email = self._extract_user_email(request)
            user_id = self._extract_user_id(request)

            if not user_email or not user_id:
                logger.warning(
                    "Missing IAP headers - authentication required",
                    path=request.url.path,
                    has_email=bool(user_email),
                    has_user_id=bool(user_id)
                )
                response = JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Authentication required",
                        "detail": "IAP headers missing. Ensure request passes through Identity-Aware Proxy."
                    }
                )
                await response(scope, receive, send)
                return

            logger.info(
                "IAP authentication successful",
                user_email=user_email,
                user_id=user_id,
                path=request.url.path
            )

            scope["state"] = {
                "user_email": user_email,
                "user_id": user_id,
            }

        except Exception as e:
            logger.error("IAP authentication error", error=str(e), path=request.url.path)
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Authentication processing failed"}
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def _should_bypass_auth(self, path: str) -> bool:
        """Check if path should bypass authentication with normalized path matching"""
        clean_path = path.split('?')[0].rstrip('/')
        bypass_paths = [p.rstrip('/') for p in settings.auth_bypass_paths]
        return clean_path in bypass_paths

    def _validate_iap_jwt(self, request: Request) -> bool:
        """
        Validate IAP JWT signature to prevent header spoofing.

        This provides defense-in-depth by verifying the JWT even though
        GCP IAP already validates at the load balancer level.
        """
        jwt_token = request.headers.get("x-goog-iap-jwt-assertion")
        if not jwt_token:
            logger.warning("IAP JWT token missing from request")
            return False

        try:
            audience = f"/projects/{settings.gcp_project_number}/global/backendServices/{settings.gcp_project_id}"
            decoded = id_token.verify_token(
                jwt_token,
                requests.Request(),
                audience=audience
            )
            logger.debug("IAP JWT validation successful", subject=decoded.get("sub"))
            return True
        except Exception as e:
            logger.error("JWT validation failed", error=str(e), error_type=type(e).__name__)
            return False

    def _extract_user_email(self, request: Request) -> Optional[str]:
        """
        Extract user email from IAP header.
        Header format: accounts.google.com:user@example.com
        """
        header_value = request.headers.get(settings.iap_header_email)
        if not header_value:
            return None

        match = re.match(r"accounts\.google\.com:(.+)", header_value)
        if match:
            return match.group(1)

        return header_value

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """
        Extract user ID from IAP header.
        Header format: accounts.google.com:1234567890
        """
        header_value = request.headers.get(settings.iap_header_user_id)
        if not header_value:
            return None

        match = re.match(r"accounts\.google\.com:(.+)", header_value)
        if match:
            return match.group(1)

        return header_value


def get_authenticated_user(request: Request) -> dict:
    """
    Get authenticated user information from request state.

    Returns:
        dict with user_email and user_id

    Raises:
        HTTPException if user not authenticated
    """
    if not hasattr(request.state, "user_email") or not hasattr(request.state, "user_id"):
        logger.error("Attempted to access user info without authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )

    return {
        "user_email": request.state.user_email,
        "user_id": request.state.user_id
    }
