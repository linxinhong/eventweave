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
for_each: order
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

## Top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique scenario identifier. |
| `name` | string | no | Human-readable name. |
| `domain` | string | yes | Domain pack to load. |
| `version` | string | no | DSL version. Default `1.0`. |
| `for_each` | string | recommended | Primary entity type that defines a flow. |
| `duration` | string | no | Scenario duration, e.g. `30m`, `1h`. |
| `seed` | integer | no | Random seed for deterministic output. |
| `entities` | map | no | Entity templates to generate. |
| `sources` | list | no | Simulated event sources. |
| `timeline` | list | no | Scenario-level event timeline template. |
| `rules` | list | no | Declarative rules. |

## `for_each`

`for_each` declares the primary entity type for flow expansion. The compiler creates one flow per instance of this type.

```yaml
for_each: order
```

If `for_each` is omitted, the compiler infers it from the first timeline event type (e.g. `order.created` -> `order`) and emits a warning.

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

Each timeline item describes one step in the scenario flow.

```yaml
timeline:
  - id: create_order
    at: "00:00:00"
    event: order.created
    source: order-service
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Step id used for `$ref` references. Defaults to `event`. |
| `event` | string | Event type. Required. |
| `source` | string | Source id that emits the event. |
| `at` | string | Absolute offset from scenario start, e.g. `00:01:30`. |
| `after` | string | Preceding step id or event type. |
| `delay` | string | Delay after `after`. Supports ranges like `1m..5m`. |
| `probability` | float | Chance to emit this item. Default `1.0`. |
| `entity_refs` | map | Role -> entity reference spec. |
| `attributes` | map | Static event attributes. |
| `labels` | list | Event labels. |

### Entity reference specs

| Spec | Meaning |
|------|---------|
| `$flow` | The current flow's primary entity. |
| `$entity.<type>` | Pick a random entity of `<type>` from the scenario pool. |
| `$new.<type>` | Create a new entity of `<type>` for this flow. |
| `$ref.<step_id>.<role>` | Reference `<role>` from a previous timeline step in the same flow. |

Example:

```yaml
timeline:
  - id: create_order
    event: order.created
    entity_refs:
      order: "$flow"
      customer: "$entity.customer"

  - id: pay_order
    after: create_order
    event: order.paid
    entity_refs:
      order: "$ref.create_order.order"
      customer: "$ref.create_order.customer"
      payment: "$new.payment"
```

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

By default rule violations are reported as warnings. Use `--strict` to treat them as errors.

## Background noise

Add normal background events around the ground-truth timeline:

```yaml
noise:
  enabled: true
  ratio: 5.0
  events:
    - event: user.login.success
      weight: 5
    - event: dns.query
      weight: 10
```

- `ratio` — noise events per timeline event.
- `events` — templates with relative `weight`.
- Noise events are tagged `ground_truth.noise: true`.

## Time jitter

Perturb timestamps deterministically:

```yaml
jitter:
  enabled: true
  max_offset: 10s
  preserve_order: true
```

Override jitter for a single step:

```yaml
timeline:
  - id: alert_triggered
    event: alert.triggered
    jitter: 2s
```

## Time formats

- `1h30m10s`
- `5m`
- `30s`
- `00:01:30`

## CLI usage

```bash
# Validate a scenario
eventweave validate examples/ecommerce/refund.yaml

# Validate in strict mode
eventweave validate examples/ecommerce/refund.yaml --strict

# Compile a scenario
eventweave compile examples/ecommerce/refund.yaml -o dist

# Compile in strict mode
eventweave compile examples/ecommerce/refund.yaml -o dist --strict

# Export events as JSONL
eventweave export dist/ecommerce_refund_flow --format jsonl --output out/events.jsonl
```
