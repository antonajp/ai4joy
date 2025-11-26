"""Game Database Tools - Async Functions for ADK Agents"""

from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Short Form improv games catalog
GAMES_DB = [
    {
        "id": "freeze_tag",
        "name": "Freeze Tag",
        "description": "Two players start a scene. At any point, another player yells 'Freeze!', tags one player out, takes their exact position, and starts a completely new scene.",
        "rules": [
            "Two players begin with a scene suggestion",
            "Players maintain physical positions when frozen",
            "New player must start completely different scene",
            "Tagged player sits out and watches",
        ],
        "player_count": {"min": 4, "max": 8},
        "energy_level": "high",
        "skills": ["physicality", "quick_thinking", "scene_work"],
        "duration_minutes": 10,
        "difficulty": "beginner",
    },
    {
        "id": "185",
        "name": "185",
        "description": "Players stand in a line and deliver 185 jokes in the format '185 [subject] walk into a bar. The bartender says...' Each player adds one punchline.",
        "rules": [
            "Host gets audience suggestion for subject",
            "Format must be '185 [subject] walk into a bar'",
            "Each player delivers one punchline quickly",
            "Focus on speed and energy over perfection",
        ],
        "player_count": {"min": 4, "max": 10},
        "energy_level": "high",
        "skills": ["wordplay", "quick_thinking", "pattern_recognition"],
        "duration_minutes": 5,
        "difficulty": "beginner",
    },
    {
        "id": "questions_only",
        "name": "Questions Only",
        "description": "Players can only speak in questions. Any statement, hesitation, or repeated question gets you eliminated.",
        "rules": [
            "All dialogue must be questions",
            "No statements allowed",
            "No hesitations longer than 2 seconds",
            "Cannot repeat a question already asked",
            "Last player standing wins",
        ],
        "player_count": {"min": 2, "max": 6},
        "energy_level": "medium",
        "skills": ["quick_thinking", "listening", "grammar"],
        "duration_minutes": 8,
        "difficulty": "intermediate",
    },
    {
        "id": "party_quirks",
        "name": "Party Quirks",
        "description": "One player is the party host, others are guests with secret quirky personalities. Host must guess each quirk.",
        "rules": [
            "Host leaves while audience assigns quirks to guests",
            "Guests enter one at a time doing their quirk",
            "Host interacts naturally while trying to guess",
            "Guests become more obvious if host struggles",
            "Game ends when all quirks are guessed",
        ],
        "player_count": {"min": 3, "max": 5},
        "energy_level": "medium",
        "skills": ["character_work", "subtlety", "deduction"],
        "duration_minutes": 12,
        "difficulty": "intermediate",
    },
    {
        "id": "three_headed_broadway_star",
        "name": "Three-Headed Broadway Star",
        "description": "Three players form one person, each saying one word at a time to create a song about an audience suggestion.",
        "rules": [
            "Three players stand together as one entity",
            "Each player says only one word at a time",
            "Words must flow left to right consistently",
            "Must create rhyming song with melody",
            "Host conducts for emotional changes",
        ],
        "player_count": {"min": 3, "max": 3},
        "energy_level": "high",
        "skills": ["word_association", "singing", "teamwork"],
        "duration_minutes": 6,
        "difficulty": "advanced",
    },
    {
        "id": "conducted_story",
        "name": "Conducted Story",
        "description": "Players tell a story one word at a time, controlled by conductor's hand gestures for speed (fast, slow, reverse, emotional shifts).",
        "rules": [
            "Get story title from audience",
            "Conductor points to player who speaks",
            "Each player says one word when pointed to",
            "Hand gestures control speed and style",
            "Story must remain coherent despite changes",
        ],
        "player_count": {"min": 4, "max": 6},
        "energy_level": "medium",
        "skills": ["listening", "word_association", "adaptability"],
        "duration_minutes": 8,
        "difficulty": "intermediate",
    },
    {
        "id": "sound_effects",
        "name": "Sound Effects",
        "description": "Two players act out a scene while two others provide all sound effects, often with hilarious mismatches.",
        "rules": [
            "Get scene location from audience",
            "Actors perform physical actions clearly",
            "Sound effect artists make sounds for any action",
            "Actors must justify unexpected sounds",
            "No speaking from sound effect artists",
        ],
        "player_count": {"min": 4, "max": 4},
        "energy_level": "high",
        "skills": ["physicality", "justification", "audio_creativity"],
        "duration_minutes": 7,
        "difficulty": "beginner",
    },
    {
        "id": "alphabet_game",
        "name": "Alphabet Game",
        "description": "Players act out a scene where each line must start with the next letter of the alphabet in sequence.",
        "rules": [
            "Get scene suggestion from audience",
            "First line starts with assigned letter (usually A)",
            "Each subsequent line starts with next letter",
            "Must maintain coherent scene despite constraint",
            "When reaching Z, either end or start over",
        ],
        "player_count": {"min": 2, "max": 4},
        "energy_level": "medium",
        "skills": ["quick_thinking", "vocabulary", "scene_work"],
        "duration_minutes": 10,
        "difficulty": "intermediate",
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
