"""OAuth Authentication Endpoints"""
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse, Response, HTMLResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from app.config import get_settings
from app.utils.logger import get_logger
from app.middleware.oauth_auth import OAuthSessionMiddleware

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["authentication"])

# Initialize OAuth client
starlette_config = StarletteConfig(environ={
    "GOOGLE_CLIENT_ID": settings.oauth_client_id,
    "GOOGLE_CLIENT_SECRET": settings.oauth_client_secret,
})

oauth = OAuth(starlette_config)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account',  # Always show account selection
    }
)

# Middleware instance for creating session cookies
session_middleware = OAuthSessionMiddleware(app=None)


@router.get("/login")
async def login(request: Request, next: str = "/"):
    """
    Initiate OAuth login flow.

    Query Parameters:
        next: URL to redirect to after successful authentication (default: "/")

    This endpoint redirects the user to Google's OAuth consent screen.
    """
    logger.info("Initiating OAuth login flow", next_url=next)

    # Store the 'next' URL in the session for retrieval after callback
    redirect_uri = settings.oauth_redirect_uri

    # If running in production, use HTTPS redirect URI
    if request.url.hostname != "localhost":
        redirect_uri = f"https://{request.url.hostname}/auth/callback"

    logger.debug(
        "OAuth redirect configuration",
        redirect_uri=redirect_uri,
        next_url=next
    )

    try:
        return await oauth.google.authorize_redirect(
            request,
            redirect_uri,
            state=next  # Pass 'next' URL as state parameter
        )
    except Exception as e:
        logger.error("OAuth login initiation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate login. Please try again."
        )


@router.get("/callback")
async def auth_callback(request: Request):
    """
    OAuth callback endpoint.

    Google redirects here after user grants/denies permission.
    This endpoint exchanges the authorization code for an access token,
    retrieves user info, and creates a session cookie.
    """
    logger.info("Processing OAuth callback")

    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info:
            logger.error("No user info in OAuth token response")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information"
            )

        logger.info(
            "OAuth authentication successful",
            user_email=user_info.get('email'),
            user_id=user_info.get('sub')
        )

        # Check if user is allowed to access the application
        user_email = user_info.get('email', '')
        allowed_users = settings.allowed_users_list

        if allowed_users and user_email not in allowed_users:
            logger.warning(
                "Access denied - user not in whitelist",
                user_email=user_email,
                whitelist_count=len(allowed_users)
            )
            # Return user-friendly HTML error page
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Access Denied - Improv Olympics</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }}
                    .container {{
                        background: white;
                        padding: 3rem;
                        border-radius: 12px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        max-width: 500px;
                        text-align: center;
                    }}
                    h1 {{ color: #dc2626; margin-bottom: 1rem; }}
                    p {{ color: #4b5563; line-height: 1.6; margin-bottom: 1rem; }}
                    .email {{
                        background: #f3f4f6;
                        padding: 0.5rem 1rem;
                        border-radius: 6px;
                        font-family: monospace;
                        color: #1f2937;
                        margin: 1rem 0;
                    }}
                    .button {{
                        display: inline-block;
                        margin-top: 1.5rem;
                        padding: 0.75rem 1.5rem;
                        background: #667eea;
                        color: white;
                        text-decoration: none;
                        border-radius: 6px;
                        font-weight: 500;
                    }}
                    .button:hover {{ background: #5568d3; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🚫 Access Denied</h1>
                    <p>Your email address is not authorized to access this application.</p>
                    <div class="email">{user_email}</div>
                    <p>This application is currently in private beta. If you believe you should have access, please contact the administrator.</p>
                    <a href="/auth/logout" class="button">Sign Out</a>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=403)

        # Create session cookie
        session_cookie = session_middleware.create_session_cookie(user_info)

        # Get the 'next' URL from state parameter
        next_url = request.query_params.get('state', '/')

        # Create redirect response with session cookie
        response = RedirectResponse(url=next_url, status_code=302)

        # Use secure cookies only in production (HTTPS)
        is_production = request.url.hostname != "localhost"

        response.set_cookie(
            key="session",
            value=session_cookie,
            httponly=True,  # Prevent JavaScript access
            secure=is_production,  # HTTPS only in production
            samesite="lax", # CSRF protection
            max_age=86400,  # 24 hours
        )

        logger.info(
            "Session created successfully",
            user_email=user_info.get('email'),
            redirect_to=next_url
        )

        return response

    except Exception as e:
        logger.error("OAuth callback processing failed", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/logout")
async def logout(request: Request):
    """
    Logout endpoint.

    Clears the session cookie and redirects to home page.
    """
    logger.info("User logout requested")

    response = RedirectResponse(url="/", status_code=302)

    # Delete the session cookie
    response.delete_cookie(key="session")

    logger.info("Session cleared - user logged out")

    return response


@router.get("/user")
async def get_current_user(request: Request):
    """
    Get current authenticated user information.

    This endpoint is protected by the OAuth middleware and will only
    be accessible if the user has a valid session.

    Returns:
        User information including email, name, and user ID
    """
    from app.middleware.oauth_auth import get_authenticated_user

    try:
        user = get_authenticated_user(request)
        return {
            "authenticated": True,
            "user": user
        }
    except HTTPException:
        return {
            "authenticated": False,
            "user": None
        }
