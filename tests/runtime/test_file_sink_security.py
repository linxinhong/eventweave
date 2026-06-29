from pathlib import Path

import pytest

from eventweave.runtime.sinks.file import FileSink


def test_file_sink_allows_path_inside_output_dir(tmp_path: Path) -> None:
    sink = FileSink("out/events.jsonl", output_dir=tmp_path)
    assert sink.path == tmp_path / "out" / "events.jsonl"


def test_file_sink_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        FileSink("../etc/passwd", output_dir=tmp_path / "out")


def test_file_sink_rejects_absolute_path_outside_output_dir(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        FileSink("/etc/passwd", output_dir=tmp_path)


def test_file_sink_rejects_nested_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        FileSink("foo/../../etc/passwd", output_dir=tmp_path / "out")


def test_file_sink_allows_absolute_path_inside_output_dir(tmp_path: Path) -> None:
    target = tmp_path / "events.jsonl"
    sink = FileSink(target, output_dir=tmp_path)
    assert sink.path == target
