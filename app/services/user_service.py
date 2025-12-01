"""User Service - Firestore User CRUD Operations

This service provides async Firestore operations for user management including:
- User lookup by email
- User creation with tier assignment
- Tier updates
- Audio usage tracking
- Migration from ALLOWED_USERS environment variable
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict

from app.config import get_settings
from app.models.user import UserProfile, UserTier
from app.services.firestore_tool_data_service import get_firestore_client
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Collection name for users
USERS_COLLECTION = "users"


class UserNotFoundError(Exception):
    """Raised when a user is not found."""

    pass


class UserAlreadyExistsError(Exception):
    """Raised when trying to create a user that already exists."""

    pass


async def get_user_by_email(email: str) -> Optional[UserProfile]:
    """Get user by email address.

    Args:
        email: User email address

    Returns:
        UserProfile if found, None otherwise
    """
    client = get_firestore_client()
    collection = client.collection(USERS_COLLECTION)
    query = collection.where("email", "==", email)

    async for doc in query.stream():
        doc_data = doc.to_dict()
        if doc_data:
            doc_data["user_id"] = doc_data.get("user_id", doc.id)
            logger.debug("User found by email", email=email)
            return UserProfile.from_firestore(doc_data)

    logger.debug("User not found by email", email=email)
    return None


async def get_user_by_id(user_id: str) -> Optional[UserProfile]:
    """Get user by user ID.

    Args:
        user_id: User ID

    Returns:
        UserProfile if found, None otherwise
    """
    client = get_firestore_client()
    collection = client.collection(USERS_COLLECTION)
    query = collection.where("user_id", "==", user_id)

    async for doc in query.stream():
        doc_data = doc.to_dict()
        if doc_data:
            doc_data["user_id"] = doc_data.get("user_id", doc.id)
            logger.debug("User found by ID", user_id=user_id)
            return UserProfile.from_firestore(doc_data)

    logger.debug("User not found by ID", user_id=user_id)
    return None


async def create_user(
    email: str,
    tier: UserTier,
    display_name: Optional[str] = None,
    user_id: Optional[str] = None,
    created_by: Optional[str] = None,
) -> UserProfile:
    """Create a new user.

    Args:
        email: User email address
        tier: User tier level
        display_name: Optional display name
        user_id: Optional user ID (generated if not provided)
        created_by: Admin email who created the user

    Returns:
        Created UserProfile

    Raises:
        UserAlreadyExistsError: If user with email already exists
    """
    # Check if user already exists
    existing = await get_user_by_email(email)
    if existing:
        raise UserAlreadyExistsError(f"User with email {email} already exists")

    client = get_firestore_client()
    collection = client.collection(USERS_COLLECTION)

    now = datetime.now(timezone.utc)
    profile = UserProfile(
        user_id=user_id or f"provisioned-{email.replace('@', '-').replace('.', '-')}",
        email=email,
        tier=tier,
        display_name=display_name,
        tier_assigned_at=now,
        audio_usage_seconds=0,
        audio_usage_reset_at=now,
        created_at=now,
        created_by=created_by,
    )

    # Add to Firestore
    _, doc_ref = await collection.add(profile.to_dict())
    logger.info(
        "User created",
        email=email,
        tier=tier.value,
        doc_id=doc_ref.id,
        created_by=created_by,
    )

    return profile


async def update_user_tier(email: str, tier: UserTier) -> bool:
    """Update user tier.

    Args:
        email: User email address
        tier: New tier level

    Returns:
        True if updated successfully

    Raises:
        UserNotFoundError: If user not found
    """
    user = await get_user_by_email(email)
    if not user:
        raise UserNotFoundError(f"User with email {email} not found")

    client = get_firestore_client()
    collection = client.collection(USERS_COLLECTION)
    query = collection.where("email", "==", email)

    async for doc in query.stream():
        await collection.document(doc.id).update(
            {
                "tier": tier.value,
                "tier_assigned_at": datetime.now(timezone.utc),
            }
        )
        logger.info("User tier updated", email=email, new_tier=tier.value)
        return True

    return False


async def update_last_login(email: str) -> None:
    """Update user's last login timestamp.

    Args:
        email: User email address
    """
    client = get_firestore_client()
    collection = client.collection(USERS_COLLECTION)
    query = collection.where("email", "==", email)

    async for doc in query.stream():
        await collection.document(doc.id).update(
            {
                "last_login_at": datetime.now(timezone.utc),
            }
        )
        logger.debug("Last login updated", email=email)
        return


async def list_users(tier: Optional[UserTier] = None) -> List[UserProfile]:
    """List all users, optionally filtered by tier.

    Args:
        tier: Optional tier to filter by

    Returns:
        List of UserProfile objects
    """
    client = get_firestore_client()
    collection = client.collection(USERS_COLLECTION)

    if tier:
        query = collection.where("tier", "==", tier.value)
    else:
        query = collection

    users: List[UserProfile] = []
    async for doc in query.stream():
        doc_data = doc.to_dict()
        if doc_data:
            doc_data["user_id"] = doc_data.get("user_id", doc.id)
            users.append(UserProfile.from_firestore(doc_data))

    logger.info("Users listed", count=len(users), tier=tier.value if tier else "all")
    return users


async def delete_user(email: str) -> bool:
    """Delete a user.

    Args:
        email: User email address

    Returns:
        True if deleted successfully

    Raises:
        UserNotFoundError: If user not found
    """
    user = await get_user_by_email(email)
    if not user:
        raise UserNotFoundError(f"User with email {email} not found")

    client = get_firestore_client()
    collection = client.collection(USERS_COLLECTION)
    query = collection.where("email", "==", email)

    async for doc in query.stream():
        await collection.document(doc.id).delete()
        logger.info("User deleted", email=email)
        return True

    return False


async def increment_audio_usage(email: str, seconds: int) -> None:
    """Increment user's audio usage.

    Args:
        email: User email address
        seconds: Seconds to add to usage
    """
    client = get_firestore_client()
    collection = client.collection(USERS_COLLECTION)
    query = collection.where("email", "==", email)

    async for doc in query.stream():
        doc_data = doc.to_dict()
        current_usage = doc_data.get("audio_usage_seconds", 0) if doc_data else 0

        await collection.document(doc.id).update(
            {
                "audio_usage_seconds": current_usage + seconds,
            }
        )
        logger.debug(
            "Audio usage incremented",
            email=email,
            added=seconds,
            new_total=current_usage + seconds,
        )
        return


async def get_audio_usage(email: str) -> int:
    """Get user's current audio usage in seconds.

    Args:
        email: User email address

    Returns:
        Current audio usage in seconds
    """
    user = await get_user_by_email(email)
    if user:
        return user.audio_usage_seconds
    return 0


async def reset_audio_usage(email: str) -> None:
    """Reset user's audio usage for new period.

    Args:
        email: User email address
    """
    client = get_firestore_client()
    collection = client.collection(USERS_COLLECTION)
    query = collection.where("email", "==", email)

    async for doc in query.stream():
        await collection.document(doc.id).update(
            {
                "audio_usage_seconds": 0,
                "audio_usage_reset_at": datetime.now(timezone.utc),
            }
        )
        logger.info("Audio usage reset", email=email)
        return


async def migrate_from_allowed_users(
    default_tier: UserTier = UserTier.REGULAR,
    created_by: str = "migration-script",
) -> Dict[str, int]:
    """Migrate users from ALLOWED_USERS environment variable.

    Args:
        default_tier: Tier to assign to migrated users
        created_by: Attribution for migration

    Returns:
        Dictionary with migration stats: {migrated: int, skipped: int}
    """
    allowed_users = settings.allowed_users_list

    stats = {"migrated": 0, "skipped": 0, "errors": 0}

    for email in allowed_users:
        try:
            existing = await get_user_by_email(email)
            if existing:
                logger.debug("User already exists, skipping", email=email)
                stats["skipped"] += 1
                continue

            await create_user(
                email=email,
                tier=default_tier,
                created_by=created_by,
            )
            stats["migrated"] += 1
            logger.info("User migrated", email=email, tier=default_tier.value)

        except Exception as e:
            logger.error("Migration error", email=email, error=str(e))
            stats["errors"] += 1

    logger.info(
        "Migration complete",
        migrated=stats["migrated"],
        skipped=stats["skipped"],
        errors=stats["errors"],
    )
    return stats
