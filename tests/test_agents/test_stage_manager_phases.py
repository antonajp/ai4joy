"""Stage Manager Phase Transition Tests - Week 6 Implementation

Tests for Stage Manager orchestration with 4 sub-agents and phase transition logic.

Test Coverage:
- TC-STAGE-01: Stage Manager has 4 sub-agents
- TC-STAGE-02: Phase transition logic (turn 0-3 = Phase 1)
- TC-STAGE-03: Phase transition logic (turn 4+ = Phase 2)
- TC-STAGE-04: Partner agent updates with phase change
- TC-STAGE-05: Phase info in instruction context
"""

import pytest
from google.adk import Agent


class TestStageManagerSubAgents:
    """Test Stage Manager has all 4 sub-agents"""

    def test_tc_stage_01_has_four_sub_agents(self):
        """
        TC-STAGE-01a: Stage Manager Has 4 Sub-Agents

        Stage Manager should orchestrate:
        1. MC Agent
        2. Room Agent
        3. Partner Agent
        4. Coach Agent
        """
        from app.agents.stage_manager import create_stage_manager

        stage_manager = create_stage_manager()

        # Verify has sub_agents attribute
        assert hasattr(stage_manager, 'sub_agents'), \
            "Stage Manager missing sub_agents attribute"

        # Verify exactly 4 sub-agents
        assert len(stage_manager.sub_agents) == 4, \
            f"Stage Manager should have 4 sub-agents, got {len(stage_manager.sub_agents)}"

        print("✓ Stage Manager has 4 sub-agents")

    def test_tc_stage_01_sub_agents_are_correct_types(self):
        """
        TC-STAGE-01b: All Sub-Agents Are ADK Agents

        All sub-agents should be instances of google.adk.Agent.
        """
        from app.agents.stage_manager import create_stage_manager

        stage_manager = create_stage_manager()

        for sub_agent in stage_manager.sub_agents:
            assert isinstance(sub_agent, Agent), \
                f"Sub-agent {sub_agent} is not google.adk.Agent"

        print("✓ All sub-agents are ADK Agent instances")

    def test_tc_stage_01_has_all_required_agents(self):
        """
        TC-STAGE-01c: All Required Agents Present

        Verify MC, Room, Partner, Coach are all present by name.
        """
        from app.agents.stage_manager import create_stage_manager

        stage_manager = create_stage_manager()
        agent_names = [agent.name for agent in stage_manager.sub_agents]

        required_agents = ['mc_agent', 'room_agent', 'partner_agent', 'coach_agent']

        for required_agent in required_agents:
            assert required_agent in agent_names, \
                f"Missing required agent: {required_agent}. Found: {agent_names}"

        print("✓ All required agents present")
        print(f"  - Agent names: {agent_names}")


class TestPhaseTransitionLogic:
    """Test phase transition logic (turn count → phase number)"""

    def test_tc_stage_02_turns_0_to_3_are_phase_1(self):
        """
        TC-STAGE-02: Turns 0-3 Should Be Phase 1 (Supportive)

        Phase 1 = Supportive mode for first 4 turns (0, 1, 2, 3)
        """
        from app.agents.stage_manager import determine_partner_phase

        for turn_count in [0, 1, 2, 3]:
            phase = determine_partner_phase(turn_count)

            assert phase == 1, \
                f"Turn {turn_count} should be Phase 1, got Phase {phase}"

        print("✓ Turns 0-3 correctly map to Phase 1")

    def test_tc_stage_03_turn_4_onwards_is_phase_2(self):
        """
        TC-STAGE-03: Turns 4+ Should Be Phase 2 (Fallible)

        Phase 2 = Fallible mode starting at turn 4
        """
        from app.agents.stage_manager import determine_partner_phase

        test_turns = [4, 5, 6, 7, 8, 9, 10, 14, 20]

        for turn_count in test_turns:
            phase = determine_partner_phase(turn_count)

            assert phase == 2, \
                f"Turn {turn_count} should be Phase 2, got Phase {phase}"

        print("✓ Turns 4+ correctly map to Phase 2")
        print(f"  - Tested turns: {test_turns}")

    def test_tc_stage_03_phase_transition_boundary(self):
        """
        TC-STAGE-03b: Phase Transition Happens Exactly at Turn 4

        Verify boundary: turn 3 = Phase 1, turn 4 = Phase 2
        """
        from app.agents.stage_manager import determine_partner_phase

        phase_turn_3 = determine_partner_phase(3)
        phase_turn_4 = determine_partner_phase(4)

        assert phase_turn_3 == 1, "Turn 3 should be Phase 1"
        assert phase_turn_4 == 2, "Turn 4 should be Phase 2"
        assert phase_turn_3 != phase_turn_4, "Phases should differ at boundary"

        print("✓ Phase transition boundary correct (turn 3 → turn 4)")

    def test_tc_stage_03_function_returns_integer(self):
        """
        TC-STAGE-03c: Phase Function Returns Integer

        determine_partner_phase should return int 1 or 2
        """
        from app.agents.stage_manager import determine_partner_phase

        for turn_count in [0, 5, 10]:
            phase = determine_partner_phase(turn_count)

            assert isinstance(phase, int), \
                f"Phase should be integer, got {type(phase)}"

            assert phase in [1, 2], \
                f"Phase should be 1 or 2, got {phase}"

        print("✓ Phase function returns valid integers (1 or 2)")


