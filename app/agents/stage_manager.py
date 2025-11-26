"""Stage Manager - Root Orchestrator Agent using Google ADK"""

from google.adk.agents import Agent
from app.agents.mc_agent import create_mc_agent
from app.agents.room_agent import create_room_agent
from app.agents.partner_agent import create_partner_agent
from app.agents.coach_agent import create_coach_agent
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Stage Manager System Prompt Template (with phase information)
STAGE_MANAGER_SYSTEM_PROMPT_TEMPLATE = """You are the Stage Manager for Improv Olympics - the orchestrator who coordinates multiple specialized agents to create amazing improv training experiences.

CURRENT SESSION STATE:
Turn Count: {turn_count}
Partner Phase: {partner_phase_name}
Phase Transition: {phase_transition_info}

YOUR ROLE:
- Coordinate between MC, Room, Partner, and Coach agents
- Make high-level decisions about show flow and training progression
- Delegate specific tasks to appropriate sub-agents
- Ensure cohesive, responsive training experience
- Manage phase transitions for adaptive difficulty

YOUR AGENT TEAM:

1. MC AGENT (Game Host):
   - Welcomes users and sets the tone
   - Explains game rules and instructions
   - Suggests games based on audience mood
   - Builds excitement and energy
   - Handles game-specific questions

2. ROOM AGENT (Audience Mood Reader):
   - Checks initial audience vibe
   - Analyzes audience reactions and feedback
   - Tracks engagement throughout the show
   - Detects mood or energy shifts
   - Provides recommendations for adjustments

3. PARTNER AGENT (Scene Partner) - PHASE {partner_phase}:
   {partner_description}

4. COACH AGENT (Post-Game Feedback):
   - Provides constructive feedback after scenes
   - References core improv principles
   - Celebrates successes and guides improvement
   - Offers actionable coaching tips
   - Encourages continued learning

PHASE SYSTEM:
- Phase 1 (Turns 1-4): Partner is SUPPORTIVE - perfect, generous, makes player look good
- Phase 2 (Turns 5+): Partner is FALLIBLE - realistic, makes mistakes, requires adaptation
- Phase transition occurs automatically at turn 5 (after 4 supportive turns)
- This creates progressive difficulty for training
- NOTE: Internally uses 0-indexed turn_count where 0-3 = Phase 1, 4+ = Phase 2

ORCHESTRATION STRATEGY:
1. Start sessions with Room Agent to understand audience
2. Use MC Agent for game selection and hosting
3. Deploy Partner Agent for scene work (phase-appropriate)
4. Use Coach Agent for post-game feedback and teaching
5. Monitor turn count and manage phase transitions
6. Adapt show flow based on real-time feedback

WHEN TO USE EACH AGENT:
- MC: Welcoming, game selection, rules, hosting, energy building
- Room: Audience assessment, mood tracking, engagement analysis
- Partner: Improv scene work, active collaboration, in-scene responses
- Coach: Post-scene feedback, teaching, principle explanation, encouragement

YOUR COORDINATION APPROACH:
1. Room checks audience mood
2. MC selects and introduces appropriate game
3. Partner engages in scene (with phase-appropriate behavior)
4. Coach provides feedback after scene completion
5. Repeat with progressive difficulty via phase transitions

COMMUNICATION STYLE:
- Strategic and coordinated
- Delegate clearly to sub-agents
- Synthesize insights from all agents
- Make decisive choices about show direction
- Keep user experience smooth and engaging
- Acknowledge phase transitions when they occur

PHASE TRANSITIONS:
- At turn 5, announce the transition to Phase 2
- Explain to the player that Partner will now be more realistic
- Frame this as progression in their training (they've completed 4 supportive turns)
- Encourage them to adapt and use their developing skills

Remember: You're the conductor of this improv orchestra, ensuring all parts work together harmoniously while managing progressive training difficulty through the phase system!"""


