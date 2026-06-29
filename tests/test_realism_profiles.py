"""Tests for pack-level realism profiles."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from eventweave.cli.main import app
from eventweave.compiler import compile_scenario_file
from eventweave.compiler.errors import CompileError
from eventweave.compiler.pack_loader import PackRegistry
from eventweave.compiler.realism_resolver import RealismProfileResolver
from eventweave.core.noise import NoiseConfig
from eventweave.core.scenario import Scenario
from eventweave.pack.scaffold import scaffold_pack


def test_pack_registry_loads_realism_profiles() -> None:
    registry = PackRegistry()
    pack = registry.load("security")
    assert "endpoint_background" in pack.realism_profiles
    profile = pack.realism_profiles["endpoint_background"]
    assert profile.id == "endpoint_background"
    assert profile.noise is not None
    assert profile.jitter is not None


def test_pack_registry_loads_ecommerce_realism_profiles() -> None:
    registry = PackRegistry()
    pack = registry.load("ecommerce")
    assert "shopping_background" in pack.realism_profiles


def test_resolver_without_pack_prefix() -> None:
    scenario = Scenario(
        id="test",
        domain="security",
        realism_profile="endpoint_background",
    )
    registry = PackRegistry()
    noise, jitter = RealismProfileResolver(registry).resolve(scenario)
    assert noise is not None
    assert jitter is not None
    assert noise.ratio == 1.0
    assert jitter.max_offset == "5s"


def test_resolver_with_pack_prefix() -> None:
    scenario = Scenario(
        id="test",
        domain="ecommerce",
        realism_profile="security.endpoint_background",
    )
    registry = PackRegistry()
    noise, jitter = RealismProfileResolver(registry).resolve(scenario)
    assert noise is not None
    assert jitter is not None


def test_resolver_unknown_profile_raises() -> None:
    scenario = Scenario(
        id="test",
        domain="security",
        realism_profile="unknown_profile",
    )
    registry = PackRegistry()
    with pytest.raises(CompileError, match="Realism profile"):
        RealismProfileResolver(registry).resolve(scenario)


def test_scenario_noise_overrides_profile() -> None:
    scenario = Scenario(
        id="test",
        domain="security",
        realism_profile="endpoint_background",
        noise=NoiseConfig(enabled=True, ratio=99.0),
    )
    registry = PackRegistry()
    noise, _jitter = RealismProfileResolver(registry).resolve(scenario)
    assert noise is not None
    assert noise.ratio == 99.0


def test_realism_block_overrides_profile_noise() -> None:
    scenario = Scenario(
        id="test",
        domain="security",
        realism={
            "profile": "endpoint_background",
            "noise": {"enabled": True, "ratio": 7.0},
        },
    )
    registry = PackRegistry()
    noise, jitter = RealismProfileResolver(registry).resolve(scenario)
    assert noise is not None
    assert noise.ratio == 7.0
    assert jitter is not None
    assert jitter.max_offset == "5s"


def test_realism_profile_shorthand_normalized() -> None:
    scenario = Scenario(
        id="test",
        domain="security",
        realism_profile="endpoint_background",
    )
    assert scenario.realism is not None
    assert scenario.realism.profile == "endpoint_background"


def test_conflicting_realism_profile_and_block_rejected() -> None:
    with pytest.raises(ValueError, match="Cannot specify both"):
        Scenario(
            id="test",
            domain="security",
            realism_profile="endpoint_background",
            realism={"profile": "endpoint_background"},
        )


def test_security_benchmark_scenario_compiles_with_profile() -> None:
    result = compile_scenario_file(
        "examples/security/lateral_movement.yaml",
        seed=20260628,
    )
    assert result.ok
    assert any(
        e.ground_truth.get("noise") is True for e in result.plan.events
    )


def test_ecommerce_benchmark_scenario_compiles_with_profile() -> None:
    result = compile_scenario_file(
        "examples/ecommerce/refund_fraud_pattern.yaml",
        seed=20260628,
    )
    assert result.ok
    assert any(
        e.ground_truth.get("noise") is True for e in result.plan.events
    )


def test_pack_validate_security_passes() -> None:
    registry = PackRegistry()
    issues = registry.validate_pack("security")
    errors = [issue for issue in issues if issue.startswith("ERROR:")]
    assert not errors, issues


def test_pack_validate_ecommerce_passes() -> None:
    registry = PackRegistry()
    issues = registry.validate_pack("ecommerce")
    errors = [issue for issue in issues if issue.startswith("ERROR:")]
    assert not errors, issues


def test_pack_inspect_shows_realism_profile_count() -> None:
    result = CliRunner().invoke(app, ["pack", "inspect", "security"])
    assert result.exit_code == 0, result.output
    assert "Realism profiles" in result.output
    assert "1" in result.output


def test_scaffold_creates_realism_dir(tmp_path: Path) -> None:
    PackRegistry(packs_dir=tmp_path)
    scaffold_pack("mydomain", tmp_path)
    assert (tmp_path / "mydomain" / "realism").is_dir()
