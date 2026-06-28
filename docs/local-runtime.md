# Python Local Runtime

The Python Local Runtime replays a compiled and resolved event plan through an
output sink. It is designed for local debugging, demos, and low-QPS event stream
simulation. It is not a production-grade high-performance runtime.

## When to use it

- Validate that a compiled scenario produces the expected event flow.
- Inspect events with semantic assets injected.
- Generate a JSONL file for downstream testing or demos.
- Dry-run a scenario to count events without emitting them.

## CLI

```bash
# Replay to stdout in real time (1x speed)
eventweave run dist/ecommerce_refund_flow_semantic --sink stdout

# Write to a JSONL file, immediately (no waiting)
eventweave run dist/ecommerce_refund_flow_semantic \
  --sink file --output out/events.jsonl --no-wait

# Replay with 10x time acceleration
eventweave run dist/ecommerce_refund_flow_semantic --sink stdout --speed 10

# Dry-run: count events without emitting
eventweave run dist/ecommerce_refund_flow_semantic --dry-run
```

## Sinks

| Sink     | Description                                   |
|----------|-----------------------------------------------|
| `stdout` | Print each event as a JSON line to stdout.    |
| `file`   | Append events to a JSONL file.                |
| `null`   | Count events without writing them.            |

## Runtime output

At the end of a run the CLI prints a short summary:

```text
Runtime finished
Events emitted: 55
Duration: 0.008s
```

If any event still contains unresolved `semantic://` placeholders, a warning is
printed:

```text
Warning: 3 events have unresolved refs
```

To avoid this warning, run `eventweave semantic generate` before `eventweave run`.

## Time control

- `--speed N` accelerates scenario time by `N`. For example, `--speed 10` makes a
  10-second scenario interval take 1 second of real time.
- `--no-wait` disables all sleeping and emits events as fast as possible. This is
  useful for generating output files and tests.

## Architecture

```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Resolved       │────▶│  Local Runtime   │────▶│  Sink           │
│  event_plan     │     │  - scheduler     │     │  - stdout       │
│  .jsonl         │     │  - clock         │     │  - file         │
│                 │     │  - stats         │     │  - null         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

The runtime does not mutate canonical event content. It only controls when and
where events are emitted.

## Determinism

Given the same compiled plan, the local runtime always emits the same events in
the same order. Timing depends on `--speed` and `--no-wait`, but the event
sequence and content are stable.

## Custom sinks

Implement the `Sink` interface to add a new sink:

```python
from eventweave.core.event import Event
from eventweave.runtime.sink import Sink

class MySink(Sink):
    def open(self) -> None:
        pass

    def write(self, event: Event) -> None:
        # Send event somewhere.
        pass

    def close(self) -> None:
        pass

    def flush(self) -> None:
        pass

    def count(self) -> int:
        return 0
```

## Limitations

v0.3 intentionally does not include:

- HTTP, Kafka, Syslog, ClickHouse, or Elasticsearch sinks
- Multi-worker concurrency
- Backpressure handling
- Long-running daemon mode
- Pause/resume API

These are planned for later versions.
