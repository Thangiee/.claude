---
name: mint-sre-investigator
description: Use when investigating alerts, incidents, or answering operational questions about MINT services. Provides expert SRE guidance using Grafana metrics/logs and Unblocked context.
---

# MINT SRE Investigator

## Overview

Expert SRE skill for MINT service investigations. Uses metrics-first approach.

**Tools:** `mcp__grafana__metrics`, `mcp__grafana__logs`, `mcp__unblocked__*`

## Services

`menu-integration`, `olo-integration`, `toast-integration-service`, `chipotle-integration`, `seven-eleven-integration`, `stream-integration`

## Workflow

```
1. METRICS (fast)  → Aggregated health check
2. LOGS (if needed) → Specific errors (always limit 50)
3. UNBLOCKED       → Jira/Confluence/Slack context
```

## Output Format

**Always start with triage headline:**
```
🔴 CRITICAL: {metric} at {value} (normal: {baseline})
🟡 ELEVATED: {metric} showing {pattern}
🟢 HEALTHY: {service} metrics nominal
```

Include queries used. Expand to full report only if asked.

## Investigation Routing

Based on the investigation type, read the appropriate reference file:

| Investigation Type | Read This File |
|-------------------|----------------|
| Any investigation | `metrics-catalog.md` (skim for relevant metrics) |
| Need query help | `query-optimization.md` |
| Specific scenario | `playbooks.md` (find matching playbook) |

Reference files are in the same directory as this skill.

## For Complex Investigations

For multi-service issues or deep investigations, spawn a subagent:

```
Task(
  subagent_type="general-purpose",
  prompt="<include content from reference files relevant to the investigation>
          Investigate: <user's question>
          Return: triage summary with queries used",
  model="sonnet"
)
```

This keeps the main conversation context clean while allowing thorough investigation.
