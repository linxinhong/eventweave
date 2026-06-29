# Multi-source / Multi-port Runtime Server

The Go runtime can run as a server that exposes events over multiple protocol endpoints. This is useful when you want EventWeave to simulate several distinct device or service sources at the same time, each on its own port and protocol.

## Commands

| Command | Mode |
|---------|------|
| `eventweave-runtime run` | Push events to a single sink |
| `eventweave-runtime serve` | Start multiple endpoints and let clients connect |
| `eventweave-runtime bench` | Benchmark throughput |

## Server configuration

Create a YAML file describing each endpoint:

```yaml
servers:
  - id: edr_syslog_tcp
    protocol: syslog_tcp
    bind: 127.0.0.1
    port: 5515
    source_filter:
      source_id: edr-001

  - id: firewall_syslog_udp
    protocol: syslog_udp
    bind: 127.0.0.1
    port: 5514
    source_filter:
      source_id: firewall-001

  - id: edr_http
    protocol: http
    bind: 127.0.0.1
    port: 8081
    path: /events
    encoder: windows-event-json
    source_filter:
      source_id: edr-001

  - id: firewall_syslog_tcp
    protocol: syslog_tcp
    bind: 127.0.0.1
    port: 5516
    encoder: fortinet-fortigate
    enrich: true
    source_filter:
      source_id: firewall-001
```

### Endpoint fields

- `id` — unique endpoint identifier.
- `protocol` — `http`, `syslog_udp`, or `syslog_tcp`.
- `bind` — interface to bind to. Defaults to `127.0.0.1`. Use `0.0.0.0` only with explicit configuration.
- `port` — listener port. Must be `>= 1024`.
- `path` — HTTP path. Defaults to `/events`.
- `encoder` — optional encoder name (e.g. `nginx-access`, `syslog-rfc3164`, `fortinet-fortigate`).
  When set, the endpoint emits encoded output instead of canonical JSON.
- `enrich` — optional. When `true`, apply the encoder's enrichment profile
  before encoding. Can also be enabled globally with `--enrich`.
- `source_filter` — selects events for this endpoint.
  - `source_id` — match `source_id` field.
  - `event_type` — match `event_type` field.

A missing filter field means "match all" for that field.

## Running the server

```bash
eventweave-runtime serve dist/security_lateral_movement \
  --server-config examples/runtime/security_multi_source.yaml
```

Optional flags:

- `--limit` — maximum number of events to serve across all endpoints.
- `--stats-json` — write per-endpoint stats to a JSON file.
- `--enrich` — apply encoder enrichment profiles to all endpoints with an encoder.

## Protocol behavior

### HTTP

Clients open `GET http://<bind>:<port><path>` and receive events as a newline-delimited stream of SSE `data:` frames:

```text
data: {"event_id":"...","event_type":"...",...}

data: {"event_id":"...",...}

```

If the endpoint has an `encoder`, each `data:` payload is the encoder output. For example, an HTTP endpoint configured with `encoder: nginx-access` emits nginx combined log lines.

### Syslog TCP

Clients connect to the TCP port. The server pushes one message per event. By default it wraps the canonical JSON event in an RFC3164-like envelope:

```text
<134>Jun 28 12:00:00 eventweave {"event_id":"...",...}
```

If the endpoint configures a syslog encoder such as `syslog-rfc3164` or
`syslog-rfc5424`, the encoder output is sent directly (no double wrapping).
Non-syslog encoders are wrapped in the same RFC3164-like envelope.

### Syslog UDP

The server listens on the UDP port. Clients must first send any datagram to that port so the server learns their address. After registration, the server forwards messages to all registered clients using the same encoding rules as Syslog TCP.

## Safety defaults

- Endpoints bind to `127.0.0.1` by default.
- Binding to `0.0.0.0` is allowed but triggers a validation warning because it exposes the server externally.
- Privileged ports `< 1024` are rejected.
- Duplicate `bind:port` combinations are rejected before any listener starts.

## Stats

The server prints aggregate and per-endpoint counters when it finishes:

```text
Server finished
Events loaded: 1200
Endpoints active: 3
  edr_syslog_tcp: emitted=400 failed=0
  firewall_syslog_udp: emitted=400 failed=0
  edr_http: emitted=400 failed=0
```

## Demo stack

A runnable multi-source example is included in the demo stack:

```bash
make demo-stack
```

It uses `examples/demo-stack/security_multi_source.yaml` to expose firewall,
edr, waf, and dns sources over Syslog and HTTP, with receiver containers and
Grafana dashboards. See [docs/demo-stack.md](demo-stack.md).

## Current limitations

- Kafka, gRPC, MQTT, or WebSocket endpoints.
- TLS or authentication.
- Stateful per-client session simulation.
- Inter-event timing control in serve mode.
