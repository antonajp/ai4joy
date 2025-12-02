"""OAuth Authentication Endpoints"""

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from app.config import get_settings
from app.utils.logger import get_logger
from app.middleware.oauth_auth import OAuthSessionMiddleware

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["authentication"])

# Initialize OAuth client
starlette_config = StarletteConfig(
    environ={
        "GOOGLE_CLIENT_ID": settings.oauth_client_id,
        "GOOGLE_CLIENT_SECRET": settings.oauth_client_secret,
    }
)

oauth = OAuth(starlette_config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "prompt": "select_account",  # Always show account selection
    },
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
        "OAuth redirect configuration", redirect_uri=redirect_uri, next_url=next
    )

    try:
        return await oauth.google.authorize_redirect(
            request,
            redirect_uri,
            state=next,  # Pass 'next' URL as state parameter
        )
    except Exception as e:
        logger.error("OAuth login initiation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate login. Please try again.",
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
        user_info = token.get("userinfo")
        if not user_info:
            logger.error("No user info in OAuth token response")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information",
            )

        logger.info(
            "OAuth authentication successful",
            user_email=user_info.get("email"),
            user_id=user_info.get("sub"),
        )

        # Check if user is allowed to access the application
        # Uses Firestore-based authorization when USE_FIRESTORE_AUTH is enabled
        user_email = user_info.get("email", "")
        is_authorized = await check_user_authorization(user_email)

        if not is_authorized:
            logger.warning(
                "Access denied - user not authorized",
                user_email=user_email,
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
        next_url = request.query_params.get("state", "/")

        # Create redirect response with session cookie
        response = RedirectResponse(url=next_url, status_code=302)

        # Use secure cookies only in production (HTTPS)
        is_production = request.url.hostname != "localhost"

        # Determine the domain for the cookie
        # For ai4joy.org, use the base domain so cookie works across subdomains
        cookie_domain = None
        if request.url.hostname == "ai4joy.org" or request.url.hostname.endswith(
            ".ai4joy.org"
        ):
            cookie_domain = "ai4joy.org"

        response.set_cookie(
            key="session",
            value=session_cookie,
            domain=cookie_domain,  # Set explicit domain for ai4joy.org
            path="/",  # Make cookie valid for entire site
            httponly=True,  # Prevent JavaScript access
            secure=is_production,  # HTTPS only in production
            samesite="lax",  # CSRF protection
            max_age=86400,  # 24 hours
        )

        logger.info(
            "Session created successfully",
            user_email=user_info.get("email"),
            redirect_to=next_url,
        )

        return response

    except Exception as e:
        logger.error(
            "OAuth callback processing failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}",
        )


@router.get("/logout")
async def logout(request: Request):
    """
    Logout endpoint.

    Clears the session cookie and redirects to home page.
    """
    logger.info("User logout requested")

    response = RedirectResponse(url="/", status_code=302)

    # Delete the session cookie (must match path and domain used when setting it)
    # Delete with domain specified for ai4joy.org
    if request.url.hostname == "ai4joy.org" or request.url.hostname.endswith(
        ".ai4joy.org"
    ):
        response.delete_cookie(key="session", path="/", domain="ai4joy.org")
    # Also delete without domain to clear any legacy cookies
    response.delete_cookie(key="session", path="/")

    logger.info("Session cleared - user logged out")

    return response


@router.get("/user")
async def get_current_user(request: Request):
    """
    Get current authenticated user information.

    This endpoint bypasses the OAuth middleware (so it doesn't redirect
    unauthenticated users) and directly checks the session cookie.

    Returns:
        User information including email, name, user ID, and tier, or
        authenticated=False if no valid session exists.
    """
    # Read session cookie directly since this endpoint bypasses middleware
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return {"authenticated": False, "user": None}

    try:
        # Validate and deserialize the session cookie
        session_data = session_middleware.serializer.loads(
            session_cookie, max_age=session_middleware.max_age
        )

        user_email = session_data.get("email")
        user_tier = "free"  # Default tier

        # Look up user tier from Firestore if enabled
        if user_email:
            from app.middleware.oauth_auth import should_use_firestore_auth

            if should_use_firestore_auth():
                from app.services.user_service import get_user_by_email

                try:
                    user_profile = await get_user_by_email(user_email)
                    if user_profile:
                        user_tier = user_profile.tier.value
                except Exception as tier_err:
                    logger.warning("Failed to fetch user tier", error=str(tier_err))

        return {
            "authenticated": True,
            "user": {
                "user_email": user_email,
                "user_id": session_data.get("sub"),
                "user_name": session_data.get("name"),
                "tier": user_tier,
            },
        }
    except Exception as e:
        logger.warning("Session validation failed", error=str(e))
        return {"authenticated": False, "user": None}


@router.get("/ws-token")
async def get_websocket_token(request: Request):
    """
    Get a token for WebSocket authentication.

    Since the session cookie is httponly (for security), JavaScript cannot
    read it directly. This endpoint returns the session token value that
    can be used for WebSocket authentication.

    Returns:
        Token for WebSocket auth, or 401 if not authenticated.
    """
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        # Validate session by attempting to deserialize (raises on invalid)
        session_middleware.serializer.loads(
            session_cookie, max_age=session_middleware.max_age
        )
        # Return the session cookie value as the token
        # The WebSocket handler will validate this same token
        return {"token": session_cookie}
    except Exception as e:
        logger.warning("WS token request failed - invalid session", error=str(e))
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Session expired")


async def check_user_authorization(email: str) -> bool:
    """Check if user is authorized to access the application.

    Uses Firestore if USE_FIRESTORE_AUTH is enabled, otherwise
    falls back to ALLOWED_USERS environment variable.

    Args:
        email: User email address

    Returns:
        True if user is authorized
    """
    from app.middleware.oauth_auth import (
        should_use_firestore_auth,
        validate_user_access,
        validate_user_access_legacy,
    )

    if should_use_firestore_auth():
        # Check Firestore users collection
        user_profile = await validate_user_access(email)
        return user_profile is not None
    else:
        # Legacy: Check ALLOWED_USERS env var
        return validate_user_access_legacy(email)


# =============================================================================
# Firebase Authentication Endpoints (Phase 1 - IQS-65)
# =============================================================================


@router.post("/firebase/token")
async def verify_firebase_token_endpoint(request: Request):
    """Verify Firebase ID token and create session cookie (AC-AUTH-04).

    This endpoint:
    1. Verifies the Firebase ID token from the client
    2. Checks email verification status (AC-AUTH-03)
    3. Gets or creates user in Firestore
    4. Creates a session cookie compatible with existing OAuth flow
    5. Handles migration for existing OAuth users (AC-AUTH-05)

    Request body:
        {
            "id_token": "eyJhbGc...",  // Firebase ID token from client
        }

    Returns:
        {
            "success": true,
            "user": {
                "email": "user@example.com",
                "user_id": "firebase_uid",
                "display_name": "User Name",
                "tier": "free"
            }
        }

    Sets session cookie in response (httponly, secure in production).

    Error responses:
        400: Invalid or expired token
        403: Email not verified
        500: Server error
    """
    from app.services.firebase_auth_service import (
        verify_firebase_token,
        get_or_create_user_from_firebase_token,
        create_session_data_from_firebase_token,
        FirebaseTokenExpiredError,
        FirebaseTokenInvalidError,
        FirebaseUserNotVerifiedError,
        FirebaseAuthError,
    )

    # Check if Firebase auth is enabled
    if not settings.firebase_auth_enabled:
        logger.warning("Firebase auth endpoint called but Firebase auth is disabled")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase authentication is not enabled",
        )

    try:
        # Parse request body
        body = await request.json()
        id_token = body.get("id_token")

        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="id_token is required",
            )

        logger.info("Processing Firebase token verification request")

        # Verify Firebase ID token
        decoded_token = await verify_firebase_token(id_token)

        # Get or create user (handles migration automatically)
        user_profile = await get_or_create_user_from_firebase_token(
            decoded_token,
            require_email_verification=settings.firebase_require_email_verification,
        )

        logger.info(
            "Firebase authentication successful",
            user_email=user_profile.email,
            user_id=user_profile.user_id,
            tier=user_profile.tier.value,
        )

        # Create session data compatible with OAuth format
        session_data = create_session_data_from_firebase_token(
            decoded_token, user_profile
        )

        # Create session cookie using existing middleware
        session_cookie = session_middleware.create_session_cookie(session_data)

        # Determine cookie settings based on environment
        is_production = request.url.hostname != "localhost"
        cookie_domain = None
        if request.url.hostname == "ai4joy.org" or request.url.hostname.endswith(
            ".ai4joy.org"
        ):
            cookie_domain = "ai4joy.org"

        # Create response with user info
        response = JSONResponse(
            content={
                "success": True,
                "user": {
                    "email": user_profile.email,
                    "user_id": user_profile.user_id,
                    "display_name": user_profile.display_name or "",
                    "tier": user_profile.tier.value,
                },
            }
        )

        # Set session cookie (matches OAuth flow)
        response.set_cookie(
            key="session",
            value=session_cookie,
            domain=cookie_domain,
            path="/",
            httponly=True,
            secure=is_production,
            samesite="lax",
            max_age=86400,  # 24 hours
        )

        logger.info(
            "Firebase session created successfully",
            user_email=user_profile.email,
            tier=user_profile.tier.value,
        )

        return response

    except FirebaseUserNotVerifiedError as e:
        logger.warning("Firebase user email not verified", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except (FirebaseTokenExpiredError, FirebaseTokenInvalidError) as e:
        logger.warning("Firebase token validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except FirebaseAuthError as e:
        logger.error("Firebase authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}",
        )

    except Exception as e:
        logger.error(
            "Unexpected error in Firebase token verification",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during authentication",
        )


# =============================================================================
# Multi-Factor Authentication Endpoints (Phase 2 - IQS-65)
# =============================================================================


@router.post("/mfa/enroll")
async def mfa_enroll(request: Request):
    """Start MFA enrollment process (AC-MFA-01, AC-MFA-02, AC-MFA-03, AC-MFA-04).

    This endpoint:
    1. Generates TOTP secret for the user
    2. Creates QR code for authenticator app scanning (min 200x200px)
    3. Generates 8 recovery codes
    4. Returns data for enrollment wizard

    Must be called by authenticated user who hasn't enrolled in MFA yet.

    Returns:
        {
            "secret": "JBSWY3DPEHPK3PXP",  // For manual entry if needed
            "qr_code_data_uri": "data:image/png;base64,...",  // QR code as data URI
            "recovery_codes": ["A3F9-K2H7", "B8D4-L9M3", ...],  // 8 codes to display
            "enrollment_pending": true
        }

    Error responses:
        401: Not authenticated
        409: MFA already enabled
        500: Server error
    """
    from app.services.mfa_service import (
        create_mfa_enrollment_session,
        hash_recovery_codes,
    )
    from app.services.user_service import get_user_by_email
    import base64

    # Check authentication
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        # Get user from session
        session_data = session_middleware.serializer.loads(
            session_cookie, max_age=session_middleware.max_age
        )
        user_email = session_data.get("email")
        user_id = session_data.get("sub")

        if not user_email or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session",
            )

        # Check if user already has MFA enabled
        user_profile = await get_user_by_email(user_email)
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        if user_profile.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="MFA is already enabled for this account",
            )

        # Generate MFA enrollment data
        secret, recovery_codes, qr_code_png = create_mfa_enrollment_session(
            user_id, user_email
        )

        # Convert QR code PNG to base64 data URI
        qr_code_b64 = base64.b64encode(qr_code_png).decode('utf-8')
        qr_code_data_uri = f"data:image/png;base64,{qr_code_b64}"

        # Store secret temporarily in session for verification
        # (will be moved to user profile after successful verification)
        from app.services.firestore_tool_data_service import get_firestore_client
        from datetime import datetime, timezone, timedelta

        client = get_firestore_client()
        collection = client.collection("mfa_enrollments")

        # Create temporary enrollment record (expires in 15 minutes)
        enrollment_data = {
            "user_id": user_id,
            "user_email": user_email,
            "secret": secret,
            "recovery_codes_hash": hash_recovery_codes(recovery_codes),
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
            "verified": False,
        }

        await collection.document(user_id).set(enrollment_data)

        logger.info(
            "MFA enrollment initiated",
            user_id=user_id,
            user_email=user_email,
        )

        return {
            "secret": secret,
            "qr_code_data_uri": qr_code_data_uri,
            "recovery_codes": recovery_codes,  # Display to user for saving
            "enrollment_pending": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA enrollment failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate MFA enrollment",
        )


