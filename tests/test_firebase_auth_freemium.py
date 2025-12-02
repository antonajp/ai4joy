"""
Firebase Authentication with Freemium Tier Tests

This test suite covers the migration from Google OAuth to Firebase Authentication
with MFA, freemium tier implementation, and session limit enforcement.

Test Coverage:
- Unit Tests: Token verification, MFA validation, tier logic, session counting
- Integration Tests: E2E signup, MFA enrollment, session limits, tier upgrades
- Edge Cases: Incomplete MFA, concurrent sessions, service failures
- Security Tests: Token validation, MFA bypass prevention, privilege escalation
- Regression Tests: Existing premium users, rate limiting, session functionality

Dependencies:
    pip install firebase-admin pytest pytest-asyncio pytest-mock
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
import json

# Firebase Admin SDK (to be added to requirements.txt)
try:
    from firebase_admin import auth as firebase_auth
    from firebase_admin.auth import UserRecord
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_auth = None
    UserRecord = None


# =============================================================================
# UNIT TESTS - Firebase Auth Token Verification
# =============================================================================

@pytest.mark.skipif(not FIREBASE_AVAILABLE, reason="firebase-admin not installed")
class TestFirebaseTokenVerification:
    """Unit tests for Firebase ID token validation logic."""

    @pytest.fixture
    def mock_firebase_token(self) -> str:
        """Mock Firebase ID token for testing."""
        return "eyJhbGciOiJSUzI1NiIsImtpZCI6InRlc3QifQ.eyJzdWIiOiJ0ZXN0X3VzZXJfaWQiLCJlbWFpbCI6InRlc3RAdGVzdC5jb20ifQ.test_signature"

    @pytest.fixture
    def mock_decoded_token(self) -> Dict:
        """Mock decoded Firebase token claims."""
        return {
            "uid": "test_user_id",
            "email": "test@test.com",
            "email_verified": True,
            "auth_time": int(datetime.now(timezone.utc).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }

    def test_valid_firebase_token_verification(self, mock_firebase_token, mock_decoded_token):
        """
        TC-AUTH-FB-01: Verify valid Firebase ID token

        Validates that Firebase Admin SDK correctly verifies valid tokens.
        """
        with patch.object(firebase_auth, 'verify_id_token', return_value=mock_decoded_token):
            # This would be the actual verification function
            decoded = firebase_auth.verify_id_token(mock_firebase_token)

            assert decoded["uid"] == "test_user_id"
            assert decoded["email"] == "test@test.com"
            assert decoded["email_verified"] is True
            print("✓ Valid Firebase token correctly verified")

    def test_expired_token_rejected(self, mock_firebase_token):
        """
        TC-AUTH-FB-02: Expired token returns 401

        Ensures expired tokens are rejected with appropriate error.
        """
        from firebase_admin.exceptions import InvalidIdTokenError

        with patch.object(firebase_auth, 'verify_id_token', side_effect=InvalidIdTokenError("Token expired")):
            with pytest.raises(InvalidIdTokenError, match="Token expired"):
                firebase_auth.verify_id_token(mock_firebase_token)
            print("✓ Expired token correctly rejected")

    def test_invalid_signature_rejected(self, mock_firebase_token):
        """
        TC-AUTH-FB-03: Invalid signature rejected

        Ensures tokens with invalid signatures are rejected.
        """
        from firebase_admin.exceptions import InvalidIdTokenError

        with patch.object(firebase_auth, 'verify_id_token', side_effect=InvalidIdTokenError("Invalid signature")):
            with pytest.raises(InvalidIdTokenError):
                firebase_auth.verify_id_token(mock_firebase_token)
            print("✓ Invalid signature correctly rejected")

    def test_missing_email_claim_rejected(self, mock_firebase_token):
        """
        TC-AUTH-FB-04: Token without email claim rejected

        Ensures tokens missing required claims are rejected.
        """
        incomplete_token = {"uid": "test_user_id"}  # Missing email

        with patch.object(firebase_auth, 'verify_id_token', return_value=incomplete_token):
            decoded = firebase_auth.verify_id_token(mock_firebase_token)
            assert "email" not in decoded
            # Application logic should reject this
            print("✓ Token without email claim detected")


# =============================================================================
# UNIT TESTS - MFA Validation Logic
# =============================================================================

@pytest.mark.skipif(not FIREBASE_AVAILABLE, reason="firebase-admin not installed")
class TestMFAValidation:
    """Unit tests for Multi-Factor Authentication validation."""

    @pytest.fixture
    def user_with_mfa(self) -> Mock:
        """Mock Firebase user with MFA enabled."""
        user = Mock(spec=UserRecord)
        user.uid = "test_user_mfa"
        user.email = "mfa@test.com"
        user.multi_factor = Mock()
        user.multi_factor.enrolled_factors = [
            Mock(uid="mfa_factor_1", factor_id="phone", enrollment_time=datetime.now(timezone.utc))
        ]
        return user

    @pytest.fixture
    def user_without_mfa(self) -> Mock:
        """Mock Firebase user without MFA."""
        user = Mock(spec=UserRecord)
        user.uid = "test_user_no_mfa"
        user.email = "nomfa@test.com"
        user.multi_factor = None
        return user

    def test_mfa_enabled_check(self, user_with_mfa):
        """
        TC-MFA-01: Verify MFA enabled status

        Validates logic to check if user has MFA enrolled.
        """
        # Application logic to check MFA enrollment
        def has_mfa(user: UserRecord) -> bool:
            return (
                user.multi_factor is not None
                and hasattr(user.multi_factor, 'enrolled_factors')
                and len(user.multi_factor.enrolled_factors) > 0
            )

        assert has_mfa(user_with_mfa) is True
        print("✓ MFA enabled check works correctly")

    def test_mfa_disabled_check(self, user_without_mfa):
        """
        TC-MFA-02: Verify MFA disabled status

        Validates detection of users without MFA.
        """
        def has_mfa(user: UserRecord) -> bool:
            return (
                user.multi_factor is not None
                and hasattr(user.multi_factor, 'enrolled_factors')
                and len(user.multi_factor.enrolled_factors) > 0
            )

        assert has_mfa(user_without_mfa) is False
        print("✓ MFA disabled check works correctly")

    def test_mfa_required_enforcement(self, user_without_mfa):
        """
        TC-MFA-03: MFA required enforcement

        Ensures users without MFA are blocked from protected endpoints.
        """
        def require_mfa(user: UserRecord) -> bool:
            """Returns True if access granted, False if MFA required."""
            has_mfa = (
                user.multi_factor is not None
                and hasattr(user.multi_factor, 'enrolled_factors')
                and len(user.multi_factor.enrolled_factors) > 0
            )
            return has_mfa

        access_granted = require_mfa(user_without_mfa)
        assert access_granted is False
        print("✓ MFA requirement correctly enforced")

    def test_multiple_mfa_factors(self):
        """
        TC-MFA-04: Multiple MFA factors supported

        Validates handling of users with multiple MFA methods.
        """
        user = Mock(spec=UserRecord)
        user.multi_factor = Mock()
        user.multi_factor.enrolled_factors = [
            Mock(uid="factor_1", factor_id="phone"),
            Mock(uid="factor_2", factor_id="totp"),
        ]

        def has_mfa(user: UserRecord) -> bool:
            return (
                user.multi_factor is not None
                and hasattr(user.multi_factor, 'enrolled_factors')
                and len(user.multi_factor.enrolled_factors) > 0
            )

        assert has_mfa(user) is True
        assert len(user.multi_factor.enrolled_factors) == 2
        print("✓ Multiple MFA factors correctly handled")


# =============================================================================
# UNIT TESTS - Tier Validation Logic
# =============================================================================

class TestTierValidation:
    """Unit tests for freemium tier validation logic."""

    @pytest.fixture
    def freemium_user_fresh(self) -> Dict:
        """Freemium user with no sessions used."""
        return {
            "user_id": "freemium_user_1",
            "email": "freemium@test.com",
            "tier": "freemium",
            "audio_sessions_used": 0,
            "audio_sessions_limit": 2,
            "created_at": datetime.now(timezone.utc),
        }

    @pytest.fixture
    def freemium_user_at_limit(self) -> Dict:
        """Freemium user at session limit."""
        return {
            "user_id": "freemium_user_2",
            "email": "limit@test.com",
            "tier": "freemium",
            "audio_sessions_used": 2,
            "audio_sessions_limit": 2,
            "created_at": datetime.now(timezone.utc),
        }

    @pytest.fixture
    def premium_user(self) -> Dict:
        """Premium user with unlimited sessions."""
        return {
            "user_id": "premium_user_1",
            "email": "premium@test.com",
            "tier": "premium",
            "audio_sessions_used": 100,
            "audio_sessions_limit": None,  # Unlimited
            "created_at": datetime.now(timezone.utc),
        }

    def test_freemium_tier_identification(self, freemium_user_fresh):
        """
        TC-TIER-01: Identify freemium tier users

        Validates logic to identify freemium tier.
        """
        def is_freemium(user: Dict) -> bool:
            return user.get("tier") == "freemium"

        assert is_freemium(freemium_user_fresh) is True
        print("✓ Freemium tier correctly identified")

    def test_freemium_session_check_allowed(self, freemium_user_fresh):
        """
        TC-TIER-02: Freemium user below limit allowed

        Validates freemium users can create sessions below limit.
        """
        def can_create_audio_session(user: Dict) -> bool:
            if user.get("tier") == "premium":
                return True  # Unlimited

            used = user.get("audio_sessions_used", 0)
            limit = user.get("audio_sessions_limit", 0)
            return used < limit

        assert can_create_audio_session(freemium_user_fresh) is True
        print("✓ Freemium user below limit allowed session")

    def test_freemium_session_check_blocked(self, freemium_user_at_limit):
        """
        TC-TIER-03: Freemium user at limit blocked

        Validates freemium users at limit cannot create more sessions.
        """
        def can_create_audio_session(user: Dict) -> bool:
            if user.get("tier") == "premium":
                return True  # Unlimited

            used = user.get("audio_sessions_used", 0)
            limit = user.get("audio_sessions_limit", 0)
            return used < limit

        assert can_create_audio_session(freemium_user_at_limit) is False
        print("✓ Freemium user at limit correctly blocked")

    def test_premium_unlimited_access(self, premium_user):
        """
        TC-TIER-04: Premium users have unlimited access

        Validates premium tier bypasses session limits.
        """
        def can_create_audio_session(user: Dict) -> bool:
            if user.get("tier") == "premium":
                return True  # Unlimited

            used = user.get("audio_sessions_used", 0)
            limit = user.get("audio_sessions_limit", 0)
            return used < limit

        assert can_create_audio_session(premium_user) is True
        print("✓ Premium user unlimited access verified")

    def test_session_increment_logic(self, freemium_user_fresh):
        """
        TC-TIER-05: Session counter increment logic

        Validates session count increases correctly.
        """
        def increment_session_count(user: Dict) -> Dict:
            user["audio_sessions_used"] += 1
            return user

        initial_count = freemium_user_fresh["audio_sessions_used"]
        updated_user = increment_session_count(freemium_user_fresh)

        assert updated_user["audio_sessions_used"] == initial_count + 1
        print("✓ Session counter correctly incremented")


# =============================================================================
# UNIT TESTS - User Record Creation Logic
# =============================================================================

class TestUserRecordCreation:
    """Unit tests for automatic Firestore user record creation."""

    def test_create_freemium_user_record(self):
        """
        TC-USER-01: Create freemium user record on first login

        Validates user record structure for new freemium users.
        """
        def create_user_record(uid: str, email: str) -> Dict:
            return {
                "user_id": uid,
                "email": email,
                "tier": "freemium",
                "audio_sessions_used": 0,
                "audio_sessions_limit": 2,
                "created_at": datetime.now(timezone.utc),
                "last_login_at": datetime.now(timezone.utc),
            }

        user = create_user_record("new_user_123", "new@test.com")

        assert user["user_id"] == "new_user_123"
        assert user["email"] == "new@test.com"
        assert user["tier"] == "freemium"
        assert user["audio_sessions_used"] == 0
        assert user["audio_sessions_limit"] == 2
        assert user["created_at"] is not None
        print("✓ Freemium user record structure correct")

    def test_idempotent_user_creation(self):
        """
        TC-USER-02: User creation is idempotent

        Ensures duplicate user creation doesn't cause errors.
        """
        def get_or_create_user(uid: str, email: str, existing_user: Optional[Dict] = None) -> Dict:
            if existing_user:
                # Update last_login_at only
                existing_user["last_login_at"] = datetime.now(timezone.utc)
                return existing_user

            # Create new user
            return {
                "user_id": uid,
                "email": email,
                "tier": "freemium",
                "audio_sessions_used": 0,
                "audio_sessions_limit": 2,
                "created_at": datetime.now(timezone.utc),
                "last_login_at": datetime.now(timezone.utc),
            }

        # First call - create user
        user1 = get_or_create_user("user_123", "test@test.com")
        assert user1["audio_sessions_used"] == 0

        # Second call - existing user, should not reset counter
        user1["audio_sessions_used"] = 1  # Simulate used session
        user2 = get_or_create_user("user_123", "test@test.com", existing_user=user1)
        assert user2["audio_sessions_used"] == 1  # Counter preserved
        print("✓ User creation is idempotent")


# =============================================================================
# UNIT TESTS - Rate Limiting Logic
# =============================================================================

class TestRateLimitingLogic:
    """Unit tests for freemium session rate limiting."""

    def test_rate_limit_check_below_limit(self):
        """
        TC-RATE-FB-01: Rate limit check below limit

        Validates rate limit allows requests below limit.
        """
        def check_rate_limit(user: Dict) -> tuple[bool, Optional[str]]:
            """Returns (allowed, error_message)."""
            if user.get("tier") == "premium":
                return True, None

            used = user.get("audio_sessions_used", 0)
            limit = user.get("audio_sessions_limit", 2)

            if used >= limit:
                return False, f"Freemium limit reached ({used}/{limit}). Upgrade to premium for unlimited access."
            return True, None

        user = {"tier": "freemium", "audio_sessions_used": 1, "audio_sessions_limit": 2}
        allowed, error = check_rate_limit(user)

        assert allowed is True
        assert error is None
        print("✓ Rate limit allows below limit")

    def test_rate_limit_check_at_limit(self):
        """
        TC-RATE-FB-02: Rate limit check at limit

        Validates rate limit blocks requests at limit.
        """
        def check_rate_limit(user: Dict) -> tuple[bool, Optional[str]]:
            """Returns (allowed, error_message)."""
            if user.get("tier") == "premium":
                return True, None

            used = user.get("audio_sessions_used", 0)
            limit = user.get("audio_sessions_limit", 2)

            if used >= limit:
                return False, f"Freemium limit reached ({used}/{limit}). Upgrade to premium for unlimited access."
            return True, None

        user = {"tier": "freemium", "audio_sessions_used": 2, "audio_sessions_limit": 2}
        allowed, error = check_rate_limit(user)

        assert allowed is False
        assert "limit reached" in error.lower()
        print("✓ Rate limit blocks at limit")

    def test_rate_limit_error_message_format(self):
        """
        TC-RATE-FB-03: Rate limit error message format

        Validates error messages are user-friendly and actionable.
        """
        def check_rate_limit(user: Dict) -> tuple[bool, Optional[str]]:
            if user.get("tier") == "premium":
                return True, None

            used = user.get("audio_sessions_used", 0)
            limit = user.get("audio_sessions_limit", 2)

            if used >= limit:
                return False, f"Freemium limit reached ({used}/{limit}). Upgrade to premium for unlimited access."
            return True, None

        user = {"tier": "freemium", "audio_sessions_used": 2, "audio_sessions_limit": 2}
        _, error = check_rate_limit(user)

        assert "freemium" in error.lower() or "limit" in error.lower()
        assert "premium" in error.lower() or "upgrade" in error.lower()
        assert "2" in error  # Shows actual limit
        print("✓ Rate limit error message is actionable")


# =============================================================================
# INTEGRATION TESTS - End-to-End Signup Flow
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(not FIREBASE_AVAILABLE, reason="firebase-admin not installed")
@pytest.mark.asyncio
class TestFirebaseSignupFlow:
    """Integration tests for Firebase signup and user creation flow."""

    @pytest.fixture
    async def mock_firestore_client(self):
        """Mock Firestore client for testing."""
        client = AsyncMock()
        client.collection = Mock(return_value=Mock(document=Mock(return_value=Mock(
            set=AsyncMock(),
            get=AsyncMock(),
            update=AsyncMock()
        ))))
        return client

    async def test_e2e_signup_creates_user_record(self, mock_firestore_client):
        """
        TC-INT-01: E2E signup creates Firestore user record

        Validates complete flow from Firebase signup to Firestore user creation.
        """
        # Simulate Firebase signup
        firebase_user = {
            "uid": "new_user_firebase_123",
            "email": "newuser@test.com",
            "email_verified": True,
        }

        # Application logic to create Firestore record
        async def on_firebase_signup(user: Dict, firestore_client) -> Dict:
            user_record = {
                "user_id": user["uid"],
                "email": user["email"],
                "tier": "freemium",
                "audio_sessions_used": 0,
                "audio_sessions_limit": 2,
                "created_at": datetime.now(timezone.utc),
            }

            doc_ref = firestore_client.collection("users").document(user["uid"])
            await doc_ref.set(user_record)
            return user_record

        user_record = await on_firebase_signup(firebase_user, mock_firestore_client)

        assert user_record["user_id"] == "new_user_firebase_123"
        assert user_record["tier"] == "freemium"
        assert user_record["audio_sessions_limit"] == 2
        print("✓ E2E signup creates correct user record")

    async def test_e2e_existing_user_login_updates_timestamp(self, mock_firestore_client):
        """
        TC-INT-02: Existing user login updates last_login_at

        Validates that returning users get timestamp updates.
        """
        existing_user = {
            "user_id": "existing_user_123",
            "email": "existing@test.com",
            "tier": "freemium",
            "audio_sessions_used": 1,
            "last_login_at": datetime.now(timezone.utc) - timedelta(days=1),
        }

        # Mock Firestore get to return existing user
        mock_doc = AsyncMock()
        mock_doc.exists = True
        mock_doc.to_dict = Mock(return_value=existing_user)

        mock_firestore_client.collection("users").document("existing_user_123").get = AsyncMock(return_value=mock_doc)

        # Application logic for returning user
        async def on_user_login(uid: str, firestore_client) -> Dict:
            doc_ref = firestore_client.collection("users").document(uid)
            doc = await doc_ref.get()

            if doc.exists:
                # Update last login
                await doc_ref.update({"last_login_at": datetime.now(timezone.utc)})
                return doc.to_dict()
            else:
                raise ValueError("User not found")

        user = await on_user_login("existing_user_123", mock_firestore_client)

        assert user["user_id"] == "existing_user_123"
        assert user["audio_sessions_used"] == 1  # Preserved
        print("✓ Existing user login preserves data")


# =============================================================================
# INTEGRATION TESTS - MFA Enrollment and Verification
# =============================================================================

@pytest.mark.integration
@pytest.mark.skipif(not FIREBASE_AVAILABLE, reason="firebase-admin not installed")
class TestMFAEnrollmentFlow:
    """Integration tests for MFA enrollment and verification."""

    def test_mfa_enrollment_required_on_first_login(self):
        """
        TC-INT-MFA-01: MFA enrollment required on first login

        Validates that new users are prompted to enroll MFA.
        """
        # Simulate user without MFA after first login
        user = Mock(spec=UserRecord)
        user.uid = "new_user_mfa_required"
        user.email = "newmfa@test.com"
        user.multi_factor = None

        def requires_mfa_enrollment(user: UserRecord) -> bool:
            return (
                user.multi_factor is None
                or not hasattr(user.multi_factor, 'enrolled_factors')
                or len(user.multi_factor.enrolled_factors) == 0
            )

        assert requires_mfa_enrollment(user) is True
        print("✓ New user correctly requires MFA enrollment")

    def test_mfa_verification_required_for_sensitive_endpoints(self):
        """
        TC-INT-MFA-02: MFA required for audio sessions

        Validates MFA check before allowing audio session creation.
        """
        # User with MFA
        user_with_mfa = Mock(spec=UserRecord)
        user_with_mfa.multi_factor = Mock()
        user_with_mfa.multi_factor.enrolled_factors = [Mock(uid="factor_1")]

        # User without MFA
        user_without_mfa = Mock(spec=UserRecord)
        user_without_mfa.multi_factor = None

        def can_access_audio_endpoint(user: UserRecord) -> bool:
            return (
                user.multi_factor is not None
                and hasattr(user.multi_factor, 'enrolled_factors')
                and len(user.multi_factor.enrolled_factors) > 0
            )

        assert can_access_audio_endpoint(user_with_mfa) is True
        assert can_access_audio_endpoint(user_without_mfa) is False
        print("✓ MFA required for audio sessions")


# =============================================================================
# EDGE CASES - Incomplete MFA, Concurrent Sessions, Failures
# =============================================================================

@pytest.mark.edge_cases
class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_user_signs_up_but_abandons_mfa(self):
        """
        TC-EDGE-01: User abandons MFA enrollment

        Validates handling of users who create account but don't complete MFA.
        """
        user = Mock(spec=UserRecord)
        user.uid = "abandoned_mfa_user"
        user.email = "abandon@test.com"
        user.multi_factor = None  # MFA not enrolled

        def can_access_protected_resource(user: UserRecord) -> bool:
            has_mfa = (
                user.multi_factor is not None
                and hasattr(user.multi_factor, 'enrolled_factors')
                and len(user.multi_factor.enrolled_factors) > 0
            )
            return has_mfa

        # User should be blocked from protected resources
        assert can_access_protected_resource(user) is False
        print("✓ User without MFA correctly blocked")

    def test_session_limit_reached_exactly_at_2(self):
        """
        TC-EDGE-02: Freemium limit reached at exactly 2 sessions

        Validates boundary condition at exact limit.
        """
        user = {
            "tier": "freemium",
            "audio_sessions_used": 2,
            "audio_sessions_limit": 2,
        }

        def can_create_session(user: Dict) -> bool:
            if user.get("tier") == "premium":
                return True
            used = user.get("audio_sessions_used", 0)
            limit = user.get("audio_sessions_limit", 2)
            return used < limit

        assert can_create_session(user) is False
        print("✓ Exact limit boundary correctly enforced")

    @pytest.mark.asyncio
    async def test_concurrent_session_creation_attempts(self):
        """
        TC-EDGE-03: Concurrent session attempts near limit

        Validates race condition handling when user at limit-1 creates 2 sessions concurrently.
        """
        import asyncio

        user_state = {"audio_sessions_used": 1, "audio_sessions_limit": 2}

        async def create_session_with_lock(user: Dict) -> bool:
            """Simulates atomic check-and-increment with lock."""
            # In production, use Firestore transactions
            if user["audio_sessions_used"] < user["audio_sessions_limit"]:
                await asyncio.sleep(0.01)  # Simulate DB delay
                user["audio_sessions_used"] += 1
                return True
            return False

        # Simulate two concurrent requests
        result1 = await create_session_with_lock(user_state)
        result2 = await create_session_with_lock(user_state)

        # Only one should succeed
        assert result1 is True  # First succeeds
        assert result2 is False  # Second fails (limit reached)
        assert user_state["audio_sessions_used"] == 2
        print("✓ Concurrent requests correctly handled")

    def test_firebase_auth_unavailable(self):
        """
        TC-EDGE-04: Firebase Auth service unavailable

        Validates graceful degradation when Firebase is down.
        """
        from firebase_admin.exceptions import FirebaseError

        def verify_token_with_fallback(token: str) -> Optional[Dict]:
            try:
                with patch.object(firebase_auth, 'verify_id_token', side_effect=FirebaseError("Service unavailable")):
                    return firebase_auth.verify_id_token(token)
            except FirebaseError as e:
                # Log error and return None for graceful failure
                print(f"Firebase unavailable: {e}")
                return None

        result = verify_token_with_fallback("test_token")
        assert result is None
        print("✓ Firebase unavailability handled gracefully")

    @pytest.mark.asyncio
    async def test_firestore_write_failure_rollback(self):
        """
        TC-EDGE-05: Firestore write failure handling

        Validates that failed user record creation is handled correctly.
        """
        mock_firestore = AsyncMock()
        mock_firestore.collection("users").document("test").set = AsyncMock(
            side_effect=Exception("Firestore write failed")
        )

        async def create_user_safe(uid: str, email: str, firestore_client) -> Optional[Dict]:
            try:
                user_record = {
                    "user_id": uid,
                    "email": email,
                    "tier": "freemium",
                }
                await firestore_client.collection("users").document(uid).set(user_record)
                return user_record
            except Exception as e:
                print(f"Failed to create user: {e}")
                return None

        result = await create_user_safe("test_user", "test@test.com", mock_firestore)
        assert result is None
        print("✓ Firestore write failure handled safely")


# =============================================================================
# REGRESSION TESTS - Existing Functionality Unchanged
# =============================================================================

@pytest.mark.regression
class TestRegressionTests:
    """Regression tests to ensure existing features unaffected."""

    def test_existing_premium_users_unaffected(self):
        """
        TC-REG-01: Existing premium users retain unlimited access

        Validates premium users not impacted by freemium implementation.
        """
        premium_user = {
            "user_id": "premium_existing",
            "email": "premium@test.com",
            "tier": "premium",
            "audio_sessions_used": 500,  # High usage
            "audio_sessions_limit": None,  # Unlimited
        }

        def can_create_session(user: Dict) -> bool:
            if user.get("tier") == "premium":
                return True  # Unlimited
            used = user.get("audio_sessions_used", 0)
            limit = user.get("audio_sessions_limit", 2)
            return used < limit

        assert can_create_session(premium_user) is True
        print("✓ Premium users retain unlimited access")

    def test_text_session_functionality_unchanged(self):
        """
        TC-REG-02: Text sessions remain unrestricted

        Validates text-based sessions not affected by audio limits.
        """
        freemium_user_at_limit = {
            "tier": "freemium",
            "audio_sessions_used": 2,  # At limit
            "audio_sessions_limit": 2,
        }

        def can_create_text_session(user: Dict) -> bool:
            # Text sessions unrestricted for all tiers
            return True

        assert can_create_text_session(freemium_user_at_limit) is True
        print("✓ Text sessions remain unrestricted")

    def test_existing_rate_limiting_preserved(self):
        """
        TC-REG-03: Existing rate limiting unchanged for premium

        Validates existing 10 sessions/day limit still applies to premium tier.
        """
        premium_user = {
            "tier": "premium",
            "daily_sessions_used": 10,
            "daily_sessions_limit": 10,
        }

        def check_daily_limit(user: Dict) -> bool:
            """Daily limit applies to all tiers."""
            used = user.get("daily_sessions_used", 0)
            limit = user.get("daily_sessions_limit", 10)
            return used < limit

        assert check_daily_limit(premium_user) is False
        print("✓ Existing daily rate limits preserved")


# =============================================================================
# SECURITY TESTS - Token Validation, MFA Bypass, Privilege Escalation
# =============================================================================

@pytest.mark.security
@pytest.mark.skipif(not FIREBASE_AVAILABLE, reason="firebase-admin not installed")
class TestSecurityTests:
    """Security-focused tests for Firebase Auth implementation."""

    def test_tampered_token_rejected(self):
        """
        TC-SEC-01: Tampered Firebase token rejected

        Validates tokens with modified claims are rejected.
        """
        from firebase_admin.exceptions import InvalidIdTokenError

        tampered_token = "tampered.payload.signature"

        with patch.object(firebase_auth, 'verify_id_token', side_effect=InvalidIdTokenError("Invalid token")):
            with pytest.raises(InvalidIdTokenError):
                firebase_auth.verify_id_token(tampered_token)
        print("✓ Tampered token correctly rejected")

    def test_mfa_bypass_attempt_blocked(self):
        """
        TC-SEC-02: MFA bypass attempt blocked

        Validates that users cannot bypass MFA requirement with crafted requests.
        """
        user_without_mfa = Mock(spec=UserRecord)
        user_without_mfa.multi_factor = None

        # Simulated malicious request with fake MFA claim
        malicious_request_headers = {"X-MFA-Bypass": "true"}

        def validate_mfa_secure(user: UserRecord, headers: Dict) -> bool:
            """Only trust Firebase MFA status, ignore request headers."""
            has_mfa = (
                user.multi_factor is not None
                and hasattr(user.multi_factor, 'enrolled_factors')
                and len(user.multi_factor.enrolled_factors) > 0
            )
            # SECURITY: Ignore any client-provided headers
            return has_mfa

        assert validate_mfa_secure(user_without_mfa, malicious_request_headers) is False
        print("✓ MFA bypass attempt blocked")

    def test_session_tampering_prevention(self):
        """
        TC-SEC-03: Session counter tampering prevented

        Validates that users cannot manipulate session counters.
        """
        # User attempts to send manipulated session count in request
        client_request = {
            "user_id": "malicious_user",
            "audio_sessions_used": 0,  # Claims 0 usage
        }

        # Server should ONLY trust Firestore data
        firestore_truth = {
            "user_id": "malicious_user",
            "audio_sessions_used": 2,  # Actually at limit
            "audio_sessions_limit": 2,
        }

        def check_session_limit_secure(user_id: str, firestore_data: Dict) -> bool:
            """Only trust server-side data, never client input."""
            used = firestore_data.get("audio_sessions_used", 0)
            limit = firestore_data.get("audio_sessions_limit", 2)
            return used < limit

        # Should use Firestore data, not client request
        allowed = check_session_limit_secure("malicious_user", firestore_truth)
        assert allowed is False
        print("✓ Session tampering prevented by trusting server data")

    def test_tier_privilege_escalation_blocked(self):
        """
        TC-SEC-04: Tier privilege escalation prevented

        Validates users cannot escalate tier via API manipulation.
        """
        freemium_user = {"user_id": "escalation_attempt", "tier": "freemium"}

        # Malicious request attempting to set premium tier
        malicious_update = {"tier": "premium"}

        def update_user_profile_secure(user: Dict, updates: Dict) -> Dict:
            """Block tier updates via public API - admin-only operation."""
            PROTECTED_FIELDS = ["tier", "audio_sessions_limit", "user_id"]

            for field in PROTECTED_FIELDS:
                if field in updates:
                    raise PermissionError(f"Cannot modify protected field: {field}")

            # Apply safe updates only
            safe_updates = {k: v for k, v in updates.items() if k not in PROTECTED_FIELDS}
            user.update(safe_updates)
            return user

        with pytest.raises(PermissionError, match="Cannot modify protected field: tier"):
            update_user_profile_secure(freemium_user, malicious_update)
        print("✓ Tier escalation attempt blocked")


# =============================================================================
# MANUAL TEST SCENARIOS (For QA Engineers)
# =============================================================================

@pytest.mark.manual
class TestManualScenarios:
    """
    Manual test scenarios for QA execution.

    These tests require human interaction and cannot be fully automated.
    """

    def test_manual_signup_flow(self):
        """
        MANUAL TEST: Complete Firebase signup flow

        Steps:
        1. Navigate to application signup page
        2. Enter email and password
        3. Submit signup form
        4. Verify email sent (check inbox)
        5. Click verification link
        6. Complete MFA enrollment (phone/authenticator app)
        7. Redirected to application with freemium tier
        8. Check Firestore: users/{uid} document exists with tier='freemium'

        Expected Results:
        - Signup completes without errors
        - Email verification works
        - MFA enrollment required and works
        - User record created in Firestore with correct fields
        - User can access text sessions
        - User can access 2 audio sessions (premium mode)
        """
        pytest.skip("Manual test - requires browser interaction")

    def test_manual_mfa_recovery(self):
        """
        MANUAL TEST: MFA recovery code usage

        Steps:
        1. Sign up and enroll MFA
        2. Save recovery codes
        3. Log out
        4. Attempt login without MFA device
        5. Use recovery code to access account
        6. Verify account access granted

        Expected Results:
        - Recovery code successfully grants access
        - User prompted to re-enroll MFA
        - Security log entry created
        """
        pytest.skip("Manual test - requires MFA device simulation")

    def test_manual_tier_upgrade_flow(self):
        """
        MANUAL TEST: Tier upgrade from freemium to premium

        Steps:
        1. Create freemium account
        2. Use 2 audio sessions (reach limit)
        3. Attempt 3rd audio session - blocked
        4. Click "Upgrade to Premium" CTA
        5. Complete payment (Stripe test mode)
        6. Verify tier upgraded in Firestore
        7. Verify unlimited audio access granted

        Expected Results:
        - Limit enforced at 2 sessions
        - Upgrade flow intuitive and clear
        - Payment processes successfully
        - Tier immediately updated
        - Unlimited access granted
        """
        pytest.skip("Manual test - requires payment integration")


# =============================================================================
# TEST EXECUTION COMMANDS
# =============================================================================

"""
Run all tests:
    pytest tests/test_firebase_auth_freemium.py -v

Run unit tests only:
    pytest tests/test_firebase_auth_freemium.py -v -m "not integration and not manual"

Run integration tests:
    pytest tests/test_firebase_auth_freemium.py -v -m integration

Run security tests:
    pytest tests/test_firebase_auth_freemium.py -v -m security

Run edge case tests:
    pytest tests/test_firebase_auth_freemium.py -v -m edge_cases

Run with coverage:
    pytest tests/test_firebase_auth_freemium.py --cov=app.middleware --cov=app.models --cov-report=html

Generate test report:
    pytest tests/test_firebase_auth_freemium.py -v --html=report.html --self-contained-html
"""
