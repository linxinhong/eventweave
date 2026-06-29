"""Shared fixtures for evaluation tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def compiled_benchmark_plans(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Compile all benchmark scenarios once and point EVENTWEAVE_PLAN_DIR at them."""
    dist_dir = tmp_path_factory.mktemp("dist")

    scenario_paths = [
        "examples/security/lateral_movement.yaml",
        "examples/security/brute_force_login.yaml",
        "examples/security/dns_exfiltration.yaml",
        "examples/security/malware_callback.yaml",
        "examples/ecommerce/refund.yaml",
        "examples/ecommerce/payment_failure_spike.yaml",
        "examples/ecommerce/refund_fraud_pattern.yaml",
    ]

    from eventweave.compiler import compile_scenario_file
    from eventweave.compiler.writer import PlanWriter

    packs_dir = Path("packs")
    for path_str in scenario_paths:
        path = Path(path_str)
        result = compile_scenario_file(path, packs_dir=packs_dir, seed=20260628)
        if result.errors:
            raise RuntimeError(f"Failed to compile {path}: {result.errors}")
        PlanWriter(dist_dir / result.plan.scenario.id).write(
            result.plan, semantic_tasks=result.semantic_tasks
        )

    os.environ["EVENTWEAVE_PLAN_DIR"] = str(dist_dir)
    return dist_dir
