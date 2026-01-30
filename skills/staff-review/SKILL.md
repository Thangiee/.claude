---
name: staff-review
description: Staff-level code review focusing on architecture, system impact, and strategic trade-offs
---

# Staff Review

A code review skill that thinks like a staff engineer.

## Invocation

`/staff-review` - Review uncommitted changes
`/staff-review <PR-URL>` - Review a specific PR
`/staff-review <files>` - Review specific files

## Workflow

### Phase 1: Context Gathering

Before reviewing code, understand the system. Spawn an Explore subagent:

**Prompt for Explore agent:**
> Analyze this codebase to understand its architecture and patterns.
>
> Find and summarize:
> 1. **Purpose** - What does this system do? (README, main entry points)
> 2. **Architecture** - How is it structured? (folder layout, key abstractions)
> 3. **Patterns** - What conventions are used? (naming, error handling, testing)
> 4. **Domain** - What business concepts exist? (models, services, APIs)
> 5. **Dependencies** - What external systems does it integrate with?
>
> Return a structured summary (not raw file contents). Be concise.

Use Task tool with `subagent_type: "Explore"` and `model: "haiku"` (context gathering is mechanical).

Store the summary for Phase 3.
