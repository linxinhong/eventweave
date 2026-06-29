from __future__ import annotations

import pytest

from eventweave.compiler.rules import (
    EventAfterRule,
    EventBeforeRule,
    FieldLteRefRule,
    RuleRegistry,
    RuleViolationError,
)
from eventweave.core.event import Event
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario


def _event(event_id: str, event_type: str, attributes: dict | None = None, **refs: str) -> Event:
    return Event(
        event_id=event_id,
        scenario_id="sc1",
        source_id="src1",
        event_type=event_type,
        event_time="2024-01-01T00:00:00Z",
        entity_refs=refs,
        attributes=attributes or {},
    )


def _plan(events: list[Event]) -> RuntimePlan:
    return RuntimePlan(scenario=Scenario(id="sc1", domain="test"), events=events)


def test_event_after_rule_passes() -> None:
    plan = _plan(
        [
            _event("e1", "order.paid", order="o1"),
            _event("e2", "refund.requested", order="o1"),
        ]
    )
    rule = EventAfterRule(
        "r1", {"event": "refund.requested", "after": "order.paid", "scope": "order"}
    )
    rule.validate(plan.scenario, plan)


def test_event_after_rule_fails() -> None:
    plan = _plan([_event("e2", "refund.requested", order="o1")])
    rule = EventAfterRule(
        "r1", {"event": "refund.requested", "after": "order.paid", "scope": "order"}
    )
    with pytest.raises(RuleViolationError):
        rule.validate(plan.scenario, plan)


def test_event_before_rule_passes() -> None:
    plan = _plan(
        [
            _event("e1", "order.paid", order="o1"),
            _event("e2", "refund.requested", order="o1"),
        ]
    )
    rule = EventBeforeRule(
        "r1", {"event": "order.paid", "before": "refund.requested", "scope": "order"}
    )
    rule.validate(plan.scenario, plan)


def test_event_before_rule_fails() -> None:
    plan = _plan(
        [
            _event("e1", "refund.requested", order="o1"),
            _event("e2", "order.paid", order="o1"),
        ]
    )
    rule = EventBeforeRule(
        "r1", {"event": "order.paid", "before": "refund.requested", "scope": "order"}
    )
    with pytest.raises(RuleViolationError):
        rule.validate(plan.scenario, plan)


def test_field_lte_ref_passes() -> None:
    plan = _plan(
        [
            _event("e1", "order.paid", {"payment.amount": 100}, order="o1"),
            _event("e2", "refund.requested", {"refund.amount": 80}, order="o1"),
        ]
    )
    rule = FieldLteRefRule(
        "r1",
        {
            "event": "refund.requested",
            "field": "refund.amount",
            "ref_event": "order.paid",
            "ref_field": "payment.amount",
            "scope": "order",
        },
    )
    rule.validate(plan.scenario, plan)


def test_field_lte_ref_fails_when_exceeds() -> None:
    plan = _plan(
        [
            _event("e1", "order.paid", {"payment.amount": 100}, order="o1"),
            _event("e2", "refund.requested", {"refund.amount": 120}, order="o1"),
        ]
    )
    rule = FieldLteRefRule(
        "r1",
        {
            "event": "refund.requested",
            "field": "refund.amount",
            "ref_event": "order.paid",
            "ref_field": "payment.amount",
            "scope": "order",
        },
    )
    with pytest.raises(RuleViolationError):
        rule.validate(plan.scenario, plan)


def test_registry_warns_on_not_implemented_rule() -> None:
    registry = RuleRegistry()
    registry.register("r1", "state_transition", {})
    warnings = registry.validate(Scenario(id="sc1", domain="test"), _plan([]))
    assert any("not implemented" in w.lower() for w in warnings)
    assert any("state_transition" in w for w in warnings)


def test_registry_collects_violations_as_warnings() -> None:
    registry = RuleRegistry()
    registry.register("r1", "event_after", {"event": "refund.requested", "after": "order.paid"})
    plan = _plan([_event("e2", "refund.requested")])
    warnings = registry.validate(plan.scenario, plan)
    assert any("no preceding" in w for w in warnings)
