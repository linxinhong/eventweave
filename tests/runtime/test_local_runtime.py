import json
from pathlib import Path

from eventweave.core.event import Event
from eventweave.runtime.local import LocalRuntime
from eventweave.runtime.sinks.file import FileSink
from eventweave.runtime.sinks.null import NullSink


def _event(event_id: str, event_type: str, t: str, refs: list[str] | None = None) -> Event:
    return Event(
        event_id=event_id,
        scenario_id="sc1",
        source_id="src1",
        event_type=event_type,
        event_time=t,
        semantic_refs=refs or [],
    )


def _write_plan(tmp_path: Path, events: list[Event]) -> Path:
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    event_plan = plan_dir / "event_plan.jsonl"
    with event_plan.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(event.model_dump_json() + "\n")
    return plan_dir


def test_local_runtime_loads_event_plan(tmp_path):
    plan_dir = _write_plan(
        tmp_path,
        [
            _event("e1", "login", "2024-01-01T00:00:00Z"),
            _event("e2", "logout", "2024-01-01T00:00:01Z"),
        ],
    )
    sink = NullSink()
    runtime = LocalRuntime(plan_dir, sink=sink, no_wait=True)
    stats = runtime.run()
    assert stats.emitted == 2
    assert sink.count() == 2


def test_null_sink_counts_events(tmp_path):
    plan_dir = _write_plan(tmp_path, [_event("e1", "login", "2024-01-01T00:00:00Z")])
    sink = NullSink()
    runtime = LocalRuntime(plan_dir, sink=sink, no_wait=True)
    runtime.run()
    assert sink.count() == 1


def test_file_sink_writes_jsonl(tmp_path):
    plan_dir = _write_plan(
        tmp_path,
        [
            _event("e1", "login", "2024-01-01T00:00:00Z"),
            _event("e2", "logout", "2024-01-01T00:00:01Z"),
        ],
    )
    output = tmp_path / "out.jsonl"
    sink = FileSink(output, output_dir=tmp_path)
    runtime = LocalRuntime(plan_dir, sink=sink, no_wait=True)
    runtime.run()

    lines = output.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["event_id"] == "e1"
    assert json.loads(lines[1])["event_id"] == "e2"


def test_no_wait_runs_without_sleep(tmp_path):
    plan_dir = _write_plan(
        tmp_path,
        [
            _event("e1", "login", "2024-01-01T00:00:00Z"),
            _event("e2", "logout", "2024-01-01T01:00:00Z"),
        ],
    )
    sink = NullSink()
    runtime = LocalRuntime(plan_dir, sink=sink, no_wait=True)
    stats = runtime.run()
    assert stats.emitted == 2
    assert stats.duration < 1.0


def test_runtime_warns_unresolved_semantic_refs(tmp_path):
    plan_dir = _write_plan(
        tmp_path,
        [
            _event("e1", "login", "2024-01-01T00:00:00Z", refs=["semantic://task1"]),
        ],
    )
    sink = NullSink()
    runtime = LocalRuntime(plan_dir, sink=sink, no_wait=True)
    stats = runtime.run()
    assert stats.unresolved_refs == 1


def test_runtime_does_not_mutate_events(tmp_path):
    events = [_event("e1", "login", "2024-01-01T00:00:00Z", refs=["asset1"])]
    plan_dir = _write_plan(tmp_path, events)
    sink = NullSink()
    runtime = LocalRuntime(plan_dir, sink=sink, no_wait=True)
    runtime.run()
    assert events[0].semantic_refs == ["asset1"]
    assert events[0].event_id == "e1"


def test_run_limit(tmp_path):
    plan_dir = _write_plan(
        tmp_path,
        [
            _event("e1", "login", "2024-01-01T00:00:00Z"),
            _event("e2", "login", "2024-01-01T00:00:01Z"),
            _event("e3", "login", "2024-01-01T00:00:02Z"),
        ],
    )
    sink = NullSink()
    runtime = LocalRuntime(plan_dir, sink=sink, no_wait=True, limit=2)
    stats = runtime.run()
    assert stats.emitted == 2
    assert sink.count() == 2


def test_runtime_stats_success_failure_counts(tmp_path):
    plan_dir = _write_plan(
        tmp_path,
        [_event("e1", "login", "2024-01-01T00:00:00Z")],
    )
    sink = NullSink()
    runtime = LocalRuntime(plan_dir, sink=sink, no_wait=True)
    stats = runtime.run()
    assert stats.emitted == 1
    assert stats.failed == 0