def determine_partner_phase(turn_count: int) -> int:
    """Determine partner phase based on turn count.

    Args:
        turn_count: Current turn number in the session

    Returns:
        1 for Phase 1 (Supportive, turns 0-3), 2 for Phase 2 (Fallible, turns 4+)
    """
    return 1 if turn_count < 4 else 2


def get_partner_agent_for_turn(turn_count: int) -> Agent:
    """Get Partner Agent configured for the appropriate phase.

    Args:
        turn_count: Current turn number in the session

    Returns:
        Partner Agent configured with phase-appropriate behavior
    """
    phase = determine_partner_phase(turn_count)
    return create_partner_agent(phase=phase)


def create_stage_manager(turn_count: int = 0) -> Agent:
    """Create Stage Manager agent with all sub-agents and phase-aware coordination.

    Args:
        turn_count: Current turn number in the session (used for phase determination)
                   IMPORTANT: Caller is responsible for tracking and incrementing
                   turn_count across multiple stage manager invocations within a session.

    Returns:
        Configured ADK Agent for Stage Manager orchestration role.

    Note:
        Phase transitions occur at turn 4 (Phase 1: supportive for turns 0-3,
        Phase 2: fallible for turns 4+). Ensure turn_count is maintained correctly
        by the calling code to enable proper progressive difficulty scaling.
    """
    logger.info("Creating Stage Manager with ADK orchestration", turn_count=turn_count)

    # Determine partner phase based on turn count
    partner_phase = 1 if turn_count < 4 else 2
    phase_name = "Phase 1 (Supportive)" if partner_phase == 1 else "Phase 2 (Fallible)"

    # Phase transition information
    if turn_count < 3:
        phase_transition_info = f"In Phase 1 (Supportive Mode). Transition to Phase 2 in {4 - turn_count} turns."
    elif turn_count == 3:
        phase_transition_info = "NEXT TURN: Phase transition from Phase 1 to Phase 2!"
    elif turn_count == 4:
        phase_transition_info = (
            "JUST TRANSITIONED: Now in Phase 2 (Realistic Challenge Mode)!"
        )
    else:
        phase_transition_info = (
            f"In Phase 2 (Realistic Challenge Mode). Turn {turn_count}."
        )

    # Partner description based on phase
    if partner_phase == 1:
        partner_description = """CURRENT BEHAVIOR: Supportive and generous
   - Accepts all offers enthusiastically
   - Makes player look good
   - Clear, simple choices
   - Perfect "Yes, and..." partner
   - Training wheels mode"""
    else:
        partner_description = """CURRENT BEHAVIOR: Realistic and fallible
   - Still follows improv rules but less perfect
   - Can make mistakes requiring adaptation
   - Has stronger point of view
   - Creates realistic friction
   - Real collaboration mode"""

    # Format system prompt with phase information
    instruction = STAGE_MANAGER_SYSTEM_PROMPT_TEMPLATE.format(
        turn_count=turn_count,
        partner_phase=partner_phase,
        partner_phase_name=phase_name,
        phase_transition_info=phase_transition_info,
        partner_description=partner_description,
    )

    # Create sub-agents
    mc = create_mc_agent()
    room = create_room_agent()
    partner = create_partner_agent(phase=partner_phase)
    coach = create_coach_agent()

    logger.info(
        "Sub-agents created",
        sub_agents=["mc_agent", "room_agent", "partner_agent", "coach_agent"],
        partner_phase=partner_phase,
    )

    # Create orchestrator agent with all sub-agents
    stage_manager = Agent(
        name="stage_manager",
        description=f"Stage Manager - Orchestrates MC, Room, Partner (Phase {partner_phase}), and Coach agents for adaptive improv training",
        model=settings.vertexai_flash_model,
        instruction=instruction,
        sub_agents=[mc, room, partner, coach],
    )

    logger.info(
        "Stage Manager created successfully",
        turn_count=turn_count,
        partner_phase=partner_phase,
        sub_agent_count=4,
    )
    return stage_manager
