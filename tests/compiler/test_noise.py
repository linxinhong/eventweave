"""Tests for deterministic background noise generation."""

from __future__ import annotations

from eventweave.compiler import compile_scenario
from eventweave.core.scenario import Scenario


def _scenario_with_noise(ratio: float = 2.0) -> Scenario:
    return Scenario.model_validate(
        {
            "id": "noise_test",
            "domain": "security",
            "for_each": "host",
            "duration": "10m",
            "seed": 42,
            "entities": {
                "host": {"count": 2, "type": "host"},
                "user": {"count": 2, "type": "user"},
            },
            "sources": [
                {"id": "auth", "type": "service", "role": "auth"},
                {"id": "dns", "type": "service", "role": "dns"},
            ],
            "timeline": [
                {
                    "id": "login",
                    "at": "00:00:00",
                    "event": "user.login.failed",
                    "source": "auth",
                    "entity_refs": {"host": "$flow", "user": "$entity.user"},
                }
            ],
            "noise": {
                "enabled": True,
                "ratio": ratio,
                "events": [
                    {"event": "user.login.success", "weight": 1},
                    {"event": "dns.query", "weight": 2},
                ],
            },
        }
    )


def test_noise_generates_deterministic_events() -> None:
    scenario = _scenario_with_noise()
    result_a = compile_scenario(scenario)
    result_b = compile_scenario(scenario)

    noise_a = [e for e in result_a.plan.events if e.ground_truth.get("noise")]
    noise_b = [e for e in result_b.plan.events if e.ground_truth.get("noise")]
    assert len(noise_a) == len(noise_b)
    assert [e.event_id for e in noise_a] == [e.event_id for e in noise_b]
    assert [e.event_type for e in noise_a] == [e.event_type for e in noise_b]


def test_noise_events_marked_as_noise() -> None:
    scenario = _scenario_with_noise()
    result = compile_scenario(scenario)

    noise = [e for e in result.plan.events if e.ground_truth.get("noise")]
    assert len(noise) > 0
    for event in noise:
        assert event.ground_truth.get("noise") is True
        assert event.event_id.startswith("evt-noise-test-noise-")


def test_noise_ratio_approximate() -> None:
    scenario = _scenario_with_noise(ratio=3.0)
    result = compile_scenario(scenario)

    key_events = [e for e in result.plan.events if e.ground_truth.get("is_key_event")]
    noise_events = [e for e in result.plan.events if e.ground_truth.get("noise")]
    assert len(noise_events) == len(key_events) * 3


def test_noise_does_not_change_ground_truth_event_ids() -> None:
    scenario_without_noise = _scenario_with_noise(ratio=0.0)
    scenario_with_noise = _scenario_with_noise(ratio=5.0)

    result_without = compile_scenario(scenario_without_noise)
    result_with = compile_scenario(scenario_with_noise)

    ids_without = {e.event_id for e in result_without.plan.events}
    key_with = {e.event_id for e in result_with.plan.events if e.ground_truth.get("is_key_event")}
    assert key_with == ids_without
