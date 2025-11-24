"""PII Detection and Redaction Service"""
import re
from typing import Dict, List, Tuple, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PIIMatch:
    """Represents a detected PII pattern match"""

    def __init__(self, pii_type: str, start: int, end: int, value: str):
        self.pii_type = pii_type
        self.start = start
        self.end = end
        self.value = value


class PIIDetectionResult:
    """Result of PII detection operation"""

    def __init__(
        self,
        has_pii: bool,
        redacted_text: str,
        detections: List[PIIMatch]
    ):
        self.has_pii = has_pii
        self.redacted_text = redacted_text
        self.detections = detections


class PIIDetector:
    """
    Detects and redacts Personally Identifiable Information (PII) from text.

    Patterns covered:
    - Email addresses
    - Phone numbers (US and international formats)
    - Social Security Numbers (SSN)
    - Credit card numbers
    """

    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    PHONE_PATTERNS = [
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
        r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',
        r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
    ]

    SSN_PATTERN = r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'

    CREDIT_CARD_PATTERNS = [
        r'\b(?:4[0-9]{12}(?:[0-9]{3})?)\b',
        r'\b(?:5[1-5][0-9]{14})\b',
        r'\b(?:3[47][0-9]{13})\b',
        r'\b(?:6(?:011|5[0-9]{2})[0-9]{12})\b',
        r'\b(?:3(?:0[0-5]|[68][0-9])[0-9]{11})\b',
    ]

    def __init__(self):
        self._stats = {
            "total_checks": 0,
            "pii_detected": 0,
            "by_type": {
                "email": 0,
                "phone": 0,
                "ssn": 0,
                "credit_card": 0
            }
        }

    def detect_pii(self, text: str) -> PIIDetectionResult:
        """
        Detect PII patterns in text and return redacted version.

        Args:
            text: Input text to scan

        Returns:
            PIIDetectionResult with detection details and redacted text
        """
        self._stats["total_checks"] += 1

        detections: List[PIIMatch] = []

        email_matches = self._find_emails(text)
        detections.extend(email_matches)

        phone_matches = self._find_phones(text)
        detections.extend(phone_matches)

        ssn_matches = self._find_ssns(text)
        detections.extend(ssn_matches)

        cc_matches = self._find_credit_cards(text)
        detections.extend(cc_matches)

        has_pii = len(detections) > 0

        if has_pii:
            self._stats["pii_detected"] += 1
            for detection in detections:
                self._stats["by_type"][detection.pii_type] += 1

            logger.warning(
                "PII detected in user input",
                detection_count=len(detections),
                types=[d.pii_type for d in detections]
            )

            redacted_text = self._redact_pii(text, detections)
        else:
            redacted_text = text

        return PIIDetectionResult(
            has_pii=has_pii,
            redacted_text=redacted_text,
            detections=detections
        )

    def redact_pii(self, text: str) -> str:
        """
        Redact PII from text and return sanitized version.

        Args:
            text: Input text

        Returns:
            Text with PII replaced by redaction tokens
        """
        result = self.detect_pii(text)
        return result.redacted_text

    def has_pii(self, text: str) -> bool:
        """
        Quick check if text contains PII.

        Returns True if any PII patterns detected.
        """
        result = self.detect_pii(text)
        return result.has_pii

    def _find_emails(self, text: str) -> List[PIIMatch]:
        """Find email addresses in text"""
        matches = []
        for match in re.finditer(self.EMAIL_PATTERN, text):
            matches.append(PIIMatch(
                pii_type="email",
                start=match.start(),
                end=match.end(),
                value=match.group()
            ))
        return matches

    def _find_phones(self, text: str) -> List[PIIMatch]:
        """Find phone numbers in text"""
        matches = []
        for pattern in self.PHONE_PATTERNS:
            for match in re.finditer(pattern, text):
                phone_str = match.group()
                digits_only = re.sub(r'\D', '', phone_str)
                if len(digits_only) >= 10:
                    matches.append(PIIMatch(
                        pii_type="phone",
                        start=match.start(),
                        end=match.end(),
                        value=match.group()
                    ))
        return matches

    def _find_ssns(self, text: str) -> List[PIIMatch]:
        """Find Social Security Numbers in text"""
        matches = []
        for match in re.finditer(self.SSN_PATTERN, text):
            ssn_str = match.group()
            digits_only = re.sub(r'\D', '', ssn_str)
            if len(digits_only) == 9:
                matches.append(PIIMatch(
                    pii_type="ssn",
                    start=match.start(),
                    end=match.end(),
                    value=match.group()
                ))
        return matches

    def _find_credit_cards(self, text: str) -> List[PIIMatch]:
        """Find credit card numbers in text"""
        matches = []
        for pattern in self.CREDIT_CARD_PATTERNS:
            for match in re.finditer(pattern, text):
                cc_str = match.group()
                digits_only = re.sub(r'\D', '', cc_str)
                if self._luhn_check(digits_only):
                    matches.append(PIIMatch(
                        pii_type="credit_card",
                        start=match.start(),
                        end=match.end(),
                        value=match.group()
                    ))
        return matches

    def _luhn_check(self, card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm"""
        def digits_of(n):
            return [int(d) for d in str(n)]

        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10 == 0

    def _redact_pii(self, text: str, detections: List[PIIMatch]) -> str:
        """Replace PII values with redaction tokens"""
        detections_sorted = sorted(detections, key=lambda x: x.start, reverse=True)

        redacted = text
        for detection in detections_sorted:
            redaction_token = f"[REDACTED_{detection.pii_type.upper()}]"
            redacted = (
                redacted[:detection.start] +
                redaction_token +
                redacted[detection.end:]
            )

        return redacted

    def get_stats(self) -> Dict[str, any]:
        """Get PII detection statistics"""
        return {
            "total_checks": self._stats["total_checks"],
            "pii_detected": self._stats["pii_detected"],
            "detection_rate": (
                self._stats["pii_detected"] / self._stats["total_checks"]
                if self._stats["total_checks"] > 0
                else 0.0
            ),
            "by_type": self._stats["by_type"].copy()
        }


_detector_instance: Optional[PIIDetector] = None


def get_pii_detector() -> PIIDetector:
    """Get singleton PII detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = PIIDetector()
    return _detector_instance
