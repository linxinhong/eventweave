"""Tests for timeline planner."""

from __future__ import annotations

from eventweave.compiler.planner import TimelineExpander
from eventweave.core.scenario import Scenario
from eventweave.core.timeline import TimelineItem


class TestTimelineExpander:
    def test_for_each_infer_warning(self) -> None:
        scenario = Scenario(
            id="test",
            domain="test",
            entities={"order": {"count": 2, "type": "order"}},
            timeline=[
                TimelineItem(id="create", event="order.created"),
            ],
        )
        from eventweave.core.entity import Entity

        entities = [
            Entity(id="order_001", type="order", domain="test"),
            Entity(id="order_002", type="order", domain="test"),
        ]
        expander = TimelineExpander(scenario, entities)
        events, _relations, warnings = expander.expand()

        assert len(events) == 2
        assert any("for_each is not set" in w for w in warnings)

    def test_explicit_for_each_no_warning(self) -> None:
        scenario = Scenario(
            id="test",
            domain="test",
            for_each="order",
            entities={"order": {"count": 2, "type": "order"}},
            timeline=[
                TimelineItem(id="create", event="order.created"),
            ],
        )
        from eventweave.core.entity import Entity

        entities = [
            Entity(id="order_001", type="order", domain="test"),
            Entity(id="order_002", type="order", domain="test"),
        ]
        expander = TimelineExpander(scenario, entities)
        events, _relations, warnings = expander.expand()

        assert len(events) == 2
        assert not any("for_each is not set" in w for w in warnings)

    def test_ref_resolution(self) -> None:
        scenario = Scenario(
            id="test",
            domain="test",
            for_each="order",
            entities={"order": {"count": 1, "type": "order"}},
            timeline=[
                TimelineItem(
                    id="create",
                    event="order.created",
                    entity_refs={"order": "$flow"},
                ),
                TimelineItem(
                    id="pay",
                    after="create",
                    event="order.paid",
                    entity_refs={"order": "$ref.create.order"},
                ),
            ],
        )
        from eventweave.core.entity import Entity

        entities = [Entity(id="order_001", type="order", domain="test")]
        expander = TimelineExpander(scenario, entities)
        events, _relations, _warnings = expander.expand()

        assert len(events) == 2
        pay_event = next(e for e in events if e.event_type == "order.paid")
        assert pay_event.entity_refs["order"] == "order_001"

    def test_event_time_ordering(self) -> None:
        scenario = Scenario(
            id="test",
            domain="test",
            for_each="order",
            entities={"order": {"count": 3, "type": "order"}},
            timeline=[
                TimelineItem(id="create", event="order.created"),
            ],
        )
        from eventweave.core.entity import Entity

        entities = [
            Entity(id="order_001", type="order", domain="test"),
            Entity(id="order_002", type="order", domain="test"),
            Entity(id="order_003", type="order", domain="test"),
        ]
        expander = TimelineExpander(scenario, entities)
        events, _relations, _warnings = expander.expand()

        # All create events share the same absolute time, so they should be sorted
        # stably by event_id.
        event_ids = [e.event_id for e in events]
        assert event_ids == sorted(event_ids)
