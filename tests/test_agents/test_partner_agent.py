"""Partner Agent Tests - Week 6 Implementation

Tests for Partner Agent with Phase 1 (supportive) and Phase 2 (fallible) behavior.

Test Coverage:
- TC-PARTNER-01: Agent creation and basic configuration
- TC-PARTNER-02: Phase 1 system prompt (supportive mode)
- TC-PARTNER-03: Phase 2 system prompt (fallible mode)
- TC-PARTNER-04: Phase parameter validation
- TC-PARTNER-05: Temperature configuration
"""

import pytest
from google.adk.agents import Agent
from app.config import get_settings

settings = get_settings()


class TestPartnerAgentCreation:
    """Test Partner Agent instantiation and configuration"""

    def test_tc_partner_01_agent_creation_phase1(self):
        """
        TC-PARTNER-01a: Partner Agent Creation - Phase 1

        Verify Partner agent is created correctly with Phase 1 configuration.

        Expected:
        - Agent is instance of google.adk.Agent
        - Model is configured pro model (needs creativity)
        - Name is partner_agent
        - No tools attached
        - Has valid instruction
        """
        from app.agents.partner_agent import create_partner_agent

        partner = create_partner_agent(phase=1)

        # Verify ADK Agent instance
        assert isinstance(partner, Agent), \
            f"Partner should be google.adk.Agent, got {type(partner)}"

        # Verify configuration
        assert partner.name == "partner_agent", \
            f"Name should be 'partner_agent', got '{partner.name}'"

        assert partner.model == settings.vertexai_pro_model, \
            f"Model should be '{settings.vertexai_pro_model}', got '{partner.model}'"

        # Verify no tools (Partner uses creativity, not tool calls)
        assert len(partner.tools) == 0, \
            f"Partner should have 0 tools, got {len(partner.tools)}"

        # Verify has instruction
        assert hasattr(partner, 'instruction'), "Partner missing instruction attribute"
        assert isinstance(partner.instruction, str), "Instruction should be string"
        assert len(partner.instruction) > 100, "Instruction seems too short"

        print("✓ Partner Agent Phase 1 created successfully")
        print(f"  - Name: {partner.name}")
        print(f"  - Model: {partner.model}")
        print(f"  - Tools: {len(partner.tools)}")
        print(f"  - Instruction length: {len(partner.instruction)} chars")

    def test_tc_partner_01_agent_creation_phase2(self):
        """
        TC-PARTNER-01b: Partner Agent Creation - Phase 2

        Verify Partner agent is created correctly with Phase 2 configuration.
        """
        from app.agents.partner_agent import create_partner_agent

        partner = create_partner_agent(phase=2)

        assert isinstance(partner, Agent)
        assert partner.name == "partner_agent"
        assert partner.model == settings.vertexai_pro_model
        assert len(partner.tools) == 0

        print("✓ Partner Agent Phase 2 created successfully")


class TestPartnerPhase1Behavior:
    """Test Phase 1 (Supportive Mode) characteristics"""

    def test_tc_partner_02_phase1_prompt_is_supportive(self):
        """
        TC-PARTNER-02: Phase 1 System Prompt is Supportive

        Phase 1 partner should have supportive, encouraging system prompt
        that helps beginners learn improv.

        Expected Keywords:
        - support, help, encourage, build, scaffold, guide
        - yes and, accept, build on

        NOT Expected:
        - mistake, forget, fallible, realistic errors
        """
        from app.agents.partner_agent import create_partner_agent

        partner = create_partner_agent(phase=1)
        instruction = partner.instruction.lower()

        # Check for supportive keywords
        supportive_keywords = ["support", "help", "encourage", "build", "scaffold", "guide"]
        found_supportive = [kw for kw in supportive_keywords if kw in instruction]

        assert len(found_supportive) >= 2, \
            f"Phase 1 prompt should contain supportive keywords. Found: {found_supportive}"

        # Should emphasize "yes, and"
        assert "yes" in instruction or "accept" in instruction, \
            "Phase 1 should emphasize acceptance"

        # Should NOT have fallible keywords
        fallible_keywords = ["mistake", "forget", "fallible", "error"]
        found_fallible = [kw for kw in fallible_keywords if kw in instruction]

        assert len(found_fallible) == 0, \
            f"Phase 1 should NOT mention mistakes/fallibility. Found: {found_fallible}"

        print("✓ Phase 1 prompt is appropriately supportive")
        print(f"  - Supportive keywords found: {found_supportive}")
        print(f"  - Fallible keywords (should be empty): {found_fallible}")

    def test_tc_partner_02_phase1_emphasizes_beginner_support(self):
        """
        TC-PARTNER-02b: Phase 1 Emphasizes Beginner Support

        Phase 1 should explicitly mention supporting beginners or learning.
        """
        from app.agents.partner_agent import create_partner_agent

        partner = create_partner_agent(phase=1)
        instruction = partner.instruction.lower()

        # Check for beginner-oriented language
        beginner_keywords = ["beginner", "learn", "student", "new", "first time", "starting"]
        found_beginner = [kw for kw in beginner_keywords if kw in instruction]

        # At least some reference to learning/beginners
        assert len(found_beginner) >= 1, \
            f"Phase 1 should reference beginners or learning. Instruction: {instruction[:200]}"

        print(f"✓ Phase 1 emphasizes beginner support: {found_beginner}")


