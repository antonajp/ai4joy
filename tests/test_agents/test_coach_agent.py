"""Coach Agent Tests - Week 6 Implementation

Tests for Coach Agent with improv expert tools for post-game feedback.

Test Coverage:
- TC-COACH-01: Agent creation and basic configuration
- TC-COACH-02: Tool attachment verification
- TC-COACH-03: System prompt characteristics
- TC-COACH-04: Tool invocation tests
"""

import pytest
from google.adk.agents import Agent
from app.config import get_settings

settings = get_settings()


class TestCoachAgentCreation:
    """Test Coach Agent instantiation and configuration"""

    def test_tc_coach_01_agent_creation(self):
        """
        TC-COACH-01: Coach Agent Creation

        Verify Coach agent is created correctly with proper configuration.

        Expected:
        - Agent is instance of google.adk.Agent
        - Model is configured flash model (faster for coaching)
        - Name is coach_agent
        - Has exactly 4 improv expert tools
        - Has valid instruction
        """
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()

        # Verify ADK Agent instance
        assert isinstance(coach, Agent), \
            f"Coach should be google.adk.Agent, got {type(coach)}"

        # Verify configuration
        assert coach.name == "coach_agent", \
            f"Name should be 'coach_agent', got '{coach.name}'"

        assert coach.model == settings.vertexai_flash_model, \
            f"Model should be '{settings.vertexai_flash_model}', got '{coach.model}'"

        # Verify has 4 tools
        assert len(coach.tools) == 4, \
            f"Coach should have 4 improv expert tools, got {len(coach.tools)}"

        # Verify has instruction
        assert hasattr(coach, 'instruction'), "Coach missing instruction attribute"
        assert isinstance(coach.instruction, str), "Instruction should be string"
        assert len(coach.instruction) > 200, "Instruction seems too short for coaching role"

        print("✓ Coach Agent created successfully")
        print(f"  - Name: {coach.name}")
        print(f"  - Model: {coach.model}")
        print(f"  - Tools: {len(coach.tools)}")
        print(f"  - Instruction length: {len(coach.instruction)} chars")


class TestCoachToolAttachment:
    """Test Coach Agent tool configuration"""

    def test_tc_coach_02_has_all_four_tools(self):
        """
        TC-COACH-02: Coach Has All 4 Improv Expert Tools

        Coach should have:
        1. get_all_principles()
        2. get_principle_by_id(id)
        3. get_beginner_essentials()
        4. search_principles_by_keyword(keyword)
        """
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()
        tool_names = [tool.__name__ for tool in coach.tools]

        # Check for all 4 required tools
        required_tools = [
            'get_all_principles',
            'get_principle_by_id',
            'get_beginner_essentials',
            'search_principles_by_keyword'
        ]

        for required_tool in required_tools:
            assert required_tool in tool_names, \
                f"Coach missing tool: {required_tool}. Has: {tool_names}"

        print("✓ Coach has all 4 improv expert tools")
        print(f"  - Tools: {tool_names}")

    def test_tc_coach_02_tools_from_correct_module(self):
        """
        TC-COACH-02b: Tools Are From Improv Expert Module

        All tools should be from app.tools.improv_expert_tools
        """
        from app.agents.coach_agent import create_coach_agent
        from app.tools import improv_expert_tools

        coach = create_coach_agent()

        for tool in coach.tools:
            # Check tool is from improv_expert_tools module
            assert tool.__module__ == improv_expert_tools.__name__, \
                f"Tool {tool.__name__} should be from improv_expert_tools module"

        print("✓ All tools from improv_expert_tools module")

    def test_tc_coach_02_no_duplicate_tools(self):
        """
        TC-COACH-02c: No Duplicate Tools

        Each tool should be attached exactly once.
        """
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()
        tool_names = [tool.__name__ for tool in coach.tools]

        # Check for duplicates
        assert len(tool_names) == len(set(tool_names)), \
            f"Coach has duplicate tools: {tool_names}"

        print("✓ No duplicate tools attached")


