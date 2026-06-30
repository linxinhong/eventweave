# Golden Baseline Workflow

EventWeave uses **golden baselines** to guard the stability of compiled output.
A golden file is a committed snapshot of a deterministic compiler product. When
planner, schema, encoder, or rule changes alter the event stream shape, the
golden diff must be reviewed deliberately and updated only when the change is
intentional.

This document defines:

- What belongs to the golden baseline.
- How to check it (`make golden-check`).
- How to update it (`make golden-update`).
- When an update is allowed — and when it is not.
- How schema-validation warnings affect golden review.
- How to verify that `ground_truth` and benchmark samples are still correct.

## What is the golden baseline?

The golden baseline is a set of committed files under `tests/golden/<scenario_id>/`.
Each directory contains the compiler output for a representative scenario with a
fixed seed. The baseline makes compiler-output changes visible in `git diff` and
gives reviewers a concrete signal that a code change has observable effects.

## What files belong to the baseline?

For each scenario we track the full compiler output:

- `scenario.json`
- `entities.json`
- `relations.json`
- `sources.json`
- `runtime_plan.json`
- `event_plan.jsonl`
- `ground_truth.json`
- `semantic_tasks.json` (when present)

The snapshot test in `tests/test_golden.py` compares a **stable signature** of
each event rather than raw timestamps, because wall-clock fields such as
`event_time` and `generated_at` are expected to drift between runs.

## Scenario coverage

Current golden scenarios:

| Scenario file | Scenario ID | Why it is covered |
|---------------|-------------|-------------------|
| `examples/ecommerce/refund.yaml` | `ecommerce_refund_flow` | Multi-entity order/refund flow |
| `examples/security/lateral_movement.yaml` | `security_lateral_movement` | Multi-source security timeline |

Add a new golden scenario only when it exercises a new compiler behaviour that
existing baselines do not cover.

## Update commands

### Check the baseline

```bash
make golden-check
```

Equivalent to:

```bash
uv run pytest tests/test_golden.py -q
```

### Update the baseline

```bash
make golden-update
```

This recompiles every golden scenario with the fixed seed `20260628` and copies
the artifacts into `tests/golden/<scenario_id>/`. Review the resulting diff
before committing.

You can also update a single scenario manually:

```bash
uv run eventweave compile examples/ecommerce/refund.yaml \
  -o /tmp/golden-update --force --seed 20260628
cp /tmp/golden-update/ecommerce_refund_flow/event_plan.jsonl \
   tests/golden/ecommerce_refund_flow/event_plan.jsonl
```

## When is an update allowed?

A golden update is allowed when **all** of the following are true:

- [ ] The code change that caused the diff is intentional.
- [ ] `scenario_id` has not changed.
- [ ] The `seed` used to generate the baseline has not changed.
- [ ] `event_id` values remain stable for the same input (unless event identity
generation itself changed).
- [ ] `event_time` / `generated_at` drift is the only change — these are
ignored by the test signature.
- [ ] `ground_truth` key-event markings and evidence references are still
correct, or their changes are documented in the PR.
- [ ] `flow_id`, `source_id`, `entity_refs`, `event_type`, and `attributes`
changes are explained.
- [ ] Benchmark suites such as `benchmarks/ecommerce.yaml` and
`benchmarks/security.yaml` still validate successfully.

## When is an update NOT allowed?

Do not update golden files to mask:

- Accidental entity or event loss.
- Non-deterministic output (unstable IDs, unstable ordering, or unseeded random
  fields).
- Broken `ground_truth` evidence.
- Regression in benchmark sample scores.
- Unexplained schema-validation errors (use `--strict-schema` to surface them).

If the diff shows unexpected changes, fix the code first. Only update the
golden baseline after the root cause is understood.

## Reviewing `event_plan.jsonl` diffs

A good `event_plan.jsonl` review looks at:

1. **Count** — `wc -l tests/golden/<scenario>/event_plan.jsonl` should match
   expectations.
2. **Event types** — run:
   ```bash
   cat tests/golden/<scenario>/event_plan.jsonl | jq -r '.event_type' | sort | uniq -c
   ```
3. **Key events** — key events are marked in `ground_truth.json`:
   ```bash
   cat tests/golden/<scenario>/ground_truth.json | jq '.key_events'
   ```
4. **Entity references** — ensure `entity_refs` still point to the right roles.
5. **Attributes** — spot-check a few events for expected fields and values.

Timestamps (`event_time`, `generated_at`, `emit_time`, `ingest_time`) are allowed
to drift and are not part of the golden assertion.

## Handling schema-validation warnings

The compiler now emits schema-validation warnings by default. Golden baselines
may be regenerated after schema validation changes. Treat warnings as signals,
not noise:

- **Required-field warnings** on entities (for example missing `customer.name`)
  usually mean the scenario generator or the pack schema needs alignment. If the
  warning existed before the change, a golden update is acceptable. If the
  change introduced the warning, fix the generator or schema before updating
  golden files.
- **Unknown event type** or **enum violation** warnings indicate a real schema
  mismatch and must be resolved.
- Use `eventweave compile ... --strict-schema` during review to turn warnings
  into errors. Golden baselines should not be committed while `--strict-schema`
  fails unless the failure is documented and accepted.

## Verifying `ground_truth` and benchmark samples

After updating golden files, run the evaluation and benchmark checks:

```bash
# Recompile a scenario for evaluation
uv run eventweave eval prepare examples/security/lateral_movement.yaml \
  -o dist/lateral_movement --force --seed 20260628

# Validate benchmark suites
uv run eventweave benchmark validate --suite benchmarks/security.yaml
uv run eventweave benchmark validate --suite benchmarks/ecommerce.yaml
```

If a benchmark sample no longer scores as expected, investigate before
committing the golden update.

## PR checklist for golden changes

When a pull request changes golden files, include:

- A short explanation of why the baseline changed.
- `make golden-check` output showing the new baseline passes.
- The result of `eventweave benchmark validate` for affected suites.
- Confirmation that `ground_truth` key events and evidence are still correct.
- If schema warnings changed, note which warnings are expected and which were
  fixed.

## Relationship to releases

Golden baselines should be in a known-good state at every tagged release. Before
cutting a release:

1. Run `make golden-check`.
2. If it fails, run `make golden-update` and review the diff.
3. Run `make check`.
4. Run `cd runtime-go && go test ./... && go vet ./...`.

Only tag after all checks pass and the golden diff is understood.
