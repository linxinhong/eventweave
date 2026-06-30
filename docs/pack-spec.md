# Pack Specification

Packs are domain-specific extensions for EventWeave. The core framework remains
domain-agnostic; packs provide entity schemas, event schemas, declarative rules,
and runnable examples.

## Pack layout (v0.5)

```text
packs/<domain>/
├── pack.yaml
├── entities/
│   ├── customer.yaml
│   └── order.yaml
├── events/
│   ├── order.yaml
│   └── refund.yaml
├── rules.yaml
├── encoders/          # optional
│   ├── __init__.py
│   └── enrichment.yaml
├── semantic/          # optional
├── realism/           # optional
│   └── profiles.yaml
└── examples/          # optional but recommended
    └── refund.yaml
```

## pack.yaml

```yaml
id: ecommerce
name: E-commerce
version: "1.0"
description: Orders, payments, refunds, and tickets.
depends_on:
  - common
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Pack identifier, should match directory name. |
| `name` | string | yes | Human-readable name. |
| `version` | string | yes | Pack version. |
| `description` | string | no | Short description of the domain. |
| `depends_on` | list | no | Other packs this pack depends on. |
| `entities_path` | string | no | Path to entity schemas (default `entities`). |
| `events_path` | string | no | Path to event schemas (default `events`). |
| `rules_path` | string | no | Path to rules file (default `rules.yaml`). |
| `semantic_path` | string | no | Path to semantic templates (default `semantic`). Use `""` to disable. |
| `realism_path` | string | no | Path to realism profiles (default `realism`). Use `""` to disable. |
| `examples_path` | string | no | Path to examples (default `examples`). Use `""` to disable. |
| `encoders` | list | no | Recommended encoder mapping for this pack (see below). |

### Encoder mapping

A pack can declare which encoders are recommended for its event types:

```yaml
encoders:
  - name: fortinet-fortigate
    description: FortiGate traffic log format
    required_fields:
      - devname
      - type
      - subtype
      - srcip
      - dstip
      - action
    supported_event_types:
      - network.lateral_connection
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Encoder name, must be registered globally. |
| `description` | string | Short description. |
| `required_fields` | list | Fields required by this encoder. |
| `supported_event_types` | list | Event types from this pack that the encoder handles. |

`eventweave pack validate` checks that the encoder is registered and that each
`supported_event_type` exists in the pack.

## Encoder enrichment profiles

Packs may provide `encoders/enrichment.yaml` to auto-fill missing encoder fields:

```yaml
profiles:
  fortinet-fortigate:
    description: FortiGate traffic log enrichment.
    defaults:
      devname: firewall-01
      type: traffic
      subtype: forward
      action: accept
      srcip: 10.0.0.1
      dstip: 10.0.0.2
    mappings:
      srcip: src_ip
      dstip: dest_ip
      srcport: src_port
      dstport: dest_port
      proto: protocol
```

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Short description. |
| `defaults` | map | Default values applied when a field is missing. |
| `mappings` | map | `target_field: source_field` copies applied when target is missing. |

Enrichment is deterministic and does not modify the canonical event. Values are
applied with this priority:

1. Existing target attribute.
2. Mapped source attribute.
3. Default value.

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

### Supported rule types

- `required_entity_ref` — event must reference an entity role.
- `event_after` — event must occur after another event in the same flow.
- `field_required` — event must contain a field.
- `field_enum` — field value must be in allowed set.

## Realism profiles

Packs may define reusable background-noise and time-jitter templates in
`realism/profiles.yaml`:

```text
packs/<domain>/
├── realism/
│   └── profiles.yaml
```

```yaml
profiles:
  endpoint_background:
    description: Background endpoint noise for security scenarios.
    noise:
      enabled: true
      ratio: 5
      events:
        - event: dns.query
          weight: 10
        - event: user.login.success
          weight: 5
    jitter:
      enabled: true
      max_offset: 10s
      preserve_order: true
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Profile identifier unique within the pack. |
| `description` | string | Human-readable description. |
| `noise` | object | Background noise configuration. |
| `jitter` | object | Timestamp jitter configuration. |

Scenarios reference a profile with:

```yaml
realism_profile: security.endpoint_background
```

or the explicit block form:

```yaml
realism:
  profile: security.endpoint_background
  noise:
    ratio: 8
  jitter:
    max_offset: 15s
```

Profile refs use `[<pack>.]<profile_id>`. Without a pack prefix the compiler
looks in the scenario's own domain pack, then its declared dependencies.
Scenario-level `noise:` / `jitter:` still take precedence for backward
compatibility.

## Pack dependencies

A pack can declare dependencies in `pack.yaml`:

```yaml
depends_on:
  - common
```

The compiler loads dependencies recursively. The `common` pack provides shared
entity types such as `user` and `device`.

## Examples

Packs may include runnable scenarios in `examples/`:

```text
packs/ecommerce/examples/refund.yaml
```

Examples are validated by `eventweave pack validate <id>` to ensure they still
compile against the current pack schemas.

## Schema validation

Starting with v0.9.7, EventWeave validates compiled events and entities against
the schemas declared in their domain packs. Schema mismatches are emitted as
**warnings** by default so existing scenarios keep compiling.

Use `--strict-schema` to upgrade schema violations to errors:

```bash
eventweave validate examples/ecommerce/refund.yaml --strict-schema
eventweave compile examples/ecommerce/refund.yaml -o dist --strict-schema
```

Validation covers:

- Event `event_type` exists in the scenario's pack or its dependencies.
- Required event fields are present.
- Event field types match `string`, `number`, `integer`, or `boolean`.
- Event `enum` values are respected.
- `format: email` and `format: ipv4` values are syntactically valid.
- Event `entity_refs` roles are declared in the event schema and point to
  entities of the expected type.
- Entity types exist and required entity fields are present.

Unknown event attributes are allowed by default (warning) so that encoder-
specific and enrichment fields do not break compilation.

## Validation

Run pack validation with:

```bash
eventweave pack validate ecommerce
```

Validation checks:

- `pack.yaml` exists and parses.
- Required fields (`id`, `name`, `version`) are present.
- `id` matches the directory name (warning otherwise).
- All `depends_on` packs exist.
- `entities/` directory exists.
- `events/` directory exists (warning if missing).
- `rules.yaml` exists and has a top-level `rules` list (warning if missing).
- `realism/profiles.yaml` parses if present.
- Each entity and event schema has a `type` matching its key.
- Event `entity_refs` point to known entity types in the pack or its dependencies.
- Every example scenario compiles successfully and passes schema validation.
- Encoder mappings in `pack.yaml` reference registered encoders and known event types.

## Current limitations

- No dynamic Python rule plugins.
- No remote pack marketplace.
- No pack version resolution or semver constraints.
- Schema validation covers primitive types, required fields, enums, formats, and
  entity-ref existence; it is not a full JSON Schema engine.

## Future extensions

- Remote pack registry and `eventweave pack install`.
- Semantic dependency resolution.
- Per-event dynamic encoder routing in `eventweave-runtime serve`.
- `tests/` directory for pack-level tests.
