"""Week 6 Edge Case Tests - Additional Coverage for Partner/Coach/Stage Manager

This test file provides additional edge case coverage beyond the main test suites.
Focuses on:
- Non-integer phase values (float, string)
- Boundary conditions
- Invalid tool invocations
- Concurrent agent creation
- Memory/performance edge cases
"""

import pytest
from app.config import get_settings

settings = get_settings()


class TestPartnerAgentEdgeCases:
    """Edge cases for Partner Agent not covered in main test suite"""

    def test_partner_phase_float_value_rejected(self):
        """Phase parameter should reject float values"""
        from app.agents.partner_agent import create_partner_agent

        with pytest.raises(TypeError, match="phase must be an integer"):
            create_partner_agent(phase=1.5)

        with pytest.raises(TypeError, match="phase must be an integer"):
            create_partner_agent(phase=2.0)

    def test_partner_phase_string_value_rejected(self):
        """Phase parameter should reject string values"""
        from app.agents.partner_agent import create_partner_agent

        with pytest.raises(TypeError, match="phase must be an integer"):
            create_partner_agent(phase="1")

        with pytest.raises(TypeError, match="phase must be an integer"):
            create_partner_agent(phase="Phase 1")

    def test_partner_phase_none_value_rejected(self):
        """Phase parameter should reject None"""
        from app.agents.partner_agent import create_partner_agent

        with pytest.raises(TypeError):
            create_partner_agent(phase=None)

    def test_partner_agent_idempotent(self):
        """Creating same phase multiple times should produce consistent agents"""
        from app.agents.partner_agent import create_partner_agent

        # Create Phase 1 multiple times
        p1_a = create_partner_agent(phase=1)
        p1_b = create_partner_agent(phase=1)

        # Should have identical configuration
        assert p1_a.name == p1_b.name
        assert p1_a.model == p1_b.model
        assert p1_a.instruction == p1_b.instruction
        assert len(p1_a.tools) == len(p1_b.tools)

    def test_partner_prompt_length_reasonable(self):
        """Prompts should be detailed but not excessively long"""
        from app.agents.partner_agent import create_partner_agent

        p1 = create_partner_agent(phase=1)
        p2 = create_partner_agent(phase=2)

        # Prompts should be substantial (> 500 chars) but not excessive (< 10000 chars)
        assert 500 < len(p1.instruction) < 10000, (
            f"Phase 1 prompt length: {len(p1.instruction)}"
        )

        assert 500 < len(p2.instruction) < 10000, (
            f"Phase 2 prompt length: {len(p2.instruction)}"
        )


class TestCoachAgentEdgeCases:
    """Edge cases for Coach Agent tool integration"""

    @pytest.mark.asyncio
    async def test_get_principle_by_invalid_id(self):
        """Tool should handle invalid principle IDs gracefully"""
        from app.tools import improv_expert_tools

        # Non-existent ID should return empty dict
        result = await improv_expert_tools.get_principle_by_id("nonexistent_principle")
        assert result == {}, "Should return empty dict for invalid ID"

    @pytest.mark.asyncio
    async def test_search_principles_empty_keyword(self):
        """Tool should handle empty search keyword"""
        from app.tools import improv_expert_tools

        # Empty keyword should return all principles (matches everything)
        result = await improv_expert_tools.search_principles_by_keyword("")
        assert len(result) == 10, "Empty keyword should match all principles"

    @pytest.mark.asyncio
    async def test_search_principles_case_insensitive(self):
        """Search should be case-insensitive"""
        from app.tools import improv_expert_tools

        result_lower = await improv_expert_tools.search_principles_by_keyword("yes")
        result_upper = await improv_expert_tools.search_principles_by_keyword("YES")
        result_mixed = await improv_expert_tools.search_principles_by_keyword("YeS")

        # All should return same results
        assert len(result_lower) == len(result_upper) == len(result_mixed)

    @pytest.mark.asyncio
    async def test_get_principles_by_invalid_importance(self):
        """Tool should handle invalid importance levels"""
        from app.tools import improv_expert_tools

        result = await improv_expert_tools.get_principles_by_importance("invalid_level")
        assert result == [], "Invalid importance should return empty list"

    def test_coach_tool_count_correct(self):
        """Coach should have exactly 4 tools, no more, no less"""
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()

        # Verify tool count
        assert len(coach.tools) == 4, f"Expected 4 tools, got {len(coach.tools)}"

        # Verify tool names are unique
        tool_names = [t.__name__ for t in coach.tools]
        assert len(tool_names) == len(set(tool_names)), "Tool names should be unique"


