"""Tests for evaluation precision and matched/missed/extra details."""

from __future__ import annotations

from pathlib import Path

from eventweave.compiler import compile_scenario_file
from eventweave.compiler.writer import PlanWriter
from eventweave.core.ground_truth import ExpectedFinding, GroundTruth
from eventweave.evaluation.agent_output import AgentFinding, AgentOutput
from eventweave.evaluation.evaluator import Evaluator


def _make_ground_truth(**overrides: object) -> GroundTruth:
    defaults = {
        "scenario_id": "test_scenario",
        "expected_findings": [],
        "expected_summary": None,
        "key_event_ids": [],
        "attributes": {},
    }
    defaults.update(overrides)
    return GroundTruth(**defaults)  # type: ignore[arg-type]


def test_extra_finding_reduces_precision() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(type="suspicious_login", stage="initial_access"),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        findings=[
            AgentFinding(type="suspicious_login", stage="initial_access"),
            AgentFinding(type="fake_finding", stage="execution"),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["finding_type_recall"] == 1.0
    assert report.metrics["finding_type_precision"] == 0.5
    assert len(report.extra_findings) == 1
    assert report.extra_findings[0].matched_type == "fake_finding"


def test_wrong_event_id_reduces_event_precision() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(
                type="suspicious_login",
                evidence_event_ids=["evt-001"],
            ),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        findings=[
            AgentFinding(
                type="suspicious_login",
                evidence_event_ids=["evt-001", "evt-999"],
            ),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["event_id_recall"] == 1.0
    assert report.metrics["event_id_precision"] == 0.5


def test_matched_missed_extra_findings() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(type="a", stage="s1"),
            ExpectedFinding(type="b", stage="s2"),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        findings=[
            AgentFinding(type="a", stage="s1"),
            AgentFinding(type="c", stage="s3"),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert len(report.matched_findings) == 1
    assert len(report.missed_findings) == 1
    assert report.missed_findings[0].expected_type == "b"
    assert len(report.extra_findings) == 1
    assert report.extra_findings[0].matched_type == "c"


def test_ground_truth_accepts_evidence_event_ids() -> None:
    gt = GroundTruth(
        scenario_id="s",
        expected_findings=[
            {"type": "x", "evidence_event_ids": ["evt-001"]},
        ],
    )
    assert gt.expected_findings[0].evidence_event_ids == ["evt-001"]


def test_ground_truth_legacy_evidence_events_alias() -> None:
    gt = GroundTruth(
        scenario_id="s",
        expected_findings=[
            {"type": "x", "evidence_events": ["evt-001"]},
        ],
    )
    assert gt.expected_findings[0].evidence_event_ids == ["evt-001"]


def test_balanced_score_combines_recall_and_precision() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(type="a"),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        findings=[
            AgentFinding(type="a"),
            AgentFinding(type="b"),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["finding_type_recall"] == 1.0
    assert report.metrics["finding_type_precision"] == 0.5
    assert 0.0 < report.metrics["balanced_score"] < 1.0


def test_sample_agent_output_scores_1_0(tmp_path: Path) -> None:
    """Sample agent output for security_lateral_movement should score perfectly."""
    scenario_path = Path("examples/security/lateral_movement.yaml")
    ao_path = Path("examples/evaluation/security_lateral_movement_agent_output.json")
    assert scenario_path.exists(), f"Scenario not found: {scenario_path}"
    assert ao_path.exists(), f"Sample agent output not found: {ao_path}"

    result = compile_scenario_file(
        scenario_path, packs_dir=Path("packs"), seed=20260628
    )
    assert result.ok, result.errors

    plan_dir = tmp_path / result.plan.scenario.id
    PlanWriter(plan_dir).write(result.plan, semantic_tasks=result.semantic_tasks)
    gt_path = plan_dir / "ground_truth.json"
    assert gt_path.exists(), f"Ground truth not written: {gt_path}"

    gt = GroundTruth.model_validate_json(gt_path.read_text(encoding="utf-8"))
    ao = AgentOutput.model_validate_json(ao_path.read_text(encoding="utf-8"))
    report = Evaluator(gt, ao).evaluate()

    assert report.metrics["overall_score"] == 1.0
    assert report.metrics["balanced_score"] == 1.0
    assert len(report.missed_findings) == 0
    assert len(report.extra_findings) == 0
