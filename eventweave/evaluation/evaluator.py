"""Deterministic agent-output evaluator."""

from __future__ import annotations

from eventweave.core.ground_truth import ExpectedFinding, GroundTruth
from eventweave.evaluation.agent_output import AgentFinding, AgentOutput
from eventweave.evaluation.report import EvaluationReport, FindingResult


def _normalize(value: str) -> str:
    """Normalize a string for deterministic comparison."""
    return value.strip().lower()


def _recall(expected: list[str], actual: list[str]) -> float:
    """Compute set-intersection recall."""
    if not expected:
        return 1.0
    expected_set = {_normalize(item) for item in expected}
    actual_set = {_normalize(item) for item in actual}
    hits = len(expected_set & actual_set)
    return hits / len(expected_set)


def _match_finding(
    expected: ExpectedFinding,
    candidates: list[AgentFinding],
) -> AgentFinding | None:
    """Find the first agent finding matching expected type and optional stage."""
    expected_type = _normalize(expected.type)
    expected_stage = _normalize(expected.stage) if expected.stage is not None else None
    for candidate in candidates:
        if _normalize(candidate.type) != expected_type:
            continue
        if expected_stage is not None:
            candidate_stage = _normalize(candidate.stage) if candidate.stage is not None else None
            if candidate_stage != expected_stage:
                continue
        return candidate
    return None


class Evaluator:
    """Compare an AgentOutput against a GroundTruth deterministically."""

    def __init__(self, ground_truth: GroundTruth, agent_output: AgentOutput) -> None:
        self.ground_truth = ground_truth
        self.agent_output = agent_output

    def evaluate(self) -> EvaluationReport:
        """Produce an EvaluationReport."""
        finding_results: list[FindingResult] = []
        matched_count = 0
        staged_count = 0
        staged_matched_count = 0
        entity_recalls: list[float] = []
        event_recalls: list[float] = []

        for expected in self.ground_truth.expected_findings:
            matched = _match_finding(expected, self.agent_output.findings)
            if matched is not None:
                matched_count += 1
                er = _recall(expected.entities, matched.entities)
                evr = _recall(expected.evidence_events, matched.evidence_event_ids)
                entity_recalls.append(er)
                event_recalls.append(evr)
                finding_results.append(
                    FindingResult(
                        expected_type=expected.type,
                        expected_stage=expected.stage,
                        matched=True,
                        matched_type=matched.type,
                        matched_stage=matched.stage,
                        entity_recall=er,
                        event_recall=evr,
                    )
                )
            else:
                finding_results.append(
                    FindingResult(
                        expected_type=expected.type,
                        expected_stage=expected.stage,
                        matched=False,
                    )
                )

            if expected.stage is not None:
                staged_count += 1
                if matched is not None and (
                    _normalize(matched.stage) == _normalize(expected.stage)
                    if matched.stage is not None
                    else False
                ):
                    staged_matched_count += 1

        total_findings = len(self.ground_truth.expected_findings)
        if total_findings == 0:
            finding_type_recall = 1.0
            entity_recall = 1.0
            event_id_recall = 1.0
            timeline_stage_accuracy = 1.0
        else:
            finding_type_recall = matched_count / total_findings
            entity_recall = (
                sum(entity_recalls) / len(entity_recalls) if entity_recalls else 0.0
            )
            event_id_recall = (
                sum(event_recalls) / len(event_recalls) if event_recalls else 0.0
            )
            timeline_stage_accuracy = (
                1.0 if staged_count == 0 else staged_matched_count / staged_count
            )
        overall_score = (
            finding_type_recall + entity_recall + event_id_recall + timeline_stage_accuracy
        ) / 4.0

        metrics = {
            "finding_type_recall": finding_type_recall,
            "entity_recall": entity_recall,
            "event_id_recall": event_id_recall,
            "timeline_stage_accuracy": timeline_stage_accuracy,
            "overall_score": overall_score,
        }

        summary = (
            f"Matched {matched_count}/{total_findings} expected findings; "
            f"overall_score={overall_score:.2f}."
        )

        return EvaluationReport(
            scenario_id=self.ground_truth.scenario_id,
            metrics=metrics,
            finding_results=finding_results,
            summary=summary,
        )
