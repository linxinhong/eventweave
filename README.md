# EventWeave

> AI-assisted synthetic event streams from scenarios, rules, and timelines.

[![CI](https://github.com/eventweave/eventweave/actions/workflows/ci.yml/badge.svg)](https://github.com/eventweave/eventweave/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Generate event flows, not just fake rows.

EventWeave turns scenario files and natural language descriptions into realistic, rule-aware, time-aware synthetic event streams.

---

## What it can generate

- application logs
- API events
- audit records
- security telemetry
- user behavior
- order flows
- device telemetry
- workflow events
- operational alerts
- agent evaluation datasets

## Why EventWeave?

Most mock data tools generate static records.

EventWeave generates coherent event flows with:

- entities
- relationships
- timelines
- state changes
- background noise
- delayed events
- out-of-order events
- semantic context
- ground truth

---

## Quick start

```bash
# Clone and install
git clone https://github.com/eventweave/eventweave.git
cd eventweave
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run checks
make check

# Validate a scenario
eventweave validate examples/ecommerce/refund.yaml

# Compile a scenario into a runtime plan
eventweave compile examples/ecommerce/refund.yaml -o dist

# Generate semantic assets for the semantic-enabled example
eventweave semantic generate dist/ecommerce_refund_flow_semantic --provider template

# Generate semantic assets with a Chat Completions compatible AI (e.g. Kimi)
export EVENTWEAVE_AI_BASE_URL=https://api.moonshot.cn/v1
export EVENTWEAVE_AI_API_KEY=your-kimi-api-key
export EVENTWEAVE_AI_MODEL=moonshot-v1-8k
eventweave semantic generate dist/ecommerce_refund_flow_semantic --provider ai

# Inspect generated semantic assets
eventweave semantic inspect dist/ecommerce_refund_flow_semantic/semantic_pool.json

# Run the resolved event plan through the local runtime
eventweave run dist/ecommerce_refund_flow_semantic --sink file --output out/events.jsonl --no-wait

# Or replay to stdout with 10x time acceleration
eventweave run dist/ecommerce_refund_flow_semantic --sink stdout --speed 10

# Dry-run to count events without emitting
eventweave run dist/ecommerce_refund_flow_semantic --dry-run

# Emit only the first 5 events
eventweave run dist/ecommerce_refund_flow_semantic --sink stdout --limit 5

# Stream events to a local HTTP receiver
python examples/receivers/http_receiver.py &
eventweave run dist/ecommerce_refund_flow_semantic \
  --sink http --url http://127.0.0.1:8080/events --no-wait

# List and inspect domain packs
eventweave pack list
eventweave pack inspect ecommerce
eventweave pack validate ecommerce

# Scaffold a new domain pack
eventweave pack scaffold mydomain
eventweave pack validate mydomain
eventweave compile packs/mydomain/examples/basic.yaml -o dist

# Reference a pack realism profile in a scenario
# (configure in packs/<domain>/realism/profiles.yaml)
eventweave validate examples/security/lateral_movement.yaml
eventweave compile examples/security/lateral_movement.yaml -o dist

# Or use the high-performance Go runtime
cd runtime-go
go run ./cmd/eventweave-runtime run ../dist/ecommerce_refund_flow_semantic \
  --sink file --output ../out/events.jsonl --no-wait

# Go runtime: stream to Kafka
go run ./cmd/eventweave-runtime run ../dist/ecommerce_refund_flow_semantic \
  --sink kafka --brokers localhost:9092 --topic events --no-wait

# Go runtime: stream to Syslog
go run ./cmd/eventweave-runtime run ../dist/ecommerce_refund_flow_semantic \
  --sink syslog --syslog-addr 127.0.0.1:514 --syslog-proto udp --no-wait

# Go runtime: rate-limited replay (1000 events/sec)
go run ./cmd/eventweave-runtime run ../dist/security_lateral_movement \
  --sink null --rate 1000 --limit 10000

# Go runtime: benchmark throughput
go run ./cmd/eventweave-runtime bench ../dist/ecommerce_refund_flow_semantic \
  --sink null --limit 100000

# Go runtime: write stats to JSON
go run ./cmd/eventweave-runtime run ../dist/ecommerce_refund_flow_semantic \
  --sink file --output ../out/events.jsonl --no-wait \
  --stats-json ../out/stats.json

# Go runtime: serve events over multiple protocol endpoints
cd runtime-go
go run ./cmd/eventweave-runtime serve ../dist/security_lateral_movement \
  --server-config ../examples/runtime/security_multi_source.yaml \
  --limit 100
# In another terminal:
# curl http://127.0.0.1:8081/events
# nc -l 127.0.0.1 5515  # for syslog_tcp
# nc -u -l 127.0.0.1 5514  # for syslog_udp (send any packet first)

# Compile a scenario with ground truth and evaluate a sample agent output
eventweave compile examples/security/lateral_movement.yaml -o dist
# Prepare evaluation artifacts (ground truth, runtime plan, event plan)
eventweave eval prepare examples/security/lateral_movement.yaml
eventweave eval task dist/security_lateral_movement -o dist/security_lateral_movement/eval/task.json
eventweave eval validate-output examples/evaluation/security_lateral_movement_agent_output.json
eventweave eval run \
  --ground-truth dist/security_lateral_movement/ground_truth.json \
  --agent-output examples/evaluation/security_lateral_movement_agent_output.json \
  --output report.json

# Run a multi-scenario benchmark suite and compare agents
eventweave benchmark list
eventweave benchmark run \
  --suite benchmarks/security.yaml \
  --agent-outputs examples/evaluation/ \
  --output scorecards/security.json
# Validate a benchmark suite and its sample data before running it
eventweave benchmark validate --suite benchmarks/security.yaml

# Generate a validation report JSON
eventweave benchmark validate \
  --suite benchmarks/security.yaml \
  --output validation/security.json

# Validate with realism gates (requires noise/jitter in scenarios)
eventweave benchmark validate \
  --suite benchmarks/security.yaml \
  --min-noise-ratio 0.5 \
  --min-event-types 6 \
  --min-sources 3 \
  --require-jitter

eventweave benchmark leaderboard scorecards/security.json

# Compare multiple agents on the same suite
eventweave benchmark run \
  --suite benchmarks/security.yaml \
  --agent-outputs agents/gpt-4o/ \
  --agent-outputs agents/claude-sonnet/ \
  --output scorecards/security.json

# Start the local observability demo stack
make demo-stack

# Generate a synthetic realism report for a compiled plan
eventweave quality realism dist/security_lateral_movement
eventweave quality realism dist/security_lateral_movement --output realism.json

# Export events as JSONL
eventweave export dist/ecommerce_refund_flow --format jsonl --output out/events.jsonl

# Encode events as vendor/log formats
eventweave encode run dist/security_lateral_movement \
  --encoder syslog-rfc3164 \
  --output out/syslog.log

# Use enrichment to auto-fill missing encoder fields
eventweave encode run dist/security_lateral_movement \
  --encoder fortinet-fortigate \
  --enrich \
  --output out/fortigate.log

# Compare encodability with and without enrichment
eventweave encode preflight dist/security_lateral_movement \
  --encoder fortinet-fortigate \
  --enrich \
  --compare-enrichment

eventweave run dist/security_lateral_movement \
  --sink file \
  --output out/suricata.jsonl \
  --encoder suricata-eve \
  --no-wait

eventweave-runtime run dist/security_lateral_movement \
  --sink syslog \
  --syslog-addr 127.0.0.1:5514 \
  --encoder syslog-rfc3164 \
  --no-wait
```

---

## Example scenario

```yaml
id: ecommerce_refund_flow
name: E-commerce refund flow
domain: ecommerce
for_each: order
duration: 30m
seed: 20260628

entities:
  customer:
    count: 100
  order:
    count: 200
  payment:
    count: 200

sources:
  - id: order-service
    type: service
    role: order_service
    rate:
      base_qps: 100
      burst_qps: 800
      jitter: 0.1

timeline:
  - id: create_order
    at: "00:00:00"
    event: order.created
    source: order-service
    entity_refs:
      order: "$flow"
      customer: "$entity.customer"

  - id: pay_order
    after: create_order
    delay: "1m..5m"
    event: order.paid
    source: order-service
    entity_refs:
      order: "$ref.create_order.order"
      payment: "$new.payment"

  - id: request_refund
    after: pay_order
    delay: "5m..20m"
    probability: 0.2
    event: refund.requested
    source: order-service
    entity_refs:
      order: "$ref.create_order.order"
      refund: "$new.refund"

rules:
  - id: order_must_be_paid_before_refund
    type: event_after
    event: refund.requested
    after: order.paid
    scope: order
```

---

## Example output

`eventweave compile` produces canonical events in `dist/<scenario>/event_plan.jsonl`:

```json
{
  "event_id": "evt-ecommerce-refund-flow-001-001",
  "scenario_id": "ecommerce_refund_flow",
  "flow_id": "order_001",
  "source_id": "order-service",
  "event_type": "order.created",
  "event_time": "2026-06-28T10:00:00+00:00",
  "entity_refs": {
    "flow": "order_001",
    "order": "order_001",
    "customer": "customer_042"
  },
  "attributes": {
    "amount": 299.0,
    "currency": "CNY"
  },
  "semantic_refs": [],
  "labels": [],
  "ground_truth": {
    "is_key_event": true
  }
}
```

## Semantic output sample

After running `eventweave semantic generate`, `semantic_pool.json` contains
validated text assets:

```json
{
  "scenario_id": "ecommerce_refund_flow_semantic",
  "assets": [
    {
      "id": "request_refund_2-mock-evt-ecommerce-refund-flow-semantic-006-003-0",
      "type": "refund.reason",
      "text": "[refund.reason] Mock semantic content for task request_refund_2.",
      "meta": {
        "provider": "mock",
        "source_task": "request_refund_2",
        "source_event": "evt-ecommerce-refund-flow-semantic-006-003",
        "review_status": "approved"
      }
    }
  ]
}
```

The matching event in `event_plan.jsonl` now references the concrete asset id:

```json
{
  "event_id": "evt-ecommerce-refund-flow-semantic-006-003",
  "event_type": "refund.requested",
  "semantic_refs": [
    "request_refund_2-mock-evt-ecommerce-refund-flow-semantic-006-003-0"
  ]
}
```

---

## Core concepts

| Concept | Description |
|---------|-------------|
| **Scenario** | What happens: a declarative description of an event flow. |
| **Entity** | Objects that participate in the scenario: users, orders, hosts, etc. |
| **Relation** | Associations between entities. |
| **Timeline** | Scenario-level event template with timing, probability, and refs. |
| **Rule** | Declarative constraint that the generated events must satisfy. |
| **Source** | A simulated emitter with rate, time policy, and output targets. |
| **Pack** | Domain-specific extension: entities, events, rules, examples. |
| **Ground Truth** | Expected findings for agent evaluation. |

---

## Project status

Current version: **v0.9.0** — Vendor Log Encoders

What works:

- YAML/JSON scenario definitions
- A-lite pack loader (`pack.yaml`, `entities/`, `events/`, `rules.yaml`)
- Scenario compiler (`validate`, `compile`, `export`, `inspect`)
- Declarative rules (`required_entity_ref`, `event_after`, `field_required`, `field_enum`)
- Deterministic output with `--seed`
- JSONL exporter
- Makefile and GitHub Actions CI
- Semantic task and asset models (`SemanticTask`, `SemanticAsset`, `SemanticPool`)
- Offline providers (`mock`, `template`) with swappable `Provider` interface
- File-based semantic asset cache and validator
- CLI `semantic generate` and `semantic inspect`
- Placeholder `semantic_refs` resolved to concrete asset ids in `event_plan.jsonl`
- Python Local Runtime with `stdout`, `file`, `http`, and `null` sinks
- Time acceleration (`--speed`), immediate replay (`--no-wait`), and `--limit`
- Runtime stats and unresolved semantic ref warnings
- Go runtime MVP in `runtime-go/` with compatible CLI and sinks
- Go runtime reads the same `event_plan.jsonl` produced by Python compiler
- Go runtime Kafka sink with configurable brokers, topic, and message key
- Go runtime Syslog sink over UDP/TCP with configurable facility, severity, and tag
- Go runtime `--rate` for fixed EPS replay
- Go runtime `bench` sub-command for throughput testing
- Go runtime `--stats-json` and `--max-failures`
- Pack ecosystem with `eventweave pack list / inspect / validate`
- Formal pack manifest, local registry, and pack validation
- Self-contained pack examples under `packs/<domain>/examples/`
- `eventweave pack scaffold` for quick pack creation
- Generic `ai` provider for Chat Completions compatible APIs (Kimi, DeepSeek,
  Qwen, Ollama, etc.) with environment-variable credentials
- v0.6.0: Agent Evaluation Harness with ground truth, `AgentOutput` schema,
  deterministic evaluator, and `eventweave eval task / run`
- v0.6.1: Precision metrics, `matched/missed/extra` finding details,
  `eventweave eval validate-output`, and sample agent output
- v0.6.2: Multi-source / multi-port Go runtime server with HTTP and Syslog
  endpoints via `eventweave-runtime serve`
- v0.7.0: Multi-scenario benchmark suites, scorecards, and local leaderboard
  via `eventweave benchmark list / run / leaderboard`
- v0.7.1: Go runtime observability with Prometheus metrics and `/healthz`
- v0.7.2: Kafka batching and worker pool for high-throughput kafka/http sinks
- v0.7.3: Expanded benchmark suites with 3 new security and 2 new e-commerce
  scenarios, plus `eventweave benchmark validate` dataset quality gate
- v0.7.4: Local observability demo stack with Redpanda, Prometheus, Grafana,
  multi-source runtime receivers, and a starter dashboard
- v0.8.0: Synthetic realism tools — background noise, time jitter, and
  `eventweave quality realism` reports
- v0.8.1: Benchmark realism gates — optional `--min-noise-ratio`,
  `--min-event-types`, `--min-sources`, `--max-burstiness`, and
  `--require-jitter` thresholds on `eventweave benchmark validate`
- v0.8.2: Pack realism profiles — reusable `noise:` / `jitter:` templates in
  `packs/<domain>/realism/profiles.yaml`, referenced by scenarios via
  `realism_profile: <pack>.<profile>`
- v0.8.4 / v0.8.5: Security, evaluation, and runtime hardening — sink SSRF/path-traversal
  protection, CLI command split, evaluation decoupled from runtime compilation
  with `eventweave eval prepare`, HTTP retry governance, AI cache key
  collision fix, lazy metrics registration, Go config upper bounds, and an
  anomalous Prometheus dependency removed
- v0.9.0: Vendor log encoders — emit canonical events as `syslog-rfc3164`,
  `syslog-rfc5424`, `nginx-access`, `suricata-eve`, and `windows-event-json`
  via `eventweave encode` / `eventweave-runtime --encoder`
- v0.9.1: Additional vendor encoders (Fortinet, Palo Alto, Zeek, DNS)
- v0.9.2: Encoder metadata, `encode inspect`, `encode preflight`, and pack
  encoder mapping
- v0.9.3: Per-endpoint encoders for `eventweave-runtime serve`
- v0.9.4: Encoder field enrichment / auto-fill profiles via
  `--enrich` and pack `encoders/enrichment.yaml`
- v0.9.5: Pre-v1 hardening sweep — core model tests, CLI smoke tests, stub pack
  fill, `encode inspect` fix, SSRF warning, and `docs/security.md`
- v0.9.6: Python / Go runtime HTTP sink SSRF parity
- v0.9.7: Pack schema validation — `eventweave validate/compile --strict-schema`,
  default warning mode, event/entity field and entity-ref checks
- v0.9.8: Golden baseline workflow — `make golden-check` / `make golden-update`,
  `docs/golden-baseline.md`, and refreshed golden snapshots

What is planned:

- v0.9.9: API compatibility audit
- v1.0: API stabilization and release polish

## Security

EventWeave includes sink-level safeguards against SSRF and path traversal:

- The `http` sink rejects loopback, private, link-local, multicast, and reserved
  addresses in both the Python and Go runtimes. Go also resolves hostnames and
  rejects URLs that resolve to internal IPs.
- HTTP redirects are disabled for the `http` sink.
- The `file` sink refuses paths that escape `--output-dir`.
- `--allow-internal-url` disables these protections and prints a warning; use it
  only in trusted local/test environments.

See [docs/security.md](docs/security.md) for details.

## Pack Ecosystem

EventWeave is extensible through **packs**. A pack defines entities, events,
rules, semantic templates, and examples for a domain.

```text
packs/<domain>/
├── pack.yaml
├── entities/
├── events/
├── rules.yaml
├── semantic/          # optional
└── examples/          # optional but recommended
```

Use the pack CLI:

```bash
eventweave pack list
eventweave pack inspect ecommerce
eventweave pack validate ecommerce
```

See [docs/pack-spec.md](docs/pack-spec.md) for the manifest specification and
[docs/pack-authoring.md](docs/pack-authoring.md) for a step-by-step authoring
guide.

---

See [docs/design.md](docs/design.md) for the full design and roadmap.

---

## Development

```bash
make test       # pytest
make lint       # ruff check
make typecheck  # mypy
make check      # lint + typecheck + test
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT. See [LICENSE](LICENSE).
