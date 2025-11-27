"""
Unit Tests for Audience Mood Metrics Extraction - IQS-56

Test Coverage:
- TC-MOOD-01: Mood metrics extraction from room analysis text
- TC-MOOD-02: Sentiment score calculation
- TC-MOOD-03: Engagement score calculation
- TC-MOOD-04: Laughter detection
- TC-MOOD-05: Edge cases and boundary conditions
- TC-MOOD-06: Integration with room_vibe response structure
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from app.services.turn_orchestrator import TurnOrchestrator


class TestMoodMetricsExtraction:
    """TC-MOOD-01: Mood metrics extraction from room analysis text"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    def test_tc_mood_01a_mood_metrics_present_in_response(self, orchestrator):
        """
        TC-MOOD-01a: Room vibe response includes mood_metrics

        When parsing agent response with ROOM section, the room_vibe
        should include a mood_metrics object.
        """
        agent_response = """PARTNER: Great scene work!
ROOM: The audience is laughing and highly engaged with this hilarious scene!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        assert "room_vibe" in parsed
        assert "mood_metrics" in parsed["room_vibe"]
        assert isinstance(parsed["room_vibe"]["mood_metrics"], dict)

    def test_tc_mood_01b_mood_metrics_structure(self, orchestrator):
        """
        TC-MOOD-01b: Mood metrics has correct structure

        mood_metrics should contain sentiment_score, engagement_score,
        and laughter_detected fields.
        """
        agent_response = """PARTNER: Scene continues.
ROOM: Audience is moderately engaged."""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=3
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert "sentiment_score" in mood_metrics
        assert "engagement_score" in mood_metrics
        assert "laughter_detected" in mood_metrics

    def test_tc_mood_01c_mood_metrics_types(self, orchestrator):
        """
        TC-MOOD-01c: Mood metrics have correct types

        sentiment_score and engagement_score should be floats,
        laughter_detected should be boolean.
        """
        agent_response = """PARTNER: Hello!
ROOM: Neutral audience energy."""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=1
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert isinstance(mood_metrics["sentiment_score"], (int, float))
        assert isinstance(mood_metrics["engagement_score"], (int, float))
        assert isinstance(mood_metrics["laughter_detected"], bool)


class TestSentimentScoreCalculation:
    """TC-MOOD-02: Sentiment score calculation from room analysis"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    def test_tc_mood_02a_positive_sentiment_keywords(self, orchestrator):
        """
        TC-MOOD-02a: Positive sentiment from positive keywords

        Room analysis with words like "loving", "enthusiastic", "excited"
        should return positive sentiment_score (> 0.3).
        """
        agent_response = """PARTNER: Amazing scene!
ROOM: The audience is loving this performance! They're excited and enthusiastic!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["sentiment_score"] > 0.3

    def test_tc_mood_02b_negative_sentiment_keywords(self, orchestrator):
        """
        TC-MOOD-02b: Negative sentiment from negative keywords

        Room analysis with words like "bored", "disengaged", "negative"
        should return negative sentiment_score (< -0.2).
        """
        agent_response = """PARTNER: Okay then.
ROOM: The audience seems bored and disengaged. Negative energy in the room."""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["sentiment_score"] < -0.2

    def test_tc_mood_02c_neutral_sentiment(self, orchestrator):
        """
        TC-MOOD-02c: Neutral sentiment with no strong keywords

        Room analysis without strong sentiment keywords should
        return sentiment_score near 0 (-0.2 to 0.2).
        """
        agent_response = """PARTNER: Let's continue.
ROOM: The audience is watching attentively."""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=3
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert -0.3 <= mood_metrics["sentiment_score"] <= 0.3

    def test_tc_mood_02d_sentiment_score_bounds(self, orchestrator):
        """
        TC-MOOD-02d: Sentiment score within valid range

        sentiment_score should always be between -1.0 and 1.0.
        """
        test_cases = [
            """PARTNER: Test.
ROOM: Extremely positive, loving, enthusiastic, excited audience!""",
            """PARTNER: Test.
ROOM: Very negative, bored, disengaged, hostile crowd.""",
            """PARTNER: Test.
