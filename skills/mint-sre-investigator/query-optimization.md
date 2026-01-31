# Query Optimization Rules

**Context is precious. Every query must minimize data returned.**

## PromQL Rules

| Avoid | Use Instead | Why |
|-------|-------------|-----|
| `rate(metric[1m])` over 1h | `sum(increase(metric[1h]))` | 1 value vs 60 |
| `metric[1d]` | `metric[1d:1h]` | 24 values vs 1440 |
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
Step 1: Aggregated count/rate (single number)
        ↓ Anomaly detected?
Step 2: Break down by key dimension (topk 10)
        ↓ Identify culprit?
Step 3: Narrow time window, sample logs (limit 50)
        ↓ Need more context?
Step 4: Pull Unblocked context
```

## Time Ranges

| Type | Start With | Expand To |
|------|------------|-----------|
| Active incident | 15m | 1h |
| "What happened?" | 1h | 6h |
| Trend analysis | 24h (1h buckets) | 7d |