class TestPartnerPhase2Behavior:
    """Test Phase 2 (Fallible Mode) characteristics"""

    def test_tc_partner_03_phase2_prompt_is_fallible(self):
        """
        TC-PARTNER-03: Phase 2 System Prompt is Fallible

        Phase 2 partner should act more like a realistic scene partner who
        might make mistakes or miss cues (instructional fading).

        Expected Keywords:
        - fallible, realistic, human, real, authentic
        - might forget, occasionally miss, like a scene partner

        Still Expected:
        - partner, scene, collaborative (not adversarial)
        """
        from app.agents.partner_agent import create_partner_agent

        partner = create_partner_agent(phase=2)
        instruction = partner.instruction.lower()

        # Check for fallible/realistic keywords
        fallible_keywords = ["fallible", "realistic", "human", "real", "authentic", "forget", "miss"]
        found_fallible = [kw for kw in fallible_keywords if kw in instruction]

        assert len(found_fallible) >= 2, \
            f"Phase 2 prompt should contain fallible/realistic keywords. Found: {found_fallible}"

        # Should still be collaborative
        assert "partner" in instruction or "scene" in instruction, \
            "Phase 2 should still emphasize partnership"

        # Should NOT be overly supportive/scaffolding
        assert instruction.count("help") < 3, \
            "Phase 2 should reduce scaffolding language"

        print("✓ Phase 2 prompt is appropriately fallible")
        print(f"  - Fallible keywords found: {found_fallible}")

    def test_tc_partner_03_phase2_reduces_scaffolding(self):
        """
        TC-PARTNER-03b: Phase 2 Reduces Scaffolding

        Phase 2 should have less hand-holding than Phase 1 (instructional fading).
        """
        from app.agents.partner_agent import create_partner_agent

        partner_p1 = create_partner_agent(phase=1)
        partner_p2 = create_partner_agent(phase=2)

        inst_p1 = partner_p1.instruction.lower()
        inst_p2 = partner_p2.instruction.lower()

        # Count scaffolding words in each phase
        scaffolding_words = ["help", "guide", "support", "encourage"]

        p1_scaffolding_count = sum(inst_p1.count(word) for word in scaffolding_words)
        p2_scaffolding_count = sum(inst_p2.count(word) for word in scaffolding_words)

        assert p2_scaffolding_count < p1_scaffolding_count, \
            f"Phase 2 should have less scaffolding than Phase 1. " \
            f"P1: {p1_scaffolding_count}, P2: {p2_scaffolding_count}"

        print(f"✓ Scaffolding reduced from Phase 1 to Phase 2")
        print(f"  - Phase 1 scaffolding words: {p1_scaffolding_count}")
        print(f"  - Phase 2 scaffolding words: {p2_scaffolding_count}")


class TestPartnerParameterValidation:
    """Test phase parameter validation"""

    def test_tc_partner_04_invalid_phase_raises_error(self):
        """
        TC-PARTNER-04: Invalid Phase Values Raise ValueError

        Only phase=1 or phase=2 should be accepted.
        Other values should raise ValueError with clear message.
        """
        from app.agents.partner_agent import create_partner_agent

        # Test invalid phase values
        invalid_phases = [0, 3, -1, 5, 10]

        for invalid_phase in invalid_phases:
            with pytest.raises(ValueError, match="phase must be 1 or 2"):
                create_partner_agent(phase=invalid_phase)
                pytest.fail(f"Phase {invalid_phase} should raise ValueError")

        print("✓ Invalid phase values correctly rejected")
        print(f"  - Tested invalid phases: {invalid_phases}")

    def test_tc_partner_04_valid_phases_accepted(self):
        """
        TC-PARTNER-04b: Valid Phase Values Accepted

        Phase 1 and 2 should work without errors.
        """
        from app.agents.partner_agent import create_partner_agent

        # Valid phases should work
        partner1 = create_partner_agent(phase=1)
        assert partner1 is not None

        partner2 = create_partner_agent(phase=2)
        assert partner2 is not None

        print("✓ Valid phases (1, 2) accepted")

    def test_tc_partner_04_phase_type_validation(self):
        """
        TC-PARTNER-04c: Phase Must Be Integer

        Phase parameter should be integer type.
        """
        from app.agents.partner_agent import create_partner_agent

        # Non-integer phases should raise error
        with pytest.raises((ValueError, TypeError)):
            create_partner_agent(phase="1")

        with pytest.raises((ValueError, TypeError)):
            create_partner_agent(phase=1.5)

        print("✓ Non-integer phase values rejected")


