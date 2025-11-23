# The Problem: The "Atrophy of Presence"

After years of remote work, asynchronous communication, and "cameras off" meetings, the global workforce is facing a hidden crisis: Social Atrophy.
* **The Shift:** As professionals return to offices or hybrid models, they are discovering that the "muscle memory" for real-time, high-stakes collaboration has weakened.
* **The Pain Point:** Without the ability to "mute" or edit a Slack message, employees report higher anxiety in face-to-face negotiations, brainstorming sessions, and conflict resolution.
* **The Gap:** Companies are investing billions in "Return to Office" logistics (desks, policies) but zero in "Social Re-Onboarding." We are asking people to run a marathon after years on the couch, without a gym.

There is currently no scalable way to let digital-native professionals "practice" social courage and empathy in a safe, low-stakes digital environment before they face high-stakes real-world conflicts.

# The Solution

Improv Olympics is an AI-powered "Social Gym." It uses a Multi-Agent System to simulate the friction, ambiguity, and immediacy of in-person collaboration.

By simulating the "Ritual of Uncertainty" found in improv theatre, we provide a private, judgment-free simulator where professionals can rebuild their conversational stamina and adaptive listening skills before stepping back into the boardroom.

New pilots spend hundreds of hours in flight simulators not because they prefer them to real planes, but because crashing in a simulator is free. Improv Olympics is a conversational flight simulator for social interactions, meeting digital-native adults where they are (screens/chat) to teach them the skills they need to be emotionally resilient.

By utilizing a multi-agent system, we create a "safe simulation" where students can practice:
* **Adaptive Resilience:** Normalizing the "glitch" of social awkwardness through the "Yes-And" framework.
* **Empathy Building:** Collaborating with diverse agent personas to build shared narratives.
* **Active Listening:** Moving beyond "listening to respond" to "listening to understand".

# Why Agents?

Traditional software is deterministic. Human conversation—and improv—is non-deterministic. LLMs are non-deterministic. Agents can handle infinite variability. This unpredictability is a feature, not a bug. It forces the student to actually listen and adapt, rather than memorize patterns.

To simulate the pressure of a boardroom or a pitch meeting, we need Agentic Chaos, but controlled chaos:
* **The Audience ("The Room"):** A single aggregator agent that simulates collective sentiment. In real life, you don't process 5 individual voices at once; you process "The Room." This agent forces the user to read the room's temperature (tense, bored, or engaged) while speaking.
* **The "Yes-And" Partner:** An agent designed to model Psychological Safety—validating the user’s ideas to build confidence before introducing "Fallibility Protocols" (unexpected mistakes) that force the user to lead.

# Agent Architecture: The "Vibe Check" Pattern

The system utilizes a Central Orchestrator (Hub-and-Spoke) pattern to manage the complex state of a theatrical scene. We utilize a simplified loop to reduce API calls and prevent the "buggy chatroom" feel of multiple agents interrupting one another.

## 1. The Stage Manager (Root Agent)
* **Role:** The "Operating System" of the show.
* **Responsibility:** Manages the `SessionState` (current game, emotional temperature, turn history). It does not "act" but routes traffic—deciding when to poll the audience, when to cue the partner, and when to end the scene.
* **Model:** Code / Logic (State Machine).

## 2. The Cast (Sub-Agents)

### The MC (Game Starter)
* **Role:** High-energy host.
* **Model:** `gemini-1.5-flash`
* **Task:** "Vibes" with the audience, selects the game from the `GameDatabase` tool, and explains the constraints (e.g., "World's Worst Advice").

### The Audience: "The Room" (Single-Agent Aggregator)
* **Role:** The Vibe Check.
* **Model:** `gemini-1.5-flash` (Single Agent).
* **The Logic:** Instead of 5 independent agents running in parallel (which causes sync issues and high latency), this single agent simulates the collective consciousness of the room.
* **Task:** It reads the input and decides the "Room Temp" (e.g., Tense, Bored, With You). It generally stays silent but will occasionally "Spotlight" one specific reaction from a persona list (e.g., "The Heckler in the back coughs loudly") if the scene drags.
* **Efficiency:** This reduces API calls from ~7 per turn to just 3 (MC, Partner, Audience).

### The Dynamic Scene Partner
* **Role:** The Dynamic Scaffolding & "Yes-And" Expert.
* **Model:** `gemini-1.5-pro` (Complex reasoning).
* **Task:** To guide the user through the "Zone of Proximal Development" by dynamically adjusting its competence level. It operates in two distinct modes based on the session state:
    * **Phase 1: The Anchor (Hyper-Competence).** In the early game, the agent generates scene content. Uses a high temperature (0.9+) to maximize creativity and wordplay. It is instructed to never block the user's offer, but to heighten it. This agent is the "perfect castmate." It never rejects an idea.
    * **Phase 2: The Stumble (Instructional Fading).** As the scene progresses, this agent initiates "Strategic Fallibility." It intentionally lowers its status (e.g., feigning confusion, losing an imaginary object, or expressing fear) to force the student to take the lead.

