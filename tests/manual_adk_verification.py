"""Manual ADK Verification Tests - Week 5 Rewrite Validation"""
import asyncio
import inspect
import time


async def test_a_import_and_create_agents():
    """Test A: Import and Create Agents"""
    print("\n=== Test A: Import and Create Agents ===")

    from app.agents import create_mc_agent, create_room_agent, create_stage_manager
    from google.adk.agents import Agent

    mc = create_mc_agent()
    room = create_room_agent()
    stage = create_stage_manager()

    # Verify all are Agent instances
    assert isinstance(mc, Agent), f"MC Agent is {type(mc)}, not google.adk.Agent"
    assert isinstance(room, Agent), f"Room Agent is {type(room)}, not google.adk.Agent"
    assert isinstance(stage, Agent), f"Stage Manager is {type(stage)}, not google.adk.Agent"

    print("✅ All agents are google.adk.Agent instances")
    print(f"   - MC Agent: {type(mc).__name__}")
    print(f"   - Room Agent: {type(room).__name__}")
    print(f"   - Stage Manager: {type(stage).__name__}")

    return True


async def test_b_verify_tools_are_functions():
    """Test B: Verify Tools Are Functions"""
    print("\n=== Test B: Verify Tools Are Functions ===")

    from app.tools import game_database_tools

    # Check if tools are async functions
    assert inspect.iscoroutinefunction(game_database_tools.get_all_games)
    assert inspect.iscoroutinefunction(game_database_tools.get_game_by_id)
    assert inspect.iscoroutinefunction(game_database_tools.search_games)

    print("✅ All game database tools are async functions")
    print(f"   - get_all_games: {inspect.iscoroutinefunction(game_database_tools.get_all_games)}")
    print(f"   - get_game_by_id: {inspect.iscoroutinefunction(game_database_tools.get_game_by_id)}")
    print(f"   - search_games: {inspect.iscoroutinefunction(game_database_tools.search_games)}")

    return True


async def test_c_verify_sub_agent_orchestration():
    """Test C: Verify Sub-Agent Orchestration"""
    print("\n=== Test C: Verify Sub-Agent Orchestration ===")

    from app.agents import create_stage_manager

    stage = create_stage_manager()

    assert len(stage.sub_agents) == 4, f"Expected 4 sub-agents, got {len(stage.sub_agents)}"
    sub_agent_names = [agent.name for agent in stage.sub_agents]
    assert "mc_agent" in sub_agent_names, "mc_agent not found in sub-agents"
    assert "room_agent" in sub_agent_names, "room_agent not found in sub-agents"
    assert "partner_agent" in sub_agent_names, "partner_agent not found in sub-agents"
    assert "coach_agent" in sub_agent_names, "coach_agent not found in sub-agents"

    print("✅ Stage Manager has correct sub-agent orchestration")
    print(f"   - Sub-agent count: {len(stage.sub_agents)}")
    print(f"   - Sub-agents: {', '.join(sub_agent_names)}")

    return True


async def test_d_verify_no_custom_wrappers():
    """Test D: Verify No Custom Wrappers"""
    print("\n=== Test D: Verify No Custom Wrappers ===")

    import app.agents.mc_agent as mc_module
    import app.agents.room_agent as room_module

    source_mc = inspect.getsource(mc_module)
    source_room = inspect.getsource(room_module)

    # Check that BaseImprovAgent is NOT in source
    assert "BaseImprovAgent" not in source_mc, "MC Agent still uses BaseImprovAgent"
    assert "BaseImprovAgent" not in source_room, "Room Agent still uses BaseImprovAgent"

    # Check that google.adk.agents imports ARE present
    assert "from google.adk.agents import Agent" in source_mc, "MC Agent doesn't import from google.adk.agents"
    assert "from google.adk.agents import Agent" in source_room, "Room Agent doesn't import from google.adk.agents"

    print("✅ No custom wrappers detected - using pure ADK")
    print("   - No BaseImprovAgent imports found")
    print("   - All agents import from google.adk")

    return True


async def test_e_tool_function_execution():
    """Test E: Tool Function Execution"""
    print("\n=== Test E: Tool Function Execution ===")

    from app.tools import game_database_tools

    # Test get_all_games
    games = await game_database_tools.get_all_games()
    assert isinstance(games, list), f"get_all_games returned {type(games)}, not list"
    assert len(games) > 0, "get_all_games returned empty list"

    # Test get_game_by_id
    game = await game_database_tools.get_game_by_id("freeze_tag")
    assert game is not None, "get_game_by_id returned None"
    assert "name" in game, "Game dict missing 'name' field"
    assert game["name"] == "Freeze Tag", f"Expected 'Freeze Tag', got {game['name']}"

    # Test search_games
    high_energy_games = await game_database_tools.search_games(energy_level="high")
    assert isinstance(high_energy_games, list), f"search_games returned {type(high_energy_games)}, not list"

    print("✅ All tool functions execute successfully")
    print(f"   - Total games: {len(games)}")
    print(f"   - Freeze Tag found: {game['name']}")
    print(f"   - High energy games: {len(high_energy_games)}")

    return True


async def test_f_agent_configuration_validation():
    """Test F: Agent Configuration Validation"""
    print("\n=== Test F: Agent Configuration Validation ===")

    from app.agents import create_mc_agent, create_room_agent

    mc = create_mc_agent()

    assert mc.name == "mc_agent", f"MC name is {mc.name}, not mc_agent"
    assert mc.model == "gemini-1.5-flash", f"MC model is {mc.model}, not gemini-1.5-flash"
    assert len(mc.tools) == 3, f"MC has {len(mc.tools)} tools, expected 3"
    assert mc.instruction != "", "MC has empty instruction"

    room = create_room_agent()

    assert room.name == "room_agent", f"Room name is {room.name}, not room_agent"
    assert room.model == "gemini-1.5-flash", f"Room model is {room.model}, not gemini-1.5-flash"
    assert len(room.tools) == 6, f"Room has {len(room.tools)} tools, expected 6"
    assert room.instruction != "", "Room has empty instruction"

    print("✅ All agent configurations are valid")
    print(f"   - MC Agent: {mc.name}, {mc.model}, {len(mc.tools)} tools")
    print(f"   - Room Agent: {room.name}, {room.model}, {len(room.tools)} tools")

    return True


async def test_i_agent_creation_performance():
    """Test I: Agent Creation Performance"""
    print("\n=== Test I: Agent Creation Performance ===")

    from app.agents import create_mc_agent, create_room_agent, create_stage_manager

    start = time.time()
    mc = create_mc_agent()
    room = create_room_agent()
    stage = create_stage_manager()
    elapsed = time.time() - start

    print(f"✅ Agent creation time: {elapsed:.3f}s")

    if elapsed < 1.0:
        print("   - Performance: EXCELLENT (< 1s)")
    elif elapsed < 2.0:
        print("   - Performance: GOOD (< 2s)")
    else:
        print("   - Performance: ACCEPTABLE")

    return True


async def main():
    """Run all manual verification tests"""
    print("\n" + "="*60)
    print("MANUAL ADK VERIFICATION TESTS - WEEK 5 REWRITE")
    print("="*60)

    tests = [
        test_a_import_and_create_agents,
        test_b_verify_tools_are_functions,
        test_c_verify_sub_agent_orchestration,
        test_d_verify_no_custom_wrappers,
        test_e_tool_function_execution,
        test_f_agent_configuration_validation,
        test_i_agent_creation_performance,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED: {e}")

    print("\n" + "="*60)
    print(f"MANUAL TESTS COMPLETED: {passed} passed, {failed} failed")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
