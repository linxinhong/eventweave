"""Tests for the encoder registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from eventweave.encoders.registry import EncoderRegistry, get_encoder, list_encoders


def test_list_encoders_includes_builtins_and_packs() -> None:
    names = list_encoders()
    assert "jsonl" in names
    assert "syslog-rfc3164" in names
    assert "nginx-access" in names
    assert "suricata-eve" in names
    assert "windows-event-json" in names


def test_get_encoder_unknown() -> None:
    with pytest.raises(KeyError):
        get_encoder("no-such-encoder")


def test_registry_custom_packs_dir(tmp_path: Path) -> None:
    registry = EncoderRegistry(packs_dir=tmp_path)
    # A fresh registry starts empty; built-ins are registered into the default
    # global registry via the @encoder decorator.
    assert registry.list() == []
