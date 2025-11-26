"""Sentiment Gauge Tools - Async Functions for Audience Reaction Analysis"""

from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Sentiment keywords for lightweight analysis
POSITIVE_KEYWORDS = [
    "love",
    "amazing",
    "awesome",
    "great",
    "fantastic",
    "hilarious",
    "brilliant",
    "perfect",
    "wonderful",
    "excited",
    "fun",
    "enjoyed",
    "laughing",
    "yes",
    "more",
    "best",
    "incredible",
    "excellent",
]

NEGATIVE_KEYWORDS = [
    "boring",
    "bad",
    "terrible",
    "awful",
    "hate",
    "worst",
    "slow",
    "confusing",
    "awkward",
    "uncomfortable",
    "disappointed",
    "meh",
    "lame",
    "tired",
    "done",
    "enough",
    "stop",
    "no",
]

ENGAGEMENT_KEYWORDS = {
    "high": [
        "excited",
        "participating",
        "volunteering",
        "shouting",
        "active",
        "energetic",
    ],
    "low": ["quiet", "silent", "checking phones", "leaving", "distracted", "yawning"],
}


async def analyze_text(text: str) -> dict:
    """Analyze sentiment from text input (audience comments, suggestions).

    Args:
        text: Input text to analyze

    Returns:
        Dictionary with sentiment analysis results including score and summary.
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for sentiment analysis")
        return {
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "positive_indicators": 0,
            "negative_indicators": 0,
            "text_length": 0,
            "analysis_summary": "No text provided for analysis",
        }

    text_lower = text.lower()

    positive_count = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text_lower)
    negative_count = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text_lower)

    total_sentiment_words = positive_count + negative_count

    if total_sentiment_words == 0:
        sentiment = "neutral"
        sentiment_score = 0.0
    else:
        sentiment_score = (positive_count - negative_count) / total_sentiment_words

        if sentiment_score >= 0.6:
            sentiment = "very_positive"
        elif sentiment_score >= 0.2:
            sentiment = "positive"
        elif sentiment_score <= -0.6:
            sentiment = "very_negative"
        elif sentiment_score <= -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"

    summary_map = {
        "very_positive": "Audience is loving this! Strong positive reaction.",
        "positive": "Audience is responding well with positive energy.",
        "neutral": "Audience reaction is neutral - neither strongly positive nor negative.",
        "negative": "Audience seems underwhelmed or mildly negative.",
        "very_negative": "Audience is showing strong negative reaction. Consider changing approach.",
    }

    result = {
        "sentiment": sentiment,
        "sentiment_score": round(sentiment_score, 2),
        "positive_indicators": positive_count,
        "negative_indicators": negative_count,
        "text_length": len(text),
        "analysis_summary": summary_map.get(sentiment, "Unable to determine sentiment"),
    }

    logger.info(
        "Text sentiment analyzed",
        sentiment=sentiment,
        score=result["sentiment_score"],
        text_length=result["text_length"],
    )

    return result


async def analyze_engagement(observations: list[str]) -> dict:
    """Analyze audience engagement from behavioral observations.

    Args:
        observations: List of observed audience behaviors

    Returns:
        Dictionary with engagement level, score, and summary.
    """
    if not observations:
        logger.warning("No observations provided for engagement analysis")
        return {
            "engagement": "moderate",
            "engagement_score": 0.5,
            "summary": "Insufficient data for engagement assessment",
            "high_engagement_indicators": 0,
            "low_engagement_indicators": 0,
            "observation_count": 0,
        }

    combined_text = " ".join(observations).lower()

    high_engagement_count = sum(
        1 for keyword in ENGAGEMENT_KEYWORDS["high"] if keyword in combined_text
    )

    low_engagement_count = sum(
        1 for keyword in ENGAGEMENT_KEYWORDS["low"] if keyword in combined_text
    )

    total_engagement_indicators = high_engagement_count + low_engagement_count

    if total_engagement_indicators == 0:
        engagement = "moderate"
        engagement_score = 0.5
    else:
        engagement_score = high_engagement_count / total_engagement_indicators

        if engagement_score >= 0.8:
            engagement = "highly_engaged"
        elif engagement_score >= 0.6:
            engagement = "engaged"
        elif engagement_score <= 0.2:
            engagement = "disengaged"
        elif engagement_score <= 0.4:
            engagement = "low"
        else:
            engagement = "moderate"

    summary_map = {
        "highly_engaged": "Audience is highly engaged and actively participating.",
        "engaged": "Audience is engaged and attentive.",
        "moderate": "Audience engagement is moderate - some interest shown.",
        "low": "Audience engagement is low - may need energy boost.",
        "disengaged": "Audience appears disengaged. Consider changing tactics.",
    }

    result = {
        "engagement": engagement,
        "engagement_score": round(engagement_score, 2),
        "high_engagement_indicators": high_engagement_count,
        "low_engagement_indicators": low_engagement_count,
        "observation_count": len(observations),
        "summary": summary_map.get(engagement, "Unable to determine engagement level"),
    }

    logger.info(
        "Engagement analyzed",
        engagement=engagement,
        score=result["engagement_score"],
        observations=len(observations),
    )

    return result


async def analyze_collective_mood(
    text_inputs: Optional[list[str]] = None, observations: Optional[list[str]] = None
) -> dict:
    """Analyze overall collective audience mood from multiple signals.

    Args:
        text_inputs: List of text inputs (comments, suggestions)
        observations: List of behavioral observations

    Returns:
        Dictionary with comprehensive mood analysis combining sentiment and engagement.
    """
    sentiment_results = []
    if text_inputs:
        for text in text_inputs:
            sentiment_results.append(await analyze_text(text))

    engagement_result = None
    if observations:
        engagement_result = await analyze_engagement(observations)

    if not sentiment_results and not engagement_result:
        logger.warning("No data provided for collective mood analysis")
        return {
            "overall_mood": "neutral",
            "mood_score": 0.0,
            "sentiment_score": 0.0,
            "engagement_score": 0.5,
            "text_inputs_analyzed": 0,
            "observations_analyzed": 0,
            "recommendation": "Monitor audience closely and adapt as needed.",
        }

    avg_sentiment_score = 0.0
    if sentiment_results:
        avg_sentiment_score = sum(
            r["sentiment_score"] for r in sentiment_results
        ) / len(sentiment_results)

    engagement_score = (
        engagement_result["engagement_score"] if engagement_result else 0.5
    )

    overall_mood_score = (avg_sentiment_score + engagement_score) / 2

    if overall_mood_score >= 0.7:
        overall_mood = "enthusiastic"
    elif overall_mood_score >= 0.4:
        overall_mood = "positive"
    elif overall_mood_score >= -0.2:
        overall_mood = "neutral"
    elif overall_mood_score >= -0.5:
        overall_mood = "lukewarm"
    else:
        overall_mood = "disengaged"

    recommendations = {
        "enthusiastic": "Ride this energy! Try more ambitious or interactive games.",
        "positive": "Keep momentum going. Audience is with you.",
        "neutral": "Warm up the audience. Try a high-energy game or more interaction.",
        "lukewarm": "Change the energy. Consider switching game types or style.",
        "disengaged": "Reset needed. Try audience participation or break from current approach.",
    }

    result = {
        "overall_mood": overall_mood,
        "mood_score": round(overall_mood_score, 2),
        "sentiment_score": round(avg_sentiment_score, 2),
        "engagement_score": engagement_score,
        "text_inputs_analyzed": len(text_inputs) if text_inputs else 0,
        "observations_analyzed": len(observations) if observations else 0,
        "recommendation": recommendations.get(
            overall_mood, "Monitor audience closely and adapt as needed."
        ),
    }

    logger.info(
        "Collective mood analyzed", mood=overall_mood, mood_score=result["mood_score"]
    )

    return result
