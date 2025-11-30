"""Audience Archetypes Toolset - ADK BaseToolset for Audience Demographics

This toolset provides access to audience archetype data stored in Firestore.
Used by the Room Agent for understanding audience composition and preferences.

Follows ADK patterns:
- Extends BaseToolset for proper ADK integration
- Uses FunctionTool to wrap async functions
- Supports tool filtering and prefixing
"""

import random
from typing import Optional, List, Dict, Any, Union
from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.base_toolset import BaseToolset, ToolPredicate
from google.adk.agents.readonly_context import ReadonlyContext

from app.services import firestore_tool_data_service as data_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AudienceArchetypesToolset(BaseToolset):
    """ADK Toolset for accessing audience archetypes from Firestore.

    Provides tools for:
    - generate_audience_sample: Generate diverse audience sample
    - get_all_archetypes: List all available archetypes
    - analyze_audience_traits: Analyze audience for dominant traits
    - get_vibe_check: Generate quick vibe assessment

    Example usage with ADK Agent:
        ```python
        from app.toolsets import AudienceArchetypesToolset

        toolset = AudienceArchetypesToolset()
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
        """Initialize the AudienceArchetypesToolset.

        Args:
            tool_filter: Optional filter to include specific tools by name or predicate
            tool_name_prefix: Optional prefix to prepend to all tool names
        """
        super().__init__(tool_filter=tool_filter, tool_name_prefix=tool_name_prefix)
        self._tools: Optional[List[BaseTool]] = None
        logger.info("AudienceArchetypesToolset initialized")

    async def get_tools(
        self,
        readonly_context: Optional[ReadonlyContext] = None,
    ) -> List[BaseTool]:
        """Return all audience archetype tools.

        Args:
            readonly_context: Optional context for filtering tools

        Returns:
            List of FunctionTool instances wrapping archetype functions
        """
        if self._tools is None:
            self._tools = [
                FunctionTool(self._generate_audience_sample),
                FunctionTool(self._get_all_archetypes),
                FunctionTool(self._analyze_audience_traits),
                FunctionTool(self._get_vibe_check),
                FunctionTool(self._generate_audience_suggestion),
                FunctionTool(self._get_suggestion_for_game),
            ]
            logger.debug("Archetype tools created", tool_count=len(self._tools))

        # Apply tool filter if provided
        if self.tool_filter and readonly_context:
            return [
                tool
                for tool in self._tools
                if self._is_tool_selected(tool, readonly_context)
            ]

        return self._tools

    async def _generate_audience_sample(self, size: int = 5) -> List[Dict[str, Any]]:
        """Generate diverse audience sample with multiple archetypes.

        Args:
            size: Number of audience archetypes to generate (default 5)

        Returns:
            List of audience member dictionaries with demographics and preferences.
        """
        all_archetypes = await data_service.get_all_archetypes()

        if size > len(all_archetypes):
            logger.warning(
                "Requested size exceeds available archetypes",
                requested=size,
                available=len(all_archetypes),
            )
            size = len(all_archetypes)

        selected = random.sample(all_archetypes, size)

        audience = []
        for i, archetype in enumerate(selected, 1):
            member = {"id": f"audience_member_{i}", **archetype}
            audience.append(member)

        logger.info("Audience sample generated", size=size)
        return audience

    async def _get_all_archetypes(self) -> List[Dict[str, Any]]:
        """Get complete list of all available audience archetypes.

        Returns:
            List of all archetype dictionaries.
        """
        return await data_service.get_all_archetypes()

    async def _analyze_audience_traits(
        self, audience: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze audience sample for dominant traits and preferences.

        Args:
            audience: List of audience member dictionaries

        Returns:
            Dictionary with dominant characteristics and recommendation.
        """
        all_preferences = []
        high_engagement = 0
        low_engagement = 0
        experienced = 0
        beginners = 0

        for member in audience:
            preferences = member.get("preferences", "")
            if isinstance(preferences, str):
                all_preferences.extend(preferences.split(", "))
            elif isinstance(preferences, list):
                all_preferences.extend(preferences)

            engagement_style = member.get("engagement_style", "").lower()
            if "vocal" in engagement_style or "expressive" in engagement_style:
                high_engagement += 1
            elif "quiet" in engagement_style or "reserved" in engagement_style:
                low_engagement += 1

            improv_knowledge = member.get("improv_knowledge", "").lower()
            if "extensive" in improv_knowledge or "professional" in improv_knowledge:
                experienced += 1
            elif "no prior" in improv_knowledge or "limited" in improv_knowledge:
                beginners += 1

        energy_profile = "mixed"
        if high_engagement > low_engagement * 1.5:
            energy_profile = "high_energy"
        elif low_engagement > high_engagement * 1.5:
            energy_profile = "reserved"

        experience_profile = "mixed"
        if experienced > beginners * 1.5:
            experience_profile = "experienced"
        elif beginners > experienced * 1.5:
            experience_profile = "beginner_friendly"

        recommendations = {
            ("high_energy", "experienced"): (
                "Try advanced games with audience participation. "
                "They'll appreciate creative risks."
            ),
            ("high_energy", "beginner_friendly"): (
                "Focus on accessible, energetic games with clear rules. "
                "Build confidence early."
            ),
            ("high_energy", "mixed"): (
                "Mix classic crowd-pleasers with a few adventurous choices. "
                "Read the room as you go."
            ),
            ("reserved", "experienced"): (
                "Emphasize craft and subtlety. "
                "They'll appreciate technical skill and nuance."
            ),
            ("reserved", "beginner_friendly"): (
                "Start with structured games and clear explanations. "
                "Warm them up gradually."
            ),
            ("reserved", "mixed"): (
                "Begin with accessible material, then increase complexity. "
                "Watch for engagement cues."
            ),
            ("mixed", "experienced"): (
                "Balance showcases with participation. "
                "Cater to different engagement styles."
            ),
            ("mixed", "beginner_friendly"): (
                "Use variety in pacing and game types. "
                "Something for everyone approach."
            ),
            ("mixed", "mixed"): (
                "Read the room continuously. "
                "Have backup options for energy and complexity shifts."
            ),
        }

        traits = {
            "energy_profile": energy_profile,
            "experience_profile": experience_profile,
            "total_members": len(audience),
            "high_engagement_count": high_engagement,
            "low_engagement_count": low_engagement,
            "experienced_count": experienced,
            "beginner_count": beginners,
            "recommendation": recommendations.get(
                (energy_profile, experience_profile),
                "Stay flexible and adapt to audience response.",
            ),
        }

        logger.info("Audience traits analyzed", **traits)
        return traits

    async def _get_vibe_check(self, audience: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate quick vibe check for Room Agent to assess mood.

        Args:
            audience: List of audience members

        Returns:
            Dictionary with vibe indicators and recommendations.
        """
        traits = await self._analyze_audience_traits(audience)

        vibe_indicators = []

        if traits["energy_profile"] == "high_energy":
            vibe_indicators.append("Audience is energized and ready to participate")
        elif traits["energy_profile"] == "reserved":
            vibe_indicators.append("Audience is reserved - needs warming up")
        else:
            vibe_indicators.append("Audience has mixed energy levels")

        if traits["experience_profile"] == "experienced":
            vibe_indicators.append("Audience knows improv - can handle complexity")
        elif traits["experience_profile"] == "beginner_friendly":
            vibe_indicators.append("Many first-timers - keep it accessible")
        else:
            vibe_indicators.append("Mixed experience levels in audience")

        vibe_check = {
            "overall_mood": traits["energy_profile"],
            "experience_level": traits["experience_profile"],
            "indicators": vibe_indicators,
            "recommendation": traits["recommendation"],
        }

        logger.info("Vibe check generated", mood=vibe_check["overall_mood"])
        return vibe_check

    async def _generate_audience_suggestion(
        self,
        suggestion_type: str,
        audience_sample: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate demographically-appropriate audience suggestion.

        Args:
            suggestion_type: Type of suggestion (location, relationship, occupation, topic, object)
            audience_sample: Optional audience sample. If not provided, generates a new sample.

        Returns:
            A single suggestion string appropriate for the audience demographic.
        """
        logger.info(
            "Generating audience suggestion",
            suggestion_type=suggestion_type,
            has_sample=audience_sample is not None,
        )

        # Get or generate audience sample
        if not audience_sample:
            audience_sample = await self._generate_audience_sample(size=5)

        # Extract dominant demographics from audience
        dominant_demographics = []
        for member in audience_sample:
            demographics = member.get("demographics", {})
            occupation = demographics.get("occupation", "")
            if occupation:
                dominant_demographics.append(occupation.lower())

        # Map suggestion types to demographic-based suggestions
        suggestion_pools = {
            "location": {
                "tech": ["A hackathon", "A startup office", "A data center", "A tech support hotline"],
                "healthcare": ["An operating room", "A hospital waiting room", "A medical conference", "An ambulance"],
                "education": ["A classroom", "A teachers' lounge", "A parent-teacher conference", "A school assembly"],
                "arts": ["An art gallery opening", "A theater backstage", "A costume fitting", "A rehearsal room"],
                "finance": ["A stock exchange floor", "A bank vault", "An investment meeting", "An accounting office"],
                "mixed": ["A grocery store", "A coffee shop", "An elevator", "A park bench", "A bus stop"],
            },
            "relationship": {
                "tech": ["Co-founders", "Developer and product manager", "Tech support and frustrated user", "Startup competitors"],
                "healthcare": ["Doctor and patient", "Nurse and family member", "Paramedics on a call", "Hospital roommates"],
                "education": ["Teacher and student", "Principal and parent", "Study partners", "Rival debate team members"],
                "arts": ["Director and actor", "Costume designer and performer", "Art critic and artist", "Dance partners"],
                "finance": ["Banker and loan applicant", "Investment partners", "Accountant and client", "Stock traders"],
                "mixed": ["Roommates", "First date", "Longtime friends", "Neighbors", "Siblings"],
            },
            "occupation": {
                "tech": ["Software engineer", "UX designer", "Blockchain evangelist", "AI ethicist"],
                "healthcare": ["Surgeon", "Pediatric nurse", "Hospital administrator", "Medical researcher"],
                "education": ["High school teacher", "College professor", "School counselor", "Librarian"],
                "arts": ["Stage actor", "Gallery curator", "Film director", "Dance instructor"],
                "finance": ["Investment banker", "Financial advisor", "Crypto trader", "Tax auditor"],
                "mixed": ["Barista", "Delivery driver", "Customer service rep", "Fitness instructor"],
            },
            "topic": {
                "tech": ["Artificial intelligence ethics", "The future of remote work", "Cryptocurrency trends", "Tech startup culture"],
                "healthcare": ["Healthcare reform", "Medical breakthroughs", "Patient advocacy", "Work-life balance in medicine"],
                "education": ["Education reform", "Student mental health", "The value of liberal arts", "Teaching in the digital age"],
                "arts": ["The role of art in society", "Creative process", "Art vs commerce", "Performance anxiety"],
                "finance": ["Economic inequality", "Investment strategies", "The stock market", "Personal finance"],
                "mixed": ["Climate change", "Work-life balance", "Social media", "Family traditions", "Travel"],
            },
            "object": {
                "tech": ["A laptop", "A prototype device", "A server rack", "A VR headset"],
                "healthcare": ["A stethoscope", "A medical chart", "A prescription pad", "An MRI machine"],
                "education": ["A textbook", "A whiteboard", "A report card", "A student essay"],
                "arts": ["A paintbrush", "A costume piece", "A script", "A prop"],
                "finance": ["A briefcase", "Stock certificates", "A calculator", "A vault key"],
                "mixed": ["A phone", "A set of keys", "A coffee mug", "A backpack", "A letter"],
            },
        }

        # Determine demographic category
        demographic_category = "mixed"
        if any("tech" in demo or "engineer" in demo or "developer" in demo for demo in dominant_demographics):
            demographic_category = "tech"
        elif any("doctor" in demo or "nurse" in demo or "medical" in demo for demo in dominant_demographics):
            demographic_category = "healthcare"
        elif any("teacher" in demo or "professor" in demo or "educator" in demo for demo in dominant_demographics):
            demographic_category = "education"
        elif any("artist" in demo or "actor" in demo or "creative" in demo for demo in dominant_demographics):
            demographic_category = "arts"
        elif any("banker" in demo or "finance" in demo or "investor" in demo for demo in dominant_demographics):
            demographic_category = "finance"

        # Get suggestion pool for this type and demographic
        type_pool = suggestion_pools.get(suggestion_type.lower(), suggestion_pools["location"])
        suggestions = type_pool.get(demographic_category, type_pool["mixed"])

        # Select random suggestion
        suggestion = random.choice(suggestions)

        logger.info(
            "Audience suggestion generated",
            suggestion_type=suggestion_type,
            demographic_category=demographic_category,
            suggestion=suggestion,
        )

        return suggestion

    async def _get_suggestion_for_game(
        self,
        game_name: str,
        audience_sample: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate audience suggestion appropriate for a specific game.

        Args:
            game_name: Name of the improv game
            audience_sample: Optional audience sample. If not provided, generates a new sample.

        Returns:
            Dictionary with:
                - suggestion: The generated suggestion
                - suggestion_type: Type of suggestion (location, relationship, etc.)
                - reasoning: Why the audience chose this suggestion
        """
        logger.info("Generating game-specific suggestion", game_name=game_name)

        # Map common games to their typical suggestion types
        game_suggestion_types = {
            "long form": "relationship",
            "long_form": "relationship",
            "questions only": "location",
            "questions_only": "location",
            "alphabet scene": "location",
            "alphabet_game": "location",
            "last word, first word": "relationship",
            "last_word_first_word": "relationship",
            "expert interview": "topic",
            "expert_interview": "topic",
            "emotional rollercoaster": "relationship",
            "emotional_rollercoaster": "relationship",
            "genre replay": "location",
            "genre_replay": "location",
            "one word story": "topic",
            "one_word_story": "topic",
            "character swap": "relationship",
            "character_swap": "relationship",
        }

        # Determine suggestion type for this game (default to location)
        game_key = game_name.lower().strip()
        suggestion_type = game_suggestion_types.get(game_key, "location")

        logger.debug(
            "Determined suggestion type for game",
            game_name=game_name,
            suggestion_type=suggestion_type,
        )

        # Generate the suggestion
        suggestion = await self._generate_audience_suggestion(suggestion_type, audience_sample)

        # Create reasoning based on audience demographics
        if not audience_sample:
            audience_sample = await self._generate_audience_sample(size=5)

        # Build reasoning
        sample_member = audience_sample[0] if audience_sample else {}
        demographics = sample_member.get("demographics", {})
        occupation = demographics.get("occupation", "audience member")

        reasoning = f"The {occupation.lower()} in the crowd relates to this suggestion"

        result = {
            "suggestion": suggestion,
            "suggestion_type": suggestion_type,
            "reasoning": reasoning,
        }

        logger.info(
            "Game suggestion generated",
            game_name=game_name,
            suggestion_type=suggestion_type,
            suggestion=suggestion,
        )

        return result

    async def close(self) -> None:
        """Cleanup resources when toolset is no longer needed."""
        self._tools = None
        logger.debug("AudienceArchetypesToolset closed")
