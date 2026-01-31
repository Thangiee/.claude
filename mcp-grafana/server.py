#!/usr/bin/env python3
"""MCP server for querying Grafana metrics and logs."""

import subprocess
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("grafana")

GRAFANA_QUERY = "/Users/thangle/.claude/grafana-query"


@mcp.tool()
def grafana_metrics(
    query: str,
    last: str = "1h",
    start: str = None,
    end: str = None,
) -> str:
    """
    Query Grafana Cloud Prometheus metrics using PromQL.

    Args:
        query: PromQL query (e.g., 'sum(http_requests_total{service="api"})')
        last: Relative time range like "1h", "30m", "7d" (default: "1h")
        start: Absolute start time "YYYY-MM-DD HH:MM:SS" (overrides 'last')
        end: Absolute end time "YYYY-MM-DD HH:MM:SS" (required if start is set)

    Returns:
        JSON response with metric data
    """
    return _run_query("metrics", query, last, start, end)


@mcp.tool()
def grafana_logs(
    query: str,
    last: str = "1h",
    start: str = None,
    end: str = None,
) -> str:
    """
    Query Grafana Cloud Loki logs using LogQL.

    Args:
        query: LogQL query (e.g., '{service_namespace="my-service"} |= "error"')
        last: Relative time range like "1h", "30m", "7d" (default: "1h")
        start: Absolute start time "YYYY-MM-DD HH:MM:SS" (overrides 'last')
        end: Absolute end time "YYYY-MM-DD HH:MM:SS" (required if start is set)

    Returns:
        JSON response with log data
    """
    return _run_query("logs", query, last, start, end)


def _run_query(cmd: str, query: str, last: str, start: str, end: str) -> str:
    """Run grafana-query script and return output."""
    args = [GRAFANA_QUERY, cmd, query]

    if start and end:
        args.extend(["--start", start, "--end", end])
    else:
        args.extend(["--last", last])

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return result.stderr or result.stdout
        return result.stdout
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Query timed out after 30 seconds"})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()
