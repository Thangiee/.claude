---
name: mint-sre-investigator
description: Use when investigating alerts, incidents, or answering operational questions about MINT services. Spawns expert SRE agent using Grafana metrics/logs and Unblocked context.
---

# MINT SRE Investigator

## How It Works

This skill spawns a specialized SRE agent that investigates in its own context, returning only a triage summary to your main conversation.

## Usage

For ANY MINT investigation:

1. Read the agent prompt from `~/.claude/agents/mint-sre-investigator.md`
2. Spawn the agent:

```
Task(
  subagent_type="general-purpose",
  prompt="<full content of agent file>

          ---
          INVESTIGATION REQUEST:
          <user's question or alert details>",
  model="sonnet"
)
```

3. Return the agent's triage summary to the user

## Examples

**User:** "Toast orders alert - no successful orders in 15 min"
**Action:** Spawn agent with investigation request, return triage summary

**User:** "Is OLO healthy?"
**Action:** Spawn agent, return health check summary

**User:** "Why did Chipotle fail yesterday at 3pm?"
**Action:** Spawn agent with time context, return incident summary

## Follow-ups

If user asks follow-up questions, spawn the agent again with:
- The new question
- Relevant context from previous findings

Each investigation is self-contained. Main conversation stays clean.
