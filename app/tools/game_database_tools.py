"""Game Database Tools - Async Functions for ADK Agents"""

from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Two-player verbal/conversational improv games catalog
# All games designed for 2 players in a digital/online text-based format
GAMES_DB = [
    {
        "id": "long_form",
        "name": "Long Form",
        "description": "A free-form improv scene between two players with no specific rules or constraints. Players create characters, relationships, and storylines organically through natural conversation and 'Yes, And' principles.",
        "rules": [
            "Accept and build on your partner's offers ('Yes, And')",
            "Establish who, what, where early in the scene",
            "Make your partner look good",
            "Follow the interesting thread - explore what emerges",
            "Find the game of the scene and heighten it",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "variable",
        "skills": ["listening", "scene_work", "character_work", "relationship_building"],
        "duration_minutes": 15,
        "difficulty": "beginner",
    },
    {
        "id": "questions_only",
        "name": "Questions Only",
        "description": "Players can only speak in questions. Any statement or hesitation breaks the rule. Great for building tension and advancing scenes through inquiry.",
        "rules": [
            "All dialogue must be questions",
            "No statements allowed",
            "Questions must make sense in context",
            "Keep the scene moving forward",
            "If you slip, acknowledge it and reset",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "medium",
        "skills": ["quick_thinking", "listening", "grammar", "scene_work"],
        "duration_minutes": 8,
        "difficulty": "intermediate",
    },
    {
        "id": "alphabet_game",
        "name": "Alphabet Scene",
        "description": "Players act out a scene where each line must start with the next letter of the alphabet in sequence. Alternating between players, you'll work through A to Z.",
        "rules": [
            "Start with a scene suggestion",
            "First player's line starts with A",
            "Second player's line starts with B",
            "Continue alternating through the alphabet",
            "Must maintain coherent scene despite constraint",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "medium",
        "skills": ["quick_thinking", "vocabulary", "scene_work"],
        "duration_minutes": 10,
        "difficulty": "intermediate",
    },
    {
        "id": "last_word_first_word",
        "name": "Last Word, First Word",
        "description": "Each player must begin their line with the last word (or last significant word) of their partner's previous line. Creates a flowing, connected dialogue.",
        "rules": [
            "Start with a scene suggestion",
            "Each line must begin with partner's last word",
            "Keep the scene grounded and coherent",
            "The constraint should feel natural, not forced",
            "Focus on building relationship and story",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "medium",
        "skills": ["listening", "word_association", "scene_work"],
        "duration_minutes": 8,
        "difficulty": "intermediate",
    },
    {
        "id": "expert_interview",
        "name": "Expert Interview",
        "description": "One player is an interviewer, the other is an 'expert' on a made-up or absurd topic. The expert must confidently answer any question as if they truly know the subject.",
        "rules": [
            "Interviewer asks genuine, curious questions",
            "Expert commits fully to their expertise",
            "Expert should make up convincing details",
            "Both players build the world together",
            "Roles can swap for a second round",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "medium",
        "skills": ["commitment", "quick_thinking", "world_building"],
        "duration_minutes": 8,
        "difficulty": "beginner",
    },
    {
        "id": "emotional_rollercoaster",
        "name": "Emotional Rollercoaster",
        "description": "Players perform a scene while cycling through different emotions when prompted. The scene partner (AI) will occasionally call out new emotions that both players must shift into.",
        "rules": [
            "Start with a simple scene premise",
            "When an emotion is called, shift into it naturally",
            "Justify the emotional shift within the scene",
            "Emotions affect HOW you say things, not WHAT you say",
            "Commit fully to each emotion",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "high",
        "skills": ["emotional_range", "justification", "commitment"],
        "duration_minutes": 10,
        "difficulty": "intermediate",
    },
    {
        "id": "genre_replay",
        "name": "Genre Replay",
        "description": "Players perform a short scene, then replay the same basic scene in different genres (film noir, romantic comedy, horror, sci-fi, etc.).",
        "rules": [
            "First, play a simple 2-minute scene",
            "Replay the scene's basic events in a new genre",
            "Adopt the tropes and language of each genre",
            "Keep the core relationship/conflict the same",
            "Have fun with genre conventions",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "high",
        "skills": ["genre_awareness", "character_work", "adaptability"],
        "duration_minutes": 12,
        "difficulty": "intermediate",
    },
    {
        "id": "one_word_story",
        "name": "One Word Story",
        "description": "Players build a story together, alternating one word at a time. Requires deep listening and letting go of your own agenda.",
        "rules": [
            "Each player says only one word at a time",
            "Alternate strictly between players",
            "Build coherent sentences and story",
            "Don't try to control where it goes",
            "Trust your partner's contributions",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "low",
        "skills": ["listening", "word_association", "letting_go"],
        "duration_minutes": 5,
        "difficulty": "beginner",
    },
    {
        "id": "character_swap",
        "name": "Character Swap",
        "description": "Mid-scene, players swap characters and continue as each other. Tests how well you've been listening and observing your partner.",
        "rules": [
            "Start a scene with distinct characters",
            "Establish clear character traits and voices",
            "When 'Swap!' is called, switch characters",
            "Adopt your partner's character fully",
            "Continue the scene seamlessly",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "medium",
        "skills": ["listening", "character_work", "observation"],
        "duration_minutes": 10,
        "difficulty": "advanced",
    },
    {
        "id": "first_line_last_line",
        "name": "First Line / Last Line",
        "description": "The scene is given its first and last lines. Players must create a coherent scene that logically connects these two points.",
        "rules": [
            "Scene partner provides opening and closing lines",
            "First player starts with the given opening line",
            "Build a scene that will justify the ending",
            "Scene ends when the closing line is delivered",
            "Focus on the journey between the lines",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "medium",
        "skills": ["scene_work", "narrative", "planning"],
        "duration_minutes": 8,
        "difficulty": "intermediate",
    },
    {
        "id": "accusation",
        "name": "Accusation",
        "description": "One player accuses the other of something absurd or mundane. The accused must justify and explain their actions, making the accusation true.",
        "rules": [
            "Accuser makes a specific accusation",
            "Accused must accept and justify it ('Yes, And')",
            "Accused explains the how and why",
            "Accuser can dig deeper with follow-ups",
            "Scene ends with resolution or escalation",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "medium",
        "skills": ["justification", "commitment", "quick_thinking"],
        "duration_minutes": 6,
        "difficulty": "beginner",
    },
    {
        "id": "gibberish_translator",
        "name": "Gibberish Translator",
        "description": "One player speaks only in gibberish (made-up sounds), the other 'translates' what they're saying into the scene. Tests commitment and interpretation.",
        "rules": [
            "Gibberish speaker uses expressive nonsense sounds",
            "Translator interprets meaning for the scene",
            "Gibberish should have emotional content and rhythm",
            "Translator builds the actual dialogue and story",
            "Both players drive the scene together",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "high",
        "skills": ["expression", "interpretation", "commitment"],
        "duration_minutes": 8,
        "difficulty": "intermediate",
    },
    {
        "id": "status_shift",
        "name": "Status Shift",
        "description": "Players start with clear high/low status positions, then gradually reverse over the course of the scene. Focus on the subtle power dynamics in relationships.",
        "rules": [
            "Establish clear status difference at the start",
            "High status: confident, takes space, direct eye contact",
            "Low status: tentative, small, indirect",
            "Gradually shift the power dynamic",
            "End with reversed status positions",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "medium",
        "skills": ["status_work", "subtlety", "scene_work"],
        "duration_minutes": 10,
        "difficulty": "advanced",
    },
    {
        "id": "forward_reverse",
        "name": "Forward / Reverse",
        "description": "The scene moves forward normally, but when 'Reverse' is called, players must go backwards through their dialogue until 'Forward' is called again.",
        "rules": [
            "Play scene normally when going forward",
            "When 'Reverse' is called, replay lines backwards",
            "Remember your lines to reverse accurately",
            "When 'Forward' is called, continue from that point",
            "Creates fun loops and callbacks",
        ],
        "player_count": {"min": 2, "max": 2},
        "energy_level": "high",
        "skills": ["memory", "listening", "adaptability"],
        "duration_minutes": 8,
        "difficulty": "advanced",
    },
]


async def get_all_games() -> list[dict]:
    """Get complete list of all available improv games.

    Returns:
        List of all game dictionaries with details, rules, and requirements.
    """
    logger.debug("Fetching all games", count=len(GAMES_DB))
    return GAMES_DB


async def get_game_by_id(game_id: str) -> dict:
    """Get specific improv game by its unique ID.

    Args:
        game_id: Unique game identifier (e.g., 'freeze_tag', '185')

    Returns:
        Game dictionary with all details, or empty dict if not found.
    """
    for game in GAMES_DB:
        if game["id"] == game_id:
            logger.debug("Game found", game_id=game_id, game_name=game["name"])
            return game

    logger.warning("Game not found", game_id=game_id)
    return {}


async def search_games(
    energy_level: Optional[str] = None,
    player_count: Optional[int] = None,
    difficulty: Optional[str] = None,
    max_duration: Optional[int] = None,
) -> list[dict]:
    """Search improv games by multiple criteria.

    Args:
        energy_level: Filter by energy (high, medium, low)
        player_count: Number of players available (filters by min/max range)
        difficulty: Filter by difficulty (beginner, intermediate, advanced)
        max_duration: Maximum duration in minutes

    Returns:
        List of matching game dictionaries.
    """
    results = GAMES_DB.copy()

    if energy_level:
        results = [g for g in results if g["energy_level"] == energy_level.lower()]

    if player_count is not None:
        results = [
            g
            for g in results
            if int(g["player_count"]["min"])  # type: ignore[index]
            <= player_count
            <= int(g["player_count"]["max"])  # type: ignore[index]
        ]

    if difficulty:
        results = [g for g in results if g["difficulty"] == difficulty.lower()]

    if max_duration:
        results = [g for g in results if g["duration_minutes"] <= max_duration]  # type: ignore[operator]

    logger.info(
        "Game search completed",
        energy_level=energy_level,
        player_count=player_count,
        difficulty=difficulty,
        max_duration=max_duration,
        results_count=len(results),
    )

    return results