@router.post("/mfa/verify-enrollment")
async def mfa_verify_enrollment(request: Request):
    """Complete MFA enrollment by verifying TOTP code (AC-MFA-05).

    After scanning QR code and saving recovery codes, user must:
    1. Confirm they saved recovery codes (checkbox)
    2. Enter TOTP code from authenticator app

    Request body:
        {
            "totp_code": "123456",
            "recovery_codes_confirmed": true
        }

    Returns:
        {
            "success": true,
            "mfa_enabled": true
        }

    Error responses:
        400: Invalid TOTP code or recovery codes not confirmed
        401: Not authenticated
        404: No pending enrollment found
        500: Server error
    """
    from app.services.mfa_service import verify_totp_code, InvalidTOTPCodeError
    from app.services.user_service import get_user_by_email
    from app.services.firestore_tool_data_service import get_firestore_client

    # Check authentication
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        # Parse request body
        body = await request.json()
        totp_code = body.get("totp_code")
        recovery_codes_confirmed = body.get("recovery_codes_confirmed", False)

        if not totp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="totp_code is required",
            )

        if not recovery_codes_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must confirm that you have saved your recovery codes",
            )

        # Get user from session
        session_data = session_middleware.serializer.loads(
            session_cookie, max_age=session_middleware.max_age
        )
        user_email = session_data.get("email")
        user_id = session_data.get("sub")

        if not user_email or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session",
            )

        # Get pending enrollment
        client = get_firestore_client()
        enrollment_doc = await client.collection("mfa_enrollments").document(user_id).get()

        if not enrollment_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No pending MFA enrollment found. Please start enrollment again.",
            )

        enrollment_data = enrollment_doc.to_dict()

        # Check expiration
        expires_at = enrollment_data.get("expires_at")
        if expires_at and datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA enrollment session has expired. Please start again.",
            )

        # Verify TOTP code
        secret = enrollment_data.get("secret")
        try:
            is_valid = verify_totp_code(secret, totp_code)
        except InvalidTOTPCodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid TOTP code. Please try again.",
            )

        # TOTP code verified! Enable MFA for user
        users_collection = client.collection(settings.firestore_users_collection)
        query = users_collection.where("email", "==", user_email)

        async for doc in query.stream():
            await users_collection.document(doc.id).update({
                "mfa_enabled": True,
                "mfa_secret": secret,
                "mfa_enrolled_at": datetime.now(timezone.utc),
                "recovery_codes_hash": enrollment_data.get("recovery_codes_hash", []),
            })

            logger.info(
                "MFA enrollment completed",
                user_id=user_id,
                user_email=user_email,
            )

        # Delete temporary enrollment record
        await client.collection("mfa_enrollments").document(user_id).delete()

        return {
            "success": True,
            "mfa_enabled": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete MFA enrollment",
        )


