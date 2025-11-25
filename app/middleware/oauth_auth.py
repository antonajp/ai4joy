"""Google OAuth 2.0 Authentication Middleware"""
from fastapi import Request
from fastapi.responses import RedirectResponse
from typing import Optional
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import time

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class OAuthSessionMiddleware:
    """
    Session-based authentication middleware using secure cookies.

    This middleware checks for a valid session cookie on each request.
    If no valid session exists and the path requires authentication,
    it redirects to the OAuth login flow.
    """

    def __init__(self, app):
        self.app = app
        self.serializer = URLSafeTimedSerializer(
            settings.session_secret_key or "dev-secret-key-change-in-production"
        )
        # Session expires after 24 hours
        self.max_age = 86400

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Check if this path should bypass authentication
        if self._should_bypass_auth(request.url.path):
            logger.debug("Bypassing OAuth auth", path=request.url.path)
            await self.app(scope, receive, send)
            return

        # Validate session cookie
        session_data = self._get_session_data(request)

        if not session_data:
            logger.warning(
                "No valid session - redirecting to login",
                path=request.url.path
            )
            # Redirect to login with return URL
            login_url = f"/auth/login?next={request.url.path}"
            response = RedirectResponse(url=login_url, status_code=302)
            await response(scope, receive, send)
            return

        # Session is valid - add user info to request state
        logger.debug(
            "Valid session found",
            user_email=session_data.get("email"),
            path=request.url.path
        )

        scope["state"] = {
            "user_email": session_data.get("email"),
            "user_id": session_data.get("sub"),
            "user_name": session_data.get("name"),
        }

        await self.app(scope, receive, send)

    def _should_bypass_auth(self, path: str) -> bool:
        """Check if path should bypass authentication"""
        clean_path = path.split('?')[0].rstrip('/')
        bypass_paths = [p.rstrip('/') for p in settings.auth_bypass_paths]
        return clean_path in bypass_paths

    def _get_session_data(self, request: Request) -> Optional[dict]:
        """
        Extract and validate session data from secure cookie.

        Returns user info dict if session is valid, None otherwise.
        """
        session_cookie = request.cookies.get("session")
        if not session_cookie:
            return None

        try:
            # Validate and deserialize the session cookie
            session_data = self.serializer.loads(
                session_cookie,
                max_age=self.max_age
            )
            return session_data
        except SignatureExpired:
            logger.info("Session expired")
            return None
        except BadSignature:
            logger.warning("Invalid session signature")
            return None
        except Exception as e:
            logger.error("Session validation error", error=str(e))
            return None

    def create_session_cookie(self, user_info: dict) -> str:
        """
        Create a secure session cookie with user information.

        Args:
            user_info: Dictionary containing user data from Google OAuth
                       (email, sub, name, etc.)

        Returns:
            Signed session cookie value
        """
        # Add timestamp for session tracking
        session_data = {
            **user_info,
            "created_at": int(time.time())
        }
        return self.serializer.dumps(session_data)


def get_authenticated_user(request: Request) -> dict:
    """
    Get authenticated user information from request state.

    Returns:
        dict with user_email, user_id, and user_name

    Raises:
        HTTPException if user not authenticated
    """
    from fastapi import HTTPException, status

    if not hasattr(request.state, "user_email") or not hasattr(request.state, "user_id"):
        logger.error("Attempted to access user info without authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )

    return {
        "user_email": request.state.user_email,
        "user_id": request.state.user_id,
        "user_name": getattr(request.state, "user_name", ""),
    }
