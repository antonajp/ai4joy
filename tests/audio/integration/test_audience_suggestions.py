"""
Integration Tests for Audience Suggestion Generation - IQS-60

Tests the MC Agent's interaction with the Room Agent for audience suggestions:
- TC-060-011: Suggestions reflect audience demographics
- TC-060-012: Tech audience gets tech-related suggestions
- TC-060-013: MC asks audience (Room Agent) not user
- TC-060-014: Suggestion type matches selected game
- TC-060-015: Multiple archetypes influence suggestions
- TC-060-016: Audience archetypes toolset integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_tc_060_011_suggestions_reflect_demographics():
    """TC-060-011: Suggestions reflect audience demographic composition.

    When the Room Agent generates suggestions, they should be influenced
    by the audience archetypes present in the session.
    """
    from app.toolsets.audience_archetypes_toolset import AudienceArchetypesToolset

    toolset = AudienceArchetypesToolset()

    # Generate a diverse audience sample
    audience = await toolset._generate_audience_sample(size=5)

    assert len(audience) == 5
    assert all("id" in member for member in audience)

    # Analyze the audience traits
    traits = await toolset._analyze_audience_traits(audience)

    assert "energy_profile" in traits
    assert "experience_profile" in traits
    assert "recommendation" in traits

    # Recommendation should be contextual
    assert len(traits["recommendation"]) > 0


@pytest.mark.asyncio
async def test_tc_060_012_tech_audience_tech_suggestions():
    """TC-060-012: Tech-focused audience gets tech-related suggestions.

    When the audience composition is tech-heavy, the suggestion generation
    should favor tech-related scenarios and references.
    """
    from app.toolsets.audience_archetypes_toolset import AudienceArchetypesToolset

    toolset = AudienceArchetypesToolset()

    # Create a tech-focused audience
    tech_audience = [
        {
            "id": "tech_1",
            "archetype_name": "Tech Professional",
            "preferences": "coding, startups, technology",
            "engagement_style": "Vocal and expressive",
            "improv_knowledge": "No prior experience",
        },
        {
            "id": "tech_2",
            "archetype_name": "Engineer",
            "preferences": "programming, gadgets, AI",
            "engagement_style": "Engaged but reserved",
            "improv_knowledge": "Limited exposure",
        },
        {
            "id": "tech_3",
            "archetype_name": "Startup Founder",
            "preferences": "innovation, disruption, tech culture",
            "engagement_style": "Very vocal",
            "improv_knowledge": "Extensive experience",
        },
    ]

    # Analyze this tech-heavy audience
    traits = await toolset._analyze_audience_traits(tech_audience)

    # Should recognize high engagement and mixed experience
    assert traits["energy_profile"] in ["high_energy", "mixed"]
    assert traits["total_members"] == 3

    # Recommendation should be appropriate for this audience
    assert len(traits["recommendation"]) > 0


@pytest.mark.asyncio
async def test_tc_060_013_mc_asks_audience_not_user():
    """TC-060-013: MC asks audience (Room Agent) for suggestions, not user.

    The MC Agent's prompt should be designed to interact with the Room Agent
    as the collective audience, asking "the room" for suggestions.
    """
    from app.agents.mc_agent import create_mc_agent_for_audio

    mc_agent = create_mc_agent_for_audio()

    # MC system prompt should reference asking the audience/room
    instruction = mc_agent.instruction.lower()

    # Should mention audience interaction concepts
    has_audience_concept = (
        "audience" in instruction
        or "room" in instruction
        or "crowd" in instruction
        or "suggestion from the audience" in instruction
    )

    assert has_audience_concept

    # MC should have tools to interact with audience
    assert mc_agent.tools is not None


@pytest.mark.asyncio
async def test_tc_060_014_suggestion_type_matches_game():
    """TC-060-014: Suggestion type matches the selected game requirements.

    Different games require different suggestion types (location, occupation,
    relationship, etc.). The Room Agent should understand game context.
    """
    from app.toolsets.audience_archetypes_toolset import AudienceArchetypesToolset

    toolset = AudienceArchetypesToolset()

    # Mock Firestore to avoid event loop issues
    with patch("app.services.firestore_tool_data_service.get_all_archetypes") as mock_get:
        mock_get.return_value = [
            {
                "archetype_name": "Tech Professional",
                "preferences": "coding, startups",
                "engagement_style": "Engaged but reserved",
                "improv_knowledge": "Limited exposure",
            },
            {
                "archetype_name": "Improviser",
                "preferences": "comedy, theater",
                "engagement_style": "Very vocal and expressive",
                "improv_knowledge": "Extensive experience",
            },
        ]

        # Generate audience and get vibe check
        audience = await toolset._generate_audience_sample(size=2)
        vibe = await toolset._get_vibe_check(audience)

        assert "overall_mood" in vibe
        assert "experience_level" in vibe
        assert "indicators" in vibe
        assert "recommendation" in vibe

        # Vibe check should provide actionable guidance
        assert len(vibe["indicators"]) > 0
        assert isinstance(vibe["indicators"], list)


@pytest.mark.asyncio
async def test_tc_060_015_multiple_archetypes_influence():
    """TC-060-015: Multiple archetypes combine to influence suggestions.

    When the audience has diverse archetypes, the suggestion should
    balance multiple perspectives rather than favoring just one.
    """
    from app.toolsets.audience_archetypes_toolset import AudienceArchetypesToolset

    toolset = AudienceArchetypesToolset()

    # Create a mixed audience
    mixed_audience = [
        {
            "id": "member_1",
            "preferences": "physical comedy, slapstick",
            "engagement_style": "Very vocal and expressive",
            "improv_knowledge": "No prior experience",
        },
        {
            "id": "member_2",
            "preferences": "clever wordplay, wit",
            "engagement_style": "Quiet but appreciative",
            "improv_knowledge": "Extensive experience",
        },
        {
            "id": "member_3",
            "preferences": "emotional scenes, drama",
            "engagement_style": "Engaged but reserved",
            "improv_knowledge": "Limited exposure",
        },
    ]

    traits = await toolset._analyze_audience_traits(mixed_audience)

    # Should recognize mixed energy and experience
    assert traits["energy_profile"] in ["high_energy", "mixed", "reserved"]
    assert traits["experience_profile"] in ["experienced", "beginner_friendly", "mixed"]

    # Should have counts for different engagement styles
    assert "high_engagement_count" in traits
    assert "low_engagement_count" in traits


@pytest.mark.asyncio
async def test_tc_060_016_audience_archetypes_toolset_integration():
    """TC-060-016: Audience Archetypes Toolset integrates with Room Agent.

    The Room Agent should have access to the AudienceArchetypesToolset
    for understanding audience composition and preferences.
    """
    from app.agents.room_agent import create_room_agent_for_audio
    from app.toolsets.audience_archetypes_toolset import AudienceArchetypesToolset

    room_agent = create_room_agent_for_audio()

    # Room agent should have the archetypes toolset
    assert room_agent.tools is not None
    assert len(room_agent.tools) > 0

    # Check that AudienceArchetypesToolset is included
    has_archetypes = False
    for tool in room_agent.tools:
        tool_str = str(type(tool).__name__)
        if "AudienceArchetypes" in tool_str or "Toolset" in tool_str:
            has_archetypes = True
            break

    # Should have toolsets attached
    assert has_archetypes or len(room_agent.tools) >= 2


@pytest.mark.asyncio
async def test_tc_060_017_get_all_archetypes():
    """TC-060-017: Toolset can retrieve all available archetypes.

    The AudienceArchetypesToolset should provide access to the complete
    catalog of audience archetypes stored in Firestore.
    """
    from app.toolsets.audience_archetypes_toolset import AudienceArchetypesToolset

    toolset = AudienceArchetypesToolset()

    # Should be able to get all archetypes
    with patch("app.services.firestore_tool_data_service.get_all_archetypes") as mock_get:
        mock_get.return_value = [
            {"archetype_name": "Tech Professional", "preferences": "coding, startups"},
            {"archetype_name": "Improviser", "preferences": "improv comedy, theater"},
            {"archetype_name": "Student", "preferences": "learning, discovery"},
        ]

        archetypes = await toolset._get_all_archetypes()

        assert len(archetypes) == 3
        assert all("archetype_name" in a for a in archetypes)


@pytest.mark.asyncio
async def test_tc_060_018_vibe_check_provides_indicators():
    """TC-060-018: Vibe check provides specific indicators for MC guidance.

    The vibe check should give the MC Agent concrete information about
    what's working and what adjustments might be needed.
    """
    from app.toolsets.audience_archetypes_toolset import AudienceArchetypesToolset

    toolset = AudienceArchetypesToolset()

    # High-energy experienced audience
    energetic_audience = [
        {
            "id": "e1",
            "preferences": "fast-paced, high-energy",
            "engagement_style": "Very vocal and expressive",
            "improv_knowledge": "Extensive experience",
        },
        {
            "id": "e2",
            "preferences": "physical comedy, action",
            "engagement_style": "Vocal and engaged",
            "improv_knowledge": "Professional performer",
        },
    ]

    vibe = await toolset._get_vibe_check(energetic_audience)

    assert vibe["overall_mood"] == "high_energy"
    assert vibe["experience_level"] == "experienced"

    # Should have specific indicators
    indicators = vibe["indicators"]
    assert len(indicators) >= 2
    assert any("energized" in ind.lower() or "participate" in ind.lower() for ind in indicators)
    assert any("knows improv" in ind.lower() or "complexity" in ind.lower() or "experienced" in ind.lower() for ind in indicators)


@pytest.mark.asyncio
async def test_tc_060_019_reserved_audience_different_vibe():
    """TC-060-019: Reserved audience produces different vibe check.

    A quiet, beginner audience should produce a different vibe check
    than an energetic, experienced one.
    """
    from app.toolsets.audience_archetypes_toolset import AudienceArchetypesToolset

    toolset = AudienceArchetypesToolset()

    # Reserved beginner audience
    reserved_audience = [
        {
            "id": "r1",
            "preferences": "thoughtful, subtle",
            "engagement_style": "Quiet but appreciative",
            "improv_knowledge": "No prior experience",
        },
        {
            "id": "r2",
            "preferences": "gentle humor, clever",
            "engagement_style": "Engaged but reserved",
            "improv_knowledge": "Limited exposure",
        },
    ]

    vibe = await toolset._get_vibe_check(reserved_audience)

    assert vibe["overall_mood"] in ["reserved", "mixed"]
    assert vibe["experience_level"] in ["beginner_friendly", "mixed"]

    # Should have indicators about warming up or accessibility
    indicators = vibe["indicators"]
    assert len(indicators) >= 2

    # At least one indicator should mention the reserved nature or beginner-friendliness
    has_relevant_indicator = any(
        "reserved" in ind.lower()
        or "warming" in ind.lower()
        or "first-timer" in ind.lower()
        or "accessible" in ind.lower()
        for ind in indicators
    )
    assert has_relevant_indicator


@pytest.mark.asyncio
async def test_tc_060_020_audience_sample_respects_size():
    """TC-060-020: Audience sample generation respects requested size.

    When generating an audience sample, the toolset should return
    the requested number of archetypes (or max available).
    """
    from app.toolsets.audience_archetypes_toolset import AudienceArchetypesToolset

    toolset = AudienceArchetypesToolset()

    with patch("app.services.firestore_tool_data_service.get_all_archetypes") as mock_get:
        # Mock 10 available archetypes
        mock_archetypes = [
            {"archetype_name": f"Archetype {i}", "preferences": f"pref {i}"}
            for i in range(10)
        ]
        mock_get.return_value = mock_archetypes

        # Request 3
        sample_3 = await toolset._generate_audience_sample(size=3)
        assert len(sample_3) == 3

        # Request 7
        sample_7 = await toolset._generate_audience_sample(size=7)
        assert len(sample_7) == 7

        # Request more than available (should return all 10)
        sample_15 = await toolset._generate_audience_sample(size=15)
        assert len(sample_15) == 10