class TestStageManagerEdgeCases:
    """Edge cases for Stage Manager orchestration"""

    def test_stage_manager_turn_count_zero(self):
        """Stage Manager should handle turn_count=0 (first turn)"""
        from app.agents.stage_manager import create_stage_manager

        sm = create_stage_manager(turn_count=0)
        assert sm is not None
        assert len(sm.sub_agents) == 4

        # Should be Phase 1
        assert (
            "phase 1" in sm.instruction.lower()
            or "supportive" in sm.instruction.lower()
        )

    def test_stage_manager_turn_count_boundary(self):
        """Stage Manager should handle turn_count=3 and turn_count=4 differently"""
        from app.agents.stage_manager import create_stage_manager

        sm_t3 = create_stage_manager(turn_count=3)
        sm_t4 = create_stage_manager(turn_count=4)

        # Instructions should differ at boundary
        assert sm_t3.instruction != sm_t4.instruction

        # Turn 3 should mention Phase 1, Turn 4 should mention Phase 2
        inst_t3_lower = sm_t3.instruction.lower()
        inst_t4_lower = sm_t4.instruction.lower()

        # Check phase references
        assert "phase 1" in inst_t3_lower or "supportive" in inst_t3_lower
        assert "phase 2" in inst_t4_lower or "fallible" in inst_t4_lower

    def test_stage_manager_large_turn_count(self):
        """Stage Manager should handle very large turn counts"""
        from app.agents.stage_manager import create_stage_manager

        # Should not crash with large turn count
        sm = create_stage_manager(turn_count=1000)
        assert sm is not None
        assert len(sm.sub_agents) == 4

    def test_stage_manager_negative_turn_count(self):
        """Stage Manager should handle negative turn count gracefully"""
        from app.agents.stage_manager import create_stage_manager

        # Should either default to Phase 1 or raise clear error
        # Current implementation treats negative as < 4, so Phase 1
        sm = create_stage_manager(turn_count=-1)
        assert sm is not None
        # Should be Phase 1 (supportive)
        inst_lower = sm.instruction.lower()
        assert "phase 1" in inst_lower or "supportive" in inst_lower


class TestPhaseTransitionEdgeCases:
    """Edge cases for phase transition logic"""

    def test_determine_partner_phase_boundary_values(self):
        """Test exact boundary values for phase transition"""
        from app.agents.stage_manager import determine_partner_phase

        # Test around boundary
        assert determine_partner_phase(2) == 1
        assert determine_partner_phase(3) == 1  # Last turn of Phase 1
        assert determine_partner_phase(4) == 2  # First turn of Phase 2
        assert determine_partner_phase(5) == 2

    def test_get_partner_agent_for_turn_consistency(self):
        """get_partner_agent_for_turn should be consistent for same turn"""
        from app.agents.stage_manager import get_partner_agent_for_turn

        # Same turn should produce same phase
        p1_a = get_partner_agent_for_turn(turn_count=2)
        p1_b = get_partner_agent_for_turn(turn_count=2)

        assert p1_a.instruction == p1_b.instruction
        assert p1_a.model == p1_b.model

    def test_phase_transition_all_turns_0_to_10(self):
        """Verify phase assignment for turns 0-10"""
        from app.agents.stage_manager import determine_partner_phase

        expected = {
            0: 1,
            1: 1,
            2: 1,
            3: 1,  # Phase 1
            4: 2,
            5: 2,
            6: 2,
            7: 2,
            8: 2,
            9: 2,
            10: 2,  # Phase 2
        }

        for turn, expected_phase in expected.items():
            actual_phase = determine_partner_phase(turn)
            assert actual_phase == expected_phase, (
                f"Turn {turn}: expected Phase {expected_phase}, got Phase {actual_phase}"
            )


