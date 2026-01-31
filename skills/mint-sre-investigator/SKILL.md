---
name: mint-sre-investigator
description: Use when investigating alerts, incidents, or answering operational questions about MINT services. Provides expert SRE guidance using Grafana metrics/logs and Unblocked context.
---

# MINT SRE Investigator

## Overview

Expert SRE skill for investigating MINT service health, incidents, and operational questions. Uses a metrics-first approach optimized for fast diagnosis without flooding context.

**Core principle:** Start cheap and fast (aggregated metrics), escalate only when needed (logs, then external context).

## When to Use

- Alert firing for any MINT service
- Investigating order failures, menu sync issues, webhook problems
- Answering "why did X happen?" questions about MINT services
- Health checks before/after deployments
- Capacity planning and trend analysis

## Services Covered

| Service | Primary Function |
|---------|------------------|
| `menu-integration` | Core menu processing (API + Kafka worker) |
| `olo-integration` | OLO platform ordering & menus |
| `toast-integration-service` | Toast POS ordering & menus |
| `chipotle-integration` | Chipotle POS ordering |
| `seven-eleven-integration` | 7-Eleven ordering |
| `stream-integration` | Stream platform webhooks |

## Tools Used

- `mcp__grafana__metrics` - PromQL queries (prefer this first)
- `mcp__grafana__logs` - LogQL queries (use sparingly)
- `mcp__unblocked__*` - Jira, Confluence, Slack context

---

## Investigation Workflow

**Always follow this order:**

```
1. METRICS (fast, cheap)     → Get the headline
2. LOGS (if needed)          → Find specific errors
3. UNBLOCKED (if relevant)   → Jira tickets, Slack threads, runbooks
```

### Phase 1: Metrics First

Start with aggregated metrics to get a quick health picture. Use these query patterns to minimize data:

**Aggregations over time series:**
```promql
# Good: Single value
sum(increase(toast_favor_submitted_total{success="false"}[1h]))

# Bad: 60 data points
rate(toast_favor_submitted_total{success="false"}[1m])
```

**Limit cardinality:**
```promql
# Top 10 error sources only
topk(10, sum by (error) (increase(olo_webhook_count{success="false"}[1h])))
```

**Use subqueries for trends:**
```promql
# 24 points instead of 1440
sum(rate(menu_integration_endpoint_failure[1h:1h]))
```

### Phase 2: Logs (Only If Needed)

Escalate to logs when:
- Metrics show anomaly but not root cause
- Need specific error messages or stack traces
- Investigating a single request/order

**Use metric queries first:**
```logql
# Good: Count errors (returns number)
sum(count_over_time({app="toast-integration"} |= "error" [1h]))

# Only if needed: Actual logs (limit always)
{app="toast-integration"} |= "error" | limit 50
```

### Phase 3: Context (For Specific Incidents)

Pull Unblocked context when:
- Investigating a specific Jira ticket
- Looking for related incidents or runbooks
- Need deployment history or change context

---

## MINT Metrics Catalog

### Common Patterns (All Services)

**@RecordMetrics generates these for annotated methods:**
```
{app}_{layer}_latency      # Timer: p50, p90, p95, p99
{app}_{layer}_success      # Counter: successful calls
{app}_{layer}_failure      # Counter: failed calls
```

Layers: `endpoint`, `client`, `repo`, or class name

Tags: `method`, `class`, `status`, `path`, `httpMethod`

### Order Metrics Deep Dive

**This is the most critical metric family for MINT operations.**

#### Metric Flow (Order Lifecycle)

```
favor_asked → favor_validated → favor_submitted
                    ↓                  ↓
              (validation fail)   (submission fail)
                    ↓                  ↓
             favor_skipped      favor_canceled (with failover tag)
```

#### Per-Integration Prefixes

| Integration | Prefix | Example |
|-------------|--------|---------|
| OLO | `olo_` | `olo_favor_submitted` |
| Toast | `toast_` | `toast_favor_submitted` |
| Chipotle | `chipotle_` | `chipotle_favor_submitted` |
| 7-Eleven | `seven_eleven_` | `seven_eleven_favor_submitted` |

#### Key Investigation Queries

**Overall order success rate (last hour):**
```promql
sum(increase({prefix}favor_submitted_total{success="true"}[1h]))
/
sum(increase({prefix}favor_submitted_total[1h])) * 100
```

**Validation failure rate:**
```promql
sum(increase({prefix}favor_validated_total{success="false"}[1h]))
/
sum(increase({prefix}favor_validated_total[1h])) * 100
```

**Order volume trend (hourly buckets):**
```promql
sum(increase({prefix}favor_asked_total[1h:1h]))
```

**Failover cancellations (indicates POS issues):**
```promql
sum(increase({prefix}favor_canceled_total{failover="true"}[1h]))
```

