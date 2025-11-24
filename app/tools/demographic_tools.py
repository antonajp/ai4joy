"""Demographic Tools - Async Functions for Audience Archetype Generation"""
import random
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Audience archetype templates
ARCHETYPE_TEMPLATES = [
    {
        "name": "The Enthusiast",
        "age_range": "25-35",
        "personality": "High energy, loves to participate, first to volunteer",
        "engagement_style": "Vocal and expressive, laughs loudly",
        "improv_knowledge": "Familiar with improv, may have taken classes",
        "preferences": "Fast-paced games, physical comedy, audience interaction"
    },
    {
        "name": "The Skeptic",
        "age_range": "40-55",
        "personality": "Reserved, needs to be won over, analytical",
        "engagement_style": "Quiet appreciation, selective laughter",
        "improv_knowledge": "Limited exposure, may compare to scripted comedy",
        "preferences": "Clever wordplay, structured games, clear rules"
    },
    {
        "name": "The First-Timer",
        "age_range": "18-24",
        "personality": "Curious and open-minded, slightly nervous",
        "engagement_style": "Observant, building confidence throughout show",
        "improv_knowledge": "No prior experience, learning as they watch",
        "preferences": "Accessible games, clear explanations, supportive atmosphere"
    },
    {
        "name": "The Regular",
        "age_range": "30-50",
        "personality": "Loyal fan, knows performers, understands format",
        "engagement_style": "Engaged but respectful, appreciates subtlety",
        "improv_knowledge": "Extensive, has seen many shows",
        "preferences": "Creative risks, callbacks, performer showcase moments"
    },
    {
        "name": "The Social Butterfly",
        "age_range": "22-40",
        "personality": "Here for the group experience, fun-loving",
        "engagement_style": "Laughs along with friends, contagious energy",
        "improv_knowledge": "Varies, but open to anything",
        "preferences": "Group games, sing-alongs, memorable moments to discuss"
    },
    {
        "name": "The Intellectual",
        "age_range": "35-60",
        "personality": "Appreciates craft and technique, thoughtful",
        "engagement_style": "Thoughtful laughter, notices details",
        "improv_knowledge": "May study theater or comedy theory",
        "preferences": "Sophisticated humor, narrative structure, thematic coherence"
    },
    {
        "name": "The Kid at Heart",
        "age_range": "20-70",
        "personality": "Playful and imaginative, no cynicism",
        "engagement_style": "Genuine joy, childlike wonder",
        "improv_knowledge": "Doesn't matter, here for pure fun",
        "preferences": "Silly games, physical comedy, absurdist humor"
    },
    {
        "name": "The Professional",
        "age_range": "30-55",
        "personality": "Works in comedy/entertainment, evaluating performance",
        "engagement_style": "Respectful acknowledgment, industry perspective",
        "improv_knowledge": "Professional level understanding",
        "preferences": "Technical skill, innovative formats, ensemble work"
    },
    {
        "name": "The Date Night Couple",
        "age_range": "25-45",
        "personality": "Looking for shared experience, slightly distracted",
        "engagement_style": "Focused on each other, occasional attention to show",
        "improv_knowledge": "Minimal, chose improv as date activity",
        "preferences": "Romantic moments, accessible humor, not too long"
    },
    {
        "name": "The Corporate Group",
        "age_range": "28-55",
        "personality": "Team building event, varying interest levels",
        "engagement_style": "Polite appreciation, occasional forced laughter",
        "improv_knowledge": "Minimal, may be mandatory attendance",
        "preferences": "Inclusive games, no individual spotlights, wrap on time"
    }
]


async def generate_audience_sample(size: int = 5) -> list[dict]:
    """Generate diverse audience sample with multiple archetypes.

    Args:
        size: Number of audience archetypes to generate (default 5)

    Returns:
        List of audience member dictionaries with demographics and preferences.
    """
    if size > len(ARCHETYPE_TEMPLATES):
        logger.warning(
            "Requested size exceeds available archetypes",
            requested=size,
            available=len(ARCHETYPE_TEMPLATES)
        )
        size = len(ARCHETYPE_TEMPLATES)

    selected = random.sample(ARCHETYPE_TEMPLATES, size)

    audience = []
    for i, archetype in enumerate(selected, 1):
        member = {
            "id": f"audience_member_{i}",
            **archetype
        }
        audience.append(member)

    logger.info("Audience sample generated", size=size)
    return audience


async def get_all_archetypes() -> list[dict]:
    """Get complete list of all available audience archetypes.

    Returns:
        List of all archetype dictionaries.
    """
    logger.debug("Fetching all archetypes", count=len(ARCHETYPE_TEMPLATES))
    return ARCHETYPE_TEMPLATES


async def analyze_audience_traits(audience: list[dict]) -> dict:
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
        all_preferences.extend(member['preferences'].split(', '))

        if 'vocal' in member['engagement_style'].lower() or 'expressive' in member['engagement_style'].lower():
            high_engagement += 1
        elif 'quiet' in member['engagement_style'].lower() or 'reserved' in member['engagement_style'].lower():
            low_engagement += 1

        if 'extensive' in member['improv_knowledge'].lower() or 'professional' in member['improv_knowledge'].lower():
            experienced += 1
        elif 'no prior' in member['improv_knowledge'].lower() or 'limited' in member['improv_knowledge'].lower():
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
        ("high_energy", "experienced"): "Try advanced games with audience participation. They'll appreciate creative risks.",
        ("high_energy", "beginner_friendly"): "Focus on accessible, energetic games with clear rules. Build confidence early.",
        ("high_energy", "mixed"): "Mix classic crowd-pleasers with a few adventurous choices. Read the room as you go.",
        ("reserved", "experienced"): "Emphasize craft and subtlety. They'll appreciate technical skill and nuance.",
        ("reserved", "beginner_friendly"): "Start with structured games and clear explanations. Warm them up gradually.",
        ("reserved", "mixed"): "Begin with accessible material, then increase complexity. Watch for engagement cues.",
        ("mixed", "experienced"): "Balance showcases with participation. Cater to different engagement styles.",
        ("mixed", "beginner_friendly"): "Use variety in pacing and game types. Something for everyone approach.",
        ("mixed", "mixed"): "Read the room continuously. Have backup options for energy and complexity shifts."
    }

    traits = {
        "energy_profile": energy_profile,
        "experience_profile": experience_profile,
        "total_members": len(audience),
        "high_engagement_count": high_engagement,
        "low_engagement_count": low_engagement,
        "experienced_count": experienced,
        "beginner_count": beginners,
        "recommendation": recommendations.get((energy_profile, experience_profile), "Stay flexible and adapt to audience response.")
    }

    logger.info("Audience traits analyzed", **traits)
    return traits


async def get_vibe_check(audience: list[dict]) -> dict:
    """Generate quick vibe check for Room Agent to assess mood.

    Args:
        audience: List of audience members

    Returns:
        Dictionary with vibe indicators and recommendations.
    """
    traits = await analyze_audience_traits(audience)

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
        "recommendation": traits["recommendation"]
    }

    logger.info("Vibe check generated", mood=vibe_check["overall_mood"])
    return vibe_check