## 3. The Coach (Post-Game Analysis)
* **Role:** The empathetic teacher.
* **Task:** Runs after the scene concludes. It analyzes the full context window to identify moments that align to principles identified in an `ImprovExpertDatabase` tool, framing feedback in a supportive, "low-stakes" manner.

# The Execution Loop (The Simplified "Ritual")

Since improv is cyclical, we use a custom Run Loop in the Root Agent.

**1. Initialization**
* **User Config:** Student sets Location (e.g., "Mars Colony Breakroom").
* **Audience Config:** System generates a list of 5 archetypes (e.g., "Grumpy New Yorker," "Giggling Teen") and feeds them to "The Room" agent as context, not as active agents.
* **State Set:** System initializes `current_phase = PHASE_1_SUPPORT`.

**2. The Warm-Up (MC Phase)**
* **MC Agent Invoked:** "Welcome to the stage! I need a relationship for these two actors."
* **Selection:** The MC picks the most actionable suggestion based on the location.

**3. The Scene (The Core Loop)**
This loop repeats for N turns (e.g., 10-15 turns).

* **Step A: Student Input**
    * Student speaks/types.
    * **Metric Capture:** System logs latency and sentiment.

* **Step B: The "Director" Check (Phase Logic)**
    * **Root Agent Logic:** Before calling the Partner agent, the system evaluates the state:
        * Condition: `IF Turn_Count > 4 AND Student_Sentiment is Stable...`
        * Action: Switch `current_phase` to `PHASE_2_FALLIBLE`.
        * Context Injection: The system appends the "Status Shift / Flop" instruction to the Partner's prompt.

* **Step C: Partner Generation**
    * Dynamic Scene Partner reads Student Input + `current_phase` instruction.
        * **If Phase 1:** It validates the user perfectly. "Yes! The blue wire!"
        * **If Phase 2:** It introduces a "Soft Fail." "Wait... I cut the blue wire, but the timer sped up! What do we do?!" (Forces Student to lead).

* **Step D: The Vibe Check (Audience Reaction)**
    * "The Room" agent analyzes the exchange.
    * **Logic:** Does the sentiment necessitate an interruption?
        * If "With You": Remain silent or output gentle background noise `[laughter]`.
        * If "Bored/Confused": Spotlight one archetype. `[The Grumpy New Yorker yells: "Get on with it!"]`
    * **Phase 2 Nuance:** If the Partner "flops," The Room is instructed to wait for the Student's recovery. If the Student saves the scene, The Room triggers a "High Cheer."

* **Step E: Loop Decision**
    * MC Agent monitors for a "Natural Ending" or Time Limit.

**4. The Post-Mortem (Coach Phase)**
* Coach Agent reads the full Session History to identify the top 5 core truths of key moments.
* **Pedagogical Analysis:**
    * Identifies the Transition Point: "I noticed around Turn 5, your Partner panicked."
    * Scores the Recovery: "You didn't freeze. You 'Yes-Anded' the mistake. That is advanced resilience."

# Tools & Tech Stack

* **Framework:** Google Agent Development Kit (ADK)
* **Models:** Gemini 1.5 Pro (Creative reasoning), Gemini 1.5 Flash (Orchestration & The Room).

## Custom Tools:
* **GameDatabase:** Retrieval tool for rules (Short Form vs. Long Form).
* **DemographicGenerator:** Generates lists of archetypes for "The Room" agent to reference.
* **SentimentGauge:** Measures the "temperature" of the conversation.
* **ImprovExpertDatabase:** Retrieval tool for expert improv behaviors.

# Ethical Design

**Target Population:** Hybrid teams, managers transitioning back to in-person leadership, and remote workers battling social isolation.

We recognize the risk of AI replacing human connection. To mitigate this, Improv Olympics is designed with a "Graduation Protocol." Unlike chatbots designed to maximize screen time, Improv Olympics utilizes **Instructional Fading**. As a student masters specific social mechanics, the system slowly removes its support, assigning users Real-World Missions to ensure skills transfer from the screen to the office.

# Stretch Goal: Verbal/Real-Time (Multimodal)

To move from chat to verbal interaction, we will need to shift the architecture from a standard REST API loop to a WebSocket architecture.

**Architecture Adjustments for Real-Time:**
* **WebSockets:** Use WebSockets to stream audio chunks.
* **Voice Activity Detection (VAD):** To know when the Student stops talking.
* **Latency Management via Vibe Check:**
    * The "Vibe Check" architecture naturally supports real-time better than the Swarm. Because we are only polling one Audience agent (rather than 5), we can process the "Room Temp" in parallel with the Partner's generation without clogging the network.
    * Visual Overlays: Audience reactions can be delivered as visual cues (emojis or text bubbles) to prevent audio collisions, ensuring the user isn't interrupted unless the "Spotlight" logic determines a heckle is pedagogically necessary.