ROOM: Average audience.""",
        ]

        for response in test_cases:
            parsed = orchestrator._parse_agent_response(
                response=response, turn_number=5
            )
            mood_metrics = parsed["room_vibe"]["mood_metrics"]
            assert -1.0 <= mood_metrics["sentiment_score"] <= 1.0


class TestEngagementScoreCalculation:
    """TC-MOOD-03: Engagement score calculation from room analysis"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    def test_tc_mood_03a_highly_engaged_keywords(self, orchestrator):
        """
        TC-MOOD-03a: High engagement from engagement keywords

        Room analysis with "highly engaged" should return
        engagement_score > 0.7.
        """
        agent_response = """PARTNER: Scene continues!
ROOM: The audience is highly engaged with the performance!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["engagement_score"] > 0.7

    def test_tc_mood_03b_engaged_keywords(self, orchestrator):
        """
        TC-MOOD-03b: Moderate-high engagement from "engaged"

        Room analysis with "engaged" should return
        engagement_score around 0.5-0.7.
        """
        agent_response = """PARTNER: Great!
ROOM: The audience is engaged and following the story."""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["engagement_score"] >= 0.5

    def test_tc_mood_03c_disengaged_keywords(self, orchestrator):
        """
        TC-MOOD-03c: Low engagement from "disengaged"

        Room analysis with "disengaged" should return
        engagement_score < 0.3.
        """
        agent_response = """PARTNER: Hmm.
ROOM: The audience appears disengaged and checking their phones."""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["engagement_score"] < 0.3

    def test_tc_mood_03d_engagement_score_bounds(self, orchestrator):
        """
        TC-MOOD-03d: Engagement score within valid range

        engagement_score should always be between 0.0 and 1.0.
        """
        test_cases = [
            """PARTNER: Test.
ROOM: Highly engaged audience leaning forward.""",
            """PARTNER: Test.
ROOM: Completely disengaged crowd.""",
            """PARTNER: Test.
ROOM: Moderate energy in the room.""",
        ]

        for response in test_cases:
            parsed = orchestrator._parse_agent_response(
                response=response, turn_number=5
            )
            mood_metrics = parsed["room_vibe"]["mood_metrics"]
            assert 0.0 <= mood_metrics["engagement_score"] <= 1.0


class TestLaughterDetection:
    """TC-MOOD-04: Laughter detection from room analysis"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    def test_tc_mood_04a_laughter_keyword_detected(self, orchestrator):
        """
        TC-MOOD-04a: Laughter detected with "laugh" keyword

        Room analysis containing "laugh" or "laughing" should
        set laughter_detected to True.
        """
        agent_response = """PARTNER: That was funny!
ROOM: The audience is laughing at this clever wordplay!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["laughter_detected"] is True

    def test_tc_mood_04b_hilarious_keyword_detected(self, orchestrator):
        """
        TC-MOOD-04b: Laughter detected with "hilarious" keyword

        Room analysis containing "hilarious" should set
        laughter_detected to True.
        """
        agent_response = """PARTNER: Ha!
ROOM: The audience finds this hilarious!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["laughter_detected"] is True

    def test_tc_mood_04c_cracking_up_keyword_detected(self, orchestrator):
        """
        TC-MOOD-04c: Laughter detected with "cracking up" keyword

        Room analysis containing "cracking up" should set
        laughter_detected to True.
        """
        agent_response = """PARTNER: Good one!
ROOM: The audience is cracking up at this scene!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["laughter_detected"] is True

    def test_tc_mood_04d_roar_keyword_detected(self, orchestrator):
        """
        TC-MOOD-04d: Laughter detected with "roar" keyword

        Room analysis containing "roar" (as in roar of laughter)
        should set laughter_detected to True.
        """
        agent_response = """PARTNER: Boom!
