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
```

- `id` — unique suite identifier.
- `name` / `description` — human-readable metadata.
- `scenarios` — list of scenarios to evaluate. Each scenario must declare `ground_truth`.

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

## Authoring a new suite

1. Ensure each referenced scenario declares `ground_truth`.
2. Add the scenario to a new or existing YAML file in this directory.
3. Provide sample agent outputs under `examples/evaluation/` or an agent directory.
4. Add tests in `tests/evaluation/test_benchmark.py`.
