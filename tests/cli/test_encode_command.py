"""Tests for the `eventweave encode` CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path

from eventweave.core.event import Event


def _write_plan(plan_dir: Path, attributes: dict[str, object] | None = None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    event = Event(
        event_id="evt-001",
        scenario_id="test",
        source_id="nginx",
        event_type="http.request",
        event_time="2026-06-29T12:00:00+00:00",
        attributes=attributes
        or {
            "remote_addr": "192.168.1.1",
            "request": "GET / HTTP/1.1",
            "status": 200,
            "body_bytes_sent": 42,
        },
    )
    (plan_dir / "event_plan.jsonl").write_text(
        event.model_dump_json() + "\n", encoding="utf-8"
    )


def test_encode_list() -> None:
    result = subprocess.run(
        [".venv/bin/eventweave", "encode", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "nginx-access" in result.stdout
    assert "suricata-eve" in result.stdout


def test_encode_nginx(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    _write_plan(plan_dir)
    output = tmp_path / "out.log"
    result = subprocess.run(
        [
            ".venv/bin/eventweave",
            "encode",
            "run",
            str(plan_dir),
            "--encoder",
            "nginx-access",
            "--output",
            "out.log",
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "192.168.1.1" in lines[0]


def test_encode_missing_required_field(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    _write_plan(plan_dir, attributes={"remote_addr": "192.168.1.1"})
    result = subprocess.run(
        [
            ".venv/bin/eventweave",
            "encode",
            "run",
            str(plan_dir),
            "--encoder",
            "nginx-access",
            "--output",
            "out.log",
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "missing required fields" in (result.stdout + result.stderr)


def test_encode_inspect() -> None:
    result = subprocess.run(
        [".venv/bin/eventweave", "encode", "inspect", "nginx-access"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "remote_addr" in result.stdout
    assert "body_bytes_sent" in result.stdout
    assert "python" in result.stdout


def test_encode_preflight_pass(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    _write_plan(plan_dir)
    result = subprocess.run(
        [
            ".venv/bin/eventweave",
            "encode",
            "preflight",
            str(plan_dir),
            "--encoder",
            "nginx-access",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Encodable" in result.stdout
    assert "Failed       │ 0" in result.stdout


def test_encode_preflight_fail(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    _write_plan(plan_dir, attributes={"remote_addr": "192.168.1.1"})
    result = subprocess.run(
        [
            ".venv/bin/eventweave",
            "encode",
            "preflight",
            str(plan_dir),
            "--encoder",
            "nginx-access",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Failed" in result.stdout


def test_encode_run_with_enrich(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    event = Event(
        event_id="evt-001",
        scenario_id="test",
        source_id="firewall",
        event_type="firewall.traffic",
        event_time="2026-06-29T12:00:00+00:00",
        attributes={"src_ip": "10.0.0.1", "dest_ip": "10.0.0.2"},
    )
    (plan_dir / "event_plan.jsonl").write_text(
        event.model_dump_json() + "\n", encoding="utf-8"
    )
    output = tmp_path / "out.log"
    result = subprocess.run(
        [
            ".venv/bin/eventweave",
            "encode",
            "run",
            str(plan_dir),
            "--encoder",
            "fortinet-fortigate",
            "--enrich",
            "--output",
            "out.log",
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "10.0.0.1" in lines[0]
    assert "firewall-01" in lines[0]


def test_encode_preflight_enrich_improves_encodable_count(tmp_path: Path) -> None:
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    event = Event(
        event_id="evt-001",
        scenario_id="test",
        source_id="firewall",
        event_type="firewall.traffic",
        event_time="2026-06-29T12:00:00+00:00",
        attributes={},
    )
    (plan_dir / "event_plan.jsonl").write_text(
        event.model_dump_json() + "\n", encoding="utf-8"
    )
    result = subprocess.run(
        [
            ".venv/bin/eventweave",
            "encode",
            "preflight",
            str(plan_dir),
            "--encoder",
            "fortinet-fortigate",
            "--enrich",
            "--compare-enrichment",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "without enrichment" in result.stdout
    assert "0.0% -> 100.0%" in result.stdout
