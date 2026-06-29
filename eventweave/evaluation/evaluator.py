"""Deterministic agent-output evaluator."""

from __future__ import annotations

from eventweave.core.ground_truth import ExpectedFinding, ExpectedTimelineStage, GroundTruth
from eventweave.evaluation.agent_output import AgentFinding, AgentOutput, AgentTimelineStage
from eventweave.evaluation.report import (
    EntityEventResult,
    EvaluationReport,
    ExtraFinding,
    FindingResult,
    MatchedFinding,
    MissedFinding,
)


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


def _precision(expected: list[str], actual: list[str]) -> float:
    """Compute set-intersection precision."""
    if not actual:
        return 1.0
    expected_set = {_normalize(item) for item in expected}
    actual_set = {_normalize(item) for item in actual}
    hits = len(expected_set & actual_set)
    return hits / len(actual_set)


def _match_finding(
    expected: ExpectedFinding,
    candidates: list[AgentFinding],
    consumed: set[int],
) -> tuple[AgentFinding | None, int | None]:
    """Find the first unconsumed agent finding matching expected type/stage."""
    expected_type = _normalize(expected.type)
    expected_stage = _normalize(expected.stage) if expected.stage is not None else None
    for index, candidate in enumerate(candidates):
        if index in consumed:
            continue
        if _normalize(candidate.type) != expected_type:
            continue
        if expected_stage is not None:
            candidate_stage = _normalize(candidate.stage) if candidate.stage is not None else None
            if candidate_stage != expected_stage:
                continue
        return candidate, index
    return None, None


def _stage_matches(expected: ExpectedFinding, matched: AgentFinding) -> bool:
    """Check whether the matched finding's stage aligns with the expected stage."""
    if expected.stage is None:
        return True
    if matched.stage is None:
        return False
    return _normalize(matched.stage) == _normalize(expected.stage)


def _match_timeline_stage(
    expected: ExpectedTimelineStage,
    candidates: list[AgentTimelineStage],
    consumed: set[int],
) -> tuple[AgentTimelineStage | None, int | None]:
    """Find the first unconsumed agent timeline stage matching the expected stage name."""
    expected_stage = _normalize(expected.stage)
    for index, candidate in enumerate(candidates):
        if index in consumed:
            continue
        if _normalize(candidate.stage) == expected_stage:
            return candidate, index
    return None, None


