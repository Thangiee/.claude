# Staff Review Skill - Design

**Date:** 2026-01-30
**Status:** Draft

## Overview

A code review skill that thinks like a staff engineer, focusing on architectural fit, system-wide impact, and strategic trade-offs rather than surface-level concerns.

### Invocation

`/staff-review` with optional arguments:
- No args: Review uncommitted/staged changes in current repo
- PR URL: Review a specific pull request
- File paths: Review specific files

### What Makes It "Staff-Level"

A junior reviewer asks: *"Is this code correct?"*
A staff reviewer asks: *"Is this the right code to write?"*

The skill embodies three thinking modes:

1. **Architect** - Does this fit our system design? Does it create tech debt we'll regret? Will it scale with our trajectory?
2. **Systems Thinker** - What ripple effects does this have? Which teams/services are affected? What breaks if this breaks?
3. **Strategist** - Is this the right investment of engineering time? Are we solving the root problem or a symptom?

### Explicit Non-Goals

- Linting, formatting, syntax (tools do this better)
- Line-by-line nitpicks (wastes everyone's time)
- Style preferences (subjective, not valuable)

---

## Workflow

### Phase 1: Context Gathering

Before reviewing any code, the skill explores the codebase:
- Read README, CLAUDE.md, architecture docs
- Identify key patterns (folder structure, naming conventions, existing abstractions)
- Understand the domain (what does this system do?)
- Map dependencies and integration points

This happens via a focused exploration subagent to keep the main skill concise.

### Phase 2: Change Analysis

Gather the actual changes:
- For uncommitted: `git diff` and `git diff --staged`
- For PR: Fetch diff via `gh pr diff`
- For files: Read specified files and their recent git history

### Phase 3: Staff-Level Review

Apply the three thinking modes (Architect, Systems, Strategist) to generate findings. Each finding includes:
- **Severity**: Blocking / Significant / Minor
- **Category**: Architecture / Cross-cutting / Trade-off
- **Issue**: What's the concern
- **Why it matters**: Contextual explanation (detailed for blocking, brief for minor)
- **Example**: Code snippet showing better approach (for significant+ issues)

### Phase 4: Output

Generate markdown file at: `docs/reviews/YYYY-MM-DD-<branch-or-pr>.md`

Contains: Summary, prioritized findings, and optional "What I'd do differently" section for major concerns.

---

## Output Format

```markdown
# Staff Review: <branch-name or PR title>
**Date:** YYYY-MM-DD
**Reviewer:** Claude (Staff Review Skill)
**Scope:** <files changed count> files, <lines changed> lines

## Summary
2-3 sentence executive summary. What's this change doing?
What's the overall assessment? (Ship it / Needs work / Rethink approach)

## Findings

### Blocking
> These must be addressed before merging.

#### 1. <Issue title>
**Category:** Architecture | Cross-cutting | Trade-off

<Detailed explanation of why this matters, the principle being
violated, and potential consequences if ignored.>

**Better approach:**
\```<language>
// Code example demonstrating the recommended pattern
\```

---

### Significant
> Strong recommendations that improve quality/maintainability.

#### 2. <Issue title>
**Category:** ...
<Moderate explanation.>
**Better approach:** ...

---

### Minor
> Polish items. Address if time permits.

- <Brief issue + one-liner explanation>
- <Brief issue + one-liner explanation>

## Context Gathered
<Collapsed section listing what the skill reviewed to understand the system>
```

---

## Implementation Approach

### File Structure

```
skills/staff-review/
├── SKILL.md          # ~250 lines - main skill logic
└── review-template.md # Output template (optional)
```

### Delegation Strategy

To keep the skill concise (200-300 lines), it delegates heavy lifting:

1. **Context gathering** → Spawn `Explore` subagent with focused prompt
   - "Understand this codebase's architecture, patterns, and domain"
   - Returns structured summary (not raw file contents)

2. **Diff retrieval** → Direct bash commands
   - `git diff`, `gh pr diff`, etc.
   - Minimal logic, just capture output

3. **Review generation** → Main skill logic
   - Apply the three thinking modes to diff + context
   - Generate findings with appropriate depth
   - This is where staff-level judgment lives

4. **File output** → Write tool
   - Format findings into markdown template
   - Write to `docs/reviews/` directory

### What Stays in the Skill (the "brain")

- The three thinking modes (Architect, Systems, Strategist)
- Severity classification criteria
- Prompts that encode staff-level judgment
- Output formatting logic

### What Gets Delegated (the "hands")

- Codebase exploration
- Git operations
- File I/O

---

## Staff-Level Judgment Criteria

The core value is *what questions* the skill asks:

### Architect Mode

- Does this change fight against existing patterns, or flow with them?
- Will future developers understand why this exists?
- Does this create a "one-off" that will spawn copies?
- Are we adding complexity that serves no current user need? (YAGNI)
- Is this the right layer for this logic? (Separation of concerns)
- Does this make the system harder to change later?

### Systems Thinker Mode

- What happens when this fails? Is failure handled gracefully?
- What other services/components call this? Will they break?
- Does this change a contract (API, schema, interface)?
- Are there performance implications at scale?
- Does this introduce a single point of failure?
- Could this cause cascading issues in production?

### Strategist Mode

- Is this solving a symptom or the root cause?
- Are we building the right thing, or just building something?
- What's the maintenance burden we're signing up for?
- Is this a reversible or irreversible decision?
- What are we implicitly saying "no" to by doing this?

### Severity Classification

- **Blocking:** Production risk, security issue, breaks contracts, irreversible mistake
- **Significant:** Tech debt, scalability concern, maintainability issue, missing error handling
- **Minor:** Naming, documentation gaps, minor pattern inconsistency

---

## Summary

| Aspect | Decision |
|--------|----------|
| **Trigger** | `/staff-review` command (explicit invocation) |
| **Use cases** | Self-review + reviewing others' PRs |
| **Context** | Comprehensive codebase exploration first |
| **Output** | Priority-ranked findings (blocking → significant → minor) |
| **Explanations** | Contextual depth (detailed for blocking, brief for minor) |
| **Solutions** | Code examples for significant+ issues |
| **Artifact** | Markdown file in `docs/reviews/` |
| **Skill size** | 200-300 lines, delegates heavy lifting |
