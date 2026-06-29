"""Tests for v0.9.1 security vendor encoders."""

from __future__ import annotations

import json

import pytest

from eventweave.core.event import Event
from packs.security.encoders import (
    DBAPPSecurityWAFEncoder,
    DnsJsonEncoder,
    FortinetFortigateEncoder,
    H3CSecPathEncoder,
    HillstoneNGFWEncoder,
    HuaweiUSGEncoder,
    NSFOCUSIPSEncoder,
    PaloAltoTrafficEncoder,
    QianxinNGFWEncoder,
    SangforAFEncoder,
    TopsecNGFWEncoder,
    ZeekConnEncoder,
    ZeekDNSEncoder,
)


def make_event(**attrs: object) -> Event:
    base = {
        "event_id": "evt-001",
        "scenario_id": "test",
        "source_id": "sensor",
        "event_type": "alert",
        "event_time": "2026-06-29T12:00:00+00:00",
    }
    return Event(attributes=attrs, **base)


def test_fortinet_basic() -> None:
    event = make_event(
        devname="fw-01",
        type="traffic",
        subtype="forward",
        srcip="10.0.0.5",
        dstip="8.8.8.8",
        action="accept",
        service="HTTPS",
    )
    result = FortinetFortigateEncoder().encode(event)
    assert result.success
    assert 'devname="fw-01"' in result.output
    assert "action=\"accept\"" in result.output


def test_fortinet_missing() -> None:
    result = FortinetFortigateEncoder().encode(make_event(devname="fw-01"))
    assert not result.success


def test_paloalto_basic() -> None:
    event = make_event(
        receive_time="2026/06/29 12:00:30",
        serial="001234567890",
        src="10.0.0.5",
        dst="8.8.8.8",
        sport=54321,
        dport=443,
        proto="tcp",
        action="allow",
    )
    result = PaloAltoTrafficEncoder().encode(event)
    assert result.success
    parts = result.output.split(",")
    assert parts[0] == "2026/06/29 12:00:30"
    assert "allow" in parts


def test_paloalto_missing() -> None:
    result = PaloAltoTrafficEncoder().encode(make_event(serial="x"))
    assert not result.success


def test_zeek_conn_basic() -> None:
    event = make_event(
        uid="C1234567890abcdef",
        **{
            "id.orig_h": "10.0.0.5",
            "id.orig_p": 54321,
            "id.resp_h": "8.8.8.8",
            "id.resp_p": 443,
            "proto": "tcp",
        },
    )
    result = ZeekConnEncoder().encode(event)
    assert result.success
    parts = result.output.split("\t")
    assert parts[1] == "C1234567890abcdef"


def test_zeek_conn_missing() -> None:
    result = ZeekConnEncoder().encode(make_event(uid="x"))
    assert not result.success


def test_zeek_dns_basic() -> None:
    event = make_event(
        uid="C1234567890abcdef",
        **{
            "id.orig_h": "10.0.0.5",
            "id.orig_p": 12345,
            "id.resp_h": "8.8.8.8",
            "id.resp_p": 53,
            "query": "example.com",
        },
        qtype_name="A",
    )
    result = ZeekDNSEncoder().encode(event)
    assert result.success
    assert "example.com" in result.output


def test_dns_json_basic() -> None:
    event = make_event(client_ip="10.0.0.5", query="example.com", qtype="A")
    result = DnsJsonEncoder().encode(event)
    assert result.success
    parsed = json.loads(result.output)
    assert parsed["client_ip"] == "10.0.0.5"
    assert parsed["query"] == "example.com"


def test_dns_json_missing() -> None:
    result = DnsJsonEncoder().encode(make_event())
    assert not result.success


def test_sangfor_basic() -> None:
    event = make_event(devname="af-01", srcip="10.0.0.5", dstip="8.8.8.8", action="allow")
    result = SangforAFEncoder().encode(event)
    assert result.success
    assert "sangfor_devname=\"af-01\"" in result.output


