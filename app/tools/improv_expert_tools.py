"""Improv Expert Tools - Async Functions for Core Improv Principles"""
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Core improv principles database
CORE_PRINCIPLES = [
    {
        "id": "yes_and",
        "name": "Yes, And...",
        "description": "Accept what your scene partner offers and build upon it. Never deny or block.",
        "importance": "foundational",
        "examples": [
            "Partner: 'We're on a spaceship!' You: 'Yes, and the oxygen is running low!'",
            "Partner: 'You're my doctor?' You: 'Yes, and I have some bad news about your test results.'"
        ],
        "common_mistakes": [
            "Saying 'No' or 'But' instead of accepting the offer",
            "Accepting but not adding anything new",
            "Changing the subject instead of building"
        ],
        "coaching_tips": [
            "Practice saying 'Yes, and...' out loud to internalize the pattern",
            "If you catch yourself blocking, apologize and re-offer",
            "Your job is to make your partner look good"
        ]
    },
    {
        "id": "listening",
        "name": "Active Listening",
        "description": "Truly hear what your scene partner is saying, both verbally and non-verbally.",
        "importance": "foundational",
        "examples": [
            "Notice when your partner establishes a relationship or location",
            "Pick up on emotional tone and mirror or respond to it",
            "Remember details partners establish about characters or situations"
        ],
        "common_mistakes": [
            "Planning your next line instead of listening",
            "Ignoring information your partner provides",
            "Forgetting established details from earlier in the scene"
        ],
        "coaching_tips": [
            "Focus on your partner, not on being funny",
            "Repeat back key information to show you heard it",
            "React authentically to what you hear"
        ]
    },
    {
        "id": "commitment",
        "name": "Commitment",
        "description": "Fully commit to your character, choices, and the reality of the scene.",
        "importance": "essential",
        "examples": [
            "If you're playing angry, be fully angry",
            "Commit to physical choices and maintain them",
            "Don't apologize or break character"
        ],
        "common_mistakes": [
            "Playing half-heartedly or ironically",
            "Laughing at your own choices",
            "Hedging or showing uncertainty"
        ],
        "coaching_tips": [
            "Choose quickly and commit fully",
            "Trust that commitment is more important than being right",
            "The audience can sense hesitation"
        ]
    },
    {
        "id": "object_work",
        "name": "Object Work",
        "description": "Create and manipulate imaginary objects with precision and consistency.",
        "importance": "technical",
        "examples": [
            "Establish object size, weight, and location in space",
            "Maintain consistent placement of objects",
            "Use both hands when appropriate"
        ],
        "common_mistakes": [
            "Objects changing size or weight mid-scene",
            "Forgetting where you placed something",
            "Not showing the weight or texture of objects"
        ],
        "coaching_tips": [
            "Practice mime exercises to build muscle memory",
            "Show don't tell - let actions communicate what the object is",
            "Respect your partner's object work"
        ]
    },
    {
        "id": "relationship_first",
        "name": "Relationship First",
        "description": "Establish who you are to each other before worrying about plot or jokes.",
        "importance": "essential",
        "examples": [
            "Start with 'Mom, I need to tell you something...'",
            "Establish power dynamics through behavior",
            "Show emotional connection or tension"
        ],
        "common_mistakes": [
            "Focusing on plot at the expense of character",
            "Treating all characters the same way",
            "Forgetting to establish how you know each other"
        ],
        "coaching_tips": [
            "Relationships create organic conflict and humor",
            "How you say something matters more than what you say",
            "Strong relationships make weak plots work"
        ]
    },
    {
        "id": "justification",
        "name": "Justification",
        "description": "Make unusual or unexpected choices make sense within the scene's reality.",
        "importance": "intermediate",
        "examples": [
            "If partner makes a weird sound, justify it as a medical condition",
            "If someone enters oddly, create a reason it makes sense",
            "Turn mistakes into intentional choices"
        ],
        "common_mistakes": [
            "Pointing out that something doesn't make sense",
            "Ignoring unusual choices",
            "Breaking the reality of the scene"
        ],
        "coaching_tips": [
            "There are no mistakes, only opportunities",
            "Trust that you can justify anything",
            "Justification is advanced 'yes, and'"
        ]
    },
    {
        "id": "specificity",
        "name": "Specificity",
        "description": "Use specific details instead of generic ones to create vivid, memorable scenes.",
        "importance": "intermediate",
        "examples": [
            "Instead of 'a restaurant', say 'Olive Garden'",
            "Instead of 'some time ago', say 'Tuesday at 3:47 PM'",
            "Name characters with real names, not 'guy' or 'dude'"
        ],
        "common_mistakes": [
            "Being vague or generic",
            "Asking questions instead of making statements",
            "Using placeholder words"
        ],
        "coaching_tips": [
            "Specific choices trigger more ideas",
            "Details make scenes feel real",
            "Don't be afraid to make bold specific choices"
        ]
    },
    {
        "id": "game_of_scene",
        "name": "Game of the Scene",
        "description": "Find the unusual or funny pattern in a scene and explore it.",
        "importance": "advanced",
        "examples": [
            "If one character keeps interrupting, heighten it",
            "Find the absurd logic and follow it consistently",
            "Once you find what's funny, do more of it"
        ],
        "common_mistakes": [
            "Changing the game mid-scene",
            "Not recognizing what's working",
            "Adding too many ideas instead of exploring one"
        ],
        "coaching_tips": [
            "The game often reveals itself in the first minute",
            "Heightening means doing it more, bigger, or weirder",
            "Less is more - explore one idea fully"
        ]
    },
    {
        "id": "group_mind",
        "name": "Group Mind",
        "description": "Work as ensemble, supporting each other rather than competing for attention.",
        "importance": "essential",
        "examples": [
            "Step back when others are having a moment",
            "Support other players' choices",
            "Celebrate ensemble success over individual glory"
        ],
        "common_mistakes": [
            "Forcing yourself into every scene",
            "Trying to be the funniest person",
            "Not trusting your teammates"
        ],
        "coaching_tips": [
            "The show is not about you",
            "Best shows come from strong ensemble work",
            "Support equals comedy"
        ]
    },
    {
        "id": "emotional_honesty",
        "name": "Emotional Honesty",
        "description": "Play emotions truthfully rather than indicating or playing for laughs.",
        "importance": "intermediate",
        "examples": [
            "If the scene calls for sadness, actually be sad",
            "Let emotions drive behavior naturally",
            "React honestly to what's happening"
        ],
        "common_mistakes": [
            "Indicating emotions with exaggerated faces",
            "Playing everything for comedy",
            "Not allowing real emotions in scenes"
        ],
        "coaching_tips": [
            "Real emotions create real laughs",
            "Don't be afraid of serious moments",
            "Authenticity is funnier than trying to be funny"
        ]
    }
]