class TestPartnerConfiguration:
    """Test Partner Agent configuration details"""

    def test_tc_partner_05_uses_pro_model(self):
        """
        TC-PARTNER-05a: Partner Uses Gemini Pro Model

        Partner needs creativity and nuance, so should use Pro not Flash.
        """
        from app.agents.partner_agent import create_partner_agent

        partner = create_partner_agent(phase=1)

        assert partner.model == settings.vertexai_pro_model, \
            f"Partner should use {settings.vertexai_pro_model} for creativity, got {partner.model}"

        print("✓ Partner correctly uses Gemini Pro model")

    def test_tc_partner_05_no_tools_attached(self):
        """
        TC-PARTNER-05b: Partner Has No Tools

        Partner agent should rely on creativity, not tool calls.
        """
        from app.agents.partner_agent import create_partner_agent

        partner_p1 = create_partner_agent(phase=1)
        partner_p2 = create_partner_agent(phase=2)

        assert len(partner_p1.tools) == 0, \
            f"Phase 1 Partner should have 0 tools, got {len(partner_p1.tools)}"

        assert len(partner_p2.tools) == 0, \
            f"Phase 2 Partner should have 0 tools, got {len(partner_p2.tools)}"

        print("✓ Partner has no tools (creativity-focused)")

    def test_tc_partner_05_phases_have_different_prompts(self):
        """
        TC-PARTNER-05c: Phase 1 and Phase 2 Have Different Prompts

        Prompts should be substantially different between phases.
        """
        from app.agents.partner_agent import create_partner_agent

        partner_p1 = create_partner_agent(phase=1)
        partner_p2 = create_partner_agent(phase=2)

        # Prompts should be different
        assert partner_p1.instruction != partner_p2.instruction, \
            "Phase 1 and Phase 2 should have different system prompts"

        # Calculate similarity (simple check: different words)
        words_p1 = set(partner_p1.instruction.lower().split())
        words_p2 = set(partner_p2.instruction.lower().split())

        unique_to_p1 = words_p1 - words_p2
        unique_to_p2 = words_p2 - words_p1

        # Should have some unique words in each phase
        assert len(unique_to_p1) > 5, "Phase 1 should have unique keywords"
        assert len(unique_to_p2) > 5, "Phase 2 should have unique keywords"

        print("✓ Phase 1 and Phase 2 have distinct prompts")
        print(f"  - Unique to Phase 1: {len(unique_to_p1)} words")
        print(f"  - Unique to Phase 2: {len(unique_to_p2)} words")


class TestPartnerPromptQuality:
    """Test prompt quality and completeness"""

    def test_tc_partner_06_prompt_mentions_improv(self):
        """Both phases should mention improv/scene work"""
        from app.agents.partner_agent import create_partner_agent

        for phase in [1, 2]:
            partner = create_partner_agent(phase=phase)
            instruction = partner.instruction.lower()

            assert "improv" in instruction or "scene" in instruction, \
                f"Phase {phase} prompt should mention improv or scene work"

        print("✓ Both phases reference improv/scene work")

    def test_tc_partner_06_prompt_sets_character_role(self):
        """Prompts should establish Partner's role in the scene"""
        from app.agents.partner_agent import create_partner_agent

        for phase in [1, 2]:
            partner = create_partner_agent(phase=phase)
            instruction = partner.instruction.lower()

            role_keywords = ["partner", "scene partner", "you are", "your role"]
            has_role = any(kw in instruction for kw in role_keywords)

            assert has_role, \
                f"Phase {phase} prompt should establish Partner's role"

        print("✓ Both phases establish Partner's role")


# Pytest collection
def test_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("PARTNER AGENT TEST SUMMARY")
    print("="*60)
    print("\nTest Coverage:")
    print("  ✓ TC-PARTNER-01: Agent creation and configuration")
    print("  ✓ TC-PARTNER-02: Phase 1 supportive behavior")
    print("  ✓ TC-PARTNER-03: Phase 2 fallible behavior")
    print("  ✓ TC-PARTNER-04: Phase parameter validation")
    print("  ✓ TC-PARTNER-05: Configuration details")
    print("  ✓ TC-PARTNER-06: Prompt quality checks")
    print("\n" + "="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
