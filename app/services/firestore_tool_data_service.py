"""Firestore Tool Data Service - Async Data Access for ADK Tool Collections

This module provides async Firestore access for tool data collections including:
- improv_games: Game database for MC agent
- improv_principles: Core improv principles for Coach agent
- audience_archetypes: Audience demographic archetypes for Room agent
- sentiment_keywords: Keyword lists for sentiment analysis

Follows ADK patterns with async operations and singleton service instance.
"""

import os
import threading
from typing import Optional, List, Dict, Any, Union
from google.cloud.firestore_v1 import AsyncClient, AsyncQuery, AsyncCollectionReference
from google.oauth2 import service_account
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_firestore_client: Optional[AsyncClient] = None
_init_lock = threading.Lock()


def get_firestore_client() -> AsyncClient:
    """Get singleton async Firestore client instance.

    Returns:
        AsyncClient: Shared Firestore async client instance

    Note:
        Thread-safe using double-checked locking pattern.
        Uses explicit service account credentials if GOOGLE_APPLICATION_CREDENTIALS
        is set (local development), otherwise relies on ADC (production).
    """
    global _firestore_client

    if _firestore_client is not None:
        return _firestore_client

    with _init_lock:
        if _firestore_client is None:
            logger.info(
                "Initializing Firestore async client for tool data",
                project=settings.gcp_project_id,
                database=settings.firestore_database,
            )

            # Check for explicit service account file (local development)
            service_account_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if service_account_path and os.path.exists(service_account_path):
                # Use explicit credentials from service account file
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path
                )
                logger.info(
                    "Using explicit service account credentials for Firestore",
                    path=service_account_path,
                )
                _firestore_client = AsyncClient(
                    project=settings.gcp_project_id,
                    database=settings.firestore_database,
                    credentials=credentials,
                )
            else:
                # Use Application Default Credentials (production/Cloud Run)
                logger.info("Using ADC for Firestore")
                _firestore_client = AsyncClient(
                    project=settings.gcp_project_id,
                    database=settings.firestore_database,
                )

            logger.info("Firestore async client initialized successfully")

    return _firestore_client


async def close_firestore_client() -> None:
    """Close the Firestore client connection.

    Should be called during application shutdown.
    """
    global _firestore_client
    if _firestore_client is not None:
        await _firestore_client.close()
        _firestore_client = None
        logger.info("Firestore client closed")


def reset_firestore_client() -> None:
    """Reset the singleton for testing purposes."""
    global _firestore_client
    _firestore_client = None


# =============================================================================
# IMPROV GAMES COLLECTION
# =============================================================================


async def get_all_games() -> List[Dict[str, Any]]:
    """Get all improv games from Firestore.

    Returns:
        List of game dictionaries with all fields.
    """
    client = get_firestore_client()
    collection = client.collection(settings.firestore_games_collection)

    games: List[Dict[str, Any]] = []
    async for doc in collection.stream():
        game = doc.to_dict()
        if game is not None:
            game["id"] = doc.id
            games.append(game)

    logger.debug("Fetched all games from Firestore", count=len(games))
    return games


