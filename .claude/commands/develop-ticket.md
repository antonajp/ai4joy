---
name: develop-ticket
description: Retrieve a Linear ticket and implement it using parallel agent execution (gcp-admin-deployer, agentic-ml-architect, prd-writer, qa-tester, and ux-design-reviewer, principal-code-reviewer) with iterative code review until completion
argument-hint: "<Linear ticket number>"
---

Retrieve a Linear ticket and implement its requirements using a coordinated team of specialist agents. The command orchestrates parallel implementation followed by rigorous code review, iterating until all review criteria are met.

**Core Philosophy**:

  - 🎯 **Ticket-Driven**: Implementation strictly follows ticket requirements and acceptance criteria.
  - 🔄 **Iterative Refinement**: Code review feedback and testing drives improvement cycles.
  - 🤝 **Agent Coordination**: Parallel execution with clear ownership boundaries.
  - ✅ **Review-Gated**: No implementation is complete without passing code review.

**Important**: This command implements code changes. It modifies the codebase based on ticket requirements.

## Implementation Process

### Phase 0: Git Branch Setup

1. **Check current git status**: Ensure working tree is clean
2. **Create and checkout branch**: Branch name matches ticket ID (e.g., `STU-123`)
   - If branch already exists locally, checkout existing branch
   - If branch doesn't exist, create new branch from current HEAD
3. **Record start time**: Begin tracking development time

### Phase 1: Ticket Retrieval & Analysis

1. **Retrieve ticket** from Linear using the MCP Linear tool with the provided ticket number
2. **Parse ticket content**:
   - Extract business context and purpose
   - Identify acceptance criteria
   - Note technical specifications and constraints
   - Understand dependencies and risks
3. **Validate completeness**: Ensure ticket has sufficient detail for implementation. If critical information is missing, flag it and request clarification.

### Phase 2: Parallel Agent Implementation

Launch implementation agents in parallel (single message with multiple Task tool calls):

#### Implementation Agents

- **agentic-ml-architect**: 
  - Implements core business logic and feature functionality
  - Focuses on backend APIs, data flows, and integration points
  - Ensures alignment with existing architectural patterns
  - Adds logger statements for debugging in Chrome Dev Console

- **ux-design-reviewer**:
  - Implements UI components and user-facing features
  - Ensures responsive design, accessibility, and UX consistency
  - Handles all user interaction states (loading, empty, error, success)
  - Extracts styles to separate files, creates named functions for handlers

- **gcp-admin-deployer**:
  - Implements GCP infrastructure changes (security, policies, roles)
  - Updates deployment scripts and configurations
  - Ensures compatibility with GCP deploy process
  - Documents any manual deployment steps required

- **principal-code-reviewer**:
  - Monitors implementation progress from all agents
  - Identifies architectural concerns early
  - Prepares comprehensive code review checklist

- **qa-quality-assurance**:
  - Monitors implementation progress from all agents
  - Identifies key test cases early
  - Creates and refines test automation framework
  - Executes tests and reports results

#### Agent Coordination Rules

- Each agent operates on clearly separated concerns to avoid conflicts
- Agents communicate implementation boundaries through file ownership
- Shared files require explicit coordination between agents
- All agents follow project rules (550-line limit, KISS/DRY, no comments, surgical modifications)

#### Linear Ticket Update: Implementation Complete

After parallel implementation, add a comment to the Linear ticket:

```markdown
🔨 **Implementation Complete - Iteration 1**

**Files Modified**:
- List of files changed by each agent

**Key Changes**:
- Backend: Summary of pragmatic-shipper changes
- Frontend: Summary of ux-design-reviewer changes
- Infrastructure: Summary of gcp-admin-deployer changes

**Status**: Ready for code review
```

### Phase 3: Code Review

The **principal-code-reviewer** agent performs comprehensive review:

#### Review Criteria

1. **Functional Completeness**
   - All acceptance criteria from ticket are met
   - Edge cases are handled appropriately
   - Error handling is robust and production-ready

2. **Architectural Integrity**
   - Code follows existing patterns and conventions
   - Separation of concerns is maintained
   - No unnecessary complexity or feature bloat
   - Files respect line limits (550 lines standard, 750 for web components)
   - Usage of common classes to avoid duplication of code and dual maintenance of logic

