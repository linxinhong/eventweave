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

# Stream to Kafka
eventweave-runtime run dist/ecommerce_refund_flow_semantic \
  --sink kafka --brokers localhost:9092 --topic events --no-wait

# Stream to a local Syslog server
eventweave-runtime run dist/ecommerce_refund_flow_semantic \
  --sink syslog --syslog-addr 127.0.0.1:514 --syslog-proto udp --no-wait

# Rate-limited replay (fixed EPS)
eventweave-runtime run dist/security_lateral_movement \
  --sink null --rate 1000 --limit 10000

# Benchmark throughput
eventweave-runtime bench dist/ecommerce_refund_flow_semantic \
  --sink null --limit 100000

# Write stats to JSON
eventweave-runtime run dist/ecommerce_refund_flow_semantic \
  --sink file --output out/events.jsonl --no-wait \
  --stats-json out/stats.json
```

## CLI options

| Option              | Description                                               |
|---------------------|-----------------------------------------------------------|
| `--sink`            | `stdout`, `file`, `null`, `http`, `kafka`, `syslog`       |
| `--output`          | Output path for `file` sink                               |
| `--url`             | Target URL for `http` sink                                |
| `--brokers`         | Kafka broker list, comma-separated                        |
| `--topic`           | Kafka topic                                               |
| `--key-field`       | Kafka message key: `event_id`, `flow_id`, `source_id`, `''` |
| `--syslog-addr`     | Syslog server `host:port`                                 |
| `--syslog-proto`    | Syslog protocol: `udp` or `tcp` (default `udp`)           |
| `--syslog-facility` | Syslog facility number (default 16 = local0)              |
| `--syslog-severity` | Syslog severity number (default 6 = info)                 |
| `--syslog-tag`      | Syslog tag (default `eventweave`)                         |
| `--speed`           | Time acceleration factor (default 1.0)                    |
| `--no-wait`         | Emit all events immediately                               |
| `--rate`            | Target events per second (mutually exclusive with speed/no-wait) |
| `--limit`           | Maximum number of events to emit                          |
| `--max-failures`    | Stop after N failed writes (0 = unlimited)                |
| `--timeout`         | Network request timeout for `http` and `kafka` (default 5s) |
| `--retries`         | Retry attempts for transient network failures             |
| `--stats-json`      | Write runtime stats to a JSON file                        |

## Output

```text
Runtime finished
Events loaded: 55
Events emitted: 55
Duration: 0.005s
Throughput: 11000 events/sec
Sink: file (out/events.jsonl)
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
│   ├── ratelimit/   # rate control for --rate
│   ├── sink/        # Sink interface
│   ├── sinks/       # stdout, file, null, http, kafka, syslog sinks
│   ├── stats/       # runtime stats
│   └── runtime/     # LocalRuntime orchestration
└── go.mod
```

## Commands

### `run`

Replay a compiled event plan through a sink. Use `--speed` to follow the
scenario timeline, `--no-wait` to emit immediately, or `--rate` for a fixed
EPS target. These three timing options are mutually exclusive.

### `bench`

Benchmark throughput. Defaults to `--sink null` and `--no-wait` unless you
explicitly set `--sink`, `--rate`, or `--speed`. Output is a concise benchmark
summary including events, duration, and throughput.

### `serve`

Start a multi-source, multi-port server. Each endpoint is configured in a YAML
file and can filter events by `source_id` or `event_type`.

```bash
eventweave-runtime serve dist/security_lateral_movement \
  --server-config examples/runtime/security_multi_source.yaml \
  --limit 1000
```

Supported protocols per endpoint:

- `http` — `GET /events` returns a stream of SSE `data:` frames.
- `syslog_tcp` — accepts TCP connections and pushes RFC3164-like messages.
- `syslog_udp` — listens on UDP; forwards messages to clients after they send
  a registration datagram.

See [docs/multi-source-runtime.md](multi-source-runtime.md) for the full
configuration reference.

## Sinks

v0.4.2 ships with six sinks:

- `stdout` prints JSON lines.
- `file` appends to a JSONL file.
- `null` counts events without emitting.
- `http` POSTs each event as JSON to a URL, with timeout and retry.
- `kafka` publishes each event as JSON to a topic using `segmentio/kafka-go`.
- `syslog` sends RFC3164-like messages over UDP or TCP.

Retry behavior for `http` and `kafka`:

- 5xx responses and connection errors are retried up to `--retries` times.
- 4xx responses are not retried.

Kafka message keys are controlled by `--key-field`:

- `event_id` (default)
- `flow_id`
- `source_id`
- empty string for null key

## Compatibility with Python runtime

The Go runtime emits events in the same order as the Python local runtime:
`sorted by event_time, then event_id`. Given the same compiled plan, both
runtimes produce identical output.

## Limitations

v0.4.2 is an MVP. It does not include:

- ClickHouse, Elasticsearch, or other database sinks
- Multi-worker concurrency
- Advanced backpressure handling
- Long-running daemon mode
- Pause/resume API
- Prometheus metrics

These are planned for v0.4.3 and later.
