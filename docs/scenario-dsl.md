# Scenario DSL

EventWeave scenarios are written in YAML or JSON. A scenario describes:

- what entities exist
- what sources emit events
- the timeline of events
- rules that must hold

## Minimal example

```yaml
id: ecommerce_refund_flow
name: E-commerce refund flow
domain: ecommerce
duration: 30m
seed: 20260628

entities:
  customer:
    count: 100

  order:
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
  - at: "00:00:00"
    event: order.created
    source: order-service

  - after: order.created
    delay: "1m..5m"
    event: order.paid
    source: order-service

  - after: order.paid
    delay: "5m..20m"
    probability: 0.2
    event: refund.requested
    source: order-service

rules:
  - id: order_must_be_paid_before_refund
    type: event_after
    event: refund.requested
    after: order.paid
    scope: order
```

## Top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique scenario identifier. |
| `name` | string | no | Human-readable name. |
| `domain` | string | yes | Domain pack to load. |
| `version` | string | no | DSL version. Default `1.0`. |
| `duration` | string | no | Scenario duration, e.g. `30m`, `1h`. |
| `seed` | integer | no | Random seed for deterministic output. |
| `entities` | map | no | Entity templates to generate. |
| `sources` | list | no | Simulated event sources. |
| `timeline` | list | no | Scenario-level event timeline template. |
| `rules` | list | no | Declarative rules. |

## Entities

```yaml
entities:
  customer:
    count: 100
    type: customer
    attributes:
      tier: regular
    tags:
      - demo
```

| Field | Type | Description |
|-------|------|-------------|
| `count` | integer | Number of instances to generate. |
| `type` | string | Entity type. Defaults to the map key. |
| `attributes` | map | Default attributes for every instance. |
| `tags` | list | Tags for every instance. |

## Sources

```yaml
sources:
  - id: order-service
    type: service
    role: order_service
    rate:
      base_qps: 100
      burst_qps: 800
      jitter: 0.1
    time_policy:
      mode: realtime
    outputs:
      - type: jsonl
        path: ./out/orders.jsonl
```

## Timeline

Each timeline item describes one event in the scenario flow.

```yaml
timeline:
  - at: "00:00:00"
    event: order.created
    source: order-service

  - after: order.created
    delay: "1m..5m"
    event: order.paid
    source: order-service
```

| Field | Type | Description |
|-------|------|-------------|
| `event` | string | Event type. Required. |
| `source` | string | Source id that emits the event. |
| `at` | string | Absolute offset from scenario start, e.g. `00:01:30`. |
| `after` | string | Preceding event type. |
| `delay` | string | Delay after `after`. Supports ranges like `1m..5m`. |
| `probability` | float | Chance to emit this item. Default `1.0`. |
| `entity_refs` | map | Role -> entity reference spec. |
| `attributes` | map | Static event attributes. |
| `labels` | list | Event labels. |

### Entity reference specs

| Spec | Meaning |
|------|---------|
| `primary` | The current flow's primary entity. |
| `customer` | A random entity of type `customer`. |
| `order.created.order` | The `order` ref from the previous `order.created` event in the same flow. |

## Rules

Rules are declarative constraints validated after timeline expansion.

```yaml
rules:
  - id: order_must_be_paid_before_refund
    type: event_after
    event: refund.requested
    after: order.paid
    scope: order

  - id: ticket_must_reference_existing_order
    type: required_entity_ref
    event: ticket.created
    ref: order
```

Supported rule types in v0.1:

- `required_entity_ref`
- `event_after`
- `field_required`
- `field_enum`

## Time formats

- `1h30m10s`
- `5m`
- `30s`
- `00:01:30`

## CLI usage

```bash
eventweave validate examples/ecommerce/refund.yaml
eventweave compile examples/ecommerce/refund.yaml -o dist
eventweave export dist/ecommerce_refund_flow --format jsonl --output out/events.jsonl
```