#### Common Failure Patterns

| Symptom | Likely Cause | Next Step |
|---------|--------------|-----------|
| High `favor_validated{success=false}` | Menu mismatch, item unavailable | Check `menu_translation_time`, recent menu syncs |
| High `favor_submitted{success=false}` | POS API errors | Check `client_failure` metrics, then logs for error codes |
| Spike in `favor_canceled{failover=true}` | POS outage, timeout | Check POS client latency, external status pages |
| `favor_asked` high but `favor_validated` low | Upstream throttling or errors | Check endpoint metrics, Kafka lag |
| `favor_skipped` increasing | Config issue, merchant disabled | Check Unblocked for recent tickets/changes |

#### Comparing Across Integrations

**All integrations success rate:**
```promql
topk(10,
  sum by (integration) (increase(
    {__name__=~".*_favor_submitted_total", success="true"}[1h]
  ))
  /
  sum by (integration) (increase(
    {__name__=~".*_favor_submitted_total"}[1h]
  ))
)
```

### Menu Processing Metrics

| Metric | Type | Service | Meaning |
|--------|------|---------|---------|
| `integrated_menu_published_size_bytes` | Distribution | menu-integration | Compressed menu size |
| `integrated_menu_published_item_count` | Distribution | menu-integration | Items per menu |
| `integrated_menu_empty_publish` | Counter | menu-integration | Empty menu published (bad) |
| `integrated_menu_large_publish` | Counter | menu-integration | Menu >=10MB (warning) |
| `{prefix}menu_translation_time` | Timer | per-integration | Menu conversion latency |

### Webhook Metrics (OLO, Stream)

| Metric | Type | Tags | Meaning |
|--------|------|------|---------|
| `olo_webhook_count` | Counter | `success`, `update_type` | Webhook processing count |
| `olo_webhook_processing_time` | Timer | `update_type` | Webhook latency |
| `stream_integration_kafka` | Counter | `success`, `type` | Stream event processing |

---

## Output Format

### Triage Response (Always Start Here)

Lead with severity + headline finding:

```
🔴 CRITICAL: {metric} at {value} (normal: {baseline})
   Correlated: {related finding}
   Impact: {user-facing impact estimate}

🟡 ELEVATED: {metric} showing {pattern}
   Started: {timestamp}
   Affected: {scope}

🟢 HEALTHY: {service} metrics nominal
   Checked: {what was verified}
```

### Expanded Report (When Asked or Ambiguous)

```
## Summary
{One paragraph: what's wrong, since when, impact}

## Metrics Observed
| Metric | Current | Baseline | Delta |
|--------|---------|----------|-------|
| ...    | ...     | ...      | ...   |

## Anomalies Detected
- {anomaly 1}: {description}
- {anomaly 2}: {description}

## Correlated Events
- {Jira ticket if found}
- {Recent deployment if relevant}
- {Related Slack thread}

## Potential Root Causes
1. {Most likely}: {evidence}
2. {Alternative}: {evidence}

## Recommended Actions
- [ ] {Immediate action}
- [ ] {Follow-up investigation}
- [ ] {Preventive measure}
```

### Query Sharing

Always include the queries used so operator can re-run or modify:

```
📊 Queries used:
- Success rate: `sum(increase(olo_favor_submitted_total{success="true"}[1h])) / sum(increase(olo_favor_submitted_total[1h]))`
- Error logs: `{app="olo-integration"} |= "error" | limit 50`
```

---

## Query Optimization Rules

**Context is precious. Every query must minimize data returned.**

### PromQL Rules

| Avoid | Use Instead | Why |
|-------|-------------|-----|
| `rate(metric[1m])` over 1h | `sum(increase(metric[1h]))` | 1 value vs 60 |
| `metric[1d]` | `metric[1d:1h]` | 24 values vs 1440 |
| `sum by (all_labels) (...)` | `sum by (key_label) (...)` | Reduce cardinality |
| Open-ended label queries | `topk(10, ...)` | Cap result size |
| Multiple separate queries | Combined query with `or` | Fewer round trips |

### LogQL Rules

| Avoid | Use Instead | Why |
|-------|-------------|-----|
| `{app="x"} \|= "error"` | `sum(count_over_time({app="x"} \|= "error" [1h]))` | Count first |
| No limit | `\| limit 50` always | Cap log lines |
| Broad time range | Narrow to anomaly window | Less data |
| `{app=~".*"}` | Specific app label | Targeted |

### Investigation Flow

```
Step 1: Aggregated count/rate (single number)
        ↓
        Anomaly detected?
        ↓ yes
Step 2: Break down by key dimension (topk 10)
        ↓
        Identify culprit?
        ↓ yes
Step 3: Narrow time window, get sample logs (limit 50)
        ↓
        Need more context?
        ↓ yes
Step 4: Pull Unblocked context for specific incident
```

