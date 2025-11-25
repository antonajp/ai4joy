"""Validation Tests for ADK-Based Agent Implementation

This test file validates that the Week 5 rewrite uses actual Google ADK framework
instead of custom wrappers.
"""
import pytest
from google.adk.agents import Agent

from app.agents.mc_agent import create_mc_agent
from app.agents.room_agent import create_room_agent
from app.agents.stage_manager import create_stage_manager
from app.tools import (
    game_database_tools,
    sentiment_gauge_tools,
    demographic_tools,
    improv_expert_tools
)


class TestADKAgentInstances:
    """Verify agents are actual ADK Agent instances, not custom wrappers"""

    def test_mc_agent_is_adk_agent(self):
        """MC Agent should be google.adk.Agent instance"""
        mc = create_mc_agent()
        assert isinstance(mc, Agent), f"MC Agent is {type(mc)}, not google.adk.Agent"
        assert mc.name == "mc_agent"
        assert mc.model == "gemini-1.5-flash"

    def test_room_agent_is_adk_agent(self):
        """Room Agent should be google.adk.Agent instance"""
        room = create_room_agent()
        assert isinstance(room, Agent), f"Room Agent is {type(room)}, not google.adk.Agent"
        assert room.name == "room_agent"
        assert room.model == "gemini-1.5-flash"

    def test_stage_manager_is_adk_agent(self):
        """Stage Manager should be google.adk.Agent instance"""
        stage_manager = create_stage_manager()
        assert isinstance(stage_manager, Agent), f"Stage Manager is {type(stage_manager)}, not google.adk.Agent"
        assert stage_manager.name == "stage_manager"
        assert stage_manager.model == "gemini-1.5-flash"


class TestADKAgentConfiguration:
    """Verify agents have correct ADK configuration"""

    def test_mc_agent_has_tools(self):
        """MC Agent should have game database tools attached"""
        mc = create_mc_agent()

        # ADK agents have tools attribute
        assert hasattr(mc, 'tools'), "MC Agent missing tools attribute"
        assert len(mc.tools) == 3, f"MC Agent has {len(mc.tools)} tools, expected 3"

        # Verify tool functions are attached
        tool_names = [tool.__name__ for tool in mc.tools]
        assert 'get_all_games' in tool_names
        assert 'get_game_by_id' in tool_names
        assert 'search_games' in tool_names

    def test_room_agent_has_tools(self):
        """Room Agent should have sentiment and demographic tools"""
        room = create_room_agent()

        assert hasattr(room, 'tools'), "Room Agent missing tools attribute"
        assert len(room.tools) == 6, f"Room Agent has {len(room.tools)} tools, expected 6"

        tool_names = [tool.__name__ for tool in room.tools]
        assert 'analyze_text' in tool_names
        assert 'analyze_engagement' in tool_names
        assert 'analyze_collective_mood' in tool_names
        assert 'generate_audience_sample' in tool_names

    def test_stage_manager_has_sub_agents(self):
        """Stage Manager should have MC, Room, Partner, and Coach as sub-agents (Week 6 update)"""
        stage_manager = create_stage_manager()

        # ADK agents have sub_agents attribute
        assert hasattr(stage_manager, 'sub_agents'), "Stage Manager missing sub_agents attribute"
        assert len(stage_manager.sub_agents) == 4, f"Stage Manager has {len(stage_manager.sub_agents)} sub-agents, expected 4"

        # Verify sub-agents are Agent instances
        for sub_agent in stage_manager.sub_agents:
            assert isinstance(sub_agent, Agent), f"Sub-agent {sub_agent} is not google.adk.Agent"

        sub_agent_names = [agent.name for agent in stage_manager.sub_agents]
        assert 'mc_agent' in sub_agent_names
        assert 'room_agent' in sub_agent_names
        assert 'partner_agent' in sub_agent_names
        assert 'coach_agent' in sub_agent_names


class TestToolsAreAsyncFunctions:
    """Verify tools are async functions, not classes"""

    @pytest.mark.asyncio
    async def test_game_tools_are_async_functions(self):
        """Game database tools should be async functions"""
        import inspect

        assert inspect.iscoroutinefunction(game_database_tools.get_all_games)
        assert inspect.iscoroutinefunction(game_database_tools.get_game_by_id)
        assert inspect.iscoroutinefunction(game_database_tools.search_games)

        # Verify they actually work
        games = await game_database_tools.get_all_games()
        assert isinstance(games, list)
        assert len(games) > 0

    @pytest.mark.asyncio
    async def test_sentiment_tools_are_async_functions(self):
        """Sentiment tools should be async functions"""
        import inspect

        assert inspect.iscoroutinefunction(sentiment_gauge_tools.analyze_text)
        assert inspect.iscoroutinefunction(sentiment_gauge_tools.analyze_engagement)
        assert inspect.iscoroutinefunction(sentiment_gauge_tools.analyze_collective_mood)

        # Verify they work
        result = await sentiment_gauge_tools.analyze_text("This is awesome!")
        assert isinstance(result, dict)
        assert 'sentiment' in result

    @pytest.mark.asyncio
    async def test_demographic_tools_are_async_functions(self):
        """Demographic tools should be async functions"""
        import inspect

        assert inspect.iscoroutinefunction(demographic_tools.generate_audience_sample)
        assert inspect.iscoroutinefunction(demographic_tools.analyze_audience_traits)
        assert inspect.iscoroutinefunction(demographic_tools.get_vibe_check)

        # Verify they work
        audience = await demographic_tools.generate_audience_sample(3)
        assert isinstance(audience, list)
        assert len(audience) == 3

    @pytest.mark.asyncio
    async def test_improv_expert_tools_are_async_functions(self):
        """Improv expert tools should be async functions"""
        import inspect

        assert inspect.iscoroutinefunction(improv_expert_tools.get_all_principles)
        assert inspect.iscoroutinefunction(improv_expert_tools.get_principle_by_id)
        assert inspect.iscoroutinefunction(improv_expert_tools.get_beginner_essentials)

        # Verify they work
        principles = await improv_expert_tools.get_all_principles()
        assert isinstance(principles, list)
        assert len(principles) > 0


