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

### Phase 2: Change Analysis

Gather the changes to review based on invocation:

**No arguments (uncommitted changes):**
```bash
git diff HEAD
git diff --staged
git status
```

**PR URL argument:**
```bash
gh pr diff <PR-NUMBER> --repo <OWNER/REPO>
gh pr view <PR-NUMBER> --repo <OWNER/REPO> --json title,body,files
```

**File paths argument:**
```bash
git diff HEAD -- <files>
git log --oneline -5 -- <files>
```

Capture:
- Files changed (with line counts)
- Actual diff content
- Related context (PR description, recent history)

### Phase 3: Staff-Level Review

Apply three thinking modes to the diff + context:

#### Architect Mode
Ask these questions:
- Does this change fight against existing patterns, or flow with them?
- Will future developers understand why this exists?
- Does this create a "one-off" that will spawn copies?
- Are we adding complexity that serves no current user need? (YAGNI)
- Is this the right layer for this logic? (Separation of concerns)
- Does this make the system harder to change later?

#### Systems Thinker Mode
Ask these questions:
- What happens when this fails? Is failure handled gracefully?
- What other services/components call this? Will they break?
- Does this change a contract (API, schema, interface)?
- Are there performance implications at scale?
- Does this introduce a single point of failure?
- Could this cause cascading issues in production?

#### Strategist Mode
Ask these questions:
- Is this solving a symptom or the root cause?
- Are we building the right thing, or just building something?
- What's the maintenance burden we're signing up for?
- Is this a reversible or irreversible decision?
- What are we implicitly saying "no" to by doing this?

#### Severity Classification

- **Blocking:** Production risk, security issue, breaks contracts, irreversible mistake
- **Significant:** Tech debt, scalability concern, maintainability issue, missing error handling
- **Minor:** Naming, documentation gaps, minor pattern inconsistency

#### Explanation Depth (Contextual)

Match explanation depth to severity:

**Blocking issues:**
- Full context: what, why, consequences, principle violated
- Code example showing the fix
- Reference to docs/patterns if relevant
- Teach the underlying concept

**Significant issues:**
- Clear explanation of problem and impact
- Code example showing better approach
- Brief mention of principle

**Minor issues:**
- One-liner: issue + why it matters
- No code example needed

#### What to IGNORE

Do NOT flag:
- Linting, formatting, syntax (tools do this better)
- Line-by-line nitpicks
- Style preferences
- Things that are clearly intentional trade-offs

### Phase 4: Output

Generate findings and write to markdown file.

**Output path:** `docs/reviews/YYYY-MM-DD-<branch-or-pr>.md`

**Output format:**

````markdown
# Staff Review: <branch-name or PR title>

**Date:** YYYY-MM-DD
**Reviewer:** Claude (Staff Review Skill)
**Scope:** X files, Y lines changed

## Summary

[2-3 sentence executive summary. What's this change doing? What's the overall assessment?]

**Verdict:** Ship it | Needs work | Rethink approach

## Findings

### Blocking
> These must be addressed before merging.

#### 1. [Issue title]
**Category:** Architecture | Cross-cutting | Trade-off

[Detailed explanation of why this matters, the principle being violated, and potential consequences if ignored.]

**Better approach:**
```[language]
// Code example demonstrating the recommended pattern
```

---

### Significant
> Strong recommendations that improve quality/maintainability.

#### 2. [Issue title]
**Category:** ...

[Moderate explanation - why it matters and what to do.]

**Better approach:**
```[language]
// Code example
```

---

### Minor
> Polish items. Address if time permits.

- [Brief issue]: [One-liner explanation]
- [Brief issue]: [One-liner explanation]

## What I'd Do Differently

[Optional section for major concerns - if you were building this from scratch, what approach would you take?]

## Context Gathered

<details>
<summary>System understanding (click to expand)</summary>

[Summary from Phase 1 exploration]

</details>
````
