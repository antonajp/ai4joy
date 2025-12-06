"""Sentiment Analysis Toolset - ADK BaseToolset for Audience Sentiment Analysis

This toolset provides sentiment analysis tools backed by Firestore keyword lists.
Used by the Room Agent for analyzing audience reactions and engagement.

The sentiment keywords (positive, negative, engagement) are stored in Firestore
and loaded dynamically, allowing for updates without code changes.

Follows ADK patterns:
- Extends BaseToolset for proper ADK integration
- Uses FunctionTool to wrap async functions
- Caches keyword lists for performance
"""

from typing import Optional, List, Dict, Any, Union
from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.base_toolset import BaseToolset, ToolPredicate
from google.adk.agents.readonly_context import ReadonlyContext

from app.services import firestore_tool_data_service as data_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SentimentAnalysisToolset(BaseToolset):
    """ADK Toolset for sentiment analysis with Firestore-backed keywords.

    Provides tools for:
    - analyze_text: Analyze sentiment from text input
    - analyze_engagement: Analyze audience engagement from observations
    - analyze_collective_mood: Combine sentiment and engagement analysis

    Keywords are loaded from Firestore on first use and cached.

    Example usage with ADK Agent:
        ```python
        from app.toolsets import SentimentAnalysisToolset

        toolset = SentimentAnalysisToolset()
        agent = Agent(
            name="room_agent",
            model="gemini-2.0-flash",
            instruction="...",
            tools=[toolset],
        )
        ```
    """

    def __init__(
        self,
        *,
        tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
        tool_name_prefix: Optional[str] = None,
    ):
        """Initialize the SentimentAnalysisToolset.

        Args:
            tool_filter: Optional filter to include specific tools by name or predicate
            tool_name_prefix: Optional prefix to prepend to all tool names
        """
        super().__init__(tool_filter=tool_filter, tool_name_prefix=tool_name_prefix)
        self._tools: Optional[List[BaseTool]] = None
        self._keywords_cache: Optional[Dict[str, Any]] = None
        logger.info("SentimentAnalysisToolset initialized")

    async def _ensure_keywords_loaded(self) -> Dict[str, Any]:
        """Load sentiment keywords from Firestore if not cached.

        Returns:
            Dictionary with positive, negative, and engagement keyword lists.
        """
        if self._keywords_cache is None:
            self._keywords_cache = await data_service.get_sentiment_keywords()
            logger.debug(
                "Sentiment keywords loaded",
                positive_count=len(self._keywords_cache.get("positive", [])),
                negative_count=len(self._keywords_cache.get("negative", [])),
            )
        return self._keywords_cache

    async def get_tools(
        self,
        readonly_context: Optional[ReadonlyContext] = None,
    ) -> List[BaseTool]:
        """Return all sentiment analysis tools.

        Args:
            readonly_context: Optional context for filtering tools

        Returns:
            List of FunctionTool instances wrapping sentiment functions
        """
        if self._tools is None:
            self._tools = [
                FunctionTool(self.analyze_text),
                FunctionTool(self.analyze_engagement),
                FunctionTool(self.analyze_collective_mood),
            ]
            logger.debug("Sentiment tools created", tool_count=len(self._tools))

        # Apply tool filter if provided
        if self.tool_filter and readonly_context:
            return [
                tool
                for tool in self._tools
                if self._is_tool_selected(tool, readonly_context)
            ]

        return self._tools

    async def analyze_text(self, text: str) -> Dict[str, Any]:
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

        keywords = await self._ensure_keywords_loaded()
        positive_keywords = keywords.get("positive", [])
        negative_keywords = keywords.get("negative", [])

        text_lower = text.lower()

        positive_count = sum(
            1 for keyword in positive_keywords if keyword in text_lower
        )
        negative_count = sum(
            1 for keyword in negative_keywords if keyword in text_lower
        )

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
            "neutral": (
                "Audience reaction is neutral - neither strongly positive nor negative."
            ),
            "negative": "Audience seems underwhelmed or mildly negative.",
            "very_negative": (
                "Audience is showing strong negative reaction. "
                "Consider changing approach."
            ),
        }

        result = {
            "sentiment": sentiment,
            "sentiment_score": round(sentiment_score, 2),
            "positive_indicators": positive_count,
            "negative_indicators": negative_count,
            "text_length": len(text),
            "analysis_summary": summary_map.get(
                sentiment, "Unable to determine sentiment"
            ),
        }

        logger.info(
            "Text sentiment analyzed",
            sentiment=sentiment,
            score=result["sentiment_score"],
            text_length=result["text_length"],
        )

        return result

    async def analyze_engagement(self, observations: List[str]) -> Dict[str, Any]:
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

        keywords = await self._ensure_keywords_loaded()
        engagement_keywords = keywords.get("engagement", {"high": [], "low": []})
        high_engagement_keywords = engagement_keywords.get("high", [])
        low_engagement_keywords = engagement_keywords.get("low", [])

        combined_text = " ".join(observations).lower()

        high_engagement_count = sum(
            1 for keyword in high_engagement_keywords if keyword in combined_text
        )

        low_engagement_count = sum(
            1 for keyword in low_engagement_keywords if keyword in combined_text
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
            "summary": summary_map.get(
                engagement, "Unable to determine engagement level"
            ),
        }

        logger.info(
            "Engagement analyzed",
            engagement=engagement,
            score=result["engagement_score"],
            observations=len(observations),
        )

        return result

    async def analyze_collective_mood(
        self,
        text_inputs: Optional[List[str]] = None,
        observations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Analyze overall collective audience mood from multiple signals.

        Args:
            text_inputs: List of text inputs (comments, suggestions)
            observations: List of behavioral observations

        Returns:
            Dictionary with comprehensive mood analysis combining sentiment
            and engagement.
        """
        sentiment_results = []
        if text_inputs:
            for text in text_inputs:
                sentiment_results.append(await self.analyze_text(text))

        engagement_result = None
        if observations:
            engagement_result = await self.analyze_engagement(observations)

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
            "enthusiastic": (
                "Ride this energy! Try more ambitious or interactive games."
            ),
            "positive": "Keep momentum going. Audience is with you.",
            "neutral": (
                "Warm up the audience. Try a high-energy game or more interaction."
            ),
            "lukewarm": ("Change the energy. Consider switching game types or style."),
            "disengaged": (
                "Reset needed. "
                "Try audience participation or break from current approach."
            ),
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
            "Collective mood analyzed",
            mood=overall_mood,
            mood_score=result["mood_score"],
        )

        return result

    async def close(self) -> None:
        """Cleanup resources when toolset is no longer needed."""
        self._tools = None
        self._keywords_cache = None
        logger.debug("SentimentAnalysisToolset closed")
