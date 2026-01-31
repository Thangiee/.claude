---
name: mint-sre-investigator
description: Use when investigating alerts, incidents, or answering operational questions about MINT services. Spawns expert SRE agent using Grafana metrics/logs and Unblocked context.
---

# MINT SRE Investigator

## How It Works

This skill spawns a specialized SRE agent that investigates in its own context, returning only a triage summary to your main conversation.

## Model Selection (Auto)

Choose model based on question complexity:

### Use `model="haiku"` for simple questions:
- "How many X?" / "What's the count of Y?"
- "Is X healthy?" / "Is X up?"
- "What's the current rate of X?"
- "Show me X metric"
- Single metric lookups, counts, health checks

### Use `model="sonnet"` for complex investigations:
- "Why did X fail?" / "What caused Y?"
- "Investigate..." / "Debug..." / "Analyze..."
- Alert triage requiring multi-step analysis
- Questions needing logs + metrics correlation
- Root cause analysis

## Usage

1. Read the agent prompt from `~/.claude/agents/mint-sre-investigator.md`
2. Determine model based on question complexity (see above)
3. Spawn the agent:

```
Task(
  subagent_type="general-purpose",
  prompt="<full content of agent file>

          ---
          INVESTIGATION REQUEST:
          <user's question or alert details>",
  model="haiku"  # or "sonnet" for complex investigations
)
```

4. Return the agent's triage summary to the user

## Environment

Queries default to **production**. User can specify environment:
- "How many orders in **QA**?" → `deployment_environment="qa"`
- "Check **dev** health" → `deployment_environment="dev"`

## Examples

**User:** "How many Chipotle orders yesterday?"
**Action:** Spawn with `model="haiku"` (simple count, production)

**User:** "Is OLO healthy?"
**Action:** Spawn with `model="haiku"` (simple health check, production)

**User:** "Check Toast in QA"
**Action:** Spawn with `model="haiku"` (qa environment)

**User:** "Toast orders alert - no successful orders in 15 min"
**Action:** Spawn with `model="sonnet"` (alert triage, needs investigation)

**User:** "Why did Chipotle fail yesterday at 3pm?"
**Action:** Spawn with `model="sonnet"` (root cause analysis)

## Follow-ups

If user asks follow-up questions, spawn the agent again with:
- The new question
- Relevant context from previous findings
- Same model selection logic

Each investigation is self-contained. Main conversation stays clean.
