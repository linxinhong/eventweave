"""Deterministic synthetic realism report for compiled runtime plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean, pstdev
from typing import Any

from eventweave.core.event import Event
from eventweave.core.ground_truth import GroundTruth
from eventweave.core.runtime_plan import RuntimePlan


@dataclass
class RealismReport:
    """Statistical realism metrics for a compiled runtime plan."""

    scenario_id: str
    total_events: int
    ground_truth_events: int
    noise_events: int
    noise_ratio: float
    unique_entities: int
    unique_sources: int
    event_type_distribution: dict[str, int]
    timeline_duration_seconds: float
    events_per_minute: float
    burstiness_score: float
    ground_truth_coverage: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_text(self) -> str:
        lines = [
            "Realism Report",
            f"  Scenario: {self.scenario_id}",
            f"  Total events: {self.total_events}",
            f"  Ground truth events: {self.ground_truth_events}",
            f"  Noise events: {self.noise_events}",
            f"  Noise ratio: {self.noise_ratio:.2%}",
            f"  Unique entities: {self.unique_entities}",
            f"  Unique sources: {self.unique_sources}",
            f"  Event types: {len(self.event_type_distribution)}",
            f"  Timeline duration: {self.timeline_duration_seconds:.1f}s",
            f"  Events/min: {self.events_per_minute:.1f}",
            f"  Burstiness score: {self.burstiness_score:.3f}",
            f"  Ground truth coverage: {self.ground_truth_coverage:.2%}",
        ]
        return "\n".join(lines)


class RealismAnalyzer:
    """Analyze a compiled runtime plan for realism metrics."""

    def __init__(self, plan: RuntimePlan, ground_truth: GroundTruth | None = None) -> None:
        self.plan = plan
        self.ground_truth = ground_truth

    def analyze(self) -> RealismReport:
        events = self.plan.events
        total = len(events)

        noise_events = [e for e in events if e.ground_truth.get("noise") is True]
        key_events = [e for e in events if e.ground_truth.get("is_key_event") is True]
        noise_count = len(noise_events)
        key_count = len(key_events)

        noise_ratio = noise_count / total if total else 0.0

        entity_ids: set[str] = set()
        for event in events:
            entity_ids.update(event.entity_refs.values())

        source_ids = {e.source_id for e in events}
        event_type_distribution: dict[str, int] = {}
        for event in events:
            event_type_distribution[event.event_type] = (
                event_type_distribution.get(event.event_type, 0) + 1
            )

        duration_seconds = self._duration_seconds(events)
        events_per_minute = (total / duration_seconds * 60) if duration_seconds else 0.0
        burstiness = self._burstiness(events)

        coverage = self._ground_truth_coverage()

        return RealismReport(
            scenario_id=self.plan.scenario.id,
            total_events=total,
            ground_truth_events=key_count,
            noise_events=noise_count,
            noise_ratio=noise_ratio,
            unique_entities=len(entity_ids),
            unique_sources=len(source_ids),
            event_type_distribution=event_type_distribution,
            timeline_duration_seconds=duration_seconds,
            events_per_minute=events_per_minute,
            burstiness_score=burstiness,
            ground_truth_coverage=coverage,
        )

    def _duration_seconds(self, events: list[Event]) -> float:
        if not events:
            return 0.0
        times = [e.event_time for e in events]
        min_time = min(times)
        max_time = max(times)
        return (max_time - min_time).total_seconds()

    def _burstiness(self, events: list[Event]) -> float:
        """Coefficient of variation of per-minute event counts."""
        if not events:
            return 0.0
        times = sorted(e.event_time for e in events)
        if len(times) == 1:
            return 0.0
        start = times[0]
        buckets: dict[int, int] = {}
        for t in times:
            minute = int((t - start).total_seconds() // 60)
            buckets[minute] = buckets.get(minute, 0) + 1

        counts = list(buckets.values())
        if not counts:
            return 0.0
        avg = mean(counts)
        if avg == 0:
            return 0.0
        std = pstdev(counts)
        return std / avg

    def _ground_truth_coverage(self) -> float:
        if self.ground_truth is None:
            return 0.0
        findings = self.ground_truth.expected_findings
        if not findings:
            return 0.0
        covered = sum(1 for f in findings if f.evidence_event_ids)
        return covered / len(findings)