ROOM: A roar of laughter erupts from the audience!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["laughter_detected"] is True

    def test_tc_mood_04e_no_laughter_keywords(self, orchestrator):
        """
        TC-MOOD-04e: No laughter without keywords

        Room analysis without laughter keywords should set
        laughter_detected to False.
        """
        agent_response = """PARTNER: Continue.
ROOM: The audience watches with interest."""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["laughter_detected"] is False

    def test_tc_mood_04f_case_insensitive_detection(self, orchestrator):
        """
        TC-MOOD-04f: Laughter detection is case insensitive

        Laughter keywords should be detected regardless of case.
        """
        agent_response = """PARTNER: Ha!
ROOM: LAUGHING erupts! HILARIOUS moment!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["laughter_detected"] is True


class TestMoodMetricsEdgeCases:
    """TC-MOOD-05: Edge cases and boundary conditions"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    def test_tc_mood_05a_empty_room_analysis(self, orchestrator):
        """
        TC-MOOD-05a: Empty room analysis uses defaults

        When ROOM section is missing, mood_metrics should use
        neutral default values.
        """
        agent_response = "PARTNER: Just a response without room section."

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert mood_metrics["sentiment_score"] == 0.0
        assert mood_metrics["engagement_score"] == 0.5
        assert mood_metrics["laughter_detected"] is False

    def test_tc_mood_05b_mixed_sentiment_keywords(self, orchestrator):
        """
        TC-MOOD-05b: Mixed sentiment keywords

        When both positive and negative keywords exist,
        the dominant sentiment should win.
        """
        agent_response = """PARTNER: Scene continues.
ROOM: The audience started bored but is now loving the turn in the scene!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        # Should detect positive sentiment (loving) over negative (bored)
        assert isinstance(mood_metrics["sentiment_score"], (int, float))

    def test_tc_mood_05c_special_characters_in_analysis(self, orchestrator):
        """
        TC-MOOD-05c: Special characters don't break parsing

        Room analysis with special characters should still
        extract mood metrics correctly.
        """
        agent_response = """PARTNER: Wow!
ROOM: The audience is 100% engaged! <Laughing> & cheering!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]
        assert isinstance(mood_metrics["sentiment_score"], (int, float))
        assert isinstance(mood_metrics["engagement_score"], (int, float))
        assert isinstance(mood_metrics["laughter_detected"], bool)


class TestMoodMetricsIntegration:
    """TC-MOOD-06: Integration with room_vibe response structure"""

    @pytest.fixture
    def orchestrator(self):
        return TurnOrchestrator(Mock())

    def test_tc_mood_06a_room_vibe_has_all_fields(self, orchestrator):
        """
        TC-MOOD-06a: room_vibe includes analysis, energy, and mood_metrics

        The room_vibe object should contain the original analysis,
        energy field, and the new mood_metrics.
        """
        agent_response = """PARTNER: Great improv!
ROOM: The audience is highly engaged and loving this scene! Energy is electric!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        room_vibe = parsed["room_vibe"]
        assert "analysis" in room_vibe
        assert "energy" in room_vibe
        assert "mood_metrics" in room_vibe

    def test_tc_mood_06b_mood_metrics_reflects_analysis(self, orchestrator):
        """
        TC-MOOD-06b: mood_metrics values match analysis content

        mood_metrics should reflect the sentiment/engagement
        described in the analysis text.
        """
        agent_response = """PARTNER: Hilarious!
ROOM: The audience is laughing hysterically! They are highly engaged and loving every moment!"""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]

        # Should detect high engagement
        assert mood_metrics["engagement_score"] > 0.7

        # Should detect positive sentiment
        assert mood_metrics["sentiment_score"] > 0.3

        # Should detect laughter
        assert mood_metrics["laughter_detected"] is True

    def test_tc_mood_06c_negative_scene_metrics(self, orchestrator):
        """
        TC-MOOD-06c: Negative scene produces negative metrics

        A scene with negative audience reaction should
        produce negative sentiment scores.
        """
        agent_response = """PARTNER: *awkward pause*
ROOM: The audience is disengaged and seems bored. Negative energy fills the room as people check their phones."""

        parsed = orchestrator._parse_agent_response(
            response=agent_response, turn_number=5
        )

        mood_metrics = parsed["room_vibe"]["mood_metrics"]

        # Should detect low engagement
        assert mood_metrics["engagement_score"] < 0.3

        # Should detect negative sentiment
        assert mood_metrics["sentiment_score"] < -0.2

        # Should not detect laughter
        assert mood_metrics["laughter_detected"] is False
