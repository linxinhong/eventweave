# Synthetic Realism / Dataset Quality Tools

Real-world event streams are not clean attack chains. They are buried in normal traffic, timing is irregular, and detectors must separate signal from noise. EventWeave v0.8 adds deterministic background noise, timestamp jitter, and a realism report so you can measure how "real" your generated dataset looks.

## Background noise

Add normal background events around your ground-truth timeline. The compiler inserts them deterministically based on the scenario seed.

```yaml
id: security_noisy_attack
domain: security
for_each: host
duration: 30m
seed: 20260628

noise:
  enabled: true
  ratio: 5.0
  events:
    - event: user.login.success
      weight: 5
    - event: dns.query
      weight: 10
    - event: firewall.allow
      weight: 8
    - event: edr.heartbeat
      weight: 20
```

- `ratio` — number of noise events per ground-truth timeline event.
- `events` — list of noise event templates with relative `weight`.
- Noise events are tagged with `ground_truth.noise: true` in the event plan.
- Ground-truth event ids and order are never affected by noise.

## Time jitter

Jitter perturbs event timestamps so the stream does not look artificially regular.

```yaml
jitter:
  enabled: true
  max_offset: 10s
  preserve_order: true
```

- `max_offset` — maximum time to add or subtract (e.g. `5s`, `1m`).
- `preserve_order` — when `true`, events inside the same flow are clamped so a predecessor never ends up after a successor.

You can also override jitter for a single timeline step:

```yaml
timeline:
  - id: alert_triggered
    event: alert.triggered
    jitter: 2s
```

## Realism report

After compiling a scenario, generate a deterministic realism report:

```bash
eventweave compile examples/security/lateral_movement.yaml -o dist
eventweave quality realism dist/security_lateral_movement
```

Save as JSON:

```bash
eventweave quality realism dist/security_lateral_movement --output realism.json
```

Example output:

```text
Realism Report
  Scenario: security_noisy_attack
  Total events: 1260
  Ground truth events: 12
  Noise events: 1248
  Noise ratio: 99.05%
  Unique entities: 42
  Unique sources: 4
  Event types: 9
  Timeline duration: 1800.0s
  Events/min: 42.0
  Burstiness score: 0.312
  Ground truth coverage: 100.00%
```

Metrics:

| Metric | Description |
|--------|-------------|
| `total_events` | All events in the compiled plan. |
| `ground_truth_events` | Events that belong to the scenario timeline. |
| `noise_events` | Background noise events. |
| `noise_ratio` | Percentage of noise events. |
| `unique_entities` | Distinct entity ids referenced by events. |
| `unique_sources` | Distinct source ids emitting events. |
| `event_type_distribution` | Count per event type. |
| `timeline_duration_seconds` | Time span from first to last event. |
| `events_per_minute` | Average event rate. |
| `burstiness_score` | Coefficient of variation of per-minute counts. Higher means more bursty. |
| `ground_truth_coverage` | Fraction of expected findings with evidence event ids. |

## Benchmark quality gate (optional)

Benchmark suites can expect a minimum noise ratio so datasets are not too clean:

```bash
eventweave benchmark validate --suite benchmarks/security.yaml --min-noise-ratio 3.0
```

This is a v0.8.1 follow-up; v0.8 focuses on the core noise/jitter/report capabilities.

## Limits

- Noise and jitter are deterministic but not based on real log distributions.
- No LLM-based realism judge.
- No correlation strength modeling yet.
