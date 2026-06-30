
"""Tests for pack schema validation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from eventweave.compiler.engine import (
    compile_scenario_file,
    compile_scenario_file_strict,
)
from eventweave.compiler.pack_loader import PackRegistry
from eventweave.compiler.schema_validator import SchemaValidator
from eventweave.core.entity import Entity
from eventweave.core.event import Event
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import Scenario


@pytest.fixture
def packs() -> dict[str, object]:
    registry = PackRegistry()
    return registry.load_with_dependencies("ecommerce")


@pytest.fixture
def base_scenario() -> Scenario:
    return Scenario(id="schema-test", domain="ecommerce")


def _plan(
    scenario: Scenario,
    entities: list[Entity] | None = None,
    events: list[Event] | None = None,
) -> RuntimePlan:
    return RuntimePlan(
        scenario=scenario,
        entities=entities or [],
        relations=[],
        events=events or [],
        sources=[],
    )


def test_event_schema_required_field_warning(
    packs: dict[str, object], base_scenario: Scenario
) -> None:
    """Missing required event field produces a warning by default."""
    event = Event(
        event_id="e1",
        scenario_id="schema-test",
        source_id="svc",
        event_type="order.created",
        event_time=datetime.now(UTC),
        attributes={"currency": "CNY"},  # missing amount
    )
    plan = _plan(base_scenario, events=[event])
    validator = SchemaValidator(packs, strict=False)
    warnings, errors = validator.validate(plan)
    assert errors == []
    assert any("missing required field 'amount'" in w for w in warnings)


def test_event_schema_required_field_strict_error(
    packs: dict[str, object], base_scenario: Scenario
) -> None:
    """Missing required event field becomes an error in strict mode."""
    event = Event(
        event_id="e1",
        scenario_id="schema-test",
        source_id="svc",
        event_type="order.created",
        event_time=datetime.now(UTC),
        attributes={"currency": "CNY"},
    )
    plan = _plan(base_scenario, events=[event])
    validator = SchemaValidator(packs, strict=True)
    warnings, errors = validator.validate(plan)
    assert warnings == []
    assert any("missing required field 'amount'" in e for e in errors)


def test_event_schema_type_mismatch(packs: dict[str, object], base_scenario: Scenario) -> None:
    """Event field with wrong type produces a warning."""
    event = Event(
        event_id="e1",
        scenario_id="schema-test",
        source_id="svc",
        event_type="order.created",
        event_time=datetime.now(UTC),
        attributes={"amount": "not-a-number", "currency": "CNY"},
    )
    plan = _plan(base_scenario, events=[event])
    validator = SchemaValidator(packs, strict=False)
    warnings, _ = validator.validate(plan)
    assert any("expected type 'number'" in w for w in warnings)


def test_event_schema_enum_violation(base_scenario: Scenario) -> None:
    """Event field outside allowed enum produces a warning."""
    from eventweave.compiler.pack_loader import EventSchema, FieldSchema, Pack

    pack = Pack(
        id="test",
        events={
            "status.changed": EventSchema(
                type="status.changed",
                fields={"status": FieldSchema(type="string", enum=["ok", "warn", "critical"])},
            )
        },
    )
    event = Event(
        event_id="e1",
        scenario_id="schema-test",
        source_id="svc",
        event_type="status.changed",
        event_time=datetime.now(UTC),
        attributes={"status": "unknown"},
    )
    plan = _plan(base_scenario, events=[event])
    validator = SchemaValidator({"test": pack}, strict=False)
    warnings, _ = validator.validate(plan)
    assert any("not in allowed values" in w for w in warnings)


def test_event_schema_unknown_event_type(packs: dict[str, object], base_scenario: Scenario) -> None:
    """Unknown event_type produces a warning."""
    event = Event(
        event_id="e1",
        scenario_id="schema-test",
        source_id="svc",
        event_type="order.does_not_exist",
        event_time=datetime.now(UTC),
    )
    plan = _plan(base_scenario, events=[event])
    validator = SchemaValidator(packs, strict=False)
    warnings, _ = validator.validate(plan)
    assert any("unknown event_type" in w for w in warnings)


def test_entity_schema_required_field(packs: dict[str, object], base_scenario: Scenario) -> None:
    """Entity missing required field produces a warning."""
    entity = Entity(id="customer_001", type="customer")
    plan = _plan(base_scenario, entities=[entity])
    validator = SchemaValidator(packs, strict=False)
    warnings, _ = validator.validate(plan)
    assert any("missing required field 'name'" in w for w in warnings)


def test_entity_ref_unknown_role(packs: dict[str, object], base_scenario: Scenario) -> None:
    """Event entity ref role not declared in schema produces a warning."""
    entity = Entity(id="customer_001", type="customer")
    event = Event(
        event_id="e1",
        scenario_id="schema-test",
        source_id="svc",
        event_type="order.created",
        event_time=datetime.now(UTC),
        entity_refs={"customer": "customer_001", "order": "order_001", "extra": "customer_001"},
        attributes={"amount": 100.0, "currency": "CNY"},
    )
    plan = _plan(base_scenario, entities=[entity], events=[event])
    validator = SchemaValidator(packs, strict=False)
    warnings, _ = validator.validate(plan)
    assert any("unknown entity ref role 'extra'" in w for w in warnings)


def test_entity_ref_wrong_type(packs: dict[str, object], base_scenario: Scenario) -> None:
    """Event entity ref pointing to entity of wrong type produces a warning."""
    customer = Entity(id="customer_001", type="customer")
    event = Event(
        event_id="e1",
        scenario_id="schema-test",
        source_id="svc",
        event_type="order.created",
        event_time=datetime.now(UTC),
        entity_refs={"customer": "customer_001", "order": "customer_001"},
        attributes={"amount": 100.0, "currency": "CNY"},
    )
    plan = _plan(base_scenario, entities=[customer], events=[event])
    validator = SchemaValidator(packs, strict=False)
    warnings, _ = validator.validate(plan)
    assert any("entity ref 'order' expected type 'order', got 'customer'" in w for w in warnings)


def test_validate_cli_strict_schema_fails(tmp_path: Path) -> None:
    """CLI validate --strict-schema fails on schema violations."""
    scenario = tmp_path / "bad.yaml"
    scenario.write_text(
        """
