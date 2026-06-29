"""Tests for the pack registry and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from eventweave.compiler.pack_loader import PackLoadError, PackRegistry


@pytest.fixture
def registry() -> PackRegistry:
    return PackRegistry()


def test_pack_list(registry: PackRegistry) -> None:
    packs = registry.list_packs()
    ids = {pack.id for pack in packs}
    assert "common" in ids
    assert "ecommerce" in ids
    assert "security" in ids


def test_pack_list_returns_metadata_only(registry: PackRegistry) -> None:
    packs = registry.list_packs()
    for pack in packs:
        assert pack.name
        assert pack.version
        # Entities should not be loaded for metadata listing.
        assert not pack.entities
        assert not pack.events


def test_pack_inspect_loads_full_pack(registry: PackRegistry) -> None:
    pack = registry.load("ecommerce")
    assert pack.id == "ecommerce"
    assert pack.name == "E-commerce"
    assert pack.entities
    assert pack.events
    assert pack.rules


def test_pack_validate_common(registry: PackRegistry) -> None:
    issues = registry.validate_pack("common")
    errors = [issue for issue in issues if issue.startswith("ERROR:")]
    assert not errors


def test_pack_validate_ecommerce(registry: PackRegistry) -> None:
    issues = registry.validate_pack("ecommerce")
    errors = [issue for issue in issues if issue.startswith("ERROR:")]
    assert not errors


def test_pack_validate_security(registry: PackRegistry) -> None:
    issues = registry.validate_pack("security")
    errors = [issue for issue in issues if issue.startswith("ERROR:")]
    assert not errors


def test_pack_security_encoder_metadata(registry: PackRegistry) -> None:
    pack = registry.load_metadata("security")
    names = {meta.name for meta in pack.encoders}
    assert "fortinet-fortigate" in names
    assert "nsfocus-ips" in names
    suricata = next(meta for meta in pack.encoders if meta.name == "suricata-eve")
    assert "alert.triggered" in suricata.supported_event_types


def test_pack_validate_examples_compile(registry: PackRegistry) -> None:
    # validate_pack already compiles examples; just assert no errors.
    issues = registry.validate_pack("ecommerce")
    errors = [issue for issue in issues if issue.startswith("ERROR:")]
    assert not errors


def test_pack_validate_missing_manifest(tmp_path: Path) -> None:
    registry = PackRegistry(packs_dir=tmp_path)
    (tmp_path / "badpack").mkdir()
    issues = registry.validate_pack("badpack")
    assert any("metadata missing" in issue for issue in issues)


def test_pack_validate_missing_dependency(tmp_path: Path) -> None:
    registry = PackRegistry(packs_dir=tmp_path)
    pack_dir = tmp_path / "badpack"
    pack_dir.mkdir()
    pack_dir.joinpath("pack.yaml").write_text(
        "id: badpack\nname: Bad Pack\nversion: '1.0'\ndepends_on:\n  - missing\n"
    )
    (pack_dir / "entities").mkdir()
    (pack_dir / "events").mkdir()
    pack_dir.joinpath("rules.yaml").write_text("rules: []\n")

    issues = registry.validate_pack("badpack")
    assert any("Dependency pack not found" in issue for issue in issues)


def test_pack_validate_invalid_event_schema(tmp_path: Path) -> None:
    registry = PackRegistry(packs_dir=tmp_path)
    pack_dir = tmp_path / "badpack"
    pack_dir.mkdir()
    pack_dir.joinpath("pack.yaml").write_text(
        "id: badpack\nname: Bad Pack\nversion: '1.0'\n"
    )
    (pack_dir / "entities").mkdir()
    events_dir = pack_dir / "events"
    events_dir.mkdir()
    events_dir.joinpath("bad.yaml").write_text(
        "bad.event:\n  type: wrong.type\n"
    )
    pack_dir.joinpath("rules.yaml").write_text("rules: []\n")

    issues = registry.validate_pack("badpack")
    assert any("type mismatch" in issue for issue in issues)


def test_pack_load_missing_pack() -> None:
    registry = PackRegistry(packs_dir=Path("/nonexistent"))
    with pytest.raises(PackLoadError):
        registry.load("missing")
