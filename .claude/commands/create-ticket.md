---
name: create-ticket
description: Create a comprehensive Linear ticket in the Linear Studycard project from high-level input, automatically generating detailed context, acceptance criteria, and technical specifications using a core team of five specialist agents: 
argument-hint: "<high-level description of work needed>"
---

Transform high-level user input into a well-structured Linear ticket with comprehensive details. This command uses a core team of agents (`gcp-admin-deployer`, `ux-design-reviewer`, `agentic-ml-architect`, `prd-writer`, `qa-quality-assurance`) to handle all feature planning and specification in parallel. It focuses on **pragmatic startup estimation** to ensure tickets are scoped for rapid, iterative delivery.

**Pragmatic Startup Philosophy**:

  - 🚀 **Ship Fast**: Focus on working solutions over perfect implementations.
  - 💡 **80/20 Rule**: Deliver 80% of the value with 20% of the effort.
  - 🎯 **MVP First**: Define the simplest thing that could possibly work.

**Smart Ticket Scoping**: Automatically breaks down large work into smaller, shippable tickets if the estimated effort exceeds 2 days.

**Important**: This command ONLY creates the ticket(s). It does not start implementation or modify any code.

## Core Agent Workflow

For any feature request that isn't trivial (i.e., not LIGHT), this command follows a strict parallel execution rule using the core agent trio.

## Process

1. **Launch five agents in parallel** (single message with multiple Task tool calls):
   - **prd-writer agent**: Create detailed requirements and acceptance criteria
   - **agentic-ml-architect**: Research the codebase to understand current implementation and technical context. Identify technical dependencies, potential risks, and implementation considerations. Defines the "How" for the user. Focuses on user flow, states, accessibility, and consistency.
   - **ux-design-reviewer**: Defines the "How" for the user. Focuses on user flow, states, accessibility, and consistency. If the request/change is ONLY a backend change with NO UI impact, this agent should be minimally involved if at all.
   - **gcp-admin-deployer**: Defines the what and how for the GCP changes (including possible Cognito and IAM Policy and Role changes) and deployment scripts
   - **qa-quality-assurance**: Defines the what and how for unit, regression, and integration testing


2. **Synthesize findings** from all five agents into a comprehensive ticket with:
   - Clear, concise title
   - Detailed description with context
   - Well-defined acceptance criteria
   - Technical specifications and considerations
   - Any identified risks or dependencies
   - Test plan and test cases

3. **Create the Linear ticket** in the Studycard project using the MCP Linear tool with all synthesized information

### Parallel Execution Pattern

## Ticket Generation Process

### 1) Smart Research Depth Analysis

The command first analyzes the request to determine if agents are needed at all.

LIGHT Complexity → NO AGENTS
- For typos, simple copy changes, minor style tweaks.
- Create the ticket immediately.
- Estimate: <2 hours.

STANDARD / DEEP Complexity → CORE AGENTS
- For new features, bug fixes, and architectural work.
- The five subagents are dispatched in parallel, unless it's a backend change only, in which case ux-design-reviewer can be skipped.
- The depth (Standard vs. Deep) determines the scope of their investigation.

**Override Flags (optional)**:

  - `--light`: Force minimal research (no agents).
  - `--standard` / `--deep`: Force investigation using the five subagents.
  - `--single` / `--multi`: Control ticket splitting.
  - `--noui` / `--multi`: Force investigation using the all but the ux-design-reviewer subagent.

### 2\) Scaled Investigation Strategy

#### LIGHT Research Pattern (Trivial Tickets)

NO AGENTS NEEDED.
1. Generate ticket title and description directly from the request.
2. Set pragmatic estimate (e.g., 1 hour).
3. Create ticket and finish.

#### STANDARD Research Pattern (Default for Features)

The five subagents are dispatched with a standard scope:

#### DEEP Spike Pattern (Complex or Vague Tickets)

The five agents are dispatched with a deeper scope:

   - **prd-writer agent**: Develop comprehensive user stories, business impact, and success metrics.
   - **agentic-ml-architect**: Analyze architectural trade-offs, identify key risks, and create a phased implementation roadmap.
   - **ux-design-reviewer**: Create a detailed design brief, including edge cases and state machines. If no UX impact (only backend changes), then skip this agent
   - **gcp-admin-deployer**: Thinks very hard about the corresponding GCP changes (including possible security and policy and role changes) and deployment scripts
   - **qa-quality-assurance**: Thinks very hard about the corresponding unit and regression tests

### 3\) Generate Ticket Content

Findings from the five agents are synthesized into a comprehensive ticket.

#### Description Structure

```markdown
## 🎯 Business Context & Purpose
<Synthesized from prd-writer findings>
- What problem are we solving and for whom?
- What is the expected impact on business metrics?

## 📋 Expected Behavior/Outcome
<Synthesized from prd-writer and ux-design-reviewer findings>
- A clear, concise description of the new user-facing behavior.
- Definition of all relevant states (loading, empty, error, success).

## 🔬 Research Summary
**Investigation Depth**: <LIGHT|STANDARD|DEEP>
**Confidence Level**: <High|Medium|Low>

### Key Findings
- **Product & User Story**: <Key insights from prd-writer>
- **Design & UX Approach**: <Key insights from ux-design-reviewer>
- **Technical Plan & Risks**: <Key insights from agentic-ml-architect >
- **Pragmatic Effort Estimate**: <From agentic-ml-architect and gcp-admin-deployer>
- **Test Plan**: <From agentic-ml-architect and qa-quality-assurance>

## ✅ Acceptance Criteria
<Generated from all five agents' findings>
- [ ] Functional Criterion (from PM): User can click X and see Y.
- [ ] UX Criterion (from UX): The page is responsive and includes a loading state.
- [ ] Technical Criterion (from Eng): The API endpoint returns a `201` on success.
- [ ] All new code paths are covered by tests.

## 🔗 Dependencies & Constraints
<Identified by agentic-ml-architect and ux-design-reviewer and gcp-admin-deployer>
- **Dependencies**: Relies on existing Pagination component.
- **Technical Constraints**: Must handle >10K records efficiently.

## 💡 Implementation Notes
<Technical guidance synthesized from agentic-ml-architect and gcp-admin-deployer>
- **Recommended Approach**: Extend the existing `/api/insights` endpoint...
- **Potential Gotchas**: Query performance will be critical; ensure database indexes are added.
```

### 4\) Smart Ticket Creation

  - **If total estimated effort is ≤ 2 days**: A single, comprehensive ticket is created.
  - **If total estimated effort is \> 2 days**: The work is automatically broken down into 2-3 smaller, interconnected tickets (e.g., "Part 1: Backend API," "Part 2: Frontend UI"), each with its own scope and estimate.

### 5\) Output & Confirmation

The command finishes by returning the URL(s) of the newly created ticket(s) in Linear.
