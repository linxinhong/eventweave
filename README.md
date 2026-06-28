# EventWeave

> AI-assisted synthetic event streams from scenarios, rules, and timelines.

Generate event flows, not just fake rows.

EventWeave turns scenario files and natural language descriptions into realistic, rule-aware, time-aware synthetic event streams.

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

## Install

```bash
pip install eventweave
```

## Quick start

```bash
# Validate a scenario
eventweave validate examples/ecommerce/refund.yaml

# Compile a scenario into a runtime plan
eventweave compile examples/ecommerce/refund.yaml -o dist/ecommerce_refund

# Export events as JSONL
eventweave export dist/ecommerce_refund --format jsonl --output out/ecommerce_refund.jsonl
```

## Documentation

- [docs/design.md](docs/design.md)
- [AGENTS.md](AGENTS.md)

## License

Apache-2.0