async def get_all_principles() -> list[dict]:
    """Get complete list of all core improv principles.

    Returns:
        List of all principle dictionaries with examples and coaching tips.
    """
    logger.debug("Fetching all principles", count=len(CORE_PRINCIPLES))
    return CORE_PRINCIPLES


async def get_principle_by_id(principle_id: str) -> dict:
    """Get specific improv principle by its unique ID.

    Args:
        principle_id: Unique principle identifier (e.g., 'yes_and', 'listening')

    Returns:
        Principle dictionary with all details, or empty dict if not found.
    """
    for principle in CORE_PRINCIPLES:
        if principle["id"] == principle_id:
            logger.debug("Principle found", principle_id=principle_id, name=principle["name"])
            return principle

    logger.warning("Principle not found", principle_id=principle_id)
    return {}


async def get_principles_by_importance(importance: str) -> list[dict]:
    """Get principles filtered by importance level.

    Args:
        importance: Level (foundational, essential, technical, intermediate, advanced)

    Returns:
        List of matching principles.
    """
    results = [p for p in CORE_PRINCIPLES if p["importance"] == importance.lower()]

    logger.info("Principles filtered by importance", importance=importance, count=len(results))
    return results


async def get_beginner_essentials() -> list[dict]:
    """Get essential principles for beginners to focus on first.

    Returns:
        List of foundational and essential principles.
    """
    essentials = [
        p for p in CORE_PRINCIPLES
        if p["importance"] in ["foundational", "essential"]
    ]

    logger.info("Beginner essentials retrieved", count=len(essentials))
    return essentials


async def search_principles_by_keyword(keyword: str) -> list[dict]:
    """Search principles by keyword in name or description.

    Args:
        keyword: Search term to match

    Returns:
        List of matching principles.
    """
    keyword_lower = keyword.lower()
    results = []

    for principle in CORE_PRINCIPLES:
        if (keyword_lower in principle["name"].lower() or
            keyword_lower in principle["description"].lower()):
            results.append(principle)

    logger.info("Keyword search completed", keyword=keyword, results=len(results))
    return results
