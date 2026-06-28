"""Scaffold new domain packs."""

from __future__ import annotations

import shutil
from pathlib import Path


class ScaffoldError(Exception):
    """Raised when scaffolding fails."""


def _pack_yaml(pack_id: str, name: str) -> str:
    return f"""id: {pack_id}
name: {name}
version: "0.1.0"
description: Synthetic event schemas for the {pack_id} domain.
depends_on:
  - common
entities_path: entities
events_path: events
rules_path: rules.yaml
semantic_path: semantic
examples_path: examples
"""


def _entity_yaml() -> str:
    return """thing:
  description: A domain entity.
  fields:
    name:
      type: string
      required: true
"""


def _event_yaml() -> str:
    return """thing.created:
  description: A thing is created.
  entity_refs:
    thing: thing
  fields:
    status:
      type: string
      enum:
        - active
        - inactive
      default: active
"""


def _rules_yaml() -> str:
    return """rules:
  - id: thing_requires_ref
    type: required_entity_ref
    description: thing.created must reference a thing.
    attributes:
      event: thing.created
      ref: thing
"""


def _example_yaml(pack_id: str) -> str:
    return f"""id: {pack_id}_basic_flow
name: {pack_id.replace("_", " ").title()} Basic Flow
domain: {pack_id}
duration: 1m
seed: 20260628
for_each: thing

entities:
  thing:
    count: 3
    type: thing

sources:
  - id: {pack_id}-source
    type: service
    role: event_source
    rate:
      base_qps: 1
    outputs:
      - type: jsonl
        path: ./out/{pack_id}.jsonl

timeline:
  - id: create_thing
    event: thing.created
    source: {pack_id}-source
    at: "00:00:00"
    entity_refs:
      thing: "$flow"
"""


def scaffold_pack(pack_id: str, packs_dir: Path, force: bool = False) -> Path:
    """Create a new pack skeleton and return the pack path.

    Args:
        pack_id: Pack identifier. Must be a valid directory name.
        packs_dir: Parent directory containing packs.
        force: Overwrite an existing directory.

    Returns:
        Path to the created pack directory.

    Raises:
        ScaffoldError: If the pack already exists and force is False.
    """
    pack_path = packs_dir / pack_id
    if pack_path.exists() and not force:
        raise ScaffoldError(f"Pack already exists: {pack_path}")
    if pack_path.exists() and force:
        shutil.rmtree(pack_path)

    name = f"{pack_id.replace('_', ' ').title()} Pack"

    (pack_path / "entities").mkdir(parents=True, exist_ok=True)
    (pack_path / "events").mkdir(parents=True, exist_ok=True)
    (pack_path / "semantic").mkdir(parents=True, exist_ok=True)
    (pack_path / "examples").mkdir(parents=True, exist_ok=True)

    (pack_path / "pack.yaml").write_text(_pack_yaml(pack_id, name), encoding="utf-8")
    (pack_path / "entities" / "thing.yaml").write_text(_entity_yaml(), encoding="utf-8")
    (pack_path / "events" / "thing.yaml").write_text(_event_yaml(), encoding="utf-8")
    (pack_path / "rules.yaml").write_text(_rules_yaml(), encoding="utf-8")
    (pack_path / "examples" / "basic.yaml").write_text(
        _example_yaml(pack_id), encoding="utf-8"
    )

    return pack_path