async def get_game_by_id(game_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific game by ID.

    Args:
        game_id: The game document ID

    Returns:
        Game dictionary if found, None otherwise.
    """
    client = get_firestore_client()
    doc_ref = client.collection(settings.firestore_games_collection).document(game_id)
    doc = await doc_ref.get()

    if doc.exists:
        game = doc.to_dict()
        if game is not None:
            game["id"] = doc.id
            logger.debug("Game found", game_id=game_id)
            return game

    logger.warning("Game not found", game_id=game_id)
    return None


async def get_game_by_name(game_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific game by name (case-insensitive).

    Args:
        game_name: The game name to search for

    Returns:
        Game dictionary if found, None otherwise.

    Note:
        Performs case-insensitive matching by comparing lowercase names.
        Firestore doesn't support case-insensitive queries natively.
    """
    client = get_firestore_client()
    collection_ref = client.collection(settings.firestore_games_collection)

    game_name_lower = game_name.lower().strip()

    async for doc in collection_ref.stream():
        game = doc.to_dict()
        if game is not None:
            stored_name = game.get("name", "")
            if stored_name.lower().strip() == game_name_lower:
                game["id"] = doc.id
                logger.debug("Game found by name", game_name=game_name)
                return game

    logger.warning("Game not found by name", game_name=game_name)
    return None


async def search_games(
    energy_level: Optional[str] = None,
    player_count: Optional[int] = None,
    difficulty: Optional[str] = None,
    max_duration: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Search games by criteria.

    Args:
        energy_level: Filter by energy (high, medium, low)
        player_count: Filter by player count capability
        difficulty: Filter by difficulty (beginner, intermediate, advanced)
        max_duration: Maximum duration in minutes

    Returns:
        List of matching game dictionaries.
    """
    client = get_firestore_client()
    collection_ref = client.collection(settings.firestore_games_collection)

    # Build query with available filters
    query: Union[AsyncCollectionReference, AsyncQuery] = collection_ref

    if energy_level:
        query = query.where("energy_level", "==", energy_level.lower())

    if difficulty:
        query = query.where("difficulty", "==", difficulty.lower())

    # Execute query
    results: List[Dict[str, Any]] = []
    async for doc in query.stream():
        game = doc.to_dict()
        if game is None:
            continue

        game["id"] = doc.id

        # Apply client-side filters that can't be done in Firestore directly
        if player_count is not None:
            pc = game.get("player_count", {})
            min_players = pc.get("min", 1) if isinstance(pc, dict) else 1
            max_players = pc.get("max", 99) if isinstance(pc, dict) else 99
            if not (min_players <= player_count <= max_players):
                continue

        if max_duration is not None:
            duration = game.get("duration_minutes", 0)
            if isinstance(duration, (int, float)) and duration > max_duration:
                continue

        results.append(game)

    logger.info(
        "Game search completed",
        energy_level=energy_level,
        player_count=player_count,
        difficulty=difficulty,
        max_duration=max_duration,
        results_count=len(results),
    )
    return results


# =============================================================================
# IMPROV PRINCIPLES COLLECTION
# =============================================================================


async def get_all_principles() -> List[Dict[str, Any]]:
    """Get all improv principles from Firestore.

    Returns:
        List of principle dictionaries with all fields.
    """
    client = get_firestore_client()
    collection = client.collection(settings.firestore_principles_collection)

    principles: List[Dict[str, Any]] = []
    async for doc in collection.stream():
        principle = doc.to_dict()
        if principle is not None:
            principle["id"] = doc.id
            principles.append(principle)

    logger.debug("Fetched all principles from Firestore", count=len(principles))
    return principles


async def get_principle_by_id(principle_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific principle by ID.

    Args:
        principle_id: The principle document ID

    Returns:
        Principle dictionary if found, None otherwise.
    """
    client = get_firestore_client()
    doc_ref = client.collection(settings.firestore_principles_collection).document(
        principle_id
    )
    doc = await doc_ref.get()

    if doc.exists:
        principle = doc.to_dict()
        if principle is not None:
            principle["id"] = doc.id
            logger.debug("Principle found", principle_id=principle_id)
            return principle

    logger.warning("Principle not found", principle_id=principle_id)
    return None


async def get_principles_by_importance(importance: str) -> List[Dict[str, Any]]:
    """Get principles filtered by importance level.

    Args:
        importance: Level (foundational, essential, technical, intermediate, advanced)

    Returns:
        List of matching principles.
    """
    client = get_firestore_client()
    collection_ref = client.collection(settings.firestore_principles_collection)
    query: AsyncQuery = collection_ref.where("importance", "==", importance.lower())

    results: List[Dict[str, Any]] = []
    async for doc in query.stream():
        principle = doc.to_dict()
        if principle is not None:
            principle["id"] = doc.id
            results.append(principle)

    logger.info(
        "Principles filtered by importance", importance=importance, count=len(results)
    )
    return results


async def get_beginner_essentials() -> List[Dict[str, Any]]:
    """Get essential principles for beginners.

    Returns:
        List of foundational and essential principles.
    """
    client = get_firestore_client()
    collection_ref = client.collection(settings.firestore_principles_collection)

    # Query for foundational and essential importance levels
    results: List[Dict[str, Any]] = []
    async for doc in collection_ref.stream():
        principle = doc.to_dict()
        if principle is not None:
            importance = principle.get("importance")
            if importance in ["foundational", "essential"]:
                principle["id"] = doc.id
                results.append(principle)

    logger.info("Beginner essentials retrieved", count=len(results))
    return results


async def search_principles_by_keyword(keyword: str) -> List[Dict[str, Any]]:
    """Search principles by keyword in name or description.

    Args:
        keyword: Search term to match

    Returns:
        List of matching principles.

    Note:
        This performs client-side filtering as Firestore doesn't support
        full-text search. For production, consider using Firestore with
        a search extension or external search service.
    """
    client = get_firestore_client()
    collection_ref = client.collection(settings.firestore_principles_collection)

    keyword_lower = keyword.lower()
    results: List[Dict[str, Any]] = []

    async for doc in collection_ref.stream():
        principle = doc.to_dict()
        if principle is not None:
            name = str(principle.get("name", "")).lower()
            description = str(principle.get("description", "")).lower()

            if keyword_lower in name or keyword_lower in description:
                principle["id"] = doc.id
                results.append(principle)

    logger.info("Keyword search completed", keyword=keyword, results=len(results))
    return results


# =============================================================================
# AUDIENCE ARCHETYPES COLLECTION
# =============================================================================


async def get_all_archetypes() -> List[Dict[str, Any]]:
    """Get all audience archetypes from Firestore.

    Returns:
        List of archetype dictionaries with all fields.
    """
    client = get_firestore_client()
    collection = client.collection(settings.firestore_archetypes_collection)

    archetypes: List[Dict[str, Any]] = []
    async for doc in collection.stream():
        archetype = doc.to_dict()
        if archetype is not None:
            archetype["id"] = doc.id
            archetypes.append(archetype)

    logger.debug("Fetched all archetypes from Firestore", count=len(archetypes))
    return archetypes


async def get_archetype_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a specific archetype by name.

    Args:
        name: The archetype name

    Returns:
        Archetype dictionary if found, None otherwise.
    """
    client = get_firestore_client()
    collection_ref = client.collection(settings.firestore_archetypes_collection)
    query: AsyncQuery = collection_ref.where("name", "==", name)

    async for doc in query.stream():
        archetype = doc.to_dict()
        if archetype is not None:
            archetype["id"] = doc.id
            logger.debug("Archetype found", name=name)
            return archetype

    logger.warning("Archetype not found", name=name)
    return None


# =============================================================================
# SENTIMENT KEYWORDS COLLECTION
# =============================================================================


async def get_sentiment_keywords() -> Dict[str, Any]:
    """Get sentiment keyword lists from Firestore.

    Returns:
        Dictionary with 'positive', 'negative', and 'engagement' keyword lists.
    """
    client = get_firestore_client()
    collection = client.collection(settings.firestore_sentiment_keywords_collection)

    keywords: Dict[str, Any] = {
        "positive": [],
        "negative": [],
        "engagement": {"high": [], "low": []},
    }

    async for doc in collection.stream():
        doc_id = doc.id
        data = doc.to_dict()
        if data is None:
            continue

        if doc_id == "positive_keywords":
            keywords["positive"] = data.get("keywords", [])
        elif doc_id == "negative_keywords":
            keywords["negative"] = data.get("keywords", [])
        elif doc_id == "engagement_keywords":
            keywords["engagement"] = data.get("keywords", {"high": [], "low": []})

    logger.debug(
        "Fetched sentiment keywords",
        positive_count=len(keywords["positive"]),
        negative_count=len(keywords["negative"]),
    )
    return keywords