def test_huawei_basic() -> None:
    event = make_event(devname="usg-01", srcip="10.0.0.5", dstip="8.8.8.8", action="allow")
    result = HuaweiUSGEncoder().encode(event)
    assert result.success
    assert "huawei_devname=\"usg-01\"" in result.output


def test_h3c_basic() -> None:
    event = make_event(devname="secpath-01", srcip="10.0.0.5", dstip="8.8.8.8", action="allow")
    result = H3CSecPathEncoder().encode(event)
    assert result.success
    assert "h3c_devName=\"secpath-01\"" in result.output


def test_topsec_basic() -> None:
    event = make_event(devname="topsec-01", srcip="10.0.0.5", dstip="8.8.8.8", action="allow")
    result = TopsecNGFWEncoder().encode(event)
    assert result.success
    assert "topsec_devname=\"topsec-01\"" in result.output


def test_qianxin_basic() -> None:
    event = make_event(devname="qx-01", srcip="10.0.0.5", dstip="8.8.8.8", action="allow")
    result = QianxinNGFWEncoder().encode(event)
    assert result.success
    assert "qianxin_dev_name=\"qx-01\"" in result.output


def test_hillstone_basic() -> None:
    event = make_event(devname="hill-01", srcip="10.0.0.5", dstip="8.8.8.8", action="allow")
    result = HillstoneNGFWEncoder().encode(event)
    assert result.success
    assert "hillstone_devname=\"hill-01\"" in result.output


def test_dbappsecurity_waf_basic() -> None:
    event = make_event(
        devname="waf-01",
        srcip="10.0.0.5",
        dstip="8.8.8.8",
        url="/login",
        attack_type="SQL Injection",
    )
    result = DBAPPSecurityWAFEncoder().encode(event)
    assert result.success
    parsed = json.loads(result.output)
    assert parsed["attack_type"] == "SQL Injection"


def test_dbappsecurity_waf_missing() -> None:
    result = DBAPPSecurityWAFEncoder().encode(make_event(devname="waf-01"))
    assert not result.success


def test_nsfocus_ips_basic() -> None:
    event = make_event(
        devname="ips-01",
        srcip="10.0.0.5",
        dstip="8.8.8.8",
        attack_name="SQL Injection",
        severity="high",
    )
    result = NSFOCUSIPSEncoder().encode(event)
    assert result.success
    parsed = json.loads(result.output)
    assert parsed["attack_name"] == "SQL Injection"


@pytest.mark.parametrize(
    "encoder_cls,required",
    [
        (FortinetFortigateEncoder, ["devname", "type", "subtype", "srcip", "dstip", "action"]),
        (
            PaloAltoTrafficEncoder,
            ["receive_time", "serial", "src", "dst", "sport", "dport", "proto", "action"],
        ),
        (ZeekConnEncoder, ["uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "proto"]),
        (ZeekDNSEncoder, ["uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "query"]),
        (SangforAFEncoder, ["devname", "srcip", "dstip", "action"]),
        (HuaweiUSGEncoder, ["devname", "srcip", "dstip", "action"]),
        (H3CSecPathEncoder, ["devname", "srcip", "dstip", "action"]),
        (TopsecNGFWEncoder, ["devname", "srcip", "dstip", "action"]),
        (QianxinNGFWEncoder, ["devname", "srcip", "dstip", "action"]),
        (HillstoneNGFWEncoder, ["devname", "srcip", "dstip", "action"]),
        (DBAPPSecurityWAFEncoder, ["devname", "srcip", "dstip", "url", "attack_type"]),
        (NSFOCUSIPSEncoder, ["devname", "srcip", "dstip", "attack_name"]),
    ],
)
def test_missing_required_fields(encoder_cls, required: list[str]) -> None:
    event = make_event()
    result = encoder_cls().encode(event)
    assert not result.success
    assert "missing required fields" in result.error_reason
