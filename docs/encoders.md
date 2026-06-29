# Vendor Log Encoders

EventWeave can emit canonical events in vendor-specific log formats through
**encoders**. Encoders are pure format transforms: they read the canonical
`Event` and produce a line of text or JSON suitable for SIEMs, syslog servers,
log shippers, and testing tools.

## Built-in encoders

| Name | Format | Content type |
|------|--------|--------------|
| `jsonl` | Canonical EventWeave JSON (default) | `application/x-ndjson` |
| `syslog-rfc3164` | RFC3164-style syslog message | `text/plain` |
| `syslog-rfc5424` | RFC5424-style syslog message | `text/plain` |
| `nginx-access` | nginx combined log format | `text/plain` |

## Pack encoders

Security-specific encoders live in `packs/security/encoders/` and are loaded
automatically when the registry is queried:

| Name | Format | Content type |
|------|--------|--------------|
| `suricata-eve` | Suricata EVE JSON | `application/x-ndjson` |
| `windows-event-json` | Windows Event Log JSON | `application/x-ndjson` |
| `fortinet-fortigate` | Fortinet FortiGate key=value log | `text/plain` |
| `paloalto-traffic` | Palo Alto Networks traffic CSV | `text/csv` |
| `zeek-conn` | Zeek `conn.log` TSV | `text/tab-separated-values` |
| `zeek-dns` | Zeek `dns.log` TSV | `text/tab-separated-values` |
| `dns-json` | Normalized DNS JSON | `application/json` |
| `sangfor-af` | Sangfor AF key=value log | `text/plain` |
| `huawei-usg` | Huawei USG key=value log | `text/plain` |
| `h3c-secpath` | H3C SecPath key=value log | `text/plain` |
| `topsec-ngfw` | Topsec NGFW key=value log | `text/plain` |
| `qianxin-ngfw` | Qianxin NGFW key=value log | `text/plain` |
| `hillstone-ngfw` | Hillstone NGFW key=value log | `text/plain` |
| `dbappsecurity-waf` | DBAPPSecurity WAF JSON | `application/json` |
| `nsfocus-ips` | NSFOCUS IPS JSON | `application/json` |

## Usage

### Python CLI

The `encode` command is a group with subcommands:

```bash
eventweave encode list
eventweave encode run dist/security_lateral_movement \
  --encoder syslog-rfc3164 \
  --output out/syslog.log
eventweave encode inspect fortinet-fortigate
eventweave encode preflight dist/security_lateral_movement \
  --encoder fortinet-fortigate
```

List encoders:

```bash
eventweave encode list
```

Encode a compiled event plan:

```bash
eventweave encode run dist/security_lateral_movement \
  --encoder syslog-rfc3164 \
  --output out/syslog.log
```

Inspect an encoder (metadata and required fields):

```bash
eventweave encode inspect nginx-access
```

Example output:

```text
Encoder: nginx-access
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property              ┃ Value                                           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Name                  │ nginx-access                                    │
│ Content-Type          │ text/plain                                      │
│ Description           │ nginx combined log format.                      │
│ Required fields       │ remote_addr, request, status, body_bytes_sent   │
│ Optional fields       │ remote_user, http_referer, http_user_agent      │
│ Supported event types │ http.request                                    │
│ Available in          │ python, go                                      │
└───────────────────────┴─────────────────────────────────────────────────┘
```

Preflight-check a plan before encoding:

```bash
eventweave encode preflight dist/security_lateral_movement \
  --encoder fortinet-fortigate
```

The preflight command reports how many events are encodable, which event types fail, and which required fields are missing.

Use an encoder during `run` or `export`:

```bash
eventweave run dist/security_lateral_movement \
  --sink file \
  --output out/suricata.jsonl \
  --encoder suricata-eve \
  --no-wait

eventweave export dist/security_lateral_movement \
  --encoder nginx-access \
  --output out/nginx.log
```

### Go runtime

```bash
eventweave-runtime run dist/security_lateral_movement \
  --sink file \
  --output out/suricata.jsonl \
  --encoder suricata-eve \
  --no-wait
```

Syslog with a specific encoder:

```bash
eventweave-runtime run dist/security_lateral_movement \
  --sink syslog \
  --syslog-addr 127.0.0.1:5514 \
  --encoder syslog-rfc3164 \
  --no-wait
```

## Failure semantics

Encoders can fail when the canonical event is missing required fields for the
target format. Failures are visible:

- `eventweave encode` prints the failure and exits non-zero by default. Use
  `--skip-failed` to drop those events and continue.
- `eventweave run` counts encoding failures in sink stats and stops only if
  `--max-failures` is reached.
- Go sinks increment the `Failed()` counter and return the encode error.

Example failure:

```text
Encode failed for evt-001: missing required fields: request, status, body_bytes_sent
```