class TestIntegrationEdgeCases:
    """Integration edge cases across multiple agents"""

    def test_all_agents_have_unique_names(self):
        """All sub-agents should have unique names"""
        from app.agents.stage_manager import create_stage_manager

        sm = create_stage_manager()
        names = [agent.name for agent in sm.sub_agents]

        assert len(names) == len(set(names)), (
            f"Agent names should be unique, got: {names}"
        )

    def test_all_agents_have_models_assigned(self):
        """All agents should have valid model assignments"""
        from app.agents.stage_manager import create_stage_manager

        sm = create_stage_manager()

        valid_models = [settings.vertexai_flash_model, settings.vertexai_pro_model]
        for agent in sm.sub_agents:
            assert hasattr(agent, "model"), f"Agent {agent.name} missing model"
            assert agent.model in valid_models, (
                f"Agent {agent.name} has invalid model: {agent.model}"
            )

    def test_model_selection_appropriate(self):
        """Verify appropriate model selection for each agent"""
        from app.agents.stage_manager import create_stage_manager

        sm = create_stage_manager()

        for agent in sm.sub_agents:
            if agent.name == "partner_agent":
                # Partner needs creativity, should use Pro
                assert agent.model == settings.vertexai_pro_model, (
                    "Partner should use Pro model"
                )
            elif agent.name == "coach_agent":
                # Coach can use Flash for speed
                assert agent.model == settings.vertexai_flash_model, (
                    "Coach should use Flash model"
                )
            elif agent.name == "stage_manager":
                # Stage Manager coordinates, uses Flash
                assert agent.model == settings.vertexai_flash_model, (
                    "Stage Manager should use Flash model"
                )


class TestPromptQualityEdgeCases:
    """Test prompt quality and consistency"""

    def test_all_prompts_non_empty(self):
        """All agent prompts should be non-empty"""
        from app.agents.stage_manager import create_stage_manager

        sm = create_stage_manager()

        # Check stage manager
        assert len(sm.instruction) > 0, "Stage Manager prompt is empty"

        # Check all sub-agents
        for agent in sm.sub_agents:
            assert len(agent.instruction) > 0, f"Agent {agent.name} has empty prompt"

    def test_prompts_are_strings(self):
        """All prompts should be string type"""
        from app.agents.stage_manager import create_stage_manager

        sm = create_stage_manager()

        assert isinstance(sm.instruction, str), "Stage Manager prompt not string"

        for agent in sm.sub_agents:
            assert isinstance(agent.instruction, str), (
                f"Agent {agent.name} prompt not string"
            )

    def test_partner_prompts_differ_between_phases(self):
        """Phase 1 and Phase 2 prompts should be significantly different"""
        from app.agents.partner_agent import create_partner_agent

        p1 = create_partner_agent(phase=1)
        p2 = create_partner_agent(phase=2)

        # Calculate word overlap
        words_p1 = set(p1.instruction.lower().split())
        words_p2 = set(p2.instruction.lower().split())

        overlap = words_p1.intersection(words_p2)
        unique_p1 = words_p1 - words_p2
        unique_p2 = words_p2 - words_p1

        # Should have substantial unique content in each phase
        assert len(unique_p1) > 20, "Phase 1 should have unique content"
        assert len(unique_p2) > 20, "Phase 2 should have unique content"

        # Overlap should be less than 80% of either prompt
        assert len(overlap) < 0.8 * len(words_p1), "Prompts too similar"
        assert len(overlap) < 0.8 * len(words_p2), "Prompts too similar"


# Performance and Memory Tests
class TestPerformanceEdgeCases:
    """Performance and memory edge cases"""

    def test_rapid_agent_creation(self):
        """Creating many agents rapidly should not cause issues"""
        from app.agents.partner_agent import create_partner_agent

        # Create 20 agents rapidly
        agents = []
        for i in range(20):
            phase = 1 if i % 2 == 0 else 2
            agent = create_partner_agent(phase=phase)
            agents.append(agent)

        assert len(agents) == 20
        # All should be valid
        for agent in agents:
            assert agent.name == "partner_agent"
            assert agent.model == settings.vertexai_pro_model

    def test_stage_manager_multiple_instances(self):
        """Multiple Stage Manager instances should coexist"""
        from app.agents.stage_manager import create_stage_manager

        managers = []
        for turn in range(0, 10):
            sm = create_stage_manager(turn_count=turn)
            managers.append(sm)

        assert len(managers) == 10
        # All should be valid
        for sm in managers:
            assert sm.name == "stage_manager"
            assert len(sm.sub_agents) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