class TestCoachSystemPrompt:
    """Test Coach Agent system prompt characteristics"""

    def test_tc_coach_03_prompt_is_encouraging(self):
        """
        TC-COACH-03a: Coach Prompt is Encouraging

        Coach should be constructive, not critical.

        Expected Keywords:
        - coach, feedback, encourage, support, improve, growth
        - principle, improv, learning

        Avoid:
        - bad, wrong, failure, poor
        """
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()
        instruction = coach.instruction.lower()

        # Check for encouraging keywords
        encouraging_keywords = ["coach", "feedback", "encourage", "support", "improve", "growth"]
        found_encouraging = [kw for kw in encouraging_keywords if kw in instruction]

        assert len(found_encouraging) >= 3, \
            f"Coach prompt should be encouraging. Found: {found_encouraging}"

        # Should reference improv principles
        assert "principle" in instruction or "improv" in instruction, \
            "Coach should reference improv principles"

        # Should avoid overly critical language
        critical_keywords = ["bad", "wrong", "failure", "poor"]
        found_critical = [kw for kw in critical_keywords if kw in instruction]

        assert len(found_critical) <= 1, \
            f"Coach should avoid critical language. Found: {found_critical}"

        print("✓ Coach prompt is appropriately encouraging")
        print(f"  - Encouraging keywords: {found_encouraging}")
        print(f"  - Critical keywords (should be minimal): {found_critical}")

    def test_tc_coach_03_prompt_mentions_tools(self):
        """
        TC-COACH-03b: Prompt References Available Tools

        Coach should know it has access to improv principles database.
        """
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()
        instruction = coach.instruction.lower()

        # Should mention having access to principles/tools
        tool_awareness_keywords = ["principle", "database", "tool", "reference", "access"]
        found_awareness = [kw for kw in tool_awareness_keywords if kw in instruction]

        assert len(found_awareness) >= 2, \
            f"Coach should be aware of available tools. Found: {found_awareness}"

        print(f"✓ Coach prompt references available tools: {found_awareness}")

    def test_tc_coach_03_prompt_emphasizes_constructive_feedback(self):
        """
        TC-COACH-03c: Prompt Emphasizes Constructive Feedback

        Coach should provide actionable, specific feedback.
        """
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()
        instruction = coach.instruction.lower()

        # Check for constructive feedback emphasis
        constructive_keywords = ["constructive", "actionable", "specific", "helpful", "practical"]
        found_constructive = [kw for kw in constructive_keywords if kw in instruction]

        # At least some emphasis on constructive feedback
        assert len(found_constructive) >= 1, \
            "Coach should emphasize constructive feedback"

        print(f"✓ Coach emphasizes constructive feedback: {found_constructive}")


class TestCoachToolFunctionality:
    """Test Coach tools work correctly"""

    @pytest.mark.asyncio
    async def test_tc_coach_04_get_all_principles_works(self):
        """
        TC-COACH-04a: get_all_principles Tool Works

        Tool should return all 10 core improv principles.
        """
        from app.tools import improv_expert_tools

        principles = await improv_expert_tools.get_all_principles()

        assert isinstance(principles, list), "Should return list"
        assert len(principles) == 10, f"Should have 10 principles, got {len(principles)}"

        # Check structure of first principle
        first = principles[0]
        assert "id" in first, "Principle should have 'id' field"
        assert "name" in first, "Principle should have 'name' field"
        assert "description" in first, "Principle should have 'description' field"
        assert "importance" in first, "Principle should have 'importance' field"

        print("✓ get_all_principles() works correctly")
        print(f"  - Returned {len(principles)} principles")
        print(f"  - Example: {first['name']}")

    @pytest.mark.asyncio
    async def test_tc_coach_04_get_principle_by_id_works(self):
        """
        TC-COACH-04b: get_principle_by_id Tool Works

        Tool should return specific principle by ID.
        """
        from app.tools import improv_expert_tools

        # Test retrieving "yes_and" principle
        yes_and = await improv_expert_tools.get_principle_by_id("yes_and")

        assert isinstance(yes_and, dict), "Should return dict"
        assert yes_and["id"] == "yes_and", "Should return correct principle"
        assert yes_and["name"] == "Yes, And...", "Should have correct name"
        assert "examples" in yes_and, "Should have examples"
        assert "coaching_tips" in yes_and, "Should have coaching tips"

        print("✓ get_principle_by_id() works correctly")
        print(f"  - Retrieved: {yes_and['name']}")

    @pytest.mark.asyncio
    async def test_tc_coach_04_get_beginner_essentials_works(self):
        """
        TC-COACH-04c: get_beginner_essentials Tool Works

        Tool should return foundational and essential principles.
        """
        from app.tools import improv_expert_tools

        essentials = await improv_expert_tools.get_beginner_essentials()

        assert isinstance(essentials, list), "Should return list"
        assert len(essentials) >= 5, f"Should have at least 5 essentials, got {len(essentials)}"

        # All should be foundational or essential importance
        for principle in essentials:
            assert principle["importance"] in ["foundational", "essential"], \
                f"Principle {principle['name']} should be foundational/essential"

        print("✓ get_beginner_essentials() works correctly")
        print(f"  - Returned {len(essentials)} essential principles")

    @pytest.mark.asyncio
    async def test_tc_coach_04_search_principles_works(self):
        """
        TC-COACH-04d: search_principles_by_keyword Tool Works

        Tool should search principles by keyword.
        """
        from app.tools import improv_expert_tools

        # Search for "listen"
        results = await improv_expert_tools.search_principles_by_keyword("listen")

        assert isinstance(results, list), "Should return list"
        assert len(results) >= 1, "Should find at least 1 principle about listening"

        # Check that results contain the keyword
        for principle in results:
            text = (principle["name"] + " " + principle["description"]).lower()
            assert "listen" in text, f"Result should contain 'listen': {principle['name']}"

        print("✓ search_principles_by_keyword() works correctly")
        print(f"  - Found {len(results)} principles for 'listen'")

    @pytest.mark.asyncio
    async def test_tc_coach_04_tools_return_consistent_structure(self):
        """
        TC-COACH-04e: All Tools Return Consistent Principle Structure

        All principles should have the same fields.
        """
        from app.tools import improv_expert_tools

        all_principles = await improv_expert_tools.get_all_principles()

        required_fields = ["id", "name", "description", "importance", "examples", "common_mistakes", "coaching_tips"]

        for principle in all_principles:
            for field in required_fields:
                assert field in principle, \
                    f"Principle {principle.get('name', '?')} missing field: {field}"

        print("✓ All principles have consistent structure")
        print(f"  - Required fields: {required_fields}")


