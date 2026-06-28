# Go High-Performance Runtime

The Go runtime in `runtime-go/` replays EventWeave event plans with lower
overhead than the Python local runtime. It reuses the exact same output from
the Python compiler:

```text
dist/<scenario>/
├── runtime_plan.json
└── event_plan.jsonl
```

The Go runtime only reads `event_plan.jsonl`; it does not duplicate compiler
logic.

## Build

```bash
cd runtime-go
go build ./...
go test ./...
```

## CLI

```bash
# Run from a compiled plan
eventweave-runtime run dist/ecommerce_refund_flow_semantic --sink stdout

# Write to file immediately
eventweave-runtime run dist/ecommerce_refund_flow_semantic \
  --sink file --output out/events.jsonl --no-wait

# Emit only the first 5 events
eventweave-runtime run dist/ecommerce_refund_flow_semantic --sink stdout --limit 5

# Stream to HTTP receiver
eventweave-runtime run dist/ecommerce_refund_flow_semantic \
  --sink http --url http://127.0.0.1:8080/events --no-wait
```

## CLI options

| Option        | Description                                      |
|---------------|--------------------------------------------------|
| `--sink`      | `stdout`, `file`, `null`, `http`                 |
| `--output`    | Output path for `file` sink                      |
| `--url`       | Target URL for `http` sink                       |
| `--speed`     | Time acceleration factor (default 1.0)           |
| `--no-wait`   | Emit all events immediately                      |
| `--limit`     | Maximum number of events to emit                 |
| `--timeout`   | HTTP request timeout (default 5s)                |
| `--retries`   | HTTP retry attempts for transient failures       |

## Output

```text
Runtime finished
Events emitted: 55
Duration: 0.005s
Sink: file
```

If any event still contains unresolved `semantic://` placeholders, a warning is
printed before the stats.

## Architecture

```text
runtime-go/
├── cmd/eventweave-runtime/
│   └── main.go
├── internal/
│   ├── config/      # CLI config validation
│   ├── event/       # canonical event model
│   ├── loader/      # event_plan.jsonl reader
│   ├── scheduler/   # event ordering
│   ├── clock/       # scenario-time to real-time mapping
│   ├── sink/        # Sink interface
│   ├── sinks/       # stdout, file, null, http sinks
│   ├── stats/       # runtime stats
│   └── runtime/     # LocalRuntime orchestration
└── go.mod
```

## Sinks

v0.4 ships with four sinks:

- `stdout` prints JSON lines.
- `file` appends to a JSONL file.
- `null` counts events without emitting.
- `http` POSTs each event as JSON to a URL, with timeout and retry.

Retry behavior:

- 5xx responses and connection errors are retried up to `--retries` times.
- 4xx responses are not retried.

## Compatibility with Python runtime

The Go runtime emits events in the same order as the Python local runtime:
`sorted by event_time, then event_id`. Given the same compiled plan, both
runtimes produce identical output.

## Limitations

v0.4 is an MVP. It does not include:

- Kafka, Syslog, ClickHouse, or Elasticsearch sinks
- Multi-worker concurrency
- Backpressure handling
- Long-running daemon mode
- Pause/resume API
- Prometheus metrics

These are planned for v0.4.1 and later.