class Evaluator:
    """Compare an AgentOutput against a GroundTruth deterministically."""

    def __init__(self, ground_truth: GroundTruth, agent_output: AgentOutput) -> None:
        self.ground_truth = ground_truth
        self.agent_output = agent_output

    def evaluate(self) -> EvaluationReport:
        """Produce an EvaluationReport."""
        finding_results: list[FindingResult] = []
        matched_findings: list[MatchedFinding] = []
        missed_findings: list[MissedFinding] = []
        consumed: set[int] = set()

        staged_count = 0
        staged_matched_count = 0
        entity_recalls: list[float] = []
        entity_precisions: list[float] = []
        event_recalls: list[float] = []
        event_precisions: list[float] = []

        for expected in self.ground_truth.expected_findings:
            matched, index = _match_finding(
                expected, self.agent_output.findings, consumed
            )
            if matched is not None and index is not None:
                consumed.add(index)
                er = _recall(expected.entities, matched.entities)
                ep = _precision(expected.entities, matched.entities)
                evr = _recall(expected.evidence_event_ids, matched.evidence_event_ids)
                evp = _precision(expected.evidence_event_ids, matched.evidence_event_ids)
                entity_recalls.append(er)
                entity_precisions.append(ep)
                event_recalls.append(evr)
                event_precisions.append(evp)

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
                matched_findings.append(
                    MatchedFinding(
                        expected_type=expected.type,
                        expected_stage=expected.stage,
                        matched_type=matched.type,
                        matched_stage=matched.stage,
                        entity=EntityEventResult(recall=er, precision=ep),
                        event=EntityEventResult(recall=evr, precision=evp),
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
                missed_findings.append(
                    MissedFinding(
                        expected_type=expected.type,
                        expected_stage=expected.stage,
                    )
                )

            if expected.stage is not None:
                staged_count += 1
                if matched is not None and _stage_matches(expected, matched):
                    staged_matched_count += 1

        extra_findings: list[ExtraFinding] = [
            ExtraFinding(
                matched_type=finding.type,
                matched_stage=finding.stage,
            )
            for index, finding in enumerate(self.agent_output.findings)
            if index not in consumed
        ]

        # Timeline-stage evaluation
        (
            timeline_stage_recall,
            timeline_stage_precision,
            timeline_event_recall,
            timeline_event_precision,
            missed_stages,
            extra_stages,
        ) = self._evaluate_timeline_stages()

        total_findings = len(self.ground_truth.expected_findings)
        total_agent_findings = len(self.agent_output.findings)

        if total_findings == 0:
            finding_type_recall = 1.0
            entity_recall = 1.0
            event_id_recall = 1.0
            timeline_stage_accuracy = 1.0
            finding_type_precision = 1.0
            entity_precision = 1.0
            event_id_precision = 1.0
        else:
            matched_count = len(matched_findings)
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
            finding_type_precision = (
                len(matched_findings) / total_agent_findings
                if total_agent_findings else 1.0
            )
            entity_precision = (
                sum(entity_precisions) / len(entity_precisions)
                if entity_precisions
                else 0.0
            )
            event_id_precision = (
                sum(event_precisions) / len(event_precisions)
                if event_precisions
                else 0.0
            )

        overall_score = (
            finding_type_recall + entity_recall + event_id_recall + timeline_stage_accuracy
        ) / 4.0
        balanced_score = (
            finding_type_recall
            + entity_recall
            + event_id_recall
            + timeline_stage_accuracy
            + finding_type_precision
            + entity_precision
            + event_id_precision
        ) / 7.0

        metrics = {
            "finding_type_recall": finding_type_recall,
            "entity_recall": entity_recall,
            "event_id_recall": event_id_recall,
            "timeline_stage_accuracy": timeline_stage_accuracy,
            "timeline_stage_recall": timeline_stage_recall,
            "timeline_stage_precision": timeline_stage_precision,
            "timeline_event_recall": timeline_event_recall,
            "timeline_event_precision": timeline_event_precision,
            "finding_type_precision": finding_type_precision,
            "entity_precision": entity_precision,
            "event_id_precision": event_id_precision,
            "overall_score": overall_score,
            "balanced_score": balanced_score,
        }

        matched_stages = len(self.ground_truth.expected_timeline_stages) - len(missed_stages)
        total_stages = len(self.ground_truth.expected_timeline_stages)
        summary = (
            f"Matched {len(matched_findings)}/{total_findings} expected findings; "
            f"extra={len(extra_findings)}; "
            f"timeline_stages matched={matched_stages}/{total_stages}; "
            f"overall_score={overall_score:.2f}; "
            f"balanced_score={balanced_score:.2f}."
        )

        return EvaluationReport(
            scenario_id=self.ground_truth.scenario_id,
            metrics=metrics,
            finding_results=finding_results,
            matched_findings=matched_findings,
            missed_findings=missed_findings,
            extra_findings=extra_findings,
            summary=summary,
        )

    def _evaluate_timeline_stages(
        self,
    ) -> tuple[float, float, float, float, list[str], list[str]]:
        """Compare agent timeline stages against ground truth.

        Returns (stage_recall, stage_precision, event_recall, event_precision,
                 missed_stage_names, extra_stage_names).
        """
        expected_stages = self.ground_truth.expected_timeline_stages
        actual_stages = self.agent_output.timeline_stages

        if not expected_stages:
            if not actual_stages:
                return 1.0, 1.0, 1.0, 1.0, [], []
            return 0.0, 0.0, 0.0, 0.0, [], [stage.stage for stage in actual_stages]

        consumed: set[int] = set()
        matched_event_recalls: list[float] = []
        matched_event_precisions: list[float] = []
        missed_stages: list[str] = []

        for expected in expected_stages:
            matched, index = _match_timeline_stage(expected, actual_stages, consumed)
            if matched is not None and index is not None:
                consumed.add(index)
                matched_event_recalls.append(_recall(expected.event_ids, matched.event_ids))
                matched_event_precisions.append(
                    _precision(expected.event_ids, matched.event_ids)
                )
            else:
                missed_stages.append(expected.stage)

        extra_stages = [
            stage.stage for index, stage in enumerate(actual_stages) if index not in consumed
        ]

        matched_stage_count = len(expected_stages) - len(missed_stages)
        stage_recall = matched_stage_count / len(expected_stages)
        stage_precision = (
            matched_stage_count / len(actual_stages) if actual_stages else 0.0
        )
        event_recall = (
            sum(matched_event_recalls) / len(expected_stages)
            if expected_stages
            else 1.0
        )
        event_precision = (
            sum(matched_event_precisions) / len(matched_event_precisions)
            if matched_event_precisions
            else 0.0
        )

        return (
            stage_recall,
            stage_precision,
            event_recall,
            event_precision,
            missed_stages,
            extra_stages,
        )
