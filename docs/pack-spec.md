# Pack Specification

Packs are domain-specific extensions for EventWeave. The core framework remains domain-agnostic; packs provide entity schemas, event schemas, and declarative rules.

## Pack layout (v0.1 A-lite)

```text
packs/<domain>/
├── pack.yaml
├── entities/
│   ├── customer.yaml
│   └── order.yaml
├── events/
│   ├── order.yaml
│   └── refund.yaml
└── rules.yaml
```

## pack.yaml

```yaml
id: ecommerce
name: E-commerce
version: "1.0"
depends_on:
  - common
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Pack identifier, must match directory name. |
| `name` | string | Human-readable name. |
| `version` | string | Pack version. |
| `depends_on` | list | Other packs this pack depends on. |

## Entity schemas

`entities/<type>.yaml`:

```yaml
customer:
  description: An e-commerce customer.
  fields:
    name:
      type: string
    email:
      type: string
      format: email
    tier:
      type: string
      enum:
        - regular
        - vip
```

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Human-readable description. |
| `fields` | map | Field name -> field schema. |
| `refs` | map | Role -> entity type this entity can reference. |

### Field schema

```yaml
name:
  type: string
  description: Display name.
  required: true

tier:
  type: string
  enum:
    - regular
    - vip
  default: regular
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | JSON Schema type: `string`, `number`, `integer`, `boolean`. |
| `format` | string | Optional format hint: `email`, `ipv4`. |
| `enum` | list | Allowed values. |
| `default` | any | Default value. |
| `description` | string | Description. |
| `required` | boolean | Whether the field is required. |

## Event schemas

`events/<group>.yaml`:

```yaml
order.created:
  description: A new order is created.
  entity_refs:
    customer: customer
    order: order
  fields:
    amount:
      type: number
    currency:
      type: string
```

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Human-readable description. |
| `entity_refs` | map | Role -> expected entity type. |
| `fields` | map | Event attribute schemas. |

## Rules

`rules.yaml`:

```yaml
rules:
  - id: order_must_be_paid_before_refund
    type: event_after
    description: Refund cannot be requested before order is paid.
    attributes:
      event: refund.requested
      after: order.paid
      scope: order

  - id: ticket_must_reference_existing_order
    type: required_entity_ref
    description: Ticket must reference an existing order.
    attributes:
      event: ticket.created
      ref: order
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique rule id. |
| `type` | string | Rule type. |
| `description` | string | Human-readable description. |
| `attributes` | map | Rule-specific parameters. |

## v0.1 limitations

- No dynamic Python rule plugins.
- No pack registry or marketplace.
- No pack version resolution.
- Pack schemas are informational; v0.1 does not enforce strict JSON Schema validation.

## Future extensions

- `semantic/` directory for prompt templates and text assets.
- `encoders/` directory for domain-specific output formats.
- `examples/` directory for pack-specific scenarios.
- `tests/` directory for pack tests.
