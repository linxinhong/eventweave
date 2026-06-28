# Contributing to EventWeave

Thank you for your interest in EventWeave. This guide covers the basics for contributors.

## Development environment

We use Python 3.11+ and [uv](https://github.com/astral-sh/uv) for package management.

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Common commands

```bash
make test       # run pytest
make lint       # run ruff check
make typecheck  # run mypy
make check      # run lint + typecheck + test
```

## Testing requirements

Every non-trivial change should include tests. We use `pytest`.

- Add unit tests for new core models or compiler logic.
- Add scenario tests for new DSL features.
- Update golden tests if compiler output changes intentionally.

Run tests before submitting a PR:

```bash
make check
```

## Code style

- Python 3.11+ type hints for public functions.
- Pydantic v2 for schemas.
- Clear, explicit code over clever code.
- Keep the core domain-agnostic.
- Do not put LLM calls in the runtime hot path.

## Commit messages

Use conventional commits:

```text
feat: add timeline planner
fix: validate relation references
docs: add scenario DSL example
test: add ecommerce refund golden test
refactor: split semantic validators
chore: update dependencies
```

## Pull request checklist

Before submitting a PR:

- [ ] The change has a clear purpose.
- [ ] Core remains domain-agnostic.
- [ ] Tests were added or updated.
- [ ] Example scenarios still compile.
- [ ] Docs were updated if needed.
- [ ] `make check` passes.
- [ ] No real secrets or personal data were added.
- [ ] Deterministic behavior is preserved where expected.

## Adding a domain pack

Packs live in `packs/<domain>/`. The fastest way to start is:

```bash
eventweave pack scaffold <domain>
```

A minimal pack needs:

```text
packs/<domain>/
├── pack.yaml
├── entities/
├── events/
├── rules.yaml
└── examples/
```

- Add `id`, `name`, `version`, and `description` to `pack.yaml`.
- Add at least one runnable example in `packs/<domain>/examples/`.
- Validate the pack before submitting:
  ```bash
  eventweave pack validate <domain>
  ```
- Add tests if the pack introduces new rules or behavior.
- Reuse `packs/common/` for shared entity types when possible.
- Follow the manifest spec in [docs/pack-spec.md](docs/pack-spec.md) and the
  authoring guide in [docs/pack-authoring.md](docs/pack-authoring.md).

## Do not submit

- Real API keys, tokens, passwords, or certificates.
- Real personal data, patient data, or customer data.
- Large binary files or generated artifacts.

## Questions?

Open an issue or start a discussion. For architecture questions, refer to [docs/design.md](docs/design.md) and [AGENTS.md](AGENTS.md).
