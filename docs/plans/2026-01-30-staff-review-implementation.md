# Staff Review Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a code review skill that thinks like a staff engineer, focusing on architectural fit, system-wide impact, and strategic trade-offs.

**Architecture:** Single SKILL.md file (~250 lines) that delegates context gathering to an Explore subagent, retrieves diffs via git/gh commands, applies staff-level judgment criteria, and writes findings to a markdown file.

**Tech Stack:** Markdown skill file, Bash (git/gh), Task tool (Explore subagent), Write tool

---

## Task 1: Create Skill Directory Structure

**Files:**
- Create: `skills/staff-review/SKILL.md`

**Step 1: Create the skill directory**

```bash
mkdir -p skills/staff-review
```

**Step 2: Create minimal SKILL.md with frontmatter**

```markdown
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
```

**Step 3: Verify skill appears in Claude Code**

Run: `claude` and check `/skills` or skill list
Expected: `staff-review` appears in available skills

**Step 4: Commit**

```bash
git add skills/staff-review/SKILL.md
git commit -m "feat: scaffold staff-review skill"
```

---

## Task 2: Add Context Gathering Section

**Files:**
- Modify: `skills/staff-review/SKILL.md`

**Step 1: Add Phase 1 - Context Gathering**

After the Invocation section, add:

```markdown
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
```

**Step 2: Verify the skill still loads**

Test by running `/staff-review` - should see the new content in expanded skill.

**Step 3: Commit**

```bash
git add skills/staff-review/SKILL.md
git commit -m "feat(staff-review): add context gathering phase"
```

---

## Task 3: Add Diff Retrieval Section

**Files:**
- Modify: `skills/staff-review/SKILL.md`

**Step 1: Add Phase 2 - Change Analysis**

```markdown
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
```

**Step 2: Commit**

```bash
git add skills/staff-review/SKILL.md
git commit -m "feat(staff-review): add diff retrieval phase"
```

---

## Task 4: Add Staff-Level Judgment Criteria

**Files:**
- Modify: `skills/staff-review/SKILL.md`

**Step 1: Add Phase 3 - Staff-Level Review**

```markdown
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

#### What to IGNORE

Do NOT flag:
- Linting, formatting, syntax (tools do this better)
- Line-by-line nitpicks
- Style preferences
- Things that are clearly intentional trade-offs
```

**Step 2: Commit**

```bash
git add skills/staff-review/SKILL.md
git commit -m "feat(staff-review): add staff-level judgment criteria"
```

---

## Task 5: Add Output Format and File Generation

**Files:**
- Modify: `skills/staff-review/SKILL.md`

**Step 1: Add Phase 4 - Output**

```markdown
### Phase 4: Output

Generate findings and write to markdown file.

**Output path:** `docs/reviews/YYYY-MM-DD-<branch-or-pr>.md`

**Output format:**

```markdown
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
```

**Create the reviews directory:**
```bash
mkdir -p docs/reviews
```

Use the Write tool to save the review.
```

**Step 2: Commit**

```bash
git add skills/staff-review/SKILL.md
git commit -m "feat(staff-review): add output format and file generation"
```

---

## Task 6: Add Explanation Depth Guidelines

**Files:**
- Modify: `skills/staff-review/SKILL.md`

**Step 1: Add contextual depth section**

After the Severity Classification, add:

```markdown
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
```

**Step 2: Commit**

```bash
git add skills/staff-review/SKILL.md
git commit -m "feat(staff-review): add contextual explanation depth"
```

---

## Task 7: Add Complete Workflow Example

**Files:**
- Modify: `skills/staff-review/SKILL.md`

**Step 1: Add example section at the end**

```markdown
## Example

**User runs:** `/staff-review`

**Phase 1 - Context:**
```
[Spawn Explore subagent]
→ Returns: "This is a Next.js app with App Router. Uses Prisma for DB,
   Clerk for auth. Key patterns: server components by default,
   API routes in /api, shared utils in /lib..."
```

**Phase 2 - Diff:**
```bash
git diff HEAD
→ 3 files changed: src/app/api/users/route.ts, src/lib/db.ts, prisma/schema.prisma
```

**Phase 3 - Review:**
Applying Architect/Systems/Strategist thinking...

**Phase 4 - Output:**
Written to `docs/reviews/2026-01-30-feature-user-api.md`:

```markdown
# Staff Review: feature/user-api

**Date:** 2026-01-30
**Scope:** 3 files, 89 lines

## Summary

Adds a new user API endpoint with database schema changes. The implementation
works but introduces a problematic pattern that will cause issues at scale.

**Verdict:** Needs work

## Findings

### Blocking

#### 1. N+1 query in user list endpoint
**Category:** Architecture

The `/api/users` endpoint fetches users then loops to get their roles.
This creates N+1 queries that will crush the database with 1000+ users.

**Better approach:**
```typescript
// Use Prisma include to eager-load roles
const users = await prisma.user.findMany({
  include: { roles: true }
})
```

### Significant

#### 2. Missing rate limiting on public endpoint
**Category:** Cross-cutting

This endpoint is unauthenticated and has no rate limiting.
Bots could scrape your entire user list.

**Better approach:**
```typescript
// Add rate limiting middleware
import { rateLimit } from '@/lib/rate-limit'

export const GET = rateLimit(async (req) => { ... }, {
  limit: 100,
  window: '1m'
})
```

### Minor

- **Missing pagination:** Will need it eventually, low cost to add now
- **Inconsistent error format:** Other endpoints return `{ error: string }`, this returns `{ message: string }`
```
```

**Step 2: Commit**

```bash
git add skills/staff-review/SKILL.md
git commit -m "feat(staff-review): add complete workflow example"
```

---

## Task 8: Final Polish and Line Count Check

**Files:**
- Modify: `skills/staff-review/SKILL.md`

**Step 1: Check line count**

```bash
wc -l skills/staff-review/SKILL.md
```

Target: 200-300 lines. If over, trim redundancy. If under, content is complete.

**Step 2: Add any missing frontmatter or metadata**

Ensure frontmatter has:
```yaml
---
name: staff-review
description: Staff-level code review focusing on architecture, system impact, and strategic trade-offs
---
```

**Step 3: Final commit**

```bash
git add skills/staff-review/SKILL.md
git commit -m "feat(staff-review): polish and finalize skill"
```

**Step 4: Test the complete skill**

1. Run `/staff-review` on a repo with uncommitted changes
2. Verify it explores context first
3. Verify it generates review file
4. Check output matches expected format

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Create skill directory structure | `skills/staff-review/SKILL.md` |
| 2 | Add context gathering section | `skills/staff-review/SKILL.md` |
| 3 | Add diff retrieval section | `skills/staff-review/SKILL.md` |
| 4 | Add staff-level judgment criteria | `skills/staff-review/SKILL.md` |
| 5 | Add output format and file generation | `skills/staff-review/SKILL.md` |
| 6 | Add explanation depth guidelines | `skills/staff-review/SKILL.md` |
| 7 | Add complete workflow example | `skills/staff-review/SKILL.md` |
| 8 | Final polish and line count check | `skills/staff-review/SKILL.md` |

Total: 8 tasks, 8 commits, 1 file
