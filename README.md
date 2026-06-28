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

# Inspect generated semantic assets
eventweave semantic inspect dist/ecommerce_refund_flow_semantic/semantic_pool.json

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

Current version: **v0.2** — AI Semantic Sidecar

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
- Placeholder `semantic_refs` injected into `event_plan.jsonl`

What is planned:

- v0.2: AI Semantic Sidecar
- v0.3: Python Local Runtime
- v0.4: Go High-Performance Runtime
- v0.5: Pack Ecosystem
- v0.6: Agent Evaluation Harness

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
