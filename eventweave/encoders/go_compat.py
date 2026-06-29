"""Set of encoder names that also have a Go runtime implementation."""

from __future__ import annotations

GO_ENCODER_NAMES: frozenset[str] = frozenset(
    {
        "jsonl",
        "syslog-rfc3164",
        "syslog-rfc5424",
        "nginx-access",
        "suricata-eve",
        "windows-event-json",
        "fortinet-fortigate",
        "paloalto-traffic",
        "zeek-conn",
        "zeek-dns",
        "dns-json",
        "sangfor-af",
        "huawei-usg",
        "h3c-secpath",
        "topsec-ngfw",
        "qianxin-ngfw",
        "hillstone-ngfw",
        "dbappsecurity-waf",
        "nsfocus-ips",
    }
)
