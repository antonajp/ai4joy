"""Tests for Content Filtering Service"""

import pytest
from app.services.content_filter import ContentFilter, get_content_filter


class TestContentFilter:
    """Test suite for content filtering functionality"""

    @pytest.fixture
    def content_filter(self):
        """Create a fresh ContentFilter instance for testing"""
        return ContentFilter()

    def test_clean_input_passes_through(self, content_filter):
        """Test that clean, appropriate improv input passes through unchanged"""
        clean_inputs = [
            "Let's go to the coffee shop and meet our friends",
            "I'm excited about this scene at the library",
            "We're colleagues working on a project together",
            "This scene takes place at a restaurant",
        ]

        for input_text in clean_inputs:
            result = content_filter.filter_input(input_text)
            assert result.is_allowed, f"Clean input should be allowed: {input_text}"
            assert result.cleaned_input == input_text
            assert result.severity in ["none", "low", "medium"]
            assert len(result.violations) == 0

    def test_profanity_detection(self, content_filter):
        """Test that profanity is detected"""
        profane_inputs = [
            "What the fuck is going on here",
            "This is some bullshit situation",
            "You're such an asshole character",
            "Oh damn, that's crazy",
        ]

        for input_text in profane_inputs:
            result = content_filter.filter_input(input_text)
            assert (
                len(result.violations) > 0
            ), f"Should detect profanity in: {input_text}"
            assert any("profanity" in v for v in result.violations)

    def test_severe_content_blocked(self, content_filter):
        """Test that severe offensive content is blocked"""
        severe_inputs = [
            "I want to rape someone",
            "Go kill yourself now",
        ]

        for input_text in severe_inputs:
            result = content_filter.filter_input(input_text)
            assert (
                not result.is_allowed
            ), f"Severe content should be blocked: {input_text}"
            assert result.severity == "severe"
            assert result.cleaned_input == ""

    def test_toxic_patterns_detected(self, content_filter):
        """Test that toxic behavior patterns are detected"""
        toxic_inputs = [
            "You are stupid and dumb",
            "Go die in a fire",
            "I hate you so much",
            "You suck at improv",
        ]

        for input_text in toxic_inputs:
            result = content_filter.filter_input(input_text)
            assert (
                len(result.violations) > 0
            ), f"Should detect toxicity in: {input_text}"
            assert any("toxic" in v for v in result.violations)

    def test_partial_word_matches(self, content_filter):
        """Test that partial profanity matches are caught"""
        variations = [
            "fuuuuck",
            "shiiit",
            "daaaaamn",
        ]

        for input_text in variations:
            result = content_filter.filter_input(input_text)
            assert len(result.violations) > 0, f"Should catch variation: {input_text}"

    def test_case_insensitive_detection(self, content_filter):
        """Test that detection works regardless of case"""
        case_variants = [
            "FUCK this",
            "FuCk ThAt",
            "Damn IT",
        ]

        for input_text in case_variants:
            result = content_filter.filter_input(input_text)
            assert (
                len(result.violations) > 0
            ), f"Should detect regardless of case: {input_text}"

    def test_legitimate_improv_content_allowed(self, content_filter):
        """Test that legitimate improv content isn't falsely flagged"""
        legitimate_inputs = [
            "I'm feeling determined to find the treasure",
            "The villain character is after us",
            "This is a fine cup of coffee",
            "We're in a tough spot in this mystery",
            "What is happening in this scene?",
        ]

        for input_text in legitimate_inputs:
            result = content_filter.filter_input(input_text)
            if not result.is_allowed:
                pytest.fail(f"Legitimate improv content blocked: {input_text}")

    def test_is_toxic_convenience_method(self, content_filter):
        """Test the is_toxic convenience method"""
        assert content_filter.is_toxic("Go kill yourself") is True
        assert content_filter.is_toxic("Let's do a scene at the park") is False

    def test_filter_stats_tracking(self, content_filter):
        """Test that filter statistics are tracked correctly"""
        initial_stats = content_filter.get_filter_stats()
        assert initial_stats["total_checks"] == 0

        content_filter.filter_input("Clean input")
        content_filter.filter_input("Another clean input")
        content_filter.filter_input("Severe rape content")

        stats = content_filter.get_filter_stats()
        assert stats["total_checks"] == 3
        assert stats["blocked"] >= 1
        assert "by_severity" in stats

    def test_unicode_and_special_characters(self, content_filter):
        """Test handling of unicode and special characters"""
        unicode_inputs = [
            "Let's go to the café ☕",
            "This scene is 100% awesome! 🎭",
            "Meeting at 3:30 PM in the théâtre",
        ]

        for input_text in unicode_inputs:
            result = content_filter.filter_input(input_text)
            assert result.is_allowed, f"Unicode content should be allowed: {input_text}"

    def test_empty_and_whitespace_input(self, content_filter):
        """Test handling of edge cases like empty input"""
        edge_cases = [
            "",
            "   ",
            "\n\n\n",
            "\t\t",
        ]

        for input_text in edge_cases:
            result = content_filter.filter_input(input_text)
            assert result.is_allowed
            assert result.severity == "none"

    def test_long_input_handling(self, content_filter):
        """Test that long inputs are processed correctly"""
        long_input = "This is a very long scene description. " * 50
        result = content_filter.filter_input(long_input)
        assert result.is_allowed
        assert len(result.cleaned_input) == len(long_input)

    def test_singleton_pattern(self):
        """Test that get_content_filter returns singleton instance"""
        filter1 = get_content_filter()
        filter2 = get_content_filter()
        assert filter1 is filter2


class TestContentFilterEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_mixed_severity_violations(self):
        """Test input with multiple violation types"""
        filter_instance = ContentFilter()
        mixed_input = "You're a damn idiot and I hate you"

        result = filter_instance.filter_input(mixed_input)
        assert len(result.violations) > 0
        assert not result.is_allowed or result.severity in ["medium", "high"]

    def test_context_appropriate_language(self):
        """Test that context-appropriate language is handled correctly"""
        filter_instance = ContentFilter()

        contextual_inputs = [
            "The character says 'yeah' with enthusiasm",
            "In this scene, tensions are very high",
            "The villain is one tough character",
        ]

        for input_text in contextual_inputs:
            result = filter_instance.filter_input(input_text)
            assert result.is_allowed

    def test_repeated_profanity(self):
        """Test handling of repeated profanity"""
        filter_instance = ContentFilter()
        result = filter_instance.filter_input("fuck fuck fuck fuck")

        assert not result.is_allowed
        assert result.severity in ["high", "severe"]
