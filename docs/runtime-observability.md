# Runtime Observability / Prometheus Metrics

The Go runtime can expose Prometheus metrics and a health check endpoint. This is useful when running EventWeave as a long-lived simulator or when integrating it with SIEM/SOC test pipelines.

## Enabling metrics

Metrics are disabled by default. Start the metrics server with `--metrics-addr`:

```bash
eventweave-runtime serve dist/security_lateral_movement \
  --server-config examples/runtime/security_multi_source.yaml \
  --metrics-addr 127.0.0.1:9090
```

The metrics server works for `run`, `serve`, and `bench` modes:

```bash
eventweave-runtime run dist/security_lateral_movement \
  --sink http \
  --url http://localhost:8080/events \
  --metrics-addr 127.0.0.1:9090
```

## Endpoints

- `GET /metrics` — Prometheus exposition format
- `GET /healthz` — JSON health status

Example `/healthz` response for serve mode:

```json
{
  "status": "ok",
  "mode": "serve",
  "servers": 3
}
```

## Metrics

All metrics use the `eventweave_` namespace.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `eventweave_runtime_events_loaded_total` | counter | `mode` | Events loaded from the event plan |
| `eventweave_runtime_events_emitted_total` | counter | `mode`, `sink`, `server_id`, `protocol`, `status` | Events successfully or failed delivery |
| `eventweave_runtime_events_failed_total` | counter | `mode`, `sink`, `server_id`, `protocol` | Events that failed delivery |
| `eventweave_runtime_unresolved_refs_total` | counter | `mode` | Events with unresolved semantic refs |
| `eventweave_runtime_throughput_eps` | gauge | `mode`, `sink` | Observed throughput in events/sec |
| `eventweave_runtime_duration_seconds` | gauge | `mode`, `sink` | Total runtime duration |
| `eventweave_runtime_server_up` | gauge | `mode` | 1 while the runtime is active |
| `eventweave_runtime_endpoint_events_total` | counter | `server_id`, `protocol`, `status` | Events routed to a serve endpoint |
| `eventweave_runtime_endpoint_failures_total` | counter | `server_id`, `protocol` | Failures for a serve endpoint |

## Label cardinality

The runtime intentionally uses low-cardinality labels to avoid overwhelming Prometheus:

- `mode`: `run`, `serve`, `bench`
- `sink`: `stdout`, `file`, `null`, `http`, `kafka`, `syslog`
- `server_id`: configured endpoint id in serve mode
- `protocol`: `http`, `syslog_udp`, `syslog_tcp`
- `status`: `success`, `failed`

High-cardinality values such as `event_id`, `flow_id`, dynamic `source_id`, entity IDs, or IP addresses are intentionally excluded.

## Scraping example

```bash
curl -s http://127.0.0.1:9090/metrics | grep eventweave_runtime
```

## Limitations

- Metrics are available in the Go runtime only; the Python compiler and evaluator do not expose Prometheus metrics.
- No built-in Grafana dashboards or alerting rules are provided.
