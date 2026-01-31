# grafana-query CLI Design

A shell script CLI for querying Grafana metrics and logs, primarily for Claude's use.

## Usage

```bash
# Metrics (PromQL)
grafana-query metrics 'sum(chipotle_favor_submitted_total{service="chipotle-integration-api-production",success="true"})'

# Logs (LogQL)
grafana-query logs '{app="chipotle-integration-api"}'

# Time range options (default: --last 1h)
--last 1h                                              # Relative: 1h, 30m, 7d
--start "2026-01-31 01:00:00" --end "2026-01-31 02:00:00"  # Absolute
```

## Configuration

**Token:** Stored in `~/.claude/.secrets`
```
GRAFANA_TOKEN=glsa_xxxxxxxxxxxx
```

**Hardcoded:**
- Host: `favor.grafana.net`
- Metrics datasource: `grafanacloud-prom`
- Logs datasource: `grafanacloud-logs`

## Output

Always JSON. Errors also return JSON for consistent parsing.

**Metrics response:**
```json
{"status":"success","data":{"resultType":"matrix","result":[{"metric":{},"values":[[1706666180,"42"]]}]}}
```

**Logs response:**
```json
{
  "status": "success",
  "data": {
    "resultType": "streams",
    "result": [{
      "stream": {"app": "chipotle"},
      "values": [{
        "line": "{\"@timestamp\":\"2026-01-31T09:27:46.057Z\",\"message\":\"...\",\"level\":\"INFO\"}",
        "timestamp": "1769851666058297233",
        "date": "2026-01-31T09:27:46.058Z"
      }]
    }]
  }
}
```

**Error response:**
```json
{"error": "GRAFANA_TOKEN not set in ~/.claude/.secrets"}
```

## API Details

Uses Grafana's unified datasource query API:

```
POST https://favor.grafana.net/api/ds/query
Authorization: Bearer $GRAFANA_TOKEN
Content-Type: application/json
```

Request body:
```json
{
  "queries": [{
    "refId": "A",
    "datasource": {"type": "prometheus", "uid": "grafanacloud-prom"},
    "expr": "<query>",
    "range": true,
    "intervalMs": 60000,
    "maxDataPoints": 1000
  }],
  "from": "1706662580000",
  "to": "1706666180000"
}
```

For logs, use `{"type": "loki", "uid": "grafanacloud-logs"}`.

## Implementation

**File:** `~/.claude/grafana-query`

**Structure:**
1. Source `~/.claude/.secrets` for token
2. Parse args: subcommand (metrics|logs), query, time options
3. Calculate from/to timestamps (epoch milliseconds)
4. Build JSON payload with jq or heredoc
5. curl POST to API
6. Output response

**Time parsing:**
- `--last 1h` → parse units (h, m, d, w), subtract from current time
- `--start/--end` → parse `YYYY-MM-DD HH:MM:SS` with `date` command

## Design Decisions

- **Claude-first:** JSON output, no table formatting
- **Shell script:** Simple curl wrapper, no compilation, easy to modify
- **Range queries only:** Instant queries rarely needed for troubleshooting
- **Config in .secrets:** Follows existing pattern for sensitive data
- **Hardcoded host/datasources:** Fixed for this use case, edit script if needed
