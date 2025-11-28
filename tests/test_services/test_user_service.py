"""
Tests for User Service - TDD Phase 3
Tests for Firestore user CRUD operations

Test Cases:
- TC-SVC-01: Get user by email (exists)
- TC-SVC-02: Get user by email (not exists)
- TC-SVC-03: Create new user
- TC-SVC-04: Update user tier
- TC-SVC-05: Update last login timestamp
- TC-SVC-06: List all users
- TC-SVC-07: List users by tier
- TC-SVC-08: Delete user
- TC-SVC-09: Migrate from ALLOWED_USERS env var
- TC-SVC-10: Increment audio usage
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch


async def async_generator(items: List):
    """Create an async generator from a list."""
    for item in items:
        yield item


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client for unit tests.

    The Firestore AsyncClient has sync methods for collection/where
    but async generators for stream().
    """
    with patch("app.services.user_service.get_firestore_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def sample_user_doc() -> Dict[str, Any]:
    """Sample Firestore user document."""
    return {
        "email": "test@example.com",
        "display_name": "Test User",
        "tier": "premium",
        "tier_assigned_at": datetime.now(timezone.utc),
        "tier_expires_at": None,
        "audio_usage_seconds": 0,
        "audio_usage_reset_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "last_login_at": datetime.now(timezone.utc),
        "created_by": "admin@example.com",
    }


class TestGetUserByEmail:
    """Tests for get_user_by_email function."""

    @pytest.mark.asyncio
    async def test_tc_svc_01_get_user_exists(self, mock_firestore_client, sample_user_doc):
        """TC-SVC-01: Get user by email when user exists."""
        from app.services.user_service import get_user_by_email
        from app.models.user import UserProfile

        # Mock query result
        mock_doc = MagicMock()
        mock_doc.id = "user-123"
        mock_doc.to_dict.return_value = sample_user_doc
        mock_doc.exists = True

        mock_query = MagicMock()
        mock_query.stream.return_value = async_generator([mock_doc])

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_firestore_client.collection.return_value = mock_collection

        result = await get_user_by_email("test@example.com")

        assert result is not None
        assert isinstance(result, UserProfile)
        assert result.email == "test@example.com"
        assert result.tier.value == "premium"

    @pytest.mark.asyncio
    async def test_tc_svc_02_get_user_not_exists(self, mock_firestore_client):
        """TC-SVC-02: Get user by email when user does not exist."""
        from app.services.user_service import get_user_by_email

        # Mock empty query result
        mock_query = MagicMock()
        mock_query.stream.return_value = async_generator([])

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_firestore_client.collection.return_value = mock_collection

        result = await get_user_by_email("nonexistent@example.com")

        assert result is None


class TestCreateUser:
    """Tests for create_user function."""

    @pytest.mark.asyncio
    async def test_tc_svc_03_create_user(self, mock_firestore_client):
        """TC-SVC-03: Create new user."""
        from app.services.user_service import create_user
        from app.models.user import UserProfile, UserTier

        # Mock empty query (user doesn't exist)
        mock_query = MagicMock()
        mock_query.stream.return_value = async_generator([])

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new-user-123"

        async def mock_add(*args, **kwargs):
            return (None, mock_doc_ref)

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_collection.add = mock_add
        mock_firestore_client.collection.return_value = mock_collection

        result = await create_user(
            email="newuser@example.com",
            tier=UserTier.REGULAR,
            display_name="New User",
            created_by="admin@example.com",
        )

        assert result is not None
        assert isinstance(result, UserProfile)
        assert result.email == "newuser@example.com"
        assert result.tier == UserTier.REGULAR
        assert result.display_name == "New User"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, mock_firestore_client, sample_user_doc):
        """Test that creating user with duplicate email fails."""
        from app.services.user_service import create_user, UserAlreadyExistsError
        from app.models.user import UserTier

        # Mock that user already exists
        mock_doc = MagicMock()
        mock_doc.id = "existing-user"
        mock_doc.to_dict.return_value = sample_user_doc
        mock_doc.exists = True

        mock_query = MagicMock()
        mock_query.stream.return_value = async_generator([mock_doc])

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_firestore_client.collection.return_value = mock_collection

        with pytest.raises(UserAlreadyExistsError):
            await create_user(
                email="test@example.com",  # Already exists
                tier=UserTier.REGULAR,
                created_by="admin@example.com",
            )


