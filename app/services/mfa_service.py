"""Multi-Factor Authentication (MFA) Service

This service provides TOTP-based MFA and recovery code management
for Phase 2 of IQS-65.

Features:
- TOTP secret generation and QR code creation
- TOTP token verification using pyotp
- Recovery code generation (8 codes, hashed storage)
- Recovery code validation
- MFA enrollment and verification tracking

Acceptance Criteria:
- AC-MFA-01: MFA enrollment mandatory during signup
- AC-MFA-02: TOTP-based MFA using authenticator apps
- AC-MFA-03: QR code display for app scanning (min 200x200px)
- AC-MFA-04: 8 recovery codes provided during setup
- AC-MFA-05: User confirmation of saved recovery codes
- AC-MFA-06: MFA verification required on every login
- AC-MFA-07: Recovery codes can be used if authenticator unavailable
"""

import secrets
import hashlib
import hmac
import base64
from typing import List, Optional, Tuple
from datetime import datetime, timezone
import io

# TOTP library
import pyotp

# QR code generation
import qrcode
from qrcode.image.pil import PilImage

# Secure password hashing
import bcrypt

from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class MFAError(Exception):
    """Base exception for MFA errors."""
    pass


class InvalidTOTPCodeError(MFAError):
    """Raised when TOTP code is invalid."""
    pass


class InvalidRecoveryCodeError(MFAError):
    """Raised when recovery code is invalid."""
    pass


def generate_totp_secret() -> str:
    """Generate a random TOTP secret (base32 encoded).

    Returns:
        Base32-encoded secret string (16 bytes = 26 chars in base32)

    Example:
        "JBSWY3DPEHPK3PXP"
    """
    # Generate 160-bit (20-byte) random secret
    # pyotp uses base32 encoding, which produces ~26 characters
    secret = pyotp.random_base32()

    logger.info("Generated new TOTP secret")

    return secret


