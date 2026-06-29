"""Tests for deterministic timestamp jitter."""

from __future__ import annotations

from eventweave.compiler import compile_scenario
from eventweave.core.scenario import Scenario


def _scenario_with_jitter(preserve_order: bool = True) -> Scenario:
    return Scenario.model_validate(
        {
            "id": "jitter_test",
            "domain": "security",
            "for_each": "host",
            "duration": "10m",
            "seed": 42,
            "entities": {"host": {"count": 1, "type": "host"}},
            "sources": [{"id": "edr", "type": "service", "role": "edr"}],
            "timeline": [
                {
                    "id": "login",
                    "at": "00:00:00",
                    "event": "user.login.failed",
                    "source": "edr",
                    "entity_refs": {"host": "$flow"},
                },
                {
                    "id": "process",
                    "after": "login",
                    "delay": "1m",
                    "event": "process.suspicious_started",
                    "source": "edr",
                    "entity_refs": {"host": "$ref.login.host"},
                },
            ],
            "jitter": {
                "enabled": True,
                "max_offset": "30s",
                "preserve_order": preserve_order,
            },
        }
    )


def test_jitter_is_deterministic() -> None:
    scenario = _scenario_with_jitter()
    result_a = compile_scenario(scenario)
    result_b = compile_scenario(scenario)

    # Absolute event times depend on wall-clock start_time; compare relative gaps.
    def gaps(events: list) -> list[float]:
        times = sorted(e.event_time for e in events)
        return [(times[i + 1] - times[i]).total_seconds() for i in range(len(times) - 1)]

    assert gaps(result_a.plan.events) == gaps(result_b.plan.events)


def test_jitter_preserves_order() -> None:
    scenario = _scenario_with_jitter(preserve_order=True)
    result = compile_scenario(scenario)

    events = sorted(result.plan.events, key=lambda e: e.event_id)
    login = next(e for e in events if e.event_type == "user.login.failed")
    process = next(e for e in events if e.event_type == "process.suspicious_started")
    assert process.event_time > login.event_time


def test_jitter_can_disable_preserve_order() -> None:
    scenario = _scenario_with_jitter(preserve_order=False)
    result = compile_scenario(scenario)

    baseline_scenario = _scenario_with_jitter(preserve_order=False)
    baseline_scenario.jitter = None
    baseline = compile_scenario(baseline_scenario)

    for event, base_event in zip(
        sorted(result.plan.events, key=lambda e: e.event_id),
        sorted(baseline.plan.events, key=lambda e: e.event_id),
        strict=True,
    ):
        delta = abs((event.event_time - base_event.event_time).total_seconds())
        assert delta <= 30.0