3. **Code Quality**
   - KISS and DRY principles expertly followed
   - No inline styles or handlers in web components
   - Logger statements included for debugging
   - Code is self-explanatory without comments
   - Naming conventions match existing codebase

4. **Testing & Stability**
   - Changes are deterministic and predictable
   - No regressions introduced
   - Integration points validated

5. **Deployment Readiness**
   - EB deploy compatibility verified
   - Configuration changes documented
   - Manual steps clearly listed if required

#### Review Output Format

```markdown
## 🔍 Code Review Summary

**Review Status**: [APPROVED | CHANGES REQUESTED]
**Iteration**: [1, 2, 3...]

### ✅ Strengths
- List what was well-implemented
- Highlight adherence to project principles

### ⚠️ Issues Found
[Only if CHANGES REQUESTED]

#### Critical Issues (Must Fix)
- Issue description with file location and line numbers
- Specific remediation required

#### Suggestions (Should Fix)
- Improvement opportunities
- Refactoring recommendations

### 📋 Acceptance Criteria Status
- [ ] Criterion 1: Status and notes
- [ ] Criterion 2: Status and notes
- [ ] Criterion 3: Status and notes

### 🎯 Next Steps
[If APPROVED]: Ready to commit
[If CHANGES REQUESTED]: Specific actions for next iteration
```

#### Linear Ticket Update: Code Review Complete

After code review, add a comment to the Linear ticket:

**If APPROVED**:
```markdown
✅ **Code Review APPROVED - Iteration X**

**Strengths**:
- Key highlights from review

**Acceptance Criteria**: All met

**Status**: Ready for deployment
```

**If CHANGES REQUESTED**:
```markdown
🔍 **Code Review Feedback - Iteration X**

**Issues Found**:
- Critical issue 1 (file:line)
- Critical issue 2 (file:line)

**Suggestions**:
- Improvement 1
- Improvement 2

**Status**: Addressing feedback in next iteration

**Test Result Summary**:
- Test Failure 1
- Test Failure 2
- Were any changes required to existing regression tests
```

### Phase 4: Iteration (If Needed)

If code review or testing finds issues requiring changes:

1. **Targeted agent dispatch**: Only agents responsible for flagged issues are re-invoked
2. **Focused scope**: Agents receive specific review feedback to address
3. **Surgical fixes**: Minimal, targeted changes to resolve review items
4. **Re-review**: principal-code-reviewer and qa-quality-assurnace evaluate fixes

**Iteration continues** until review status is APPROVED and all tests are passing.

#### Linear Ticket Update: Iteration Complete

After each iteration, add a comment to the Linear ticket:

```markdown
🔧 **Iteration X Complete**

**Issues Addressed**:
- Issue 1: Fix description
- Issue 2: Fix description

**Files Updated**:
- List of files modified in this iteration

**Status**: Ready for re-review
```

### Phase 5: Completion

Once code review is APPROVED and all tests are passing:

1. **Verify all files saved** (per user preference)
2. **Run linter** on modified files and fix any errors
3. **Update Linear ticket** with final summary and development time
4. **Git commit**: Commit all changes with generated commit message
   - Stage all modified files
   - Use generated commit message following conventional commits format
   - Include ticket ID in commit message
   - push the commit to origin
5. **Summary output**:
   - List all modified files
   - Confirm acceptance criteria met
   - Note any manual deployment steps
   - Display git commit hash and message

#### Linear Ticket Update: Implementation Complete

Add final comment and update ticket metadata:

**Comment**:
```markdown
✨ **Implementation Complete**

**Branch**: STU-XXX
**Commit**: abc123def
**Total Iterations**: X
**Development Time**: Y hours

**Final Summary**:
- All acceptance criteria met
- X files modified
- Code review approved
- Changes committed to branch

**Files Changed**:
- `file1.ts`: Description
- `file2.tsx`: Description

**Deployment Notes**:
[If applicable]
- Manual steps required
- Configuration changes

**Ready for**: PR creation and team review
```

**Time Tracking**:
- Calculate total development time from start to completion
- Update ticket with actual time spent

## Usage Examples

```bash
# Simple feature implementation
@develop-ticket STU-123

# Bug fix
@develop-ticket STU-456
```