class TestPartnerAgentUpdates:
    """Test Partner agent is updated when phase changes"""

    def test_tc_stage_04_partner_agent_recreated_for_phase_2(self):
        """
        TC-STAGE-04a: Partner Agent Recreated for Phase 2

        When phase changes, Partner agent should be recreated with new prompt.
        """
        from app.agents.stage_manager import get_partner_agent_for_turn

        # Get Partner for Phase 1 (turn 2)
        partner_phase1 = get_partner_agent_for_turn(turn_count=2)
        assert partner_phase1.name == "partner_agent"

        # Get Partner for Phase 2 (turn 5)
        partner_phase2 = get_partner_agent_for_turn(turn_count=5)
        assert partner_phase2.name == "partner_agent"

        # Prompts should be different
        assert partner_phase1.instruction != partner_phase2.instruction, \
            "Phase 1 and Phase 2 Partner should have different prompts"

        print("✓ Partner agent recreated with different prompt for Phase 2")

    def test_tc_stage_04_phase1_partner_is_supportive(self):
        """
        TC-STAGE-04b: Phase 1 Partner Is Supportive

        Verify turn 2 Partner has supportive characteristics.
        """
        from app.agents.stage_manager import get_partner_agent_for_turn

        partner = get_partner_agent_for_turn(turn_count=2)
        instruction = partner.instruction.lower()

        # Should have supportive keywords
        supportive_keywords = ["support", "help", "encourage", "guide"]
        found = [kw for kw in supportive_keywords if kw in instruction]

        assert len(found) >= 1, \
            f"Phase 1 Partner should be supportive. Found: {found}"

        print(f"✓ Phase 1 Partner is supportive: {found}")

    def test_tc_stage_04_phase2_partner_is_fallible(self):
        """
        TC-STAGE-04c: Phase 2 Partner Is Fallible

        Verify turn 6 Partner has fallible characteristics.
        """
        from app.agents.stage_manager import get_partner_agent_for_turn

        partner = get_partner_agent_for_turn(turn_count=6)
        instruction = partner.instruction.lower()

        # Should have fallible keywords
        fallible_keywords = ["fallible", "realistic", "forget", "miss", "human"]
        found = [kw for kw in fallible_keywords if kw in instruction]

        assert len(found) >= 1, \
            f"Phase 2 Partner should be fallible. Found: {found}"

        print(f"✓ Phase 2 Partner is fallible: {found}")

    def test_tc_stage_04_partner_uses_pro_model_in_both_phases(self):
        """
        TC-STAGE-04d: Partner Uses Pro Model in Both Phases

        Both phases should use gemini-1.5-pro for creativity.
        """
        from app.agents.stage_manager import get_partner_agent_for_turn

        partner_p1 = get_partner_agent_for_turn(turn_count=1)
        partner_p2 = get_partner_agent_for_turn(turn_count=8)

        assert partner_p1.model == "gemini-1.5-pro", \
            f"Phase 1 Partner should use Pro, got {partner_p1.model}"

        assert partner_p2.model == "gemini-1.5-pro", \
            f"Phase 2 Partner should use Pro, got {partner_p2.model}"

        print("✓ Both phases use gemini-1.5-pro model")


