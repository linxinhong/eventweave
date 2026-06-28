from eventweave.ai.resolver import SemanticResolver
from eventweave.core.event import Event
from eventweave.core.semantic import SemanticAsset, SemanticAssetMeta, SemanticPool


def _event(event_id: str, event_type: str) -> Event:
    return Event(
        event_id=event_id,
        scenario_id="sc1",
        source_id="src1",
        event_type=event_type,
        event_time="2024-01-01T00:00:00Z",
    )


def _asset(asset_id: str, task_id: str, event_id: str | None = None) -> SemanticAsset:
    return SemanticAsset(
        id=asset_id,
        type="greeting",
        text="hello",
        meta=SemanticAssetMeta(
            source_task=task_id,
            source_event=event_id,
        ),
    )


def test_resolve_event_with_matching_asset():
    pool = SemanticPool(
        scenario_id="sc1",
        assets=[_asset("a1", "t1", "e1")],
    )
    resolver = SemanticResolver(pool)
    event = _event("e1", "login")
    event.semantic_refs = ["semantic://t1"]

    resolved = resolver.resolve_event(event)
    assert resolved.semantic_refs == ["a1"]


def test_resolve_event_without_matching_asset():
    pool = SemanticPool(scenario_id="sc1", assets=[])
    resolver = SemanticResolver(pool)
    event = _event("e1", "login")
    event.semantic_refs = ["semantic://t1"]

    resolved = resolver.resolve_event(event)
    assert resolved.semantic_refs == []


def test_resolve_event_clears_task_placeholders():
    pool = SemanticPool(
        scenario_id="sc1",
        assets=[_asset("a1", "t1", "e1"), _asset("a2", "t2", "e1")],
    )
    resolver = SemanticResolver(pool)
    event = _event("e1", "login")
    event.semantic_refs = ["semantic://t1"]

    resolved = resolver.resolve_event(event)
    assert resolved.semantic_refs == ["a1", "a2"]


def test_resolve_events_keeps_non_matching_events():
    pool = SemanticPool(
        scenario_id="sc1",
        assets=[_asset("a1", "t1", "e1")],
    )
    resolver = SemanticResolver(pool)
    event1 = _event("e1", "login")
    event1.semantic_refs = ["semantic://t1"]
    event2 = _event("e2", "logout")
    event2.semantic_refs = ["semantic://t1"]

    resolved = resolver.resolve_events([event1, event2])
    assert resolved[0].semantic_refs == ["a1"]
    assert resolved[1].semantic_refs == []


def test_stats():
    pool = SemanticPool(
        scenario_id="sc1",
        assets=[_asset("a1", "t1", "e1")],
    )
    resolver = SemanticResolver(pool)
    event1 = _event("e1", "login")
    event1.semantic_refs = ["semantic://t1"]
    event2 = _event("e2", "logout")
    event2.semantic_refs = ["semantic://t1"]

    # Stats measure placeholder resolution before resolving events.
    stats = resolver.stats([event1, event2])
    assert stats["resolved"] == 0
    assert stats["unresolved"] == 2
    assert stats["total_assets"] == 1
