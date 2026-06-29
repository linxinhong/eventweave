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

## Usage

### Python CLI

List encoders:

```bash
eventweave encode --list
```

Encode a compiled event plan:

```bash
eventweave encode dist/security_lateral_movement \
  --encoder syslog-rfc3164 \
  --output out/syslog.log
```

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
