"""Unit tests for eventweave.core Pydantic models.

These tests protect the public contract used by the compiler, runtime,
evaluation and encoders. They focus on serialization, defaults and field
validation rather than business logic.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from eventweave.core.entity import Entity, EntityRef
from eventweave.core.event import Event
from eventweave.core.ground_truth import ExpectedFinding, GroundTruth
from eventweave.core.jitter import JitterConfig
from eventweave.core.noise import NoiseConfig, NoiseEventSpec
from eventweave.core.relation import Relation
from eventweave.core.runtime_plan import RuntimePlan
from eventweave.core.scenario import EntityTemplate, Scenario
from eventweave.core.semantic import (
    SemanticAsset,
    SemanticAssetMeta,
    SemanticPool,
    SemanticTask,
    SemanticTaskSpec,
)
from eventweave.core.sink import Sink
from eventweave.core.source import RatePolicy, Source, TimePolicy
from eventweave.core.timeline import TimelineItem

# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------


def test_entity_defaults_and_ref() -> None:
    entity = Entity(id="user_001", type="user")
    assert entity.id == "user_001"
    assert entity.type == "user"
    assert entity.domain is None
    assert entity.attributes == {}
    assert entity.tags == []
    assert isinstance(entity.created_at, datetime)
    assert entity.ref() == EntityRef(id="user_001", type="user")


def test_entity_serialization_roundtrip() -> None:
    entity = Entity(id="host_001", type="host", domain="security", tags=["vip"])
    data = entity.model_dump()
    restored = Entity.model_validate(data)
    assert restored.id == entity.id
    assert restored.type == entity.type
    assert restored.domain == entity.domain
    assert restored.tags == entity.tags


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


def test_event_defaults() -> None:
    now = datetime.now(UTC)
    event = Event(
        event_id="evt_001",
        scenario_id="sc_001",
        source_id="svc",
        event_type="order.created",
        event_time=now,
    )
    assert event.flow_id is None
    assert event.emit_time is None
    assert event.ingest_time is None
    assert event.entity_refs == {}
    assert event.attributes == {}
    assert event.semantic_refs == []
    assert event.labels == []
    assert event.ground_truth == {}
    assert isinstance(event.generated_at, datetime)


def test_event_roundtrip() -> None:
    event = Event(
        event_id="evt_002",
        scenario_id="sc_001",
        source_id="svc",
        event_type="order.paid",
        event_time=datetime.now(UTC),
        entity_refs={"order": "ord_001"},
        attributes={"amount": 100.0},
        semantic_refs=["sem_001"],
        labels=["key"],
        ground_truth={"is_key_event": True},
    )
    restored = Event.model_validate(event.model_dump())
    assert restored.event_id == event.event_id
    assert restored.entity_refs == event.entity_refs
    assert restored.attributes == event.attributes


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------


def test_scenario_minimal() -> None:
    scenario = Scenario(id="test", domain="common")
    assert scenario.version == "1.0"
    assert scenario.duration == "1h"
    assert scenario.entities == {}
    assert scenario.sources == []
    assert scenario.timeline == []
    assert scenario.rules == []


def test_scenario_realism_profile_shorthand() -> None:
    scenario = Scenario(
        id="test",
        domain="security",
        realism_profile="security.noisy",
    )
    assert scenario.realism is not None
    assert scenario.realism.profile == "security.noisy"


def test_scenario_realism_profile_conflict() -> None:
    with pytest.raises(ValidationError):
        Scenario(
            id="test",
            domain="security",
            realism_profile="security.noisy",
            realism={"profile": "security.noisy"},
        )


def test_scenario_with_timeline() -> None:
    scenario = Scenario(
        id="test",
        domain="ecommerce",
        entities={"customer": EntityTemplate(count=10)},
        sources=[Source(id="svc", type="service")],
        timeline=[TimelineItem(event="order.created")],
    )
    assert scenario.entities["customer"].count == 10
    assert len(scenario.sources) == 1
    assert len(scenario.timeline) == 1


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


def test_timeline_item_probability_bounds() -> None:
    item = TimelineItem(event="order.created", probability=0.5)
    assert item.probability == 0.5

    with pytest.raises(ValidationError):
        TimelineItem(event="order.created", probability=1.5)

    with pytest.raises(ValidationError):
        TimelineItem(event="order.created", probability=-0.1)


def test_timeline_item_repeat_bound() -> None:
    with pytest.raises(ValidationError):
        TimelineItem(event="order.created", repeat=0)


# ---------------------------------------------------------------------------
# Source / RatePolicy / TimePolicy
# ---------------------------------------------------------------------------


def test_source_defaults() -> None:
    source = Source(id="svc", type="service")
    assert source.rate.base_qps == 1.0
    assert source.rate.jitter == 0.0
    assert source.time_policy.mode == "realtime"
    assert source.time_policy.late_arrival_ratio == 0.0


def test_rate_policy_bounds() -> None:
    with pytest.raises(ValidationError):
        RatePolicy(base_qps=-1)

    with pytest.raises(ValidationError):
        RatePolicy(jitter=1.5)


def test_time_policy_bounds() -> None:
    with pytest.raises(ValidationError):
        TimePolicy(late_arrival_ratio=1.5)


# ---------------------------------------------------------------------------
# RuntimePlan
# ---------------------------------------------------------------------------


def test_runtime_plan_roundtrip() -> None:
    scenario = Scenario(id="test", domain="common")
    plan = RuntimePlan(scenario=scenario)
    assert plan.entities == []
    assert plan.events == []
    assert isinstance(plan.generated_at, datetime)
    restored = RuntimePlan.model_validate(plan.model_dump())
    assert restored.scenario.id == scenario.id


# ---------------------------------------------------------------------------
# Relation
# ---------------------------------------------------------------------------


def test_relation_alias() -> None:
    relation = Relation.model_validate(
        {"from": "user_001", "to": "order_001", "type": "created"}
    )
    assert relation.from_id == "user_001"
    assert relation.to_id == "order_001"
    data = relation.model_dump(by_alias=True)
    assert data["from"] == "user_001"
    assert data["to"] == "order_001"


# ---------------------------------------------------------------------------
# GroundTruth
# ---------------------------------------------------------------------------


def test_expected_finding_alias() -> None:
    finding = ExpectedFinding.model_validate(
        {"type": "lateral_movement", "evidence_events": ["evt_001"]}
    )
    assert finding.evidence_event_ids == ["evt_001"]


def test_ground_truth_derives_timeline_stages() -> None:
    gt = GroundTruth(
        scenario_id="sc_001",
        expected_findings=[
            ExpectedFinding(
                type="a", stage="initial_access", evidence_event_ids=["evt_001", "evt_002"]
            ),
            ExpectedFinding(type="b", stage="initial_access", evidence_event_ids=["evt_003"]),
        ],
    )
    assert len(gt.expected_timeline_stages) == 1
    stage = gt.expected_timeline_stages[0]
    assert stage.stage == "initial_access"
    assert stage.event_ids == ["evt_001", "evt_002", "evt_003"]


# ---------------------------------------------------------------------------
# Semantic
# ---------------------------------------------------------------------------


def test_semantic_task_defaults() -> None:
    task = SemanticTask(id="task_001", type="refund.reason")
    assert task.count == 1
    assert task.review_status == "pending"


def test_semantic_asset_valid_for_filter() -> None:
    pool = SemanticPool(
        scenario_id="sc_001",
        assets=[
            SemanticAsset(id="a1", type="reason", text="x", valid_for=["refund.requested"]),
            SemanticAsset(id="a2", type="reason", text="y", valid_for=["order.paid"]),
            SemanticAsset(id="a3", type="note", text="z"),
        ],
    )
    assert len(pool.by_type("reason")) == 2
    # Empty valid_for means applicable to all event types.
    assert len(pool.by_valid_for("refund.requested")) == 2
    assert {a.id for a in pool.by_valid_for("refund.requested")} == {"a1", "a3"}


def test_semantic_asset_meta_defaults() -> None:
    meta = SemanticAssetMeta()
    assert meta.review_status == "approved"
    assert isinstance(meta.created_at, datetime)


def test_semantic_task_spec_defaults() -> None:
    spec = SemanticTaskSpec(type="refund.reason")
    assert spec.inject is True


# ---------------------------------------------------------------------------
# Noise / Jitter / Sink
# ---------------------------------------------------------------------------


def test_noise_config_defaults() -> None:
    config = NoiseConfig()
    assert config.enabled is True
    assert config.ratio == 1.0


def test_noise_event_spec_requires_event() -> None:
    with pytest.raises(ValidationError):
        NoiseEventSpec(weight=2)


def test_jitter_config_defaults() -> None:
    config = JitterConfig()
    assert config.enabled is True
    assert config.max_offset == "10s"
    assert config.preserve_order is True


def test_sink_defaults() -> None:
    sink = Sink()
    assert sink.type == "jsonl"
    assert sink.path is None
    assert sink.url is None
