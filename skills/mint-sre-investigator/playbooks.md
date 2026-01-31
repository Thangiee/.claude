# Investigation Playbooks

**Note:** All queries default to `deployment_environment="production"`. Add to all metric selectors.

## Order Failures Spike

```
1. Identify scope
   sum by (app) (increase({__name__=~".*_favor_submitted_total", deployment_environment="production", success="false"}[1h]))

2. Validation or submission?
   - High favor_validated{success=false} → menu/item issue
   - High favor_submitted{success=false} → POS API issue

3. For POS issues, check client errors
   sum by (status) (increase({app}_client_failure[1h]))

4. Sample errors
   {app="toast-integration"} |= "favor" |= "error" | limit 30
```

## No Successful Orders (Zero Volume)

```
1. Confirm zero volume
   sum(increase({prefix}favor_submitted_total{success="true"}[30m]))

2. Orders coming in?
   sum(increase({prefix}favor_asked_total[30m]))
   - favor_asked = 0 → upstream issue (Kafka, gateway)
   - favor_asked > 0, favor_submitted = 0 → processing failure

3. Where are orders dying?
   sum(increase({prefix}favor_validated_total[30m]))
   sum(increase({prefix}favor_skipped_total[30m]))
   sum(increase({prefix}favor_canceled_total[30m]))

4. Service health
   up{app="{service}"}
   sum(increase({app}_endpoint_success[30m]))

5. Sample logs
   {app="{service}"} |= "error" | limit 50
```

## High Validation Error Rate

```
1. Confirm rate
   sum(increase({prefix}favor_validated_total{success="false"}[1h]))
   / sum(increase({prefix}favor_validated_total[1h])) * 100

2. Menu-related?
   sum(increase(integrated_menu_empty_publish_total[6h]))
   {app="{integration}"} |= "menu" |= "error" | limit 30

3. Item availability
   {app="{integration}"} |= "validation" |= "unavailable" | limit 30

4. Merchant-specific?
   topk(10, sum by (merchantId) (increase({prefix}favor_validated_total{success="false"}[1h])))
```

## High Submission Error Rate

```
1. Confirm rate
   sum(increase({prefix}favor_submitted_total{success="false"}[1h]))
   / sum(increase({prefix}favor_submitted_total[1h])) * 100

2. POS client errors
   topk(5, sum by (status, error) (increase({app}_client_failure[1h])))

3. Error patterns
   - 503/502 → POS outage
   - 401/403 → Auth issue
   - 429 → Rate limiting
   - Timeout → POS slow

4. Failover triggering?
   sum(increase({prefix}favor_canceled_total{failover="true"}[1h]))

5. Sample errors
   {app="{integration}"} |= "submit" |= "error" | limit 30
```

## Menu Sync Issues

```
1. Publishing health
   sum(increase(integrated_menu_empty_publish_total[1h]))
   sum(increase(integrated_menu_large_publish_total[1h]))

2. Translation latency
   histogram_quantile(0.99, sum by (le) (increase({prefix}menu_translation_time_bucket[1h])))

3. Kafka lag
   sum(increase(kafka_processing_time_sum[1h])) / sum(increase(kafka_processing_time_count[1h]))
```

## Webhook Issues (OLO/Stream)

```
1. Success rate
   sum(increase(olo_webhook_count{success="true"}[1h])) / sum(increase(olo_webhook_count[1h]))

2. By update type
   topk(5, sum by (update_type) (increase(olo_webhook_count{success="false"}[1h])))

3. Latency
   histogram_quantile(0.99, sum by (le, update_type) (increase(olo_webhook_processing_time_bucket[1h])))
```

## Latency Degradation

```
1. Which layer?
   histogram_quantile(0.99, sum by (layer) (increase({app}_latency_bucket[15m])))

2. Client layer → external dependency
   topk(5, histogram_quantile(0.99, sum by (client) (increase({app}_client_latency_bucket[15m]))))

3. Repo layer → database issues

4. Endpoint layer → check request volume
```

## Health Check (Pre/Post Deploy)

```
1. Quick vitals
   - Order success rate > 95%?
   - Endpoint error rate < 1%?
   - P99 latency within baseline?

2. Compare to 1h ago
   metric @ now vs metric offset 1h

3. Error log volume
   sum(count_over_time({app="X"} |= "error" [15m]))
```

---

## Unblocked Context

Pull context when metrics/logs point to something specific:

| Trigger | Tool | Query |
|---------|------|-------|
| Ticket ID known | `data_retrieval` | "Get details for MINT-4703" |
| Error pattern found | `failure_debugging` | "toast API 503 errors" |
| Need runbook | `context_engine` | "MINT toast runbook" |
| Why built this way? | `historical_context` | "toast retry logic" |
