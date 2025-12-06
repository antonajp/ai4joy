"""Firebase Authentication Service

This service provides Firebase ID token verification and session management
for the Firebase Authentication migration (IQS-65 Phase 1).

Features:
- Firebase ID token verification using firebase-admin SDK
- Automatic user provisioning for new Firebase users
- Migration support for existing Google OAuth users
- Integration with existing session cookie system
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from firebase_admin import auth as firebase_auth
from firebase_admin.exceptions import FirebaseError

from app.config import get_settings
from app.utils.logger import get_logger
from app.models.user import UserProfile, UserTier
from app.services.user_service import (
    get_user_by_email,
    get_user_by_id,
    create_user,
)

logger = get_logger(__name__)
settings = get_settings()


class FirebaseAuthError(Exception):
    """Base exception for Firebase authentication errors."""

    pass


class FirebaseTokenExpiredError(FirebaseAuthError):
    """Raised when Firebase ID token has expired."""

    pass


class FirebaseTokenInvalidError(FirebaseAuthError):
    """Raised when Firebase ID token is invalid."""

    pass


class FirebaseUserNotVerifiedError(FirebaseAuthError):
    """Raised when user's email is not verified."""

    pass


async def verify_firebase_token(id_token: str) -> Dict[str, Any]:
    """Verify Firebase ID token and return decoded token.

    Args:
        id_token: Firebase ID token from client

    Returns:
        Decoded token dictionary containing user claims

    Raises:
        FirebaseTokenExpiredError: If token has expired
        FirebaseTokenInvalidError: If token is invalid
        FirebaseAuthError: For other Firebase errors

    Token structure:
        {
            "uid": "firebase_user_id",
            "email": "user@example.com",
            "email_verified": True,
            "name": "User Name",
            "picture": "https://...",
            "iss": "https://securetoken.google.com/project-id",
            "aud": "project-id",
            "auth_time": 1234567890,
            "iat": 1234567890,
            "exp": 1234571490,  # Expires after 1 hour
            "firebase": {
                "identities": {
                    "google.com": ["google_user_id"],
                    "email": ["user@example.com"]
                },
                "sign_in_provider": "google.com"  # or "password"
            }
        }
    """
    try:
        # Verify the ID token and decode it
        # This also checks:
        # - Token signature is valid
        # - Token has not expired
        # - Token audience matches our project
        # - Token issuer is correct
        decoded_token = firebase_auth.verify_id_token(id_token)

        logger.info(
            "Firebase token verified successfully",
            uid=decoded_token.get("uid"),
            email=decoded_token.get("email"),
            provider=decoded_token.get("firebase", {}).get("sign_in_provider"),
        )

        return decoded_token

    except firebase_auth.ExpiredIdTokenError:
        logger.warning("Firebase token expired")
        raise FirebaseTokenExpiredError("Firebase ID token has expired")

    except firebase_auth.RevokedIdTokenError:
        logger.warning("Firebase token revoked")
        raise FirebaseTokenInvalidError("Firebase ID token has been revoked")

    except firebase_auth.InvalidIdTokenError as e:
        logger.warning("Invalid Firebase token", error=str(e))
        raise FirebaseTokenInvalidError(f"Invalid Firebase ID token: {str(e)}")

    except FirebaseError as e:
        logger.error("Firebase authentication error", error=str(e))
        raise FirebaseAuthError(f"Firebase authentication failed: {str(e)}")

    except Exception as e:
        logger.error("Unexpected error verifying Firebase token", error=str(e))
        raise FirebaseAuthError(f"Unexpected authentication error: {str(e)}")


