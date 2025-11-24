"""Tests for PII Detection and Redaction Service"""
import pytest
from app.services.pii_detector import PIIDetector, get_pii_detector


class TestPIIDetector:
    """Test suite for PII detection and redaction"""

    @pytest.fixture
    def pii_detector(self):
        """Create a fresh PIIDetector instance for testing"""
        return PIIDetector()

    def test_email_detection_and_redaction(self, pii_detector):
        """Test detection and redaction of email addresses"""
        test_cases = [
            ("Contact me at john.doe@example.com", "Contact me at [REDACTED_EMAIL]"),
            ("Email: user123@test-domain.org", "Email: [REDACTED_EMAIL]"),
            ("My email is alice_smith@company.co.uk", "My email is [REDACTED_EMAIL]"),
        ]

        for input_text, expected_redacted in test_cases:
            result = pii_detector.detect_pii(input_text)
            assert result.has_pii, f"Should detect email in: {input_text}"
            assert len([d for d in result.detections if d.pii_type == "email"]) > 0
            assert result.redacted_text == expected_redacted

    def test_phone_number_detection(self, pii_detector):
        """Test detection of various phone number formats"""
        phone_formats = [
            "Call me at 555-123-4567",
            "My number is (555) 123-4567",
            "Phone: 555.123.4567",
            "International: +1 555 123 4567",
            "Contact: +44 20 7123 4567",
        ]

        for input_text in phone_formats:
            result = pii_detector.detect_pii(input_text)
            assert result.has_pii, f"Should detect phone in: {input_text}"
            assert any(d.pii_type == "phone" for d in result.detections)
            assert "[REDACTED_PHONE]" in result.redacted_text

    def test_ssn_detection_and_redaction(self, pii_detector):
        """Test detection and redaction of Social Security Numbers"""
        ssn_formats = [
            ("SSN: 123-45-6789", "SSN: [REDACTED_SSN]"),
            ("Social Security Number 123 45 6789", "Social Security Number [REDACTED_SSN]"),
            ("My SSN is 123456789", "My SSN is [REDACTED_SSN]"),
        ]

        for input_text, expected_pattern in ssn_formats:
            result = pii_detector.detect_pii(input_text)
            assert result.has_pii, f"Should detect SSN in: {input_text}"
            assert any(d.pii_type == "ssn" for d in result.detections)
            assert "[REDACTED_SSN]" in result.redacted_text

    def test_credit_card_detection(self, pii_detector):
        """Test detection of credit card numbers"""
        valid_cards = [
            "4532015112830366",
            "5425233430109903",
            "374245455400126",
            "6011111111111117",
        ]

        for card_number in valid_cards:
            input_text = f"Card: {card_number}"
            result = pii_detector.detect_pii(input_text)
            assert result.has_pii, f"Should detect credit card: {card_number}"
            assert any(d.pii_type == "credit_card" for d in result.detections)
            assert "[REDACTED_CREDIT_CARD]" in result.redacted_text

    def test_invalid_credit_card_not_detected(self, pii_detector):
        """Test that invalid credit card numbers are not flagged"""
        invalid_cards = [
            "1234567890123456",
            "0000000000000000",
            "1111222233334444",
        ]

        for card_number in invalid_cards:
            input_text = f"Number: {card_number}"
            result = pii_detector.detect_pii(input_text)
            credit_card_detections = [d for d in result.detections if d.pii_type == "credit_card"]
            assert len(credit_card_detections) == 0, f"Should not detect invalid card: {card_number}"

    def test_multiple_pii_types_in_single_input(self, pii_detector):
        """Test detection of multiple PII types in one input"""
        mixed_pii = "Contact John at john@example.com or call 555-123-4567"
        result = pii_detector.detect_pii(mixed_pii)

        assert result.has_pii
        assert len(result.detections) >= 2
        assert any(d.pii_type == "email" for d in result.detections)
        assert any(d.pii_type == "phone" for d in result.detections)
        assert "[REDACTED_EMAIL]" in result.redacted_text
        assert "[REDACTED_PHONE]" in result.redacted_text

    def test_no_false_positives_on_improv_text(self, pii_detector):
        """Test that legitimate improv content doesn't trigger false positives"""
        improv_texts = [
            "Let's do a scene at the coffee shop on 5th Street",
            "The character is 25 years old and works in IT",
            "We're meeting at coordinates 123.456 and 789.012",
            "The password is 1234 and the code is 5678",
            "Scene number 555 takes place in the year 2024",
            "Call scene partners for a 10-minute rehearsal",
        ]

        for input_text in improv_texts:
            result = pii_detector.detect_pii(input_text)
            if result.has_pii:
                pytest.fail(f"False positive PII detection in: {input_text} - detected: {[d.pii_type for d in result.detections]}")

    def test_redact_pii_convenience_method(self, pii_detector):
        """Test the redact_pii convenience method"""
        input_with_pii = "Email me at test@example.com with your phone 555-1234"
        redacted = pii_detector.redact_pii(input_with_pii)

        assert "[REDACTED_EMAIL]" in redacted
        assert "test@example.com" not in redacted

    def test_has_pii_convenience_method(self, pii_detector):
        """Test the has_pii convenience method"""
        assert pii_detector.has_pii("Contact: john@example.com") is True
        assert pii_detector.has_pii("Let's meet at the park") is False

    def test_clean_input_passes_through(self, pii_detector):
        """Test that input without PII passes through unchanged"""
        clean_inputs = [
            "Let's do an improv scene at the library",
            "The character is excited about the adventure",
            "We're colleagues working on a project together",
            "This scene takes place in the year 2024",
        ]

        for input_text in clean_inputs:
            result = pii_detector.detect_pii(input_text)
            assert not result.has_pii
            assert result.redacted_text == input_text
            assert len(result.detections) == 0

    def test_pii_stats_tracking(self, pii_detector):
        """Test that PII detection statistics are tracked"""
        initial_stats = pii_detector.get_stats()
        assert initial_stats["total_checks"] == 0

        pii_detector.detect_pii("Clean text")
        pii_detector.detect_pii("Email: test@example.com")
        pii_detector.detect_pii("Phone: 555-123-4567")

        stats = pii_detector.get_stats()
        assert stats["total_checks"] == 3
        assert stats["pii_detected"] >= 2
        assert "by_type" in stats
        assert stats["by_type"]["email"] >= 1
        assert stats["by_type"]["phone"] >= 1

    def test_empty_input_handling(self, pii_detector):
        """Test handling of empty or whitespace input"""
        edge_cases = ["", "   ", "\n\n", "\t"]

        for input_text in edge_cases:
            result = pii_detector.detect_pii(input_text)
            assert not result.has_pii
            assert result.redacted_text == input_text

    def test_unicode_text_with_pii(self, pii_detector):
        """Test PII detection in unicode text"""
        unicode_with_pii = "Contact moi à test@example.com pour plus d'informations"
        result = pii_detector.detect_pii(unicode_with_pii)

        assert result.has_pii
        assert "[REDACTED_EMAIL]" in result.redacted_text

    def test_multiple_same_type_pii(self, pii_detector):
        """Test detection of multiple instances of same PII type"""
        multiple_emails = "Email john@example.com or jane@example.com or bob@test.org"
        result = pii_detector.detect_pii(multiple_emails)

        email_detections = [d for d in result.detections if d.pii_type == "email"]
        assert len(email_detections) == 3
        assert result.redacted_text.count("[REDACTED_EMAIL]") == 3

    def test_pii_in_long_text(self, pii_detector):
        """Test PII detection in longer text blocks"""
        long_text = (
            "This is a long improv scene description that goes on for a while. "
            "In the middle of it, there's an email address: secret@example.com "
            "and a phone number 555-987-6543. The scene continues with more "
            "description and dialogue, creating a realistic test case for "
            "PII detection in production scenarios."
        )

        result = pii_detector.detect_pii(long_text)
        assert result.has_pii
        assert "secret@example.com" not in result.redacted_text
        assert "555-987-6543" not in result.redacted_text
        assert "[REDACTED_EMAIL]" in result.redacted_text
        assert "[REDACTED_PHONE]" in result.redacted_text

    def test_singleton_pattern(self):
        """Test that get_pii_detector returns singleton instance"""
        detector1 = get_pii_detector()
        detector2 = get_pii_detector()
        assert detector1 is detector2


class TestPIIDetectorEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_partial_pii_patterns(self):
        """Test that partial patterns are not falsely detected"""
        detector = PIIDetector()

        partial_patterns = [
            "The number is 555-12 (incomplete)",
            "Email format test@",
            "SSN fragment 123-45",
        ]

        for input_text in partial_patterns:
            result = detector.detect_pii(input_text)
            if result.has_pii:
                pytest.fail(f"Should not detect partial pattern: {input_text}")

    def test_pii_at_boundaries(self):
        """Test PII detection at start/end of text"""
        detector = PIIDetector()

        boundary_cases = [
            "test@example.com is my email",
            "My email is test@example.com",
            "test@example.com",
        ]

        for input_text in boundary_cases:
            result = detector.detect_pii(input_text)
            assert result.has_pii
            assert "[REDACTED_EMAIL]" in result.redacted_text

    def test_redaction_preserves_structure(self):
        """Test that redaction preserves text structure"""
        detector = PIIDetector()
        structured_text = "Name: John\nEmail: john@example.com\nPhone: 555-1234\nNotes: Call after 5pm"

        result = detector.detect_pii(structured_text)
        lines = result.redacted_text.split("\n")
        assert len(lines) == 4
        assert "Name: John" in result.redacted_text
        assert "Notes: Call after 5pm" in result.redacted_text