class TestCoachConfiguration:
    """Test Coach Agent configuration details"""

    def test_tc_coach_05_uses_flash_model(self):
        """
        TC-COACH-05a: Coach Uses Gemini Flash Model

        Coach should use Flash for speed (coaching is less creative-intensive).
        """
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()

        assert coach.model == settings.vertexai_flash_model, \
            f"Coach should use {settings.vertexai_flash_model} for speed, got {coach.model}"

        print("✓ Coach correctly uses Gemini Flash model")

    def test_tc_coach_05_has_description(self):
        """
        TC-COACH-05b: Coach Has Clear Description

        Description helps Stage Manager understand Coach's role.
        """
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()

        assert hasattr(coach, 'description'), "Coach should have description"
        assert isinstance(coach.description, str), "Description should be string"
        assert len(coach.description) > 20, "Description should be meaningful"

        description_lower = coach.description.lower()
        assert "coach" in description_lower or "feedback" in description_lower, \
            "Description should mention coaching/feedback"

        print(f"✓ Coach has clear description: {coach.description[:50]}...")


class TestCoachPromptQuality:
    """Test prompt quality and role definition"""

    def test_tc_coach_06_prompt_defines_coaching_role(self):
        """Coach prompt should clearly define the coaching role"""
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()
        instruction = coach.instruction.lower()

        # Should define role
        role_keywords = ["you are", "your role", "coach", "provide feedback"]
        has_role = any(kw in instruction for kw in role_keywords)

        assert has_role, "Coach prompt should define coaching role"

        print("✓ Coach prompt defines coaching role")

    def test_tc_coach_06_prompt_emphasizes_pedagogy(self):
        """Coach should use pedagogical approach"""
        from app.agents.coach_agent import create_coach_agent

        coach = create_coach_agent()
        instruction = coach.instruction.lower()

        # Pedagogical keywords
        pedagogy_keywords = ["learn", "teach", "develop", "grow", "improve", "practice"]
        found_pedagogy = [kw for kw in pedagogy_keywords if kw in instruction]

        assert len(found_pedagogy) >= 2, \
            f"Coach should emphasize learning/development: {found_pedagogy}"

        print(f"✓ Coach emphasizes pedagogy: {found_pedagogy}")


# Integration test
class TestCoachIntegration:
    """Integration tests for Coach agent"""

    def test_tc_coach_07_agent_and_tools_compatible(self):
        """
        TC-COACH-07: Coach Agent and Tools Are Compatible

        Verify agent can be created with tools attached without errors.
        """
        from app.agents.coach_agent import create_coach_agent

        # Should create without errors
        coach = create_coach_agent()

        # Verify tools are callable
        for tool in coach.tools:
            assert callable(tool), f"Tool {tool.__name__} should be callable"

        print("✓ Coach agent and tools are compatible")
        print(f"  - All {len(coach.tools)} tools are callable")


# Pytest collection
def test_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("COACH AGENT TEST SUMMARY")
    print("="*60)
    print("\nTest Coverage:")
    print("  ✓ TC-COACH-01: Agent creation and configuration")
    print("  ✓ TC-COACH-02: Tool attachment verification")
    print("  ✓ TC-COACH-03: System prompt characteristics")
    print("  ✓ TC-COACH-04: Tool invocation tests")
    print("  ✓ TC-COACH-05: Configuration details")
    print("  ✓ TC-COACH-06: Prompt quality checks")
    print("  ✓ TC-COACH-07: Integration compatibility")
    print("\n" + "="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
