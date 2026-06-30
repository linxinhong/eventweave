"""Tests for the encoder registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from eventweave.core.event import Event
from eventweave.encoders import GO_ENCODER_NAMES
from eventweave.encoders.base import Encoder, EncodeResult
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


def test_encoder_get_info() -> None:
    enc = get_encoder("nginx-access")
    info = enc.get_info()
    assert info["name"] == "nginx-access"
    assert "remote_addr" in info["required_fields"]
    assert "http.request" in info["supported_event_types"]


def test_go_encoder_names_include_security_encoders() -> None:
    assert "fortinet-fortigate" in GO_ENCODER_NAMES
    assert "nsfocus-ips" in GO_ENCODER_NAMES


def test_encode_inspect_all_registered_encoders() -> None:
    """Every registered encoder must expose metadata without crashing."""
    for name in list_encoders():
        enc = get_encoder(name)
        info = enc.get_info()
        assert info["name"] == name
        assert isinstance(info["content_type"], str)
        assert isinstance(info["description"], str)
        assert isinstance(info["required_fields"], list)
        assert isinstance(info["optional_fields"], list)
        assert isinstance(info["supported_event_types"], list)


def test_encoder_with_base_defaults_get_info() -> None:
    """Encoder subclasses that rely on base-class defaults must not crash."""

    class DefaultOnlyEncoder(Encoder):
        name = "default-only"
        content_type = "text/plain"

        def encode(self, event: Event) -> EncodeResult:
            return self._ok("")

    info = DefaultOnlyEncoder().get_info()
    assert info["name"] == "default-only"
    assert info["required_fields"] == []
    assert info["optional_fields"] == []
    assert info["supported_event_types"] == []


def test_get_encoder_unknown_fails_cleanly() -> None:
    """Unknown encoder names raise a clear KeyError."""
    with pytest.raises(KeyError, match="Unknown encoder: no-such-encoder"):
        get_encoder("no-such-encoder")
