#!/usr/bin/env python3
"""Demonstration Script for IQS-60 Audience Suggestion Generation

This script demonstrates the new functionality where the Room Agent
provides audience suggestions based on demographic data.

Run from project root:
    python docs/IQS-60-demo-script.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.toolsets.audience_archetypes_toolset import AudienceArchetypesToolset
from app.agents.room_agent import create_room_agent_for_suggestions


async def demo_suggestion_generation():
    """Demonstrate audience suggestion generation."""
    print("=" * 70)
    print("IQS-60 Audience Suggestion Generation Demo")
    print("=" * 70)
    print()

    toolset = AudienceArchetypesToolset()

    try:
        # Demo 1: Generate location suggestion
        print("1. Generating a LOCATION suggestion...")
        location = await toolset._generate_audience_suggestion("location")
        print(f"   Result: {location}")
        print()

        # Demo 2: Generate relationship suggestion
        print("2. Generating a RELATIONSHIP suggestion...")
        relationship = await toolset._generate_audience_suggestion("relationship")
        print(f"   Result: {relationship}")
        print()

        # Demo 3: Generate topic suggestion
        print("3. Generating a TOPIC suggestion...")
        topic = await toolset._generate_audience_suggestion("topic")
        print(f"   Result: {topic}")
        print()

        # Demo 4: Get game-specific suggestion for Long Form
        print("4. Getting suggestion for LONG FORM game...")
        long_form_result = await toolset._get_suggestion_for_game("Long Form")
        print(f"   Suggestion: {long_form_result['suggestion']}")
        print(f"   Type: {long_form_result['suggestion_type']}")
        print(f"   Reasoning: {long_form_result['reasoning']}")
        print()

        # Demo 5: Get game-specific suggestion for Questions Only
        print("5. Getting suggestion for QUESTIONS ONLY game...")
        questions_result = await toolset._get_suggestion_for_game("Questions Only")
        print(f"   Suggestion: {questions_result['suggestion']}")
        print(f"   Type: {questions_result['suggestion_type']}")
        print(f"   Reasoning: {questions_result['reasoning']}")
        print()

        # Demo 6: Get game-specific suggestion for Expert Interview
        print("6. Getting suggestion for EXPERT INTERVIEW game...")
        expert_result = await toolset._get_suggestion_for_game("Expert Interview")
        print(f"   Suggestion: {expert_result['suggestion']}")
        print(f"   Type: {expert_result['suggestion_type']}")
        print(f"   Reasoning: {expert_result['reasoning']}")
        print()

        # Demo 7: Generate suggestion with tech-heavy audience
        print("7. Generating LOCATION suggestion for TECH AUDIENCE...")
        tech_audience = [
            {
                "demographics": {"occupation": "Software Engineer"},
                "preferences": "tech, innovation",
                "engagement_style": "vocal",
                "improv_knowledge": "limited",
            },
            {
                "demographics": {"occupation": "UX Designer"},
                "preferences": "tech, design",
                "engagement_style": "expressive",
                "improv_knowledge": "no prior experience",
            },
        ]
        tech_location = await toolset._generate_audience_suggestion(
            "location", audience_sample=tech_audience
        )
        print(f"   Result: {tech_location}")
        print(
            "   (Should be tech-related like 'A startup office' or 'A hackathon')"
        )
        print()

        print("=" * 70)
        print("Demo completed successfully!")
        print()
        print("NEXT STEPS:")
        print("  - Room Agent can now use _get_suggestion_for_game() tool")
        print("  - MC Agent will ask Room Agent for suggestions instead of USER")
        print("  - Suggestions will reflect audience demographics automatically")
        print("=" * 70)

    finally:
        await toolset.close()


async def demo_room_agent_creation():
    """Demonstrate creating the suggestion-focused Room Agent."""
    print()
    print("=" * 70)
    print("Room Agent for Suggestions Demo")
    print("=" * 70)
    print()

    print("Creating suggestion-focused Room Agent...")
    room_agent = create_room_agent_for_suggestions()

    print(f"✓ Agent created: {room_agent.name}")
    print(f"✓ Model: {room_agent.model}")
    print(f"✓ Description: {room_agent.description}")
    print()
    print("The Room Agent is ready to provide audience suggestions!")
    print("=" * 70)


if __name__ == "__main__":
    print("\n🎭 Starting IQS-60 Demo...\n")

    # Run suggestion generation demo
    asyncio.run(demo_suggestion_generation())

    # Run room agent creation demo
    asyncio.run(demo_room_agent_creation())

    print("\n✅ All demos completed!\n")
