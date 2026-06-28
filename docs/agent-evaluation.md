# Agent Evaluation Harness

EventWeave can generate scenario event streams together with a **ground truth**, making it possible to evaluate an agent's ability to reconstruct a timeline, identify key findings, and reference supporting events.

The evaluation harness is **fully deterministic** and does not use any LLM calls.

## Workflow

```text
1. Declare ground_truth in a scenario YAML file.
2. eventweave compile scenario.yaml -o dist
3. eventweave eval task dist/<scenario> -o dist/<scenario>/eval/task.json
4. Agent reads task.json + event_plan.jsonl and produces agent_output.json
5. eventweave eval run \
     --ground-truth dist/<scenario>/ground_truth.json \
     --agent-output agent_output.json \
     --output report.json
```

## Ground truth schema

Add an optional `ground_truth` section to a scenario file:

```yaml
id: security_lateral_movement
domain: security
# ...

ground_truth:
  scenario_id: security_lateral_movement
  expected_findings:
    - type: suspicious_login
      stage: initial_access
      entities: [user_001, host_001]
      evidence_event_ids: [evt-security-lateral-movement-001-001]
    - type: lateral_movement
      stage: lateral_movement
      entities: [host_001, host_002]
      evidence_event_ids: [evt-security-lateral-movement-001-004]
  expected_summary: >-
    Suspicious login followed by lateral movement and an EDR alert.
  key_event_ids:
    - evt-security-lateral-movement-001-001
    - evt-security-lateral-movement-001-004
```

Fields:

- `expected_findings` — list of findings the agent should report.
  - `type` — finding type (matched case-insensitively).
  - `stage` — optional MITRE / business-flow stage (matched case-insensitively).
  - `entities` — entity IDs the finding should mention.
  - `evidence_event_ids` — event IDs supporting the finding.
  - `attributes` — optional extra key/value metadata.

The field `evidence_events` is still accepted as a legacy alias for `evidence_event_ids`.
- `expected_summary` — expected narrative summary.
- `key_event_ids` — most important event IDs in the scenario.
- `attributes` — optional scenario-level metadata.

When a scenario is compiled, `ground_truth.json` is written next to the runtime plan.

## Agent output schema

The agent must produce a JSON document matching `AgentOutput`:

```json
{
  "scenario_id": "security_lateral_movement",
  "findings": [
    {
      "type": "suspicious_login",
      "stage": "initial_access",
      "entities": ["user_001", "host_001"],
      "evidence_event_ids": ["evt-security-lateral-movement-001-001"],
      "confidence": 0.95,
      "attributes": {}
    }
  ],
  "key_event_ids": ["evt-security-lateral-movement-001-001"],
  "timeline_stages": [
    {"stage": "initial_access", "event_ids": ["evt-security-lateral-movement-001-001"]}
  ],
  "summary": "Suspicious login followed by lateral movement and an EDR alert."
}
```

## Metrics

`eventweave eval run` computes the following metrics using exact normalized matching:

**Recall**

- `finding_type_recall` — fraction of expected findings whose `type` was reported.
- `entity_recall` — average per-matched-finding recall of expected entity IDs.
- `event_id_recall` — average per-matched-finding recall of expected evidence event IDs.
- `timeline_stage_accuracy` — fraction of expected findings whose `stage` was reported correctly.

**Precision**

- `finding_type_precision` — fraction of reported findings that match an expected finding.
- `entity_precision` — average per-matched-finding precision of reported entity IDs.
- `event_id_precision` — average per-matched-finding precision of reported evidence event IDs.

**Aggregates**

- `overall_score` — simple average of the four original recall/stage metrics (kept for backward compatibility).
- `balanced_score` — average of all seven metrics above, balancing recall and precision.

Recall measures漏报； precision measures误报. A finding matches when its normalized `type` equals the expected type and, if the expected finding declares a `stage`, the normalized `stage` also matches.

## Report details

`report.json` includes:

```json
{
  "matched_findings": [],
  "missed_findings": [],
  "extra_findings": []
}
```

- `matched_findings` — expected findings that were reported, with per-finding recall/precision.
- `missed_findings` — expected findings that the agent did not report.
- `extra_findings` — agent findings that do not match any expected finding (potential hallucinations).

## CLI reference

### `eventweave eval task`

Generate an agent-facing evaluation task from a compiled runtime plan.

```bash
eventweave eval task <plan-dir> [-o <task.json>]
```

The task file contains instructions, the path to the event plan, a pointer to the ground-truth file (for the evaluator), and the required `AgentOutput` schema. It does **not** embed ground-truth answers.

### `eventweave eval run`

Evaluate an agent output against ground truth.

```bash
eventweave eval run \
  --ground-truth ground_truth.json \
  --agent-output agent_output.json \
  -o report.json
```

The command prints a metrics table and writes a JSON report.

### `eventweave eval validate-output`

Validate an agent output JSON file against the `AgentOutput` schema.

```bash
eventweave eval validate-output agent_output.json
```

## Sample evaluation workflow

Use the built-in sample agent output to see a perfect score:

```bash
eventweave compile examples/security/lateral_movement.yaml -o dist
eventweave eval run \
  --ground-truth dist/security_lateral_movement/ground_truth.json \
  --agent-output examples/evaluation/security_lateral_movement_agent_output.json \
  --output report.json
```

Expected result: `overall_score = 1.00`, `balanced_score = 1.00`.

## Benchmark suites

For multi-scenario evaluation, define a benchmark suite YAML file and run it against one or more agent output directories.

### Suite format

```yaml
id: security_baseline
name: Security baseline benchmark
description: Core detection scenarios for security operations agents.
scenarios:
  - id: lateral_movement
    scenario_path: examples/security/lateral_movement.yaml
```

Each referenced scenario must declare `ground_truth`. Agent outputs are matched by `{scenario_id}.json` inside each agent directory, with a fallback to `{scenario_id}_agent_output.json`.

### CLI

List available suites:

```bash
eventweave benchmark list
```

Run a suite:

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

### Scorecard output

The scorecard JSON contains:

- `suite` — the benchmark suite definition.
- `results` — per-agent per-scenario reports and aggregate metrics.
- `ranking` — agent names ordered by `balanced_score`, then `overall_score`.

Aggregate metrics are simple averages across all scenarios in the suite.