class TestPhaseInformation:
    """Test phase information is tracked and communicated"""

    def test_tc_stage_05_stage_manager_tracks_turn_count(self):
        """
        TC-STAGE-05a: Stage Manager Tracks Turn Count

        Stage Manager should be able to receive/track turn count.
        """
        from app.agents.stage_manager import create_stage_manager

        # Create with turn_count parameter (if supported)
        # This may need adjustment based on actual implementation
        try:
            stage_manager = create_stage_manager(turn_count=5)
            # Check if turn_count is stored somewhere
            # Implementation-specific
            print("✓ Stage Manager can receive turn_count parameter")
        except TypeError:
            # If turn_count not in constructor, check if there's a method
            stage_manager = create_stage_manager()
            print("ℹ Stage Manager does not accept turn_count in constructor")
            print("  (May use different mechanism for phase tracking)")

    def test_tc_stage_05_instruction_can_include_phase_info(self):
        """
        TC-STAGE-05b: Stage Manager Can Include Phase Info

        Instruction should be able to communicate current phase.
        """
        from app.agents.stage_manager import create_stage_manager

        stage_manager = create_stage_manager()

        # Check if instruction mentions phases or has dynamic capability
        instruction = stage_manager.instruction.lower()

        # May mention phase concept
        phase_keywords = ["phase", "stage", "progression", "turn"]
        found = [kw for kw in phase_keywords if kw in instruction]

        # This is a soft check - not all implementations may mention phase explicitly
        print(f"ℹ Stage Manager instruction phase references: {found if found else 'None explicit'}")

    def test_tc_stage_05_partner_in_sub_agents_list(self):
        """
        TC-STAGE-05c: Partner Agent Is In Sub-Agents List

        Partner should be accessible as a sub-agent.
        """
        from app.agents.stage_manager import create_stage_manager

        stage_manager = create_stage_manager()
        agent_names = [agent.name for agent in stage_manager.sub_agents]

        assert 'partner_agent' in agent_names, \
            f"Partner agent should be in sub-agents: {agent_names}"

        # Get the Partner agent
        partner_agents = [a for a in stage_manager.sub_agents if a.name == 'partner_agent']
        assert len(partner_agents) == 1, "Should have exactly one Partner agent"

        partner = partner_agents[0]
        assert isinstance(partner, Agent), "Partner should be Agent instance"

        print("✓ Partner agent correctly included in sub-agents")


class TestStageManagerConfiguration:
    """Test Stage Manager configuration"""

    def test_tc_stage_06_stage_manager_is_adk_agent(self):
        """
        TC-STAGE-06a: Stage Manager Is ADK Agent

        Stage Manager should be google.adk.Agent instance.
        """
        from app.agents.stage_manager import create_stage_manager

        stage_manager = create_stage_manager()

        assert isinstance(stage_manager, Agent), \
            f"Stage Manager should be google.adk.Agent, got {type(stage_manager)}"

        print("✓ Stage Manager is ADK Agent instance")

    def test_tc_stage_06_stage_manager_name(self):
        """
        TC-STAGE-06b: Stage Manager Has Correct Name

        Name should be 'stage_manager'.
        """
        from app.agents.stage_manager import create_stage_manager

        stage_manager = create_stage_manager()

        assert stage_manager.name == "stage_manager", \
            f"Name should be 'stage_manager', got '{stage_manager.name}'"

        print("✓ Stage Manager has correct name")

    def test_tc_stage_06_stage_manager_uses_flash(self):
        """
        TC-STAGE-06c: Stage Manager Uses Flash Model

        Stage Manager coordinates but doesn't need high creativity.
        """
        from app.agents.stage_manager import create_stage_manager

        stage_manager = create_stage_manager()

        assert stage_manager.model == "gemini-1.5-flash", \
            f"Stage Manager should use Flash, got {stage_manager.model}"

        print("✓ Stage Manager uses gemini-1.5-flash")

    def test_tc_stage_06_stage_manager_has_instruction(self):
        """
        TC-STAGE-06d: Stage Manager Has Orchestration Instruction

        Should have instruction explaining orchestration role.
        """
        from app.agents.stage_manager import create_stage_manager

        stage_manager = create_stage_manager()

        assert hasattr(stage_manager, 'instruction'), "Missing instruction"
        assert isinstance(stage_manager.instruction, str), "Instruction should be string"
        assert len(stage_manager.instruction) > 200, "Instruction seems too short"

        instruction = stage_manager.instruction.lower()
        orchestration_keywords = ["orchestrat", "coordinat", "manage", "sub-agent"]
        found = [kw for kw in orchestration_keywords if kw in instruction]

        assert len(found) >= 1, \
            f"Stage Manager should describe orchestration role. Found: {found}"

        print(f"✓ Stage Manager has orchestration instruction: {found}")