@router.post("/mfa/verify")
async def mfa_verify(request: Request):
    """Verify TOTP code during login (AC-MFA-06).

    After user signs in with email/password or Google, if they have
    MFA enabled, they must provide a TOTP code to complete authentication.

    Request body:
        {
            "totp_code": "123456"
        }

    Returns:
        {
            "success": true,
            "mfa_verified": true
        }

    Sets mfa_verified=true in session cookie.

    Error responses:
        400: Invalid TOTP code
        401: Not authenticated
        404: User not found or MFA not enabled
        500: Server error
    """
    from app.services.mfa_service import verify_totp_code, InvalidTOTPCodeError
    from app.services.user_service import get_user_by_email

    # Check authentication
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        # Parse request body
        body = await request.json()
        totp_code = body.get("totp_code")

        if not totp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="totp_code is required",
            )

        # Get user from session
        session_data = session_middleware.serializer.loads(
            session_cookie, max_age=session_middleware.max_age
        )
        user_email = session_data.get("email")

        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session",
            )

        # Get user profile
        user_profile = await get_user_by_email(user_email)
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        if not user_profile.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is not enabled for this account",
            )

        # Verify TOTP code
        try:
            is_valid = verify_totp_code(user_profile.mfa_secret, totp_code)
        except InvalidTOTPCodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid TOTP code. Please try again.",
            )

        # TOTP verified! Update session to mark MFA as verified
        session_data["mfa_verified"] = True
        updated_session_cookie = session_middleware.create_session_cookie(session_data)

        # Create response
        response = JSONResponse(
            content={
                "success": True,
                "mfa_verified": True,
            }
        )

        # Update session cookie
        is_production = request.url.hostname != "localhost"
        cookie_domain = None
        if request.url.hostname == "ai4joy.org" or request.url.hostname.endswith(
            ".ai4joy.org"
        ):
            cookie_domain = "ai4joy.org"

        response.set_cookie(
            key="session",
            value=updated_session_cookie,
            domain=cookie_domain,
            path="/",
            httponly=True,
            secure=is_production,
            samesite="lax",
            max_age=86400,
        )

        logger.info(
            "MFA verification successful",
            user_email=user_email,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify MFA code",
        )


