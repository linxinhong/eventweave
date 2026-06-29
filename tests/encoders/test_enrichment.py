"""Tests for encoder field enrichment."""

from __future__ import annotations

from pathlib import Path

import yaml

from eventweave.core.event import Event
from eventweave.encoders.enrichment import (
    EnrichmentProfile,
    EnrichmentRegistry,
    enrich_event,
)


def _make_event(**attrs: object) -> Event:
    return Event(
        event_id="evt-001",
        scenario_id="test",
        source_id="sensor",
        event_type="network.connection",
        event_time="2026-06-29T12:00:00+00:00",
        attributes=attrs,
    )


def test_enrichment_applies_defaults() -> None:
    profile = EnrichmentProfile(
        encoder="fortinet-fortigate",
        defaults={"devname": "firewall-01", "action": "accept"},
    )
    event = _make_event(srcip="10.0.0.1", dstip="10.0.0.2")
    enriched = enrich_event(event, profile)

    assert enriched.attributes["devname"] == "firewall-01"
    assert enriched.attributes["action"] == "accept"
    assert enriched.attributes["srcip"] == "10.0.0.1"


def test_enrichment_applies_field_mappings() -> None:
    profile = EnrichmentProfile(
        encoder="fortinet-fortigate",
        mappings={"srcip": "src_ip", "dstip": "dest_ip"},
    )
    event = _make_event(src_ip="10.0.0.1", dest_ip="10.0.0.2")
    enriched = enrich_event(event, profile)

    assert enriched.attributes["srcip"] == "10.0.0.1"
    assert enriched.attributes["dstip"] == "10.0.0.2"


def test_enrichment_does_not_mutate_canonical_event() -> None:
    profile = EnrichmentProfile(
        encoder="fortinet-fortigate",
        defaults={"devname": "firewall-01"},
        mappings={"srcip": "src_ip"},
    )
    event = _make_event(src_ip="10.0.0.1")
    original_attrs = dict(event.attributes)

    enriched = enrich_event(event, profile)

    assert event.attributes == original_attrs
    assert "devname" not in event.attributes
    assert "srcip" not in event.attributes
    assert "devname" in enriched.attributes
    assert "srcip" in enriched.attributes


def test_enrichment_preserves_existing_target() -> None:
    profile = EnrichmentProfile(
        encoder="fortinet-fortigate",
        defaults={"srcip": "0.0.0.0"},
        mappings={"srcip": "src_ip"},
    )
    event = _make_event(src_ip="10.0.0.1", srcip="192.168.1.1")
    enriched = enrich_event(event, profile)

    assert enriched.attributes["srcip"] == "192.168.1.1"


def test_enrichment_mapping_priority_over_defaults() -> None:
    profile = EnrichmentProfile(
        encoder="fortinet-fortigate",
        defaults={"srcip": "0.0.0.0"},
        mappings={"srcip": "src_ip"},
    )
    event = _make_event(src_ip="10.0.0.1")
    enriched = enrich_event(event, profile)

    assert enriched.attributes["srcip"] == "10.0.0.1"


def test_enrichment_registry_loads_from_packs(tmp_path: Path) -> None:
    packs_dir = tmp_path / "packs"
    encoders_dir = packs_dir / "security" / "encoders"
    encoders_dir.mkdir(parents=True)
    enrichment_file = encoders_dir / "enrichment.yaml"
    enrichment_file.write_text(
        yaml.safe_dump(
            {
                "profiles": {
                    "fortinet-fortigate": {
                        "defaults": {"devname": "firewall-01"},
                        "mappings": {"srcip": "src_ip"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    registry = EnrichmentRegistry(packs_dir)
    profile = registry.get("fortinet-fortigate")

    assert profile is not None
    assert profile.defaults["devname"] == "firewall-01"
    assert profile.mappings["srcip"] == "src_ip"
    assert registry.get("unknown") is None


def test_enrichment_registry_list(tmp_path: Path) -> None:
    packs_dir = tmp_path / "packs"
    encoders_dir = packs_dir / "test" / "encoders"
    encoders_dir.mkdir(parents=True)
    (encoders_dir / "enrichment.yaml").write_text(
        yaml.safe_dump(
            {
                "profiles": {
                    "encoder-a": {"defaults": {"a": 1}},
                    "encoder-b": {"defaults": {"b": 2}},
                }
            }
        ),
        encoding="utf-8",
    )

    registry = EnrichmentRegistry(packs_dir)
    assert registry.list_profiles() == ["encoder-a", "encoder-b"]