async def get_or_create_user_from_firebase_token(
    decoded_token: Dict[str, Any],
    require_email_verification: bool = True,
) -> UserProfile:
    """Get existing user or create new user from Firebase token.

    This function handles:
    1. Email verification check (if required)
    2. Looking up existing user by Firebase UID or email
    3. Creating new user with default 'free' tier
    4. Migrating existing OAuth users to Firebase

    Args:
        decoded_token: Decoded Firebase ID token
        require_email_verification: If True, reject unverified emails

    Returns:
        UserProfile for the authenticated user

    Raises:
        FirebaseUserNotVerifiedError: If email is not verified
    """
    firebase_uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    email_verified = decoded_token.get("email_verified", False)
    display_name = decoded_token.get("name")
    sign_in_provider = decoded_token.get("firebase", {}).get("sign_in_provider")

    # Enforce email verification (AC-AUTH-03)
    if require_email_verification and not email_verified:
        logger.warning(
            "Email not verified",
            email=email,
            firebase_uid=firebase_uid,
        )
        raise FirebaseUserNotVerifiedError(
            "Email address must be verified before accessing the application. "
            "Please check your email for a verification link."
        )

    # Try to find existing user by Firebase UID first
    existing_user = await get_user_by_id(firebase_uid)

    if existing_user:
        logger.info(
            "Existing user found by Firebase UID",
            firebase_uid=firebase_uid,
            email=email,
            tier=existing_user.tier.value,
        )
        return existing_user

    # Try to find existing user by email (migration case - AC-AUTH-05)
    existing_user_by_email = await get_user_by_email(email)

    if existing_user_by_email:
        logger.info(
            "Migrating existing OAuth user to Firebase",
            email=email,
            old_user_id=existing_user_by_email.user_id,
            firebase_uid=firebase_uid,
        )

        # Update the existing user's user_id to Firebase UID
        # This maintains their tier and history while linking to Firebase
        from app.services.firestore_tool_data_service import get_firestore_client

        client = get_firestore_client()
        collection = client.collection(settings.firestore_users_collection)
        query = collection.where("email", "==", email)

        async for doc in query.stream():
            await collection.document(doc.id).update(
                {
                    "user_id": firebase_uid,
                    "firebase_migrated_at": datetime.now(timezone.utc),
                    "firebase_sign_in_provider": sign_in_provider,
                    "last_login_at": datetime.now(timezone.utc),
                }
            )

            logger.info(
                "User migration complete",
                email=email,
                firebase_uid=firebase_uid,
            )

            # Return updated user
            existing_user_by_email.user_id = firebase_uid
            return existing_user_by_email

    # Create new user with 'freemium' tier (AC-PROV-01, AC-PROV-02)
    # Phase 3 - IQS-65: Auto-provision freemium tier for new users
    logger.info(
        "Creating new user from Firebase token with FREEMIUM tier",
        firebase_uid=firebase_uid,
        email=email,
        provider=sign_in_provider,
    )

    new_user = await create_user(
        email=email,
        tier=UserTier.FREEMIUM,  # Changed from FREE to FREEMIUM
        display_name=display_name,
        user_id=firebase_uid,
        created_by="firebase-auth-service",
    )

    logger.info(
        "New Firebase user created",
        firebase_uid=firebase_uid,
        email=email,
        tier=new_user.tier.value,
    )

    return new_user


def create_session_data_from_firebase_token(
    decoded_token: Dict[str, Any],
    user_profile: UserProfile,
) -> Dict[str, Any]:
    """Create session data compatible with existing OAuth session format.

    This ensures backward compatibility with existing session cookie
    structure used by OAuthSessionMiddleware.

    Args:
        decoded_token: Decoded Firebase ID token
        user_profile: User profile from Firestore

    Returns:
        Session data dictionary compatible with OAuth session format
    """
    return {
        "sub": user_profile.user_id,  # Firebase UID
        "email": user_profile.email,
        "name": user_profile.display_name or decoded_token.get("name", ""),
        "picture": decoded_token.get("picture", ""),
        "email_verified": decoded_token.get("email_verified", False),
        # Additional metadata for debugging
        "auth_provider": "firebase",
        "firebase_sign_in_provider": decoded_token.get("firebase", {}).get(
            "sign_in_provider"
        ),
        "created_at": int(datetime.now(timezone.utc).timestamp()),
    }


async def refresh_firebase_token(refresh_token: str) -> str:
    """Refresh Firebase ID token using refresh token.

    Note: This is typically handled client-side by Firebase SDK.
    This function is here for completeness but may not be used.

    Args:
        refresh_token: Firebase refresh token

    Returns:
        New Firebase ID token

    Raises:
        FirebaseAuthError: If refresh fails
    """
    # Firebase Admin SDK doesn't directly support refresh tokens
    # This must be handled client-side via Firebase REST API
    raise NotImplementedError(
        "Token refresh should be handled client-side using Firebase SDK"
    )
