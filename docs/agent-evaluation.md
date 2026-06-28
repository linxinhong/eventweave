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
      evidence_events: [evt-security-lateral-movement-001-001]
    - type: lateral_movement
      stage: lateral_movement
      entities: [host_001, host_002]
      evidence_events: [evt-security-lateral-movement-001-004]
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
  - `evidence_events` — event IDs supporting the finding.
  - `attributes` — optional extra key/value metadata.
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

- `finding_type_recall` — fraction of expected findings whose `type` was reported.
- `entity_recall` — average per-matched-finding recall of expected entity IDs.
- `event_id_recall` — average per-matched-finding recall of expected evidence event IDs.
- `timeline_stage_accuracy` — fraction of expected findings whose `stage` was reported correctly.
- `overall_score` — simple average of the four metrics.

A finding matches when its normalized `type` equals the expected type and, if the expected finding declares a `stage`, the normalized `stage` also matches.

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