### Time Range Guidelines

| Investigation Type | Start With | Expand If Needed |
|--------------------|------------|------------------|
| Active incident | Last 15m | Last 1h |
| "What happened?" | Last 1h | Last 6h |
| Trend analysis | Last 24h (1h buckets) | Last 7d (6h buckets) |
| Capacity planning | Last 7d (1d buckets) | Last 30d |

---

## Unblocked Context Integration

**Use Unblocked to enrich investigations with organizational context.**

### When to Pull Context

| Trigger | Unblocked Tool | What to Look For |
|---------|----------------|------------------|
| Alert has ticket ID (e.g., MINT-4703) | `mcp__unblocked__data_retrieval` | Acceptance criteria, related issues |
| Investigating specific merchant | `mcp__unblocked__unblocked_context_engine` | Merchant onboarding docs, known issues |
| Error pattern unclear | `mcp__unblocked__failure_debugging` | Similar past incidents |
| "Why was this built this way?" | `mcp__unblocked__historical_context` | Design decisions, tech debt context |
| Need runbook/playbook | `mcp__unblocked__unblocked_context_engine` | Confluence runbooks |
| Link in logs/alerts | `mcp__unblocked__link_resolver` | Resolve to content |

### Query Patterns

**Jira ticket from branch/alert:**
```
Query: "Get details for MINT-4703"
→ Returns: description, acceptance criteria, comments, linked issues
```

**Search for runbooks:**
```
Query: "MINT toast integration runbook"
Query: "order failure troubleshooting guide"
```

**Find related incidents:**
```
Query: "toast API 503 errors incident"
Query: "OLO webhook failures postmortem"
```

### Context Ordering

```
1. Metrics show the problem
2. Logs confirm specific errors
3. THEN pull Unblocked:
   - If ticket ID known → get ticket details
   - If error pattern found → search for past incidents
   - If root cause unclear → search for architecture docs
```

### Don't Over-Fetch

- Pull context only when metrics/logs point to something specific
- One targeted query beats three broad searches
- Summarize findings, don't dump raw context

---

## Common Investigation Playbooks

### Playbook: Order Failures Spike

```
1. Identify scope
   sum by (app) (increase({__name__=~".*_favor_submitted_total", success="false"}[1h]))

2. Check if validation or submission
   - High favor_validated{success=false} → menu/item issue
   - High favor_submitted{success=false} → POS API issue

3. For POS API issues, check client metrics
   sum by (status) (increase({app}_client_failure[1h]))

4. Get sample errors (limit!)
   {app="toast-integration"} |= "favor" |= "error" | limit 30

5. If merchant-specific, pull Unblocked for merchant context
```

### Playbook: Menu Sync Issues

```
1. Check menu publishing health
   sum(increase(integrated_menu_empty_publish_total[1h]))
   sum(increase(integrated_menu_large_publish_total[1h]))

2. Check translation latency by integration
   histogram_quantile(0.99, sum by (le) (increase({prefix}menu_translation_time_bucket[1h])))

3. Check Kafka processing lag
   sum(increase(kafka_processing_time_sum[1h])) / sum(increase(kafka_processing_time_count[1h]))

4. If specific merchant, search logs
   {app="menu-integration"} |= "{merchant_id}" |= "error" | limit 30
```

### Playbook: Webhook Processing Issues (OLO/Stream)

```
1. Check webhook success rate
   sum(increase(olo_webhook_count{success="true"}[1h])) / sum(increase(olo_webhook_count[1h]))

2. Break down by update type
   topk(5, sum by (update_type) (increase(olo_webhook_count{success="false"}[1h])))

3. Check processing latency
   histogram_quantile(0.99, sum by (le, update_type) (increase(olo_webhook_processing_time_bucket[1h])))

4. Sample failed webhooks
   {app="olo-integration"} |= "webhook" |= "error" | limit 30
```

### Playbook: Latency Degradation

```
1. Identify which layer is slow
   histogram_quantile(0.99, sum by (layer) (increase({app}_latency_bucket[15m])))

2. If client layer → external dependency
   topk(5, histogram_quantile(0.99, sum by (client) (increase({app}_client_latency_bucket[15m]))))

3. If repo layer → database
   Check connection pool, query patterns

4. If endpoint layer → check request volume
   sum(increase({app}_endpoint_success[15m]))
```

### Playbook: No Successful Orders (Zero Volume Alert)

