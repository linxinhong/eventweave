"""Tests for the deterministic evaluator."""

from __future__ import annotations

from eventweave.core.ground_truth import ExpectedFinding, GroundTruth
from eventweave.evaluation.agent_output import AgentFinding, AgentOutput, AgentTimelineStage
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


def test_perfect_match() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(
                type="suspicious_login",
                stage="initial_access",
                entities=["user_001", "host_001"],
                evidence_event_ids=["evt-001"],
            ),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        findings=[
            AgentFinding(
                type="suspicious_login",
                stage="initial_access",
                entities=["host_001", "user_001"],
                evidence_event_ids=["evt-001"],
            ),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["finding_type_recall"] == 1.0
    assert report.metrics["entity_recall"] == 1.0
    assert report.metrics["event_id_recall"] == 1.0
    assert report.metrics["timeline_stage_accuracy"] == 1.0
    assert report.metrics["overall_score"] == 1.0


def test_partial_match_missing_finding() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(type="suspicious_login", stage="initial_access"),
            ExpectedFinding(type="lateral_movement", stage="lateral_movement"),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        findings=[
            AgentFinding(type="suspicious_login", stage="initial_access"),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["finding_type_recall"] == 0.5
    assert report.metrics["timeline_stage_accuracy"] == 0.5
    assert report.finding_results[0].matched is True
    assert report.finding_results[1].matched is False


def test_entity_and_event_recall_partial() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(
                type="suspicious_login",
                entities=["user_001", "host_001"],
                evidence_event_ids=["evt-001", "evt-002"],
            ),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        findings=[
            AgentFinding(
                type="suspicious_login",
                entities=["user_001"],
                evidence_event_ids=["evt-001"],
            ),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["finding_type_recall"] == 1.0
    assert report.metrics["entity_recall"] == 0.5
    assert report.metrics["event_id_recall"] == 0.5


def test_empty_agent_output() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(type="suspicious_login", stage="initial_access"),
        ]
    )
    ao = AgentOutput(scenario_id="test_scenario")
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["finding_type_recall"] == 0.0
    assert report.metrics["entity_recall"] == 0.0
    assert report.metrics["event_id_recall"] == 0.0
    assert report.metrics["timeline_stage_accuracy"] == 0.0


def test_empty_ground_truth() -> None:
    gt = _make_ground_truth()
    ao = AgentOutput(
        scenario_id="test_scenario",
        findings=[AgentFinding(type="suspicious_login")],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["finding_type_recall"] == 1.0
    assert report.metrics["timeline_stage_accuracy"] == 1.0
    assert report.metrics["overall_score"] == 1.0


def test_stage_mismatch_does_not_match() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(type="suspicious_login", stage="initial_access"),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        findings=[
            AgentFinding(type="suspicious_login", stage="execution"),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["finding_type_recall"] == 0.0
    assert report.metrics["timeline_stage_accuracy"] == 0.0


def test_case_insensitive_matching() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(
                type="Suspicious Login",
                stage="Initial Access",
                entities=["USER_001"],
                evidence_event_ids=["EVT-001"],
            ),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        findings=[
            AgentFinding(
                type="suspicious login",
                stage="initial access",
                entities=["user_001"],
                evidence_event_ids=["evt-001"],
            ),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["overall_score"] == 1.0


def test_timeline_stages_derived_from_findings() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(
                type="suspicious_login",
                stage="initial_access",
                evidence_event_ids=["evt-001"],
            ),
        ]
    )
    assert any(stage.stage == "initial_access" for stage in gt.expected_timeline_stages)


def test_timeline_stage_metrics_perfect() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(
                type="suspicious_login",
                stage="initial_access",
                evidence_event_ids=["evt-001", "evt-002"],
            ),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        timeline_stages=[
            AgentTimelineStage(stage="initial_access", event_ids=["evt-002", "evt-001"]),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["timeline_stage_recall"] == 1.0
    assert report.metrics["timeline_stage_precision"] == 1.0
    assert report.metrics["timeline_event_recall"] == 1.0
    assert report.metrics["timeline_event_precision"] == 1.0


def test_timeline_stage_metrics_partial() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(
                type="suspicious_login",
                stage="initial_access",
                evidence_event_ids=["evt-001", "evt-002", "evt-003"],
            ),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        timeline_stages=[
            AgentTimelineStage(stage="initial_access", event_ids=["evt-001"]),
            AgentTimelineStage(stage="extra_stage", event_ids=["evt-999"]),
        ],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["timeline_stage_recall"] == 1.0
    assert report.metrics["timeline_stage_precision"] == 0.5
    assert report.metrics["timeline_event_recall"] == 1 / 3
    assert report.metrics["timeline_event_precision"] == 1.0


def test_timeline_stage_metrics_missing() -> None:
    gt = _make_ground_truth(
        expected_findings=[
            ExpectedFinding(
                type="suspicious_login",
                stage="initial_access",
                evidence_event_ids=["evt-001"],
            ),
        ]
    )
    ao = AgentOutput(
        scenario_id="test_scenario",
        timeline_stages=[AgentTimelineStage(stage="execution", event_ids=["evt-001"])],
    )
    report = Evaluator(gt, ao).evaluate()
    assert report.metrics["timeline_stage_recall"] == 0.0
    assert report.metrics["timeline_event_recall"] == 0.0