class TestUpdateUserTier:
    """Tests for update_user_tier function."""

    @pytest.mark.asyncio
    async def test_tc_svc_04_update_user_tier(self, mock_firestore_client, sample_user_doc):
        """TC-SVC-04: Update user tier."""
        from app.services.user_service import update_user_tier
        from app.models.user import UserTier

        # Mock existing user - need to return async generator each time stream() is called
        mock_doc = MagicMock()
        mock_doc.id = "user-123"
        mock_doc.to_dict.return_value = sample_user_doc

        # Each call to stream() needs to return a new async generator
        def make_stream():
            return async_generator([mock_doc])

        mock_query = MagicMock()
        mock_query.stream.side_effect = make_stream

        async def mock_update(*args, **kwargs):
            return None

        mock_doc_ref = MagicMock()
        mock_doc_ref.update = mock_update

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore_client.collection.return_value = mock_collection

        result = await update_user_tier("test@example.com", UserTier.PREMIUM)

        assert result is True

    @pytest.mark.asyncio
    async def test_update_user_tier_not_found(self, mock_firestore_client):
        """Test updating tier for non-existent user."""
        from app.services.user_service import update_user_tier, UserNotFoundError
        from app.models.user import UserTier

        # Mock user not found
        mock_query = MagicMock()
        mock_query.stream.return_value = async_generator([])

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_firestore_client.collection.return_value = mock_collection

        with pytest.raises(UserNotFoundError):
            await update_user_tier("nonexistent@example.com", UserTier.PREMIUM)


class TestUpdateLastLogin:
    """Tests for update_last_login function."""

    @pytest.mark.asyncio
    async def test_tc_svc_05_update_last_login(self, mock_firestore_client, sample_user_doc):
        """TC-SVC-05: Update last login timestamp."""
        from app.services.user_service import update_last_login

        # Mock existing user
        mock_doc = MagicMock()
        mock_doc.id = "user-123"
        mock_doc.to_dict.return_value = sample_user_doc

        mock_query = MagicMock()
        mock_query.stream.return_value = async_generator([mock_doc])

        update_called = []

        async def mock_update(*args, **kwargs):
            update_called.append(True)
            return None

        mock_doc_ref = MagicMock()
        mock_doc_ref.update = mock_update

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore_client.collection.return_value = mock_collection

        await update_last_login("test@example.com")

        assert len(update_called) == 1


class TestListUsers:
    """Tests for list_users function."""

    @pytest.mark.asyncio
    async def test_tc_svc_06_list_all_users(self, mock_firestore_client, sample_user_doc):
        """TC-SVC-06: List all users."""
        from app.services.user_service import list_users
        from app.models.user import UserProfile

        # Mock multiple users
        mock_doc1 = MagicMock()
        mock_doc1.id = "user-1"
        mock_doc1.to_dict.return_value = sample_user_doc

        mock_doc2 = MagicMock()
        mock_doc2.id = "user-2"
        user2_doc = sample_user_doc.copy()
        user2_doc["email"] = "user2@example.com"
        user2_doc["tier"] = "regular"
        mock_doc2.to_dict.return_value = user2_doc

        mock_collection = MagicMock()
        mock_collection.stream.return_value = async_generator([mock_doc1, mock_doc2])
        mock_firestore_client.collection.return_value = mock_collection

        result = await list_users()

        assert len(result) == 2
        assert all(isinstance(u, UserProfile) for u in result)

    @pytest.mark.asyncio
    async def test_tc_svc_07_list_users_by_tier(self, mock_firestore_client, sample_user_doc):
        """TC-SVC-07: List users by tier."""
        from app.services.user_service import list_users
        from app.models.user import UserProfile, UserTier

        # Mock premium users only
        mock_doc = MagicMock()
        mock_doc.id = "user-1"
        mock_doc.to_dict.return_value = sample_user_doc

        mock_query = MagicMock()
        mock_query.stream.return_value = async_generator([mock_doc])

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_firestore_client.collection.return_value = mock_collection

        result = await list_users(tier=UserTier.PREMIUM)

        assert len(result) >= 1
        assert all(u.tier == UserTier.PREMIUM for u in result)


