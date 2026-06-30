#!/usr/bin/env python3
"""Regenerate golden baseline files for stable compiler-output scenarios."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from repository root without installation.
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from eventweave.compiler.engine import compile_scenario_file
from eventweave.compiler.writer import PlanWriter

# Scenarios that are part of the committed golden baseline.
GOLDEN_SCENARIOS: list[tuple[str, str]] = [
    ("examples/ecommerce/refund.yaml", "ecommerce_refund_flow"),
    ("examples/security/lateral_movement.yaml", "security_lateral_movement"),
]

SEED = 20260628


def update_golden() -> int:
    """Compile each golden scenario and overwrite the baseline files."""
    packs_dir = project_root / "packs"
    golden_root = project_root / "tests" / "golden"
    exit_code = 0

    for scenario_rel, scenario_id in GOLDEN_SCENARIOS:
        scenario_path = project_root / scenario_rel
        output_dir = golden_root / scenario_id
        print(f"Compiling {scenario_rel} -> {output_dir.relative_to(project_root)}")

        result = compile_scenario_file(
            scenario_path,
            packs_dir=packs_dir,
            seed=SEED,
        )

        if result.errors:
            print(f"  errors: {len(result.errors)}", file=sys.stderr)
            for error in result.errors:
                print(f"    - {error}", file=sys.stderr)
            exit_code = 1
            continue

        writer = PlanWriter(output_dir, force=True)
        writer.write(result.plan, result.semantic_tasks)

        if result.warnings:
            print(f"  warnings: {len(result.warnings)}")
            for warning in result.warnings[:10]:
                print(f"    - {warning}")
            if len(result.warnings) > 10:
                print(f"    ... and {len(result.warnings) - 10} more")

        print(f"  wrote {len(result.plan.events)} events")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(update_golden())
