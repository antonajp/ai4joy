#!/usr/bin/env python3
"""Firestore Tool Data Seeder - Populate tool collections with initial data

This script seeds the Firestore database with the improv tool data that was
previously hardcoded in the Python modules. Run this once to populate:

- improv_games: Game database for MC agent
- improv_principles: Core improv principles for Coach agent
- audience_archetypes: Audience demographics for Room agent
- sentiment_keywords: Keyword lists for sentiment analysis

Usage:
    # From project root with virtual environment activated:
    python scripts/seed_firestore_tool_data.py

    # With custom project/database:
    GCP_PROJECT_ID=my-project FIRESTORE_DATABASE=my-db python scripts/seed_firestore_tool_data.py

    # Dry run (no writes):
    python scripts/seed_firestore_tool_data.py --dry-run

Requirements:
    - Google Cloud credentials configured
    - Firestore database created
    - GOOGLE_APPLICATION_CREDENTIALS or gcloud auth configured
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from google.cloud.firestore_v1 import AsyncClient  # noqa: E402
from app.config import get_settings  # noqa: E402

settings = get_settings()


# =============================================================================
# IMPROV GAMES DATA
# =============================================================================

GAMES_DATA = [
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
        "description": "The scene is given its first and last lines by the audience. Players must create a coherent scene that logically connects these two points.",
        "rules": [
            "The AUDIENCE shouts out the opening and closing lines",
            "Player starts the scene with the audience's opening line",
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


# =============================================================================
# IMPROV PRINCIPLES DATA
# =============================================================================

PRINCIPLES_DATA = [
    {
        "id": "yes_and",
        "name": "Yes, And...",
        "description": "Accept what your scene partner offers and build upon it. Never deny or block.",
        "importance": "foundational",
        "examples": [
            "Partner: 'We're on a spaceship!' You: 'Yes, and the oxygen is running low!'",
            "Partner: 'You're my doctor?' You: 'Yes, and I have some bad news about your test results.'",
        ],
        "common_mistakes": [
            "Saying 'No' or 'But' instead of accepting the offer",
            "Accepting but not adding anything new",
            "Changing the subject instead of building",
        ],
        "coaching_tips": [
            "Practice saying 'Yes, and...' out loud to internalize the pattern",
            "If you catch yourself blocking, apologize and re-offer",
            "Your job is to make your partner look good",
        ],
    },
    {
        "id": "listening",
        "name": "Active Listening",
        "description": "Truly hear what your scene partner is saying, both verbally and non-verbally.",
        "importance": "foundational",
        "examples": [
            "Notice when your partner establishes a relationship or location",
            "Pick up on emotional tone and mirror or respond to it",
            "Remember details partners establish about characters or situations",
        ],
        "common_mistakes": [
            "Planning your next line instead of listening",
            "Ignoring information your partner provides",
            "Forgetting established details from earlier in the scene",
        ],
        "coaching_tips": [
            "Focus on your partner, not on being funny",
            "Repeat back key information to show you heard it",
            "React authentically to what you hear",
        ],
    },
    {
        "id": "commitment",
        "name": "Commitment",
        "description": "Fully commit to your character, choices, and the reality of the scene.",
        "importance": "essential",
        "examples": [
            "If you're playing angry, be fully angry",
            "Commit to physical choices and maintain them",
            "Don't apologize or break character",
        ],
        "common_mistakes": [
            "Playing half-heartedly or ironically",
            "Laughing at your own choices",
            "Hedging or showing uncertainty",
        ],
        "coaching_tips": [
            "Choose quickly and commit fully",
            "Trust that commitment is more important than being right",
            "The audience can sense hesitation",
        ],
    },
    {
        "id": "object_work",
        "name": "Object Work",
        "description": "Create and manipulate imaginary objects with precision and consistency.",
        "importance": "technical",
        "examples": [
            "Establish object size, weight, and location in space",
            "Maintain consistent placement of objects",
            "Use both hands when appropriate",
        ],
        "common_mistakes": [
            "Objects changing size or weight mid-scene",
            "Forgetting where you placed something",
            "Not showing the weight or texture of objects",
        ],
        "coaching_tips": [
            "Practice mime exercises to build muscle memory",
            "Show don't tell - let actions communicate what the object is",
            "Respect your partner's object work",
        ],
    },
    {
        "id": "relationship_first",
        "name": "Relationship First",
        "description": "Establish who you are to each other before worrying about plot or jokes.",
        "importance": "essential",
        "examples": [
            "Start with 'Mom, I need to tell you something...'",
            "Establish power dynamics through behavior",
            "Show emotional connection or tension",
        ],
        "common_mistakes": [
            "Focusing on plot at the expense of character",
            "Treating all characters the same way",
            "Forgetting to establish how you know each other",
        ],
        "coaching_tips": [
            "Relationships create organic conflict and humor",
            "How you say something matters more than what you say",
            "Strong relationships make weak plots work",
        ],
    },
    {
        "id": "justification",
        "name": "Justification",
        "description": "Make unusual or unexpected choices make sense within the scene's reality.",
        "importance": "intermediate",
        "examples": [
            "If partner makes a weird sound, justify it as a medical condition",
            "If someone enters oddly, create a reason it makes sense",
            "Turn mistakes into intentional choices",
        ],
        "common_mistakes": [
            "Pointing out that something doesn't make sense",
            "Ignoring unusual choices",
            "Breaking the reality of the scene",
        ],
        "coaching_tips": [
            "There are no mistakes, only opportunities",
            "Trust that you can justify anything",
            "Justification is advanced 'yes, and'",
        ],
    },
    {
        "id": "specificity",
        "name": "Specificity",
        "description": "Use specific details instead of generic ones to create vivid, memorable scenes.",
        "importance": "intermediate",
        "examples": [
            "Instead of 'a restaurant', say 'Olive Garden'",
            "Instead of 'some time ago', say 'Tuesday at 3:47 PM'",
            "Name characters with real names, not 'guy' or 'dude'",
        ],
        "common_mistakes": [
            "Being vague or generic",
            "Asking questions instead of making statements",
            "Using placeholder words",
        ],
        "coaching_tips": [
            "Specific choices trigger more ideas",
            "Details make scenes feel real",
            "Don't be afraid to make bold specific choices",
        ],
    },
    {
        "id": "game_of_scene",
        "name": "Game of the Scene",
        "description": "Find the unusual or funny pattern in a scene and explore it.",
        "importance": "advanced",
        "examples": [
            "If one character keeps interrupting, heighten it",
            "Find the absurd logic and follow it consistently",
            "Once you find what's funny, do more of it",
        ],
        "common_mistakes": [
            "Changing the game mid-scene",
            "Not recognizing what's working",
            "Adding too many ideas instead of exploring one",
        ],
        "coaching_tips": [
            "The game often reveals itself in the first minute",
            "Heightening means doing it more, bigger, or weirder",
            "Less is more - explore one idea fully",
        ],
    },
    {
        "id": "group_mind",
        "name": "Group Mind",
        "description": "Work as ensemble, supporting each other rather than competing for attention.",
        "importance": "essential",
        "examples": [
            "Step back when others are having a moment",
            "Support other players' choices",
            "Celebrate ensemble success over individual glory",
        ],
        "common_mistakes": [
            "Forcing yourself into every scene",
            "Trying to be the funniest person",
            "Not trusting your teammates",
        ],
        "coaching_tips": [
            "The show is not about you",
            "Best shows come from strong ensemble work",
            "Support equals comedy",
        ],
    },
    {
        "id": "emotional_honesty",
        "name": "Emotional Honesty",
        "description": "Play emotions truthfully rather than indicating or playing for laughs.",
        "importance": "intermediate",
        "examples": [
            "If the scene calls for sadness, actually be sad",
            "Let emotions drive behavior naturally",
            "React honestly to what's happening",
        ],
        "common_mistakes": [
            "Indicating emotions with exaggerated faces",
            "Playing everything for comedy",
            "Not allowing real emotions in scenes",
        ],
        "coaching_tips": [
            "Real emotions create real laughs",
            "Don't be afraid of serious moments",
            "Authenticity is funnier than trying to be funny",
        ],
    },
]


# =============================================================================
# AUDIENCE ARCHETYPES DATA
# =============================================================================

ARCHETYPES_DATA = [
    {
        "id": "enthusiast",
        "name": "The Enthusiast",
        "age_range": "25-35",
        "personality": "High energy, loves to participate, first to volunteer",
        "engagement_style": "Vocal and expressive, laughs loudly",
        "improv_knowledge": "Familiar with improv, may have taken classes",
        "preferences": "Fast-paced games, physical comedy, audience interaction",
    },
    {
        "id": "skeptic",
        "name": "The Skeptic",
        "age_range": "40-55",
        "personality": "Reserved, needs to be won over, analytical",
        "engagement_style": "Quiet appreciation, selective laughter",
        "improv_knowledge": "Limited exposure, may compare to scripted comedy",
        "preferences": "Clever wordplay, structured games, clear rules",
    },
    {
        "id": "first_timer",
        "name": "The First-Timer",
        "age_range": "18-24",
        "personality": "Curious and open-minded, slightly nervous",
        "engagement_style": "Observant, building confidence throughout show",
        "improv_knowledge": "No prior experience, learning as they watch",
        "preferences": "Accessible games, clear explanations, supportive atmosphere",
    },
    {
        "id": "regular",
        "name": "The Regular",
        "age_range": "30-50",
        "personality": "Loyal fan, knows performers, understands format",
        "engagement_style": "Engaged but respectful, appreciates subtlety",
        "improv_knowledge": "Extensive, has seen many shows",
        "preferences": "Creative risks, callbacks, performer showcase moments",
    },
    {
        "id": "social_butterfly",
        "name": "The Social Butterfly",
        "age_range": "22-40",
        "personality": "Here for the group experience, fun-loving",
        "engagement_style": "Laughs along with friends, contagious energy",
        "improv_knowledge": "Varies, but open to anything",
        "preferences": "Group games, sing-alongs, memorable moments to discuss",
    },
    {
        "id": "intellectual",
        "name": "The Intellectual",
        "age_range": "35-60",
        "personality": "Appreciates craft and technique, thoughtful",
        "engagement_style": "Thoughtful laughter, notices details",
        "improv_knowledge": "May study theater or comedy theory",
        "preferences": "Sophisticated humor, narrative structure, thematic coherence",
    },
    {
        "id": "kid_at_heart",
        "name": "The Kid at Heart",
        "age_range": "20-70",
        "personality": "Playful and imaginative, no cynicism",
        "engagement_style": "Genuine joy, childlike wonder",
        "improv_knowledge": "Doesn't matter, here for pure fun",
        "preferences": "Silly games, physical comedy, absurdist humor",
    },
    {
        "id": "professional",
        "name": "The Professional",
        "age_range": "30-55",
        "personality": "Works in comedy/entertainment, evaluating performance",
        "engagement_style": "Respectful acknowledgment, industry perspective",
        "improv_knowledge": "Professional level understanding",
        "preferences": "Technical skill, innovative formats, ensemble work",
    },
    {
        "id": "date_night",
        "name": "The Date Night Couple",
        "age_range": "25-45",
        "personality": "Looking for shared experience, slightly distracted",
        "engagement_style": "Focused on each other, occasional attention to show",
        "improv_knowledge": "Minimal, chose improv as date activity",
        "preferences": "Romantic moments, accessible humor, not too long",
    },
    {
        "id": "corporate_group",
        "name": "The Corporate Group",
        "age_range": "28-55",
        "personality": "Team building event, varying interest levels",
        "engagement_style": "Polite appreciation, occasional forced laughter",
        "improv_knowledge": "Minimal, may be mandatory attendance",
        "preferences": "Inclusive games, no individual spotlights, wrap on time",
    },
]


# =============================================================================
# SENTIMENT KEYWORDS DATA
# =============================================================================

SENTIMENT_KEYWORDS_DATA = {
    "positive_keywords": {
        "keywords": [
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
    },
    "negative_keywords": {
        "keywords": [
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
    },
    "engagement_keywords": {
        "keywords": {
            "high": [
                "excited",
                "participating",
                "volunteering",
                "shouting",
                "active",
                "energetic",
            ],
            "low": [
                "quiet",
                "silent",
                "checking phones",
                "leaving",
                "distracted",
                "yawning",
            ],
        }
    },
}


async def seed_collection(
    client: AsyncClient,
    collection_name: str,
    data: list,
    dry_run: bool = False,
) -> int:
    """Seed a single collection with data.

    Args:
        client: Firestore async client
        collection_name: Name of the collection to seed
        data: List of documents to insert (each must have 'id' field)
        dry_run: If True, don't actually write to Firestore

    Returns:
        Number of documents written
    """
    collection = client.collection(collection_name)
    count = 0

    for item in data:
        doc_id = item.get("id")
        if not doc_id:
            print(f"  WARNING: Skipping item without 'id': {item}")
            continue

        # Remove id from data since it's the document ID
        doc_data = {k: v for k, v in item.items() if k != "id"}

        if dry_run:
            print(f"  [DRY RUN] Would write: {collection_name}/{doc_id}")
        else:
            await collection.document(doc_id).set(doc_data)
            print(f"  Written: {collection_name}/{doc_id}")

        count += 1

    return count


async def seed_sentiment_keywords(
    client: AsyncClient,
    collection_name: str,
    data: dict,
    dry_run: bool = False,
) -> int:
    """Seed sentiment keywords collection with nested structure.

    Args:
        client: Firestore async client
        collection_name: Name of the collection
        data: Dictionary with keyword document data
        dry_run: If True, don't actually write to Firestore

    Returns:
        Number of documents written
    """
    collection = client.collection(collection_name)
    count = 0

    for doc_id, doc_data in data.items():
        if dry_run:
            print(f"  [DRY RUN] Would write: {collection_name}/{doc_id}")
        else:
            await collection.document(doc_id).set(doc_data)
            print(f"  Written: {collection_name}/{doc_id}")
        count += 1

    return count


async def main(dry_run: bool = False):
    """Main function to seed all Firestore tool collections."""
    print("=" * 60)
    print("Firestore Tool Data Seeder")
    print("=" * 60)
    print(f"Project: {settings.gcp_project_id}")
    print(f"Database: {settings.firestore_database}")
    print(f"Dry Run: {dry_run}")
    print("=" * 60)

    # Initialize Firestore client
    client = AsyncClient(
        project=settings.gcp_project_id,
        database=settings.firestore_database,
    )

    try:
        # Seed improv games
        print(f"\nSeeding {settings.firestore_games_collection}...")
        games_count = await seed_collection(
            client, settings.firestore_games_collection, GAMES_DATA, dry_run
        )
        print(f"  Total games: {games_count}")

        # Seed improv principles
        print(f"\nSeeding {settings.firestore_principles_collection}...")
        principles_count = await seed_collection(
            client, settings.firestore_principles_collection, PRINCIPLES_DATA, dry_run
        )
        print(f"  Total principles: {principles_count}")

        # Seed audience archetypes
        print(f"\nSeeding {settings.firestore_archetypes_collection}...")
        archetypes_count = await seed_collection(
            client, settings.firestore_archetypes_collection, ARCHETYPES_DATA, dry_run
        )
        print(f"  Total archetypes: {archetypes_count}")

        # Seed sentiment keywords
        print(f"\nSeeding {settings.firestore_sentiment_keywords_collection}...")
        keywords_count = await seed_sentiment_keywords(
            client,
            settings.firestore_sentiment_keywords_collection,
            SENTIMENT_KEYWORDS_DATA,
            dry_run,
        )
        print(f"  Total keyword documents: {keywords_count}")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Games:      {games_count}")
        print(f"Principles: {principles_count}")
        print(f"Archetypes: {archetypes_count}")
        print(f"Keywords:   {keywords_count}")
        total = games_count + principles_count + archetypes_count + keywords_count
        print(f"Total:      {total}")

        if dry_run:
            print("\n[DRY RUN] No changes were made to Firestore.")
        else:
            print("\nFirestore tool data seeding complete!")

    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed Firestore with improv tool data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without actually writing",
    )
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run))
