"""Tests for the pack scaffold command."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from eventweave.compiler.engine import compile_scenario_file
from eventweave.compiler.pack_loader import PackRegistry
from eventweave.pack.scaffold import ScaffoldError, scaffold_pack


@pytest.fixture
def scaffold_registry(tmp_path: Path) -> PackRegistry:
    """Create a registry in a temp dir that also contains the common pack."""
    source_common = Path(__file__).parent.parent / "packs" / "common"
    target_common = tmp_path / "common"
    shutil.copytree(source_common, target_common)
    return PackRegistry(packs_dir=tmp_path)


def test_pack_scaffold_creates_expected_files(scaffold_registry: PackRegistry) -> None:
    pack_path = scaffold_pack("mydomain", scaffold_registry.packs_dir)

    assert pack_path.exists()
    assert (pack_path / "pack.yaml").exists()
    assert (pack_path / "entities" / "thing.yaml").exists()
    assert (pack_path / "events" / "thing.yaml").exists()
    assert (pack_path / "rules.yaml").exists()
    assert (pack_path / "semantic").is_dir()
    assert (pack_path / "examples" / "basic.yaml").exists()


def test_pack_scaffold_generated_pack_validates(scaffold_registry: PackRegistry) -> None:
    scaffold_pack("mydomain", scaffold_registry.packs_dir)
    issues = scaffold_registry.validate_pack("mydomain")
    errors = [issue for issue in issues if issue.startswith("ERROR:")]
    assert not errors, issues


def test_pack_scaffold_example_compiles(scaffold_registry: PackRegistry) -> None:
    scaffold_pack("mydomain", scaffold_registry.packs_dir)
    example_path = scaffold_registry.packs_dir / "mydomain" / "examples" / "basic.yaml"
    result = compile_scenario_file(example_path, packs_dir=scaffold_registry.packs_dir)
    assert not result.errors, result.errors


def test_pack_scaffold_existing_dir_fails(scaffold_registry: PackRegistry) -> None:
    scaffold_pack("mydomain", scaffold_registry.packs_dir)
    with pytest.raises(ScaffoldError):
        scaffold_pack("mydomain", scaffold_registry.packs_dir, force=False)


def test_pack_scaffold_force_overwrites(scaffold_registry: PackRegistry) -> None:
    scaffold_pack("mydomain", scaffold_registry.packs_dir)
    marker = scaffold_registry.packs_dir / "mydomain" / "marker.txt"
    marker.write_text("old", encoding="utf-8")

    scaffold_pack("mydomain", scaffold_registry.packs_dir, force=True)
    assert not marker.exists()
    assert (scaffold_registry.packs_dir / "mydomain" / "pack.yaml").exists()