## Required fields per encoder

- `nginx-access`: `remote_addr`, `request`, `status`, `body_bytes_sent`
- `suricata-eve`: `event_type`, `src_ip`, `dest_ip`
- `windows-event-json`: `EventID`
- `fortinet-fortigate`: `devname`, `type`, `subtype`, `srcip`, `dstip`, `action`
- `paloalto-traffic`: `receive_time`, `serial`, `src`, `dst`, `sport`, `dport`,
  `proto`, `action`
- `zeek-conn`: `uid`, `id.orig_h`, `id.orig_p`, `id.resp_h`, `id.resp_p`, `proto`
- `zeek-dns`: `uid`, `id.orig_h`, `id.orig_p`, `id.resp_h`, `id.resp_p`, `query`
- `dns-json`: `client_ip`, `query`, `qtype`
- `sangfor-af`, `huawei-usg`, `h3c-secpath`, `topsec-ngfw`, `qianxin-ngfw`,
  `hillstone-ngfw`: `devname`, `srcip`, `dstip`, `action`
- `dbappsecurity-waf`: `devname`, `srcip`, `dstip`, `url`, `attack_type`
- `nsfocus-ips`: `devname`, `srcip`, `dstip`, `attack_name`
- `syslog-rfc3164` / `syslog-rfc5424`: no required fields; uses defaults for
  facility (`16`), severity (`6`), hostname (`source_id`), and tag (`source_id`).

## Authoring a pack encoder

Create `packs/<domain>/encoders/__init__.py` and register encoder classes with
the `@encoder` decorator:

```python
# packs/my_domain/encoders/__init__.py
from eventweave.core.event import Event
from eventweave.encoders import Encoder, EncodeResult, encoder


@encoder("my-format", content_type="text/plain")
class MyFormatEncoder(Encoder):
    name = "my-format"
    content_type = "text/plain"

    def encode(self, event: Event) -> EncodeResult:
        if "required_field" not in event.attributes:
            return self._fail("missing required field: required_field")
        return self._ok(f"{event.event_time} {event.attributes['required_field']}")
```

The registry discovers the module at runtime when an encoder name is looked up.
Encoder names must be globally unique.

## Encoder metadata

Encoders expose metadata through the `Encoder` base class:

- `name` — encoder identifier
- `content_type` — MIME type of encoded output
- `description` — short human-readable description
- `required_fields` — attributes that must be present for encoding to succeed
- `optional_fields` — attributes that are read when present
- `supported_event_types` — event types the encoder is intended for

`eventweave encode inspect <encoder>` prints this metadata, plus whether a Go
runtime implementation exists.

## Encoder field enrichment

Canonical events are often sparse: they carry the scenario-level facts but miss
the vendor-specific fields an encoder needs. Enrichment profiles solve this by
producing an encoder-friendly view **without mutating the canonical event**.

Enrichment is applied immediately before encoding. Priority:

1. Existing target attribute on the event.
2. Mapped source attribute (when target is missing and source exists).
3. Default value.

### Pack enrichment profiles

Packs define profiles in `packs/<domain>/encoders/enrichment.yaml`:

```yaml
profiles:
  fortinet-fortigate:
    description: FortiGate traffic log enrichment.
    defaults:
      devname: firewall-01
      type: traffic
      subtype: forward
      action: accept
      srcip: 10.0.0.1
      dstip: 10.0.0.2
    mappings:
      srcip: src_ip
      dstip: dest_ip
      srcport: src_port
      dstport: dest_port
      proto: protocol
```

- `defaults` — values applied when a target field is missing.
- `mappings` — `target_field: source_field` copies. Used when canonical events
  use different field names than the encoder expects.

### Python CLI

Apply enrichment during encoding:

```bash
eventweave encode run dist/security_lateral_movement \
  --encoder fortinet-fortigate \
  --enrich \
  --output out/fortigate.log
```

Preflight with enrichment comparison:

```bash
eventweave encode preflight dist/security_lateral_movement \
  --encoder fortinet-fortigate \
  --enrich \
  --compare-enrichment
```

This prints the baseline success rate, the enriched success rate, and a delta
summary.

### Go runtime

```bash
eventweave-runtime run dist/security_lateral_movement \
  --sink file \
  --output out/fortigate.log \
  --encoder fortinet-fortigate \
  --enrich \
  --no-wait
```

## Pack encoder mapping

Packs can declare which encoders are recommended for which event types by adding
an `encoders:` block to `pack.yaml`:

```yaml
encoders:
  - name: fortinet-fortigate
    required_fields:
      - devname
      - type
      - subtype
      - srcip
      - dstip
      - action
    supported_event_types:
      - network.lateral_connection
```

`eventweave pack validate <pack>` checks that every declared encoder is
registered and that every `supported_event_type` exists in the pack.
