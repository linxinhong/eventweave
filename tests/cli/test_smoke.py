"""Smoke tests for main eventweave CLI commands.

These tests exercise the happy path of the most important CLI commands to
guard against argument-parsing regressions and broken entry points.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from eventweave.core.event import Event

PROJECT_ROOT = Path(__file__).parent.parent.parent
EVENTWEAVE = PROJECT_ROOT / ".venv" / "bin" / "eventweave"


def _run(
    *args: str | Path,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(EVENTWEAVE), *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd or PROJECT_ROOT,
        env={**os.environ, **(env or {})},
    )
    return result


def _write_simple_plan(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    event = Event(
        event_id="evt-001",
        scenario_id="smoke",
        source_id="nginx",
        event_type="http.request",
        event_time="2026-06-29T12:00:00+00:00",
        attributes={
            "remote_addr": "192.168.1.1",
            "request": "GET / HTTP/1.1",
            "status": 200,
            "body_bytes_sent": 42,
        },
    )
    (plan_dir / "event_plan.jsonl").write_text(
        event.model_dump_json() + "\n", encoding="utf-8"
    )


def test_validate_example_scenario() -> None:
    result = _run("validate", "examples/ecommerce/refund.yaml")
    assert result.returncode == 0, result.stderr
    assert "Valid" in result.stdout or "Entities:" in result.stdout


def test_compile_example_scenario(tmp_path: Path) -> None:
    output_dir = tmp_path / "dist"
    result = _run(
        "compile",
        "examples/ecommerce/refund.yaml",
        "-o",
        output_dir,
        "--force",
    )
    assert result.returncode == 0, result.stderr
    plan_dir = output_dir / "ecommerce_refund_flow"
    assert (plan_dir / "event_plan.jsonl").exists()
    assert (plan_dir / "runtime_plan.json").exists()


def test_run_compiled_plan(tmp_path: Path) -> None:
    output_dir = tmp_path / "dist"
    compile_result = _run(
        "compile",
        "examples/ecommerce/refund.yaml",
        "-o",
        output_dir,
        "--force",
    )
    assert compile_result.returncode == 0, compile_result.stderr

    plan_dir = output_dir / "ecommerce_refund_flow"
    result = _run("run", plan_dir, "--sink", "null", "--no-wait")
    assert result.returncode == 0, result.stderr
    assert "emitted" in result.stdout.lower()


def test_encode_list() -> None:
    result = _run("encode", "list")
    assert result.returncode == 0, result.stderr
    assert "jsonl" in result.stdout
    assert "syslog-rfc3164" in result.stdout


def test_encode_inspect_all_encoders() -> None:
    result = _run("encode", "list")
    assert result.returncode == 0, result.stderr
    for name in result.stdout.strip().splitlines():
        inspect_result = _run("encode", "inspect", name)
        assert inspect_result.returncode == 0, (
            f"encode inspect {name} failed: {inspect_result.stderr}"
        )
        assert name in inspect_result.stdout


def test_encode_preflight(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    _write_simple_plan(plan_dir)
    result = _run("encode", "preflight", plan_dir, "--encoder", "nginx-access")
    assert result.returncode == 0, result.stderr
    assert "Encodable" in result.stdout


def test_eval_prepare(tmp_path: Path) -> None:
    output_dir = tmp_path / "dist"
    result = _run(
        "eval",
        "prepare",
        "examples/security/lateral_movement.yaml",
        "-o",
        output_dir,
        "--force",
    )
    assert result.returncode == 0, result.stderr
    plan_dir = output_dir / "security_lateral_movement"
    assert (plan_dir / "ground_truth.json").exists()


def test_benchmark_validate(tmp_path: Path) -> None:
    output_dir = tmp_path / "dist"
    suite_path = PROJECT_ROOT / "benchmarks" / "security.yaml"
    for scenario in [
        "examples/security/lateral_movement.yaml",
        "examples/security/brute_force_login.yaml",
        "examples/security/dns_exfiltration.yaml",
        "examples/security/malware_callback.yaml",
    ]:
        result = _run("eval", "prepare", scenario, "-o", output_dir, "--force")
        assert result.returncode == 0, result.stderr

    result = _run(
        "benchmark",
        "validate",
        "--suite",
        suite_path,
        env={"EVENTWEAVE_PLAN_DIR": str(output_dir)},
    )
    assert result.returncode == 0, result.stderr
    assert "passed" in result.stdout.lower()


def test_pack_validate_ecommerce() -> None:
    result = _run("pack", "validate", "ecommerce")
    assert result.returncode == 0, result.stderr


def test_pack_validate_security() -> None:
    result = _run("pack", "validate", "security")
    assert result.returncode == 0, result.stderr


def test_pack_validate_all_packs_pass() -> None:
    """All domain packs now contain enough content to pass validation."""
    for pack in ["common", "ecommerce", "security", "saas", "iot", "devops", "hospital"]:
        result = _run("pack", "validate", pack)
        assert result.returncode == 0, f"pack validate {pack} failed: {result.stderr}"


def test_pack_validate_unknown_pack_fails() -> None:
    """Unknown pack names fail validation."""
    result = _run("pack", "validate", "not-a-pack")
    assert result.returncode != 0, result.stderr


def test_http_allow_internal_url_warns(tmp_path: Path) -> None:
    """--allow-internal-url prints a security warning."""
    output_dir = tmp_path / "dist"
    compile_result = _run(
        "compile",
        "examples/ecommerce/refund.yaml",
        "-o",
        output_dir,
        "--force",
    )
    assert compile_result.returncode == 0, compile_result.stderr

    plan_dir = output_dir / "ecommerce_refund_flow"
    result = _run(
        "run",
        plan_dir,
        "--sink",
        "http",
        "--url",
        "http://127.0.0.1:1/events",
        "--allow-internal-url",
        "--no-wait",
        "--limit",
        "1",
        "--timeout",
        "0.1",
        "--retries",
        "0",
    )
    combined = result.stdout + result.stderr
    assert "--allow-internal-url disables SSRF protection" in combined