@router.post("/mfa/verify-recovery")
async def mfa_verify_recovery(request: Request):
    """Verify recovery code for MFA bypass (AC-MFA-07).

    If user loses access to authenticator app, they can use a recovery code.
    Recovery codes are single-use and will be consumed after successful verification.

    Request body:
        {
            "recovery_code": "A3F9-K2H7"
        }

    Returns:
        {
            "success": true,
            "mfa_verified": true,
            "remaining_recovery_codes": 7
        }

    Error responses:
        400: Invalid recovery code
        401: Not authenticated
        404: User not found or MFA not enabled
        500: Server error
    """
    from app.services.mfa_service import (
        consume_recovery_code,
        InvalidRecoveryCodeError,
    )
    from app.services.user_service import get_user_by_email
    from app.services.firestore_tool_data_service import get_firestore_client

    # Check authentication
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        # Parse request body
        body = await request.json()
        recovery_code = body.get("recovery_code")

        if not recovery_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recovery_code is required",
            )

        # Get user from session
        session_data = session_middleware.serializer.loads(
            session_cookie, max_age=session_middleware.max_age
        )
        user_email = session_data.get("email")

        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session",
            )

        # Get user profile
        user_profile = await get_user_by_email(user_email)
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        if not user_profile.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is not enabled for this account",
            )

        # Verify and consume recovery code
        try:
            updated_codes = consume_recovery_code(
                recovery_code, user_profile.recovery_codes_hash
            )
        except InvalidRecoveryCodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        if updated_codes is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid recovery code. Please try again or use your authenticator app.",
            )

        # Recovery code verified! Update user's recovery codes (remove used one)
        client = get_firestore_client()
        users_collection = client.collection(settings.firestore_users_collection)
        query = users_collection.where("email", "==", user_email)

        async for doc in query.stream():
            await users_collection.document(doc.id).update({
                "recovery_codes_hash": updated_codes,
            })

        # Update session to mark MFA as verified
        session_data["mfa_verified"] = True
        updated_session_cookie = session_middleware.create_session_cookie(session_data)

        # Create response
        response = JSONResponse(
            content={
                "success": True,
                "mfa_verified": True,
                "remaining_recovery_codes": len(updated_codes),
            }
        )

        # Update session cookie
        is_production = request.url.hostname != "localhost"
        cookie_domain = None
        if request.url.hostname == "ai4joy.org" or request.url.hostname.endswith(
            ".ai4joy.org"
        ):
            cookie_domain = "ai4joy.org"

        response.set_cookie(
            key="session",
            value=updated_session_cookie,
            domain=cookie_domain,
            path="/",
            httponly=True,
            secure=is_production,
            samesite="lax",
            max_age=86400,
        )

        logger.info(
            "MFA recovery code verification successful",
            user_email=user_email,
            remaining_codes=len(updated_codes),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Recovery code verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify recovery code",
        )


@router.get("/mfa/status")
async def mfa_status(request: Request):
    """Get MFA status for current user.

    Returns:
        {
            "mfa_enabled": true,
            "mfa_enrolled_at": "2025-01-15T12:00:00Z",
            "recovery_codes_count": 7,
            "mfa_verified_in_session": true
        }

    Error responses:
        401: Not authenticated
        404: User not found
        500: Server error
    """
    from app.services.user_service import get_user_by_email

    # Check authentication
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        # Get user from session
        session_data = session_middleware.serializer.loads(
            session_cookie, max_age=session_middleware.max_age
        )
        user_email = session_data.get("email")

        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session",
            )

        # Get user profile
        user_profile = await get_user_by_email(user_email)
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        # Check if MFA is verified in current session
        mfa_verified_in_session = session_data.get("mfa_verified", False)

        return {
            "mfa_enabled": user_profile.mfa_enabled,
            "mfa_enrolled_at": (
                user_profile.mfa_enrolled_at.isoformat()
                if user_profile.mfa_enrolled_at
                else None
            ),
            "recovery_codes_count": len(user_profile.recovery_codes_hash or []),
            "mfa_verified_in_session": mfa_verified_in_session,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get MFA status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get MFA status",
        )