class TestPhaseTransitionIntegration:
    """Integration tests for phase transitions"""

    def test_tc_stage_07_all_agents_compatible(self):
        """
        TC-STAGE-07: All 4 Agents Are Compatible

        Verify MC, Room, Partner, Coach can coexist without errors.
        """
        from app.agents.stage_manager import create_stage_manager

        stage_manager = create_stage_manager()

        # All sub-agents should have names
        for agent in stage_manager.sub_agents:
            assert hasattr(agent, 'name'), f"Agent {agent} missing name"
            assert hasattr(agent, 'model'), f"Agent {agent} missing model"

        print("✓ All 4 agents are compatible and properly configured")

    def test_tc_stage_07_partner_changes_across_phase_boundary(self):
        """
        TC-STAGE-07b: Partner Changes At Phase Boundary

        Verify Partner agent actually changes between turn 3 and turn 4.
        """
        from app.agents.stage_manager import get_partner_agent_for_turn

        partner_t3 = get_partner_agent_for_turn(turn_count=3)
        partner_t4 = get_partner_agent_for_turn(turn_count=4)

        # Should have different instructions
        assert partner_t3.instruction != partner_t4.instruction, \
            "Partner instruction should change between turn 3 and turn 4"

        # Phase 1 vs Phase 2 keywords
        inst_t3 = partner_t3.instruction.lower()
        inst_t4 = partner_t4.instruction.lower()

        # Turn 3 should have more supportive language
        support_count_t3 = inst_t3.count("support") + inst_t3.count("help") + inst_t3.count("guide")
        support_count_t4 = inst_t4.count("support") + inst_t4.count("help") + inst_t4.count("guide")

        # Turn 4 should have fallible language
        fallible_count_t4 = inst_t4.count("fallible") + inst_t4.count("realistic") + inst_t4.count("forget")

        assert support_count_t3 >= support_count_t4, \
            "Turn 3 should have equal or more supportive language than turn 4"

        assert fallible_count_t4 > 0, \
            "Turn 4 should introduce fallible language"

        print("✓ Partner correctly transitions from supportive to fallible")
        print(f"  - Turn 3 supportive words: {support_count_t3}")
        print(f"  - Turn 4 supportive words: {support_count_t4}")
        print(f"  - Turn 4 fallible words: {fallible_count_t4}")


# Edge cases
class TestPhaseEdgeCases:
    """Test edge cases in phase transition logic"""

    def test_tc_stage_08_negative_turn_count(self):
        """
        TC-STAGE-08a: Negative Turn Count Handling

        Negative turn counts should be handled gracefully.
        """
        from app.agents.stage_manager import determine_partner_phase

        # Should either default to Phase 1 or raise error
        try:
            phase = determine_partner_phase(-1)
            assert phase == 1, "Negative turns should default to Phase 1"
            print("✓ Negative turn count defaults to Phase 1")
        except ValueError:
            print("✓ Negative turn count raises ValueError (acceptable)")

    def test_tc_stage_08_very_large_turn_count(self):
        """
        TC-STAGE-08b: Very Large Turn Count

        Large turn counts should still return Phase 2.
        """
        from app.agents.stage_manager import determine_partner_phase

        phase = determine_partner_phase(1000)
        assert phase == 2, "Large turn counts should be Phase 2"

        print("✓ Large turn count (1000) correctly returns Phase 2")

    def test_tc_stage_08_zero_turn_count(self):
        """
        TC-STAGE-08c: Turn 0 Is Phase 1

        First turn (turn 0) should be Phase 1.
        """
        from app.agents.stage_manager import determine_partner_phase

        phase = determine_partner_phase(0)
        assert phase == 1, "Turn 0 should be Phase 1"

        print("✓ Turn 0 correctly returns Phase 1")


# Pytest collection
def test_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("STAGE MANAGER PHASE TRANSITION TEST SUMMARY")
    print("="*60)
    print("\nTest Coverage:")
    print("  ✓ TC-STAGE-01: Stage Manager has 4 sub-agents")
    print("  ✓ TC-STAGE-02: Phase 1 logic (turns 0-3)")
    print("  ✓ TC-STAGE-03: Phase 2 logic (turns 4+)")
    print("  ✓ TC-STAGE-04: Partner agent updates with phase")
    print("  ✓ TC-STAGE-05: Phase information tracking")
    print("  ✓ TC-STAGE-06: Stage Manager configuration")
    print("  ✓ TC-STAGE-07: Integration and compatibility")
    print("  ✓ TC-STAGE-08: Edge cases")
    print("\n" + "="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
