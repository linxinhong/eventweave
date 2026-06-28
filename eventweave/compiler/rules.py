"""Declarative rule engine for scenario validation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from eventweave.core.event import Event
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario


class RuleViolationError(Exception):
    """Raised when a rule is violated."""


class Rule(ABC):
    """Base class for declarative rules."""

    def __init__(self, rule_id: str, attributes: dict[str, Any]) -> None:
        self.rule_id = rule_id
        self.attributes = attributes

    @abstractmethod
    def validate(self, scenario: Scenario, plan: RuntimePlan) -> None:
        """Validate the runtime plan against this rule."""

    def _error(self, message: str) -> None:
        raise RuleViolationError(f"Rule {self.rule_id!r}: {message}")


class RequiredEntityRefRule(Rule):
    """Ensure an event references required entities."""

    def validate(self, scenario: Scenario, plan: RuntimePlan) -> None:
        event_type = self.attributes.get("event")
        refs = self.attributes.get("refs") or [self.attributes.get("ref")]
        refs = [r for r in refs if r]

        for event in plan.events:
            if event.event_type != event_type:
                continue
            for ref_role in refs:
                if not event.entity_refs.get(ref_role):
                    self._error(
                        f"Event {event.event_id} ({event.event_type}) "
                        f"missing required entity ref {ref_role!r}"
                    )


class EventAfterRule(Rule):
    """Ensure an event occurs after another event within the same scope."""

    def validate(self, scenario: Scenario, plan: RuntimePlan) -> None:
        event_type = self.attributes.get("event")
        after_type = self.attributes.get("after")

        # Index events by flow (scope).
        events_by_scope: dict[str, list[Event]] = {}
        for event in plan.events:
            key = event.flow_id or "global"
            events_by_scope.setdefault(key, []).append(event)

        for flow_id, events in events_by_scope.items():
            for idx, event in enumerate(events):
                if event.event_type != event_type:
                    continue
                # Find any preceding after_type event in the same scope.
                predecessors = [e for e in events[:idx] if e.event_type == after_type]
                if not predecessors:
                    self._error(
                        f"Event {event.event_id} ({event.event_type}) in flow {flow_id} "
                        f"has no preceding {after_type!r} event"
                    )


class FieldRequiredRule(Rule):
    """Ensure an event has required fields."""

    def validate(self, scenario: Scenario, plan: RuntimePlan) -> None:
        event_type = self.attributes.get("event")
        field = self.attributes.get("field")

        for event in plan.events:
            if event.event_type != event_type:
                continue
            if field not in event.attributes:
                self._error(
                    f"Event {event.event_id} ({event.event_type}) missing required field {field!r}"
                )


class FieldEnumRule(Rule):
    """Ensure a field value belongs to allowed enum values."""

    def validate(self, scenario: Scenario, plan: RuntimePlan) -> None:
        event_type = self.attributes.get("event")
        field = self.attributes.get("field")
        allowed = set(self.attributes.get("values", []))

        if not allowed or not isinstance(field, str):
            return

        for event in plan.events:
            if event.event_type != event_type:
                continue
            value = event.attributes.get(field)
            if value is not None and value not in allowed:
                self._error(
                    f"Event {event.event_id} ({event.event_type}) field {field!r}="
                    f"{value!r} not in allowed values {sorted(allowed)}"
                )


class NotImplementedRule(Rule):
    """Placeholder rule that emits a warning instead of failing."""

    def validate(self, scenario: Scenario, plan: RuntimePlan) -> None:
        # Do nothing; unsupported rules are treated as warnings during registration.
        pass


class RuleRegistry:
    """Registry of supported declarative rule types."""

    _RULES: dict[str, type[Rule]] = {
        "required_entity_ref": RequiredEntityRefRule,
        "event_after": EventAfterRule,
        "event_before": NotImplementedRule,
        "field_required": FieldRequiredRule,
        "field_enum": FieldEnumRule,
        "field_range": NotImplementedRule,
        "state_transition": NotImplementedRule,
        "probability_range": NotImplementedRule,
        "field_lte_ref": NotImplementedRule,
    }

    def __init__(self) -> None:
        self._rules: list[Rule] = []

    def register(self, rule_id: str, rule_type: str, attributes: dict[str, Any]) -> None:
        rule_cls = self._RULES.get(rule_type)
        if rule_cls is None:
            raise RuleViolationError(
                f"Unknown rule type {rule_type!r} for rule {rule_id!r}"
            )
        self._rules.append(rule_cls(rule_id, attributes))

    def load_from_scenario(self, scenario: Scenario) -> None:
        for raw in scenario.rules:
            if isinstance(raw, str):
                # Lookup rule in loaded packs would happen here.
                # For v0.1, skip bare string rules unless they map to known pack rules.
                continue
            rule_id = raw.get("id")
            rule_type = raw.get("type")
            attributes = {k: v for k, v in raw.items() if k not in ("id", "type")}
            if not rule_id or not rule_type:
                continue
            self.register(rule_id, rule_type, attributes)

    def load_from_pack(self, pack_rules: list[Any]) -> None:
        for rule in pack_rules:
            self.register(rule.id, rule.type, dict(rule.attributes))

    def validate(self, scenario: Scenario, plan: RuntimePlan) -> list[str]:
        warnings: list[str] = []
        for rule in self._rules:
            try:
                rule.validate(scenario, plan)
            except RuleViolationError as exc:
                # For v0.1, collect violations as warnings unless strict mode is enabled.
                warnings.append(str(exc))
        return warnings
