# Pack Authoring Guide

This guide explains how to create a domain pack for EventWeave.

## What is a pack?

A pack is a self-contained domain extension that lives in `packs/<domain>/`.
It defines:

- entity schemas
- event schemas
- declarative rules
- optional semantic templates
- runnable examples

Packs make EventWeave reusable across domains such as e-commerce, security,
IoT, SaaS, and healthcare.

## Create a new pack

```bash
cd packs
mkdir mydomain
cd mydomain
cat > pack.yaml <<EOF
id: mydomain
name: My Domain
version: "0.1.0"
description: Example domain pack for EventWeave.
depends_on:
  - common
EOF

mkdir entities events examples
```

## Define entity schemas

Create `entities/user.yaml`:

```yaml
user:
  description: A user in the domain.
  fields:
    name:
      type: string
    email:
      type: string
      format: email
    tier:
      type: string
      enum:
        - free
        - paid
      default: free
```

The top-level key (`user`) is the entity type. It must match the `type` field
added by the loader, so you can omit `type` in the YAML.

## Define event schemas

Create `events/session.yaml`:

```yaml
session.started:
  description: A user session starts.
  entity_refs:
    user: user
  fields:
    ip:
      type: string
      format: ipv4
```

Event types often use a dotted namespace (`domain.action`). The top-level key
must match the `type` field.

## Add rules

Create `rules.yaml`:

```yaml
rules:
  - id: session_requires_user
    type: required_entity_ref
    description: session.started must reference a user.
    attributes:
      event: session.started
      ref: user
```

## Add an example scenario

Create `examples/welcome_flow.yaml`:

```yaml
id: mydomain_welcome_flow
name: Welcome flow
domain: mydomain
for_each: user
duration: 10m

entities:
  user:
    count: 10
    type: user

sources:
  - id: web
    type: service
    role: web_service
    rate:
      base_qps: 10
      burst_qps: 50
      jitter: 0.1

timeline:
  - id: start_session
    at: "00:00:00"
    event: session.started
    source: web
    entity_refs:
      user: "$flow"

rules:
  - id: session_requires_user
    type: required_entity_ref
    event: session.started
    ref: user
```

## Validate the pack

```bash
eventweave pack validate mydomain
```

Fix any errors and re-run until validation passes.

## Inspect the pack

```bash
eventweave pack inspect mydomain
eventweave pack list
```

## Reuse existing packs

Depend on `common` or other packs when they provide useful entity types:

```yaml
depends_on:
  - common
```

The compiler loads dependencies recursively, so a scenario in `mydomain` can
reference entities from both `mydomain` and `common`.

## Best practices

- Keep the core framework domain-agnostic; put domain knowledge in packs.
- Add at least one runnable example per pack.
- Run `eventweave pack validate` before committing changes.
- Reuse `packs/common/` for shared entities such as `user` and `device`.
- Use descriptive event type names with namespaces.
- Document domain-specific rule attributes in the pack README or comments.

## Submitting a pack

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the pull request checklist.
A new pack should include:

- `pack.yaml` with `id`, `name`, `version`, and `description`.
- `entities/` with at least one schema.
- `events/` with at least one schema (optional for pure entity packs).
- `rules.yaml` (optional but recommended).
- `examples/` with at least one runnable scenario.
- Updated `README.md` and `docs/pack-spec.md` if the pack demonstrates new
  framework capabilities.