def generate_totp_qr_code(
    secret: str,
    user_email: str,
    issuer_name: str = "Improv Olympics"
) -> bytes:
    """Generate QR code image for TOTP enrollment.

    Creates a QR code containing the TOTP provisioning URI.
    Minimum size: 200x200px (AC-MFA-03)

    Args:
        secret: TOTP secret (base32 encoded)
        user_email: User's email address
        issuer_name: Application name shown in authenticator app

    Returns:
        PNG image bytes (256x256px)

    QR Code Format:
        otpauth://totp/Improv Olympics:user@example.com?secret=ABC&issuer=Improv Olympics
    """
    # Create TOTP object
    totp = pyotp.TOTP(secret)

    # Generate provisioning URI
    # Format: otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}
    provisioning_uri = totp.provisioning_uri(
        name=user_email,
        issuer_name=issuer_name
    )

    # Generate QR code (256x256px, exceeds 200x200px requirement)
    qr = qrcode.QRCode(
        version=1,  # Auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    # Create PIL image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to PNG bytes
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    png_bytes = buffer.getvalue()

    logger.info(
        "Generated TOTP QR code",
        user_email=user_email,
        size_bytes=len(png_bytes)
    )

    return png_bytes


def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    """Verify TOTP code against secret.

    Args:
        secret: TOTP secret (base32 encoded)
        code: 6-digit TOTP code from authenticator app
        window: Number of time windows to check (default: 1 = ±30 seconds)

    Returns:
        True if code is valid, False otherwise

    Raises:
        InvalidTOTPCodeError: If code format is invalid
    """
    # Validate code format (must be 6 digits)
    if not code or len(code) != 6 or not code.isdigit():
        logger.warning("Invalid TOTP code format", code_length=len(code) if code else 0)
        raise InvalidTOTPCodeError("TOTP code must be 6 digits")

    # Create TOTP object
    totp = pyotp.TOTP(secret)

    # Verify code (with time window for clock drift tolerance)
    is_valid = totp.verify(code, valid_window=window)

    if is_valid:
        logger.info("TOTP code verified successfully")
    else:
        logger.warning("TOTP code verification failed")

    return is_valid


def generate_recovery_codes(count: int = 8) -> List[str]:
    """Generate recovery codes for MFA bypass.

    Generates cryptographically secure recovery codes.
    Format: XXXX-XXXX (8 characters, uppercase alphanumeric)

    Args:
        count: Number of recovery codes to generate (default: 8, AC-MFA-04)

    Returns:
        List of recovery codes in format "XXXX-XXXX"

    Example:
        ["A3F9-K2H7", "B8D4-L9M3", ...]
    """
    codes = []

    # Character set: uppercase letters + digits (no ambiguous chars like 0/O, 1/I)
    charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    for _ in range(count):
        # Generate 8 random characters
        code_chars = ''.join(secrets.choice(charset) for _ in range(8))

        # Format as XXXX-XXXX for readability
        formatted_code = f"{code_chars[:4]}-{code_chars[4:]}"

        codes.append(formatted_code)

    logger.info("Generated recovery codes", count=count)

    return codes


def hash_recovery_code(code: str) -> str:
    """Hash recovery code for secure storage using bcrypt.

    Uses bcrypt with per-code salt to prevent rainbow table attacks.
    Recovery codes should never be stored in plaintext.

    Security: bcrypt automatically generates a unique salt per hash,
    making rainbow table attacks infeasible.

    Args:
        code: Recovery code (e.g., "A3F9-K2H7")

    Returns:
        bcrypt hash string (includes salt)
    """
    # Remove dashes and convert to uppercase for consistency
    normalized_code = code.replace("-", "").upper()

    # bcrypt generates unique salt per hash automatically
    # Work factor of 12 provides ~250ms hashing time (secure but not too slow)
    code_hash = bcrypt.hashpw(
        normalized_code.encode('utf-8'),
        bcrypt.gensalt(rounds=12)
    )

    return code_hash.decode('utf-8')


def hash_recovery_codes(codes: List[str]) -> List[str]:
    """Hash multiple recovery codes.

    Args:
        codes: List of recovery codes

    Returns:
        List of hashed recovery codes (same order)
    """
    return [hash_recovery_code(code) for code in codes]


def verify_recovery_code(
    code: str,
    hashed_codes: List[str]
) -> bool:
    """Verify recovery code against stored hashes using constant-time comparison.

    Uses bcrypt.checkpw which is constant-time to prevent timing attacks.

    Args:
        code: Recovery code provided by user
        hashed_codes: List of hashed recovery codes from database

    Returns:
        True if code matches any stored hash

    Raises:
        InvalidRecoveryCodeError: If code format is invalid

    Security: Uses constant-time comparison to prevent timing attacks.
    Always checks ALL hashes even after finding a match to ensure
    consistent timing regardless of match position.
    """
    # Validate code format
    if not code or len(code.replace("-", "")) != 8:
        logger.warning("Invalid recovery code format")
        raise InvalidRecoveryCodeError("Invalid recovery code format")

    # Normalize the provided code
    normalized_code = code.replace("-", "").upper()

    # Constant-time comparison against all stored hashes
    # IMPORTANT: Don't short-circuit - check all hashes for consistent timing
    is_valid = False
    for stored_hash in hashed_codes:
        try:
            if bcrypt.checkpw(normalized_code.encode('utf-8'), stored_hash.encode('utf-8')):
                is_valid = True
                # Don't break - continue checking to prevent timing attacks
        except (ValueError, TypeError):
            # Invalid hash format - continue checking others
            continue

    if is_valid:
        logger.info("Recovery code verified successfully")
    else:
        logger.warning("Recovery code verification failed")

    return is_valid


def consume_recovery_code(
    code: str,
    hashed_codes: List[str]
) -> Optional[List[str]]:
    """Consume (remove) a recovery code after use.

    Recovery codes are single-use. After verification, the code
    should be removed from the user's list.

    Uses bcrypt.checkpw for constant-time verification.

    Args:
        code: Recovery code provided by user
        hashed_codes: List of hashed recovery codes from database

    Returns:
        Updated list of hashed codes (with consumed code removed),
        or None if code was not found
    """
    # Normalize the provided code
    normalized_code = code.replace("-", "").upper()

    # Find and remove the matching hash
    matched_hash = None
    for stored_hash in hashed_codes:
        try:
            if bcrypt.checkpw(normalized_code.encode('utf-8'), stored_hash.encode('utf-8')):
                matched_hash = stored_hash
                break  # OK to break here since we're consuming, not just verifying
        except (ValueError, TypeError):
            continue

    if matched_hash is None:
        logger.warning("Recovery code not found for consumption")
        return None

    # Remove the matched hash from the list
    updated_codes = [h for h in hashed_codes if h != matched_hash]

    logger.info(
        "Recovery code consumed",
        remaining_codes=len(updated_codes)
    )

    return updated_codes


def create_mfa_enrollment_session(
    user_id: str,
    user_email: str
) -> Tuple[str, List[str], bytes]:
    """Create complete MFA enrollment session.

    Generates TOTP secret, recovery codes, and QR code for enrollment.

    Args:
        user_id: User's Firebase UID
        user_email: User's email address

    Returns:
        Tuple of (secret, recovery_codes, qr_code_png_bytes)

    Example:
        secret, codes, qr_png = create_mfa_enrollment_session("uid123", "user@example.com")
        # Display QR code to user
        # Show recovery codes for user to save
        # Store secret and hashed codes in database
    """
    # Generate TOTP secret
    secret = generate_totp_secret()

    # Generate recovery codes
    recovery_codes = generate_recovery_codes()

    # Generate QR code
    qr_code_png = generate_totp_qr_code(secret, user_email)

    logger.info(
        "Created MFA enrollment session",
        user_id=user_id,
        user_email=user_email
    )

    return secret, recovery_codes, qr_code_png
