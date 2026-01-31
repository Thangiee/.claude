# Query Optimization Rules

**Context is precious. Every query must minimize data returned.**

## Tool Parameters (CRITICAL)

The `mcp__grafana__metrics` tool has two parameters to reduce token usage:

### `instant=True` - For single values
Use when you need ONE number (count, total, rate):
```python
# "How many orders yesterday?" → 1 data point, ~150 tokens
mcp__grafana__metrics(query="sum(increase(metric[24h]))", last="24h", instant=True)
```

### `step` - For trends/patterns
Use when you need to see changes over time:
```python
# "Show hourly trend" → 24 data points, ~300 tokens (vs 1440 without step!)
mcp__grafana__metrics(query="sum(increase(metric[1h]))", last="24h", step="1h")
```

### Step size guide
| Time Range | Step | Data Points |
|------------|------|-------------|
| 1h | 5m | 12 |
| 6h | 15m | 24 |
| 24h | 1h | 24 |
| 7d | 6h | 28 |

**Default (no params) = 1-minute resolution = token explosion!**

## PromQL Rules

| Avoid | Use Instead | Why |
|-------|-------------|-----|
| `rate(metric[1m])` over 1h | `sum(increase(metric[1h]))` | 1 value vs 60 |
| No `instant` for totals | `instant=True` | 1 point vs 1440 |
| No `step` for trends | `step="1h"` for 24h | 24 points vs 1440 |
| `sum by (all_labels)` | `sum by (key_label)` | Reduce cardinality |
| Open-ended queries | `topk(10, ...)` | Cap result size |

## LogQL Rules

| Avoid | Use Instead | Why |
|-------|-------------|-----|
| `{app="x"} \|= "error"` | `sum(count_over_time({app="x"} \|= "error" [1h]))` | Count first |
| No limit | `\| limit 50` always | Cap log lines |
| Broad time range | Narrow to anomaly window | Less data |

## Investigation Flow

```
Step 1: Aggregated count/rate (instant=True, single number)
        ↓ Anomaly detected?
Step 2: Break down by key dimension (instant=True, topk 10)
        ↓ Identify culprit?
Step 3: Time series if needed (step=appropriate for range)
        ↓ Need specific logs?
Step 4: Narrow time window, sample logs (limit 50)
        ↓ Need more context?
Step 5: Pull Unblocked context
```

## Time Ranges

| Type | Start With | Expand To |
|------|------------|-----------|
| Active incident | 15m | 1h |
| "What happened?" | 1h | 6h |
| Trend analysis | 24h (1h buckets) | 7d |
