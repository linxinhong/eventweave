# EventWeave Benchmark Suites

This directory contains declarative benchmark suites for multi-scenario agent evaluation.

## Layout

Each YAML file defines a `BenchmarkSuite`:

```yaml
id: security_baseline
name: Security baseline benchmark
description: Core detection scenarios for security operations agents.
scenarios:
  - id: lateral_movement
    scenario_path: examples/security/lateral_movement.yaml
  - id: brute_force_login
    scenario_path: examples/security/brute_force_login.yaml
```

- `id` — unique suite identifier.
- `name` / `description` — human-readable metadata.
- `scenarios` — list of scenarios to evaluate. Each scenario must declare `ground_truth`.

## Available suites

- `security.yaml` — `security_baseline` with lateral movement, brute-force login,
  DNS exfiltration, and malware C2 callback scenarios.
- `ecommerce.yaml` — `ecommerce_baseline` with refund flow, payment-failure spike,
  and refund-fraud pattern scenarios.

## Validating a suite

Before running a suite, validate it and its sample data:

```bash
eventweave benchmark validate --suite benchmarks/security.yaml
```

The validator checks:

- suite YAML loads successfully
- scenario ids are unique
- every scenario file exists and compiles
- every scenario declares `ground_truth`
- expected findings are unique by `(type, stage)`
- `evidence_event_ids` reference real events in the compiled plan
- sample agent outputs in `examples/evaluation/` are valid and meet the minimum score

You can set a custom minimum sample score and write a JSON report:

```bash
eventweave benchmark validate \
  --suite benchmarks/security.yaml \
  --min-score 0.9 \
  --output validation/security.json
```

## Running a benchmark

Agent outputs are expected in a directory, with one JSON file per scenario named `{scenario_id}.json`:

```text
agents/gpt-4o/
├── security_lateral_movement.json
└── ecommerce_refund_flow.json
```

Run the benchmark:

```bash
eventweave benchmark run \
  --suite benchmarks/security.yaml \
  --agent-outputs agents/gpt-4o/ \
  --output scorecards/security.json
```

Compare multiple agents:

```bash
eventweave benchmark run \
  --suite benchmarks/security.yaml \
  --agent-outputs agents/gpt-4o/ \
  --agent-outputs agents/claude-sonnet/ \
  --output scorecards/security.json

eventweave benchmark leaderboard scorecards/security.json
```

## Realism and noise

Scenarios in benchmark suites can use `noise:` and `jitter:` to generate more
realistic datasets. After compiling, run `eventweave quality realism <plan-dir>`
to inspect noise ratio, burstiness, and other realism metrics.

Benchmark scenarios can also reference reusable realism profiles from their
domain pack:

```yaml
realism_profile: security.endpoint_background
```

See `packs/<domain>/realism/profiles.yaml` for the available profiles.

You can also enforce realism gates during validation:

```bash
eventweave benchmark validate \
  --suite benchmarks/security.yaml \
  --min-noise-ratio 0.5 \
  --min-event-types 6 \
  --min-sources 3 \
  --max-burstiness 2.0 \
  --require-jitter
```

The `--min-noise-ratio` gate is measured as noise events per ground-truth
timeline event. A JSON report written with `--output` includes a `realism`
section per scenario.

## Authoring a new suite

1. Ensure each referenced scenario declares `ground_truth`.
2. Add the scenario to a new or existing YAML file in this directory.
3. Provide sample agent outputs under `examples/evaluation/` or an agent directory.
4. Add tests in `tests/evaluation/`.
