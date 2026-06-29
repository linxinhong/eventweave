# Runtime Batching and Worker Pool

EventWeave Go runtime supports optional batching and concurrent workers for high-throughput sinks such as Kafka and HTTP.

## Kafka batching

By default the Kafka sink writes one message at a time. Enable batching with `--batch-size` and `--batch-timeout`:

```bash
eventweave-runtime run dist/security_lateral_movement \
  --sink kafka \
  --brokers 127.0.0.1:9092 \
  --topic eventweave.security \
  --batch-size 500 \
  --batch-timeout 100ms
```

Behavior:

- Events are buffered until `batch-size` is reached.
- If `batch-timeout` expires first, the partial batch is sent.
- Default `batch-size` is `1` (no batching).
- Default `batch-timeout` is `100ms`.
- Batches are retried as a unit according to `--retries`.

## Worker pool

Kafka and HTTP sinks can use concurrent workers:

```bash
eventweave-runtime run dist/security_lateral_movement \
  --sink http \
  --url http://localhost:8080/events \
  --workers 4 \
  --queue-size 2000 \
  --on-queue-full block
```

Flags:

- `--workers` — number of concurrent senders. Default `1` preserves order.
- `--queue-size` — bounded queue size. Default `1000`.
- `--on-queue-full` — `block` (default) or `fail`.

### Ordering semantics

- `--workers 1`: events are delivered in runtime emission order.
- `--workers > 1`: higher throughput, but no global order guarantee.

Kafka message keys can still preserve per-key order inside a Kafka partition.

### Backpressure

When the worker queue is full:

- `block`: the runtime waits until a worker picks up a job.
- `fail`: the event is counted as a failed write immediately.

The default is `block` to avoid silent event loss.

### Supported sinks

| Sink | Batching | Worker pool |
|------|----------|-------------|
| stdout | No | No (order preserved) |
| file | No | No (order preserved) |
| null | No | No |
| http | No | Yes |
| kafka | Yes | Yes |
| syslog | No | No by default |

## Metrics

When `--metrics-addr` is set, the following additional metrics are exposed:

- `eventweave_runtime_queue_depth`
- `eventweave_runtime_batches_total`
- `eventweave_runtime_batch_size`
- `eventweave_runtime_worker_events_total`
- `eventweave_runtime_worker_failures_total`

See [docs/runtime-observability.md](runtime-observability.md) for details.
