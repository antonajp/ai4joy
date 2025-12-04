#!/usr/bin/env python3
"""Update Games with Suggestion Fields

This script updates existing game documents in Firestore with new
suggestion-related fields (suggestion_count, suggestion_prompt, example_suggestions).

Only updates games that have these fields defined in the update data.

Usage:
    # From project root with virtual environment activated:
    python scripts/update_games_suggestions.py

    # Dry run (no writes):
    python scripts/update_games_suggestions.py --dry-run

Requirements:
    - Google Cloud credentials configured
    - Firestore database created
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


# Games that need suggestion field updates
# Only include games with explicit suggestion requirements
GAME_SUGGESTION_UPDATES = {
    "first_line_last_line": {
        "suggestion_count": 2,
        "suggestion_prompt": "This game needs TWO complete sentences from the audience: an OPENING LINE to start the scene and a CLOSING LINE to end the scene. Both should be interesting dialogue that could be said by a character.",
        "example_suggestions": [
            "Opening line: 'I can't believe you ate the last donut!' | Closing line: 'That's why I'm never trusting a baker again.'",
            "Opening line: 'Why is there a goat in the living room?' | Closing line: 'And that's how we became millionaires.'",
            "Opening line: 'This is the worst birthday ever.' | Closing line: 'I guess sometimes the universe knows what it's doing.'",
        ],
    },
    "expert_interview": {
        "suggestion_count": 1,
        "suggestion_prompt": "This game needs a made-up or absurd TOPIC that the player will be an expert in. The topic should be unusual, specific, and funny.",
        "example_suggestions": [
            "Competitive sock folding",
            "The psychology of houseplants",
            "Ancient alien cooking techniques",
            "Professional crayon sharpening",
        ],
    },
    "accusation": {
        "suggestion_count": 1,
        "suggestion_prompt": "This game needs an ACCUSATION - something absurd or mundane that one person would accuse another of doing. It should be specific and unusual.",
        "example_suggestions": [
            "You've been secretly teaching pigeons to dance!",
            "You ate my lunch from the office fridge!",
            "You've been using my Netflix account!",
            "You trained your dog to steal newspapers!",
        ],
    },
    "one_word_story": {
        "suggestion_count": 1,
        "suggestion_prompt": "This game needs a TOPIC or THEME for the story. It should be broad enough to allow creative exploration.",
        "example_suggestions": [
            "A vacation gone wrong",
            "The robot uprising",
            "Love at first sight",
            "A mysterious package",
        ],
    },
}


async def update_games(dry_run: bool = False):
    """Update game documents with new suggestion fields."""
    print("=" * 60)
    print("Game Suggestion Fields Updater")
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
        collection = client.collection(settings.firestore_games_collection)
        updated_count = 0

        for game_id, update_data in GAME_SUGGESTION_UPDATES.items():
            print(f"\nUpdating {game_id}...")

            if dry_run:
                print(f"  [DRY RUN] Would add fields:")
                print(f"    suggestion_count: {update_data.get('suggestion_count')}")
                print(f"    suggestion_prompt: {update_data.get('suggestion_prompt')[:50]}...")
                print(f"    example_suggestions: {len(update_data.get('example_suggestions', []))} examples")
            else:
                doc_ref = collection.document(game_id)
                doc = await doc_ref.get()

                if doc.exists:
                    await doc_ref.update(update_data)
                    print(f"  Updated: {game_id}")
                    updated_count += 1
                else:
                    print(f"  WARNING: Game {game_id} not found in Firestore!")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Games processed: {len(GAME_SUGGESTION_UPDATES)}")
        print(f"Games updated: {updated_count}")

        if dry_run:
            print("\n[DRY RUN] No changes were made to Firestore.")
        else:
            print("\nGame suggestion fields updated successfully!")

    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update game documents with suggestion fields"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be updated without actually writing",
    )
    args = parser.parse_args()

    asyncio.run(update_games(dry_run=args.dry_run))
