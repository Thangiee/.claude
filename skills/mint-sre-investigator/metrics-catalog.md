# MINT Metrics Catalog

## Common Patterns (All Services)

**@RecordMetrics generates for annotated methods:**
```
{app}_{layer}_latency      # Timer: p50, p90, p95, p99
{app}_{layer}_success      # Counter: successful calls
{app}_{layer}_failure      # Counter: failed calls
```
Layers: `endpoint`, `client`, `repo`, or class name
Tags: `method`, `class`, `status`, `path`, `httpMethod`

---

## Order Metrics (Critical)

### Order Lifecycle Flow
```
favor_asked → favor_validated → favor_submitted
                    ↓                  ↓
              (validation fail)   (submission fail)
                    ↓                  ↓
             favor_skipped      favor_canceled (failover tag)
```

### Per-Integration Prefixes
| Integration | Prefix |
|-------------|--------|
| OLO | `olo_` |
| Toast | `toast_` |
| Chipotle | `chipotle_` |
| 7-Eleven | `seven_eleven_` |

### Key Queries

**Order success rate:**
```promql
sum(increase({prefix}favor_submitted_total{success="true"}[1h]))
/ sum(increase({prefix}favor_submitted_total[1h])) * 100
```

**Validation failure rate:**
```promql
sum(increase({prefix}favor_validated_total{success="false"}[1h]))
/ sum(increase({prefix}favor_validated_total[1h])) * 100
```

**Failover cancellations:**
```promql
sum(increase({prefix}favor_canceled_total{failover="true"}[1h]))
```

### Failure Pattern Quick Reference
| Symptom | Likely Cause |
|---------|--------------|
| High `favor_validated{success=false}` | Menu mismatch, item unavailable |
| High `favor_submitted{success=false}` | POS API errors |
| High `favor_canceled{failover=true}` | POS outage |
| `favor_asked` high, `favor_validated` low | Upstream issue |
| `favor_skipped` increasing | Config issue |

---

## Menu Metrics

| Metric | Meaning |
|--------|---------|
| `integrated_menu_published_size_bytes` | Compressed menu size |
| `integrated_menu_published_item_count` | Items per menu |
| `integrated_menu_empty_publish` | Empty menu (bad) |
| `integrated_menu_large_publish` | Menu ≥10MB (warning) |
| `{prefix}menu_translation_time` | Menu conversion latency |

---

## Webhook Metrics (OLO, Stream)

| Metric | Tags |
|--------|------|
| `olo_webhook_count` | `success`, `update_type` |
| `olo_webhook_processing_time` | `update_type` |
| `stream_integration_kafka` | `success`, `type` |

---

## HTTP/Kafka Metrics

| Metric | Meaning |
|--------|---------|
| `{app}_http_api_request_latency` | Request processing time |
| `{app}_http_api_request_count` | Request count by status |
| `kafka_processing_time` | Kafka message processing |
