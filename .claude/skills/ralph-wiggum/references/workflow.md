# Ralph Wiggum Workflow Reference

## Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PHASE 1: REQUIREMENTS                        │
│                        (Human + LLM Conversation)                    │
├─────────────────────────────────────────────────────────────────────┤
│  1. Identify Jobs-to-Be-Done (JTBD)                                 │
│  2. Break into Topics of Concern                                     │
│  3. Generate specs for each topic → specs/*.md                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PHASE 2: PLANNING                            │
│                       ./ralph-loop.sh plan N                         │
├─────────────────────────────────────────────────────────────────────┤
│  For each iteration:                                                 │
│  1. Study specs/* with subagents                                     │
│  2. Study existing code in app/*                                     │
│  3. Gap analysis: specs vs code                                      │
│  4. Create/update IMPLEMENTATION_PLAN.md                             │
│  5. Exit (context clears)                                            │
│                                                                       │
│  NO IMPLEMENTATION - ONLY PLANNING                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         PHASE 3: BUILDING                            │
│                       ./ralph-loop.sh [N]                            │
├─────────────────────────────────────────────────────────────────────┤
│  For each iteration:                                                 │
│  1. Orient: Study specs/*                                            │
│  2. Read: Study IMPLEMENTATION_PLAN.md                               │
│  3. Select: Pick most important task                                 │
│  4. Investigate: Study relevant src/ code                            │
│  5. Implement: Use parallel subagents for file operations            │
│  6. Validate: Run tests (backpressure)                               │
│  7. Update plan: Mark task done, note discoveries                    │
│  8. Commit: git add -A && git commit && git push                     │
│  9. Exit (context clears)                                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Backpressure Mechanisms

### Upstream Steering (Deterministic)
- First ~5,000 tokens allocated to specs
- Same files loaded each loop (PROMPT.md + AGENTS.md)
- Existing code patterns shape generated output

### Downstream Steering (Feedback)
- Tests reject invalid implementations
- Type checks catch type errors
- Lints enforce code style
- Build failures block commits

## Context Management

| Budget | Usable | Smart Zone |
|--------|--------|------------|
| 200K tokens | ~176K | 40-60% (~70-100K) |

**Implications**:
- Main agent as scheduler
- Spawn subagents for expensive work
- Each subagent gets ~156KB fresh memory
- One task per loop iteration

## Escape Hatches

| Situation | Action |
|-----------|--------|
| Loop running off track | `Ctrl+C` to stop |
| Bad commits | `git reset --hard HEAD~N` |
| Wrong trajectory | Regenerate plan |
| Plan is stale | Delete and re-run plan mode |

## Claude CLI Flags

```bash
claude -p \                          # Headless mode (stdin)
    --dangerously-skip-permissions \ # Auto-approve (YOLO)
    --output-format=stream-json \    # Structured output
    --model opus \                   # Complex reasoning
    --verbose                        # Detailed logging
```

## Topic Scope Test

> "Can I describe this topic in one sentence without using 'and'?"

If you need conjunctions, it's multiple topics.

**Good**: "User authentication with OAuth"
**Bad**: "User authentication and shopping cart" → Split into 2 specs

## Spec File Template

```markdown
# [Topic Name]

## Objective
[One sentence describing the goal]

## Requirements
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

## Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

## Technical Notes
[Any implementation guidance or constraints]
```

## IMPLEMENTATION_PLAN.md Template

```markdown
# Implementation Plan

## In Progress
- [ ] [Task currently being worked on]

## High Priority
- [ ] [Critical task 1]
- [ ] [Critical task 2]

## Medium Priority
- [ ] [Important task 1]
- [ ] [Important task 2]

## Low Priority
- [ ] [Nice to have 1]
- [ ] [Nice to have 2]

## Completed
- [x] [Done task 1]
- [x] [Done task 2]

## Discoveries
- [Learning 1]
- [Learning 2]
```
