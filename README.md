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

# Compile a scenario with ground truth and evaluate a sample agent output
eventweave compile examples/security/lateral_movement.yaml -o dist
eventweave eval task dist/security_lateral_movement -o dist/security_lateral_movement/eval/task.json
eventweave eval validate-output examples/evaluation/security_lateral_movement_agent_output.json
eventweave eval run \
  --ground-truth dist/security_lateral_movement/ground_truth.json \
  --agent-output examples/evaluation/security_lateral_movement_agent_output.json \
  --output report.json

# Export events as JSONL
eventweave export dist/ecommerce_refund_flow --format jsonl --output out/events.jsonl
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

Current version: **v0.6.1** — Evaluation Polish

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

What is planned:

- v0.7: Dataset Suites / Benchmark Packs
- v0.7.x: Prometheus metrics and Kafka batching

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
