"""Tests for declarative rule engine."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eventweave.compiler.rules import (
    EventAfterRule,
    RequiredEntityRefRule,
    RuleRegistry,
    RuleViolationError,
)
from eventweave.core.event import Event
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario


class TestRequiredEntityRefRule:
    def test_missing_ref_triggers_violation(self) -> None:
        scenario = Scenario(id="test", domain="test")
        event = Event(
            event_id="e1",
            scenario_id="test",
            source_id="s1",
            event_type="ticket.created",
            event_time=datetime.now(UTC),
            entity_refs={},
        )
        plan = RuntimePlan(scenario=scenario, events=[event])
        rule = RequiredEntityRefRule(
            "ticket_order_ref",
            {"event": "ticket.created", "ref": "order"},
        )

        with pytest.raises(RuleViolationError):
            rule.validate(scenario, plan)

    def test_present_ref_passes(self) -> None:
        scenario = Scenario(id="test", domain="test")
        event = Event(
            event_id="e1",
            scenario_id="test",
            source_id="s1",
            event_type="ticket.created",
            event_time=datetime.now(UTC),
            entity_refs={"order": "order_001"},
        )
        plan = RuntimePlan(scenario=scenario, events=[event])
        rule = RequiredEntityRefRule(
            "ticket_order_ref",
            {"event": "ticket.created", "ref": "order"},
        )
        rule.validate(scenario, plan)


class TestEventAfterRule:
    def test_missing_predecessor_triggers_violation(self) -> None:
        scenario = Scenario(id="test", domain="test")
        event = Event(
            event_id="e1",
            scenario_id="test",
            flow_id="f1",
            source_id="s1",
            event_type="refund.requested",
            event_time=datetime.now(UTC),
        )
        plan = RuntimePlan(scenario=scenario, events=[event])
        rule = EventAfterRule(
            "paid_before_refund",
            {"event": "refund.requested", "after": "order.paid", "scope": "flow"},
        )

        with pytest.raises(RuleViolationError):
            rule.validate(scenario, plan)

    def test_predecessor_present_passes(self) -> None:
        scenario = Scenario(id="test", domain="test")
        now = datetime.now(UTC)
        paid = Event(
            event_id="e1",
            scenario_id="test",
            flow_id="f1",
            source_id="s1",
            event_type="order.paid",
            event_time=now,
        )
        refund = Event(
            event_id="e2",
            scenario_id="test",
            flow_id="f1",
            source_id="s1",
            event_type="refund.requested",
            event_time=now,
        )
        plan = RuntimePlan(scenario=scenario, events=[paid, refund])
        rule = EventAfterRule(
            "paid_before_refund",
            {"event": "refund.requested", "after": "order.paid", "scope": "flow"},
        )
        rule.validate(scenario, plan)


class TestRuleRegistry:
    def test_register_and_validate(self) -> None:
        registry = RuleRegistry()
        registry.register(
            "r1",
            "required_entity_ref",
            {"event": "ticket.created", "ref": "order"},
        )

        scenario = Scenario(id="test", domain="test")
        event = Event(
            event_id="e1",
            scenario_id="test",
            source_id="s1",
            event_type="ticket.created",
            event_time=datetime.now(UTC),
            entity_refs={"order": "order_001"},
        )
        plan = RuntimePlan(scenario=scenario, events=[event])
        warnings = registry.validate(scenario, plan)
        assert warnings == []
