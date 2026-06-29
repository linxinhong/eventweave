"""Static validation tests for the local observability demo stack."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

DEMO_DIR = Path("examples/demo-stack")


def _read_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def test_demo_stack_files_exist() -> None:
    required = [
        DEMO_DIR / "security_demo.yaml",
        DEMO_DIR / "security_multi_source.yaml",
        DEMO_DIR / "docker-compose.yml",
        DEMO_DIR / "prometheus.yml",
        DEMO_DIR / "grafana" / "dashboards" / "eventweave-runtime.json",
        DEMO_DIR / "grafana" / "datasources" / "datasource.yml",
        DEMO_DIR / "receivers" / "http_sse_consumer.py",
        DEMO_DIR / "receivers" / "syslog_tcp_receiver.py",
        DEMO_DIR / "receivers" / "syslog_udp_receiver.py",
        DEMO_DIR / "run_demo.sh",
    ]
    for path in required:
        assert path.exists(), f"Missing demo stack file: {path}"


def test_demo_scenario_compiles(tmp_path: Path) -> None:
    scenario = DEMO_DIR / "security_demo.yaml"
    output_dir = tmp_path / "dist"
    result = subprocess.run(
        [".venv/bin/eventweave", "compile", str(scenario), "-o", str(output_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    plan_dir = output_dir / "security_demo_multi_source"
    assert (plan_dir / "runtime_plan.json").exists()
    assert (plan_dir / "ground_truth.json").exists()

    ground_truth = json.loads((plan_dir / "ground_truth.json").read_text(encoding="utf-8"))
    assert ground_truth["scenario_id"] == "security_demo_multi_source"
    assert len(ground_truth["expected_findings"]) > 0


def test_demo_server_config_loads() -> None:
    cfg = _read_yaml(DEMO_DIR / "security_multi_source.yaml")
    assert "servers" in cfg
    servers = cfg["servers"]
    assert len(servers) == 4
    ids = {s["id"] for s in servers}
    expected = {
        "firewall_syslog_udp",
        "edr_syslog_tcp",
        "waf_http",
        "dns_http",
    }
    assert ids == expected
    for server in servers:
        assert server["bind"] == "0.0.0.0"
        assert "source_filter" in server
        assert "source_id" in server["source_filter"]


def test_demo_prometheus_config_loads() -> None:
    cfg = _read_yaml(DEMO_DIR / "prometheus.yml")
    jobs = {job["job_name"] for job in cfg.get("scrape_configs", [])}
    assert "eventweave-runtime" in jobs
    assert "prometheus" in jobs

    runtime_job = next(
        job for job in cfg["scrape_configs"] if job["job_name"] == "eventweave-runtime"
    )
    targets = runtime_job["static_configs"][0]["targets"]
    assert "host.docker.internal:9090" in targets


def test_demo_grafana_dashboard_valid() -> None:
    dashboard_path = DEMO_DIR / "grafana" / "dashboards" / "eventweave-runtime.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))

    assert dashboard["uid"] == "eventweave-runtime"
    assert dashboard["title"] == "EventWeave Runtime"
    panels = dashboard.get("panels", [])
    titles = {p["title"] for p in panels}

    expected_titles = {
        "Events Emitted Rate",
        "Runtime Health",
        "Throughput (events/sec)",
        "Events Failed Rate",
        "Endpoint Events Rate",
        "Endpoint Failures Rate",
        "Worker Events Rate",
        "Batch Write Rate",
    }
    assert expected_titles.issubset(titles), f"Missing panels: {expected_titles - titles}"


def test_demo_docker_compose_config_valid() -> None:
    if shutil.which("docker") is None:
        pytest.skip("Docker not available")

    result = subprocess.run(
        ["docker", "compose", "-f", str(DEMO_DIR / "docker-compose.yml"), "config"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    cfg = yaml.safe_load(result.stdout) or {}
    services = cfg.get("services", {})
    expected = {
        "redpanda",
        "prometheus",
        "grafana",
        "http-sse-consumer",
        "syslog-tcp-receiver",
        "syslog-udp-receiver",
    }
    missing = expected - set(services.keys())
    assert not missing, f"Missing services: {missing}"


def test_demo_docs_commands_present() -> None:
    docs = Path("docs/demo-stack.md").read_text(encoding="utf-8")
    assert "make demo-stack" in docs
    assert "docker compose down" in docs
    assert "Grafana" in docs
    assert "Prometheus" in docs
    assert "Redpanda" in docs
