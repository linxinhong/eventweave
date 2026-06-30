
"""Pack schema validation for compiled runtime plans.

This module compares the concrete entities and events produced by the planner
against the schemas declared in domain packs. By default mismatches are emitted
as warnings so existing scenarios keep compiling. Use ``strict=True`` to turn
schema violations into errors.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any

from eventweave.compiler.pack_loader import EntitySchema, EventSchema, FieldSchema, Pack
from eventweave.core.entity import Entity
from eventweave.core.event import Event
from eventweave.core.runtime_plan import RuntimePlan

# Valid primitive types declared in pack schemas.
_VALID_TYPES = {"string", "number", "integer", "boolean"}

# Reserved runtime entity-ref role injected by the timeline expander.
_INTERNAL_FLOW_ROLE = "flow"

# Supported formats and simple validators.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_email(value: Any) -> bool:
    return isinstance(value, str) and bool(_EMAIL_RE.match(value))


def _is_ipv4(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        ipaddress.IPv4Address(value)
        return True
    except ipaddress.AddressValueError:
        return False


def _check_type(value: Any, declared: str | None) -> bool:
    """Return True if value matches the declared primitive type."""
    if declared is None:
        return True
    if declared == "string":
        return isinstance(value, str)
    if declared == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "boolean":
        return isinstance(value, bool)
    # Unknown declared types are allowed through; they may be extensions.
    return True


def _check_format(value: Any, fmt: str | None) -> bool:
    """Return True if value satisfies the declared format."""
    if fmt is None:
        return True
    if fmt == "email":
        return _is_email(value)
    if fmt == "ipv4":
        return _is_ipv4(value)
    return True


def _check_field(
    name: str,
    value: Any,
    schema: FieldSchema,
) -> list[str]:
    """Validate a single field value against its schema."""
    issues: list[str] = []
    if schema.type and schema.type not in _VALID_TYPES:
        # Internal schema issue; report once at schema load time, not here.
        return issues
    if not _check_type(value, schema.type):
        issues.append(
            f"field {name!r} expected type {schema.type!r}, got {type(value).__name__}"
        )
        return issues
    if not _check_format(value, schema.format):
        issues.append(f"field {name!r} does not match format {schema.format!r}")
    if schema.enum is not None and value not in schema.enum:
        issues.append(f"field {name!r}={value!r} not in allowed values {schema.enum}")
    return issues


class SchemaValidator:
    """Validate a compiled runtime plan against pack schemas."""

    def __init__(self, packs: dict[str, Pack], strict: bool = False) -> None:
        self.packs = packs
        self.strict = strict
        self._event_schemas: dict[str, EventSchema] = {}
        self._entity_schemas: dict[str, EntitySchema] = {}
        for pack in packs.values():
            self._event_schemas.update(pack.events)
            self._entity_schemas.update(pack.entities)

    def validate(self, plan: RuntimePlan) -> tuple[list[str], list[str]]:
        """Return (warnings, errors) for schema issues in *plan*.

        When ``self.strict`` is True, all schema issues are returned as errors.
        """
        warnings: list[str] = []
        errors: list[str] = []

        entity_by_id = {entity.id: entity for entity in plan.entities}

        for event in plan.events:
            event_issues = self._validate_event(event, entity_by_id)
            self._add_issues(
                f"Event {event.event_id!r} ({event.event_type})",
                event_issues,
                warnings,
                errors,
            )

        for entity in plan.entities:
            entity_issues = self._validate_entity(entity)
            self._add_issues(
                f"Entity {entity.id!r} ({entity.type})",
                entity_issues,
                warnings,
                errors,
            )

        return warnings, errors

    def _add_issues(
        self,
        prefix: str,
        issues: list[str],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        for issue in issues:
            message = f"{prefix}: {issue}"
            if self.strict:
                errors.append(message)
            else:
                warnings.append(message)

    def _validate_event(
        self,
        event: Event,
        entity_by_id: dict[str, Entity],
    ) -> list[str]:
        """Validate a single event against its pack schema."""
        issues: list[str] = []
        schema = self._event_schemas.get(event.event_type)
        if schema is None:
            return [f"unknown event_type {event.event_type!r}"]

        # Required / known field checks.
        for field_name, field_schema in schema.fields.items():
            if field_schema.required and field_name not in event.attributes:
                issues.append(f"missing required field {field_name!r}")
                continue
            value = event.attributes.get(field_name)
            if value is not None:
                issues.extend(_check_field(field_name, value, field_schema))

        for field_name in event.attributes:
            if field_name not in schema.fields:
                issues.append(f"unknown field {field_name!r}")

        # Entity refs checks.
        for role, expected_type in schema.entity_refs.items():
            entity_id = event.entity_refs.get(role)
            if not entity_id:
                issues.append(f"missing required entity ref {role!r}")
                continue
            referenced = entity_by_id.get(entity_id)
            if referenced is None:
                issues.append(f"entity ref {role!r}={entity_id!r} does not exist")
                continue
            if referenced.type != expected_type:
                issues.append(
                    f"entity ref {role!r} expected type {expected_type!r}, got {referenced.type!r}"
                )

        for role in event.entity_refs:
            if role == _INTERNAL_FLOW_ROLE:
                continue
            if role not in schema.entity_refs:
                issues.append(f"unknown entity ref role {role!r}")

        return issues

    def _validate_entity(self, entity: Entity) -> list[str]:
        """Validate a single entity against its pack schema."""
        issues: list[str] = []
        schema = self._entity_schemas.get(entity.type)
        if schema is None:
            return [f"unknown entity type {entity.type!r}"]

        for field_name, field_schema in schema.fields.items():
            if field_schema.required and field_name not in entity.attributes:
                issues.append(f"missing required field {field_name!r}")
                continue
            value = entity.attributes.get(field_name)
            if value is not None:
                issues.extend(_check_field(field_name, value, field_schema))

        for field_name in entity.attributes:
            if field_name not in schema.fields:
                issues.append(f"unknown field {field_name!r}")

        return issues