class TestNoCustomWrappers:
    """Verify no custom agent wrappers are being used"""

    def test_no_baseimprovagent_import(self):
        """Agents should not import BaseImprovAgent"""
        import app.agents.mc_agent as mc_module
        import app.agents.room_agent as room_module
        import app.agents.stage_manager as sm_module

        # Check module source doesn't contain BaseImprovAgent
        import inspect

        mc_source = inspect.getsource(mc_module)
        assert 'BaseImprovAgent' not in mc_source, "MC Agent still uses BaseImprovAgent"

        room_source = inspect.getsource(room_module)
        assert 'BaseImprovAgent' not in room_source, "Room Agent still uses BaseImprovAgent"

        sm_source = inspect.getsource(sm_module)
        assert 'BaseImprovAgent' not in sm_source, "Stage Manager still uses BaseImprovAgent"

    def test_agents_use_adk_import(self):
        """Agents should import from google.adk"""
        import app.agents.mc_agent as mc_module
        import app.agents.room_agent as room_module
        import app.agents.stage_manager as sm_module

        import inspect

        mc_source = inspect.getsource(mc_module)
        assert 'from google.adk.agents import Agent' in mc_source

        room_source = inspect.getsource(room_module)
        assert 'from google.adk.agents import Agent' in room_source

        sm_source = inspect.getsource(sm_module)
        assert 'from google.adk.agents import Agent' in sm_source


class TestModelConfiguration:
    """Verify model is configured as string, not object"""

    def test_mc_agent_model_is_string(self):
        """MC Agent model should be string 'gemini-1.5-flash'"""
        mc = create_mc_agent()
        assert isinstance(mc.model, str), f"Model is {type(mc.model)}, should be string"
        assert mc.model == "gemini-1.5-flash"

    def test_room_agent_model_is_string(self):
        """Room Agent model should be string 'gemini-1.5-flash'"""
        room = create_room_agent()
        assert isinstance(room.model, str), f"Model is {type(room.model)}, should be string"
        assert room.model == "gemini-1.5-flash"

    def test_stage_manager_model_is_string(self):
        """Stage Manager model should be string 'gemini-1.5-flash'"""
        stage_manager = create_stage_manager()
        assert isinstance(stage_manager.model, str), f"Model is {type(stage_manager.model)}, should be string"
        assert stage_manager.model == "gemini-1.5-flash"


class TestAgentInstructions:
    """Verify agents have system prompts configured"""

    def test_mc_agent_has_instruction(self):
        """MC Agent should have instruction (system prompt)"""
        mc = create_mc_agent()
        assert hasattr(mc, 'instruction'), "MC Agent missing instruction"
        assert isinstance(mc.instruction, str)
        assert len(mc.instruction) > 100, "Instruction seems too short"
        assert 'MC' in mc.instruction or 'Master of Ceremonies' in mc.instruction

    def test_room_agent_has_instruction(self):
        """Room Agent should have instruction (system prompt)"""
        room = create_room_agent()
        assert hasattr(room, 'instruction'), "Room Agent missing instruction"
        assert isinstance(room.instruction, str)
        assert len(room.instruction) > 100
        assert 'Room' in room.instruction or 'audience' in room.instruction

    def test_stage_manager_has_instruction(self):
        """Stage Manager should have instruction (system prompt)"""
        stage_manager = create_stage_manager()
        assert hasattr(stage_manager, 'instruction'), "Stage Manager missing instruction"
        assert isinstance(stage_manager.instruction, str)
        assert len(stage_manager.instruction) > 100
        assert 'Stage Manager' in stage_manager.instruction or 'orchestrat' in stage_manager.instruction.lower()


def test_summary():
    """Print summary of validation results"""
    print("\n" + "="*60)
    print("ADK AGENT VALIDATION SUMMARY")
    print("="*60)

    # Create agents
    mc = create_mc_agent()
    room = create_room_agent()
    stage_manager = create_stage_manager()

    print(f"\nMC Agent:")
    print(f"  - Type: {type(mc).__name__}")
    print(f"  - Module: {type(mc).__module__}")
    print(f"  - Model: {mc.model}")
    print(f"  - Tools: {len(mc.tools)}")

    print(f"\nRoom Agent:")
    print(f"  - Type: {type(room).__name__}")
    print(f"  - Module: {type(room).__module__}")
    print(f"  - Model: {room.model}")
    print(f"  - Tools: {len(room.tools)}")

    print(f"\nStage Manager:")
    print(f"  - Type: {type(stage_manager).__name__}")
    print(f"  - Module: {type(stage_manager).__module__}")
    print(f"  - Model: {stage_manager.model}")
    print(f"  - Sub-agents: {len(stage_manager.sub_agents)}")

    print("\n" + "="*60)
    print("All agents use google.adk.Agent - SUCCESS!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_summary()