class TestDeleteUser:
    """Tests for delete_user function."""

    @pytest.mark.asyncio
    async def test_tc_svc_08_delete_user(self, mock_firestore_client, sample_user_doc):
        """TC-SVC-08: Delete user."""
        from app.services.user_service import delete_user

        # Mock existing user
        mock_doc = MagicMock()
        mock_doc.id = "user-123"
        mock_doc.to_dict.return_value = sample_user_doc

        # Each call to stream() needs to return a new async generator
        def make_stream():
            return async_generator([mock_doc])

        mock_query = MagicMock()
        mock_query.stream.side_effect = make_stream

        delete_called = []

        async def mock_delete(*args, **kwargs):
            delete_called.append(True)
            return None

        mock_doc_ref = MagicMock()
        mock_doc_ref.delete = mock_delete

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore_client.collection.return_value = mock_collection

        result = await delete_user("test@example.com")

        assert result is True
        assert len(delete_called) == 1


class TestMigrateFromEnv:
    """Tests for migrate_from_allowed_users function."""

    @pytest.mark.asyncio
    async def test_tc_svc_09_migrate_from_env(self, mock_firestore_client):
        """TC-SVC-09: Migrate from ALLOWED_USERS env var."""
        from app.services.user_service import migrate_from_allowed_users
        from app.models.user import UserTier

        # Mock that no users exist yet
        mock_query = MagicMock()
        mock_query.stream.return_value = async_generator([])

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "new-user"

        async def mock_add(*args, **kwargs):
            return (None, mock_doc_ref)

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_collection.add = mock_add
        mock_firestore_client.collection.return_value = mock_collection

        with patch("app.services.user_service.settings") as mock_settings:
            mock_settings.allowed_users_list = [
                "user1@example.com",
                "user2@example.com",
            ]

            result = await migrate_from_allowed_users(default_tier=UserTier.REGULAR)

            assert result["migrated"] == 2
            assert result["skipped"] == 0


class TestAudioUsage:
    """Tests for audio usage tracking."""

    @pytest.mark.asyncio
    async def test_tc_svc_10_increment_audio_usage(self, mock_firestore_client, sample_user_doc):
        """TC-SVC-10: Increment audio usage seconds."""
        from app.services.user_service import increment_audio_usage

        # Mock existing user
        mock_doc = MagicMock()
        mock_doc.id = "user-123"
        mock_doc.to_dict.return_value = sample_user_doc

        mock_query = MagicMock()
        mock_query.stream.return_value = async_generator([mock_doc])

        update_called = []

        async def mock_update(*args, **kwargs):
            update_called.append(True)
            return None

        mock_doc_ref = MagicMock()
        mock_doc_ref.update = mock_update

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_collection.document.return_value = mock_doc_ref
        mock_firestore_client.collection.return_value = mock_collection

        await increment_audio_usage("test@example.com", seconds=60)

        assert len(update_called) == 1

    @pytest.mark.asyncio
    async def test_get_audio_usage(self, mock_firestore_client, sample_user_doc):
        """Test getting current audio usage."""
        from app.services.user_service import get_audio_usage

        sample_user_doc["audio_usage_seconds"] = 1234

        mock_doc = MagicMock()
        mock_doc.id = "user-123"
        mock_doc.to_dict.return_value = sample_user_doc

        mock_query = MagicMock()
        mock_query.stream.return_value = async_generator([mock_doc])

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_query
        mock_firestore_client.collection.return_value = mock_collection

        result = await get_audio_usage("test@example.com")

        assert result == 1234