```
1. Confirm zero volume (not just alert lag)
   sum(increase({prefix}favor_submitted_total{success="true"}[30m]))

2. Check if orders are coming in at all
   sum(increase({prefix}favor_asked_total[30m]))

   - If favor_asked = 0 → upstream issue (Kafka, API gateway)
   - If favor_asked > 0 but favor_submitted = 0 → processing failure

3. For upstream issues, check Kafka consumer lag
   # Check if worker is consuming
   sum(increase(kafka_processing_time_count[30m]))

4. For processing failures, check where orders are dying
   sum(increase({prefix}favor_validated_total[30m]))      # reaching validation?
   sum(increase({prefix}favor_skipped_total[30m]))        # being skipped?
   sum(increase({prefix}favor_canceled_total[30m]))       # being canceled?

5. Check for service health (is it even running?)
   up{app="{service}"}
   sum(increase({app}_endpoint_success[30m]))

6. Sample recent logs for errors
   {app="{service}"} |= "error" | limit 50

7. Pull Unblocked for recent deployments or config changes
   Query: "{service} deployment" or "MINT config change"
```

### Playbook: High Validation Error Rate

```
1. Confirm validation failure rate
   sum(increase({prefix}favor_validated_total{success="false"}[1h]))
   /
   sum(increase({prefix}favor_validated_total[1h])) * 100

2. Check if menu-related (common cause)
   - Recent menu sync failures?
     sum(increase(integrated_menu_empty_publish_total[6h]))
   - Menu translation errors?
     {app="{integration}"} |= "menu" |= "error" | limit 30

3. Check for item availability issues
   {app="{integration}"} |= "validation" |= "unavailable" | limit 30
   {app="{integration}"} |= "validation" |= "not found" | limit 30

4. Check if merchant-specific
   # If logs show merchant ID pattern, narrow scope
   topk(10, sum by (merchantId) (increase({prefix}favor_validated_total{success="false"}[1h])))

5. Pull Unblocked for merchant issues
   Query: "merchant {id} menu issue" or "MINT-* validation"
```

### Playbook: High Submission Error Rate

```
1. Confirm submission failure rate
   sum(increase({prefix}favor_submitted_total{success="false"}[1h]))
   /
   sum(increase({prefix}favor_submitted_total[1h])) * 100

2. Check POS client errors
   topk(5, sum by (status, error) (increase({app}_client_failure[1h])))

3. Common POS error patterns
   - 503/502 → POS outage, check their status page
   - 401/403 → Auth issue, check credentials rotation
   - 429 → Rate limiting, check request volume
   - Timeout → POS slow, check client latency p99

4. Check if failover is triggering
   sum(increase({prefix}favor_canceled_total{failover="true"}[1h]))
   # High failover = POS confirmed down, orders routing elsewhere

5. Sample submission errors
   {app="{integration}"} |= "submit" |= "error" | limit 30
   {app="{integration}"} |= "favor" |= "failed" | limit 30

6. Pull Unblocked for POS incidents
   Query: "Toast API outage" or "OLO incident"
```

### Playbook: "Is X Healthy?" (Pre/Post Deploy)

```
1. Quick vitals check
   - Order success rate > 95%?
   - Endpoint error rate < 1%?
   - P99 latency within baseline?

2. Compare to 1h ago / 1d ago
   metric @ now vs metric @ (now - 1h)

3. Check for elevated error logs
   sum(count_over_time({app="X"} |= "error" [15m]))
```

---

## Usage Examples

### Example Inputs & Responses

**Alert investigation:**
```
User: "Toast orders alert firing - no successful orders in 15 min"

Response:
🔴 CRITICAL: toast_favor_submitted{success=true} = 0 over last 15m
   favor_asked: 47 orders received
   favor_validated: 12 passed, 35 failed (74% failure rate)

   Root cause: Validation failures - menu items not found
   Correlated: toast_menu_translation_time spike at 14:22 UTC

   📊 Queries used:
   - sum(increase(toast_favor_submitted_total{success="true"}[15m]))
   - sum(increase(toast_favor_validated_total{success="false"}[15m]))

   Recommend: Check recent menu sync for affected merchants. Want me to pull logs?
```

**Health check:**
```
User: "Is OLO integration healthy?"

Response:
🟢 HEALTHY: olo-integration nominal

   Order success rate: 97.2% (last 1h)
   Webhook processing: 99.1% success
   P99 latency: 342ms (baseline: 400ms)

   No anomalies detected.
```

**Historical investigation:**
```
User: "Why did Chipotle orders fail yesterday around 3pm?"

Response:
🟡 INCIDENT IDENTIFIED: chipotle_favor_submitted dropped to 23% success
   Window: 14:47 - 15:32 UTC (45 min)

   Timeline:
   - 14:47: client_failure spike (status=503)
   - 14:52: failover cancellations began
   - 15:28: errors subsided
   - 15:32: success rate recovered

   Root cause: Chipotle API returned 503s (their outage)

   📎 Related: Found MINT-4821 filed during incident

   Want expanded report with full metrics?
```