## Agent Execution Pattern

```
Phase 0: GIT SETUP
├─ Check git status (clean working tree)
├─ Create/checkout branch matching ticket ID
└─ Record start time

Phase 1: RETRIEVE
├─ Linear MCP → Fetch ticket STU-XXX
└─ Parse & validate requirements

Phase 2: IMPLEMENT (Parallel)
├─ agentic-ml-architect → Backend + business logic
├─ ux-design-reviewer → Frontend + UI components
├─ gcp-admin-deployer → GCP infrastructure + deployment
└─ principal-code-reviewer → Prepare review checklist

Phase 3: REVIEW
└─ principal-code-reviewer → Comprehensive review
    ├─ APPROVED → Phase 5
    └─ CHANGES REQUESTED → Phase 4
└─ qa-quality-assurance → Comprehensive testing
    ├─ ALL TESTS PASS → Phase 5
    └─ TEST FAILURES OCCURRED → Phase 4

Phase 4: ITERATE (Conditional)
├─ Dispatch targeted agents based on review feedback and test results
├─ Surgical fixes applied
└─ Loop to Phase 3

Phase 5: COMPLETE
├─ Save all files
├─ Run linter
├─ Update Linear ticket (final comment + time tracking)
├─ Git commit (stage all + commit with message)
└─ Output summary with commit hash
```

## Git Workflow

The command manages the complete git workflow:

**Branch Creation**:
- Branch name format: `<TICKET-ID>` (e.g., `STU-123`)
- Created from current HEAD (ensure you're on the correct base branch before running)
- If branch exists, checks out existing branch to continue work

**Commit Process**:
- Automatically stages all modified files
- Uses conventional commits format: `feat(STU-XXX): Brief description`
- Includes detailed change list in commit body
- Includes `Closes STU-XXX` footer for Linear integration

**Important**: This command does NOT push to remote. After completion, you should:
1. Review the commit with `git show`
2. Push to remote with `git push origin <branch-name>`
3. Create pull request for team review

## Time Tracking

Development time is tracked automatically throughout the implementation process:

- **Start time**: Recorded during git branch setup (Phase 0)
- **End time**: Recorded when git commit completes (Phase 5)
- **Total time**: Calculated as the difference between start and end
- **Granularity**: Rounded to nearest 0.25 hours for practical estimation

Time includes all phases: branch setup, analysis, implementation, code review, and iterations. This provides realistic effort tracking for future estimation.

## Error Handling

- **Dirty working tree**: Report uncommitted changes and request user to commit or stash before proceeding
- **Branch already exists with conflicts**: Report conflict and ask user to resolve manually
- **Ticket not found**: Report error and exit
- **Incomplete ticket**: List missing information and request user guidance
- **Agent conflicts**: Detect file collision and serialize conflicting changes
- **Review deadlock**: After 3 iterations without approval, summarize blocking issues and request user intervention
- **Linter errors**: Fix automatically if possible, otherwise report and request manual fix before commit

## Output Format

```markdown
## 🎫 Ticket Implementation: STU-XXX

**Ticket Title**: <Title from Linear>
**Status**: [COMPLETED | IN PROGRESS | BLOCKED]
**Branch**: STU-XXX
**Iterations**: X
**Development Time**: Y hours
**Commit Hash**: abc123def

### 📝 Summary
Brief description of what was implemented

### ✅ Acceptance Criteria Met
- [x] Criterion 1
- [x] Criterion 2
- [x] Criterion 3

### 📁 Files Modified
- `path/to/file1.ts` - Description of changes
- `path/to/file2.tsx` - Description of changes

### 🔄 Linear Ticket Updates
- X comments added (one per implementation/review/iteration cycle)
- Development time tracked and updated on ticket
- Final completion comment added

### 🚀 Deployment Notes
[If applicable]
- Manual steps required
- Configuration changes
- GCP resource updates

### 🔀 Git Information
**Branch**: STU-XXX
**Commit Hash**: abc123def

**Commit Message**:
```
feat(STU-XXX): Brief description

- Detailed change 1
- Detailed change 2
- Detailed change 3

Closes STU-XXX
```

**Next Steps**:
1. Review commit: `git show abc123def`
2. Push to remote: `git push origin STU-XXX`
3. Create pull request for team review
```