id: bad_schema
domain: ecommerce
for_each: customer
entities:
  customer:
    count: 1
    type: customer
sources:
  - id: svc
    type: service
timeline:
  - at: "00:00:00"
    event: order.created
    source: svc
    entity_refs:
      customer: "$flow"
      order: "$new.order"
    attributes:
      currency: CNY
""",
        encoding="utf-8",
    )
    result = compile_scenario_file_strict(scenario, strict_schema=True)
    assert result.errors
    assert any("missing required field 'amount'" in e for e in result.errors)


def test_compile_cli_strict_schema_fails(tmp_path: Path) -> None:
    """CLI compile --strict-schema fails on schema violations."""
    scenario = tmp_path / "bad.yaml"
    scenario.write_text(
        """
id: bad_schema
domain: ecommerce
for_each: customer
entities:
  customer:
    count: 1
    type: customer
sources:
  - id: svc
    type: service
timeline:
  - at: "00:00:00"
    event: order.created
    source: svc
    entity_refs:
      customer: "$flow"
      order: "$new.order"
    attributes:
      currency: CNY
""",
        encoding="utf-8",
    )
    result = compile_scenario_file_strict(scenario, strict_schema=True)
    assert result.errors


def test_pack_validate_event_entity_refs() -> None:
    """pack validate reports unknown entity type referenced by event schema."""
    registry = PackRegistry()
    issues = registry.validate_pack("security")
    errors = [i for i in issues if i.startswith("ERROR:")]
    # security pack schemas should all reference known entity types.
    assert not any("references unknown entity type" in i for i in errors)


def test_existing_examples_pass_schema_validation() -> None:
    """Existing example scenarios compile without schema errors."""
    examples = [
        Path("examples/ecommerce/refund.yaml"),
        Path("examples/security/lateral_movement.yaml"),
    ]
    for example in examples:
        result = compile_scenario_file(example)
        assert result.errors == [], f"{example} produced errors: {result.errors}"
