# Changelog

All notable changes to this project will be documented in this file.

## [0.9.7] - 2026-06-30

### Added

- Pack schema validation layer in `eventweave/compiler/schema_validator.py`.
- `eventweave validate` and `eventweave compile` now perform schema validation
  against pack event/entity schemas by default, emitting warnings for:
  - Unknown event types.
  - Missing required event/entity fields.
  - Event/entity field type mismatches (`string`, `number`, `integer`, `boolean`).
  - Event enum violations.
  - Invalid `format: email` / `format: ipv4` values.
  - Unknown or wrongly typed event `entity_refs`.
- New `--strict-schema` CLI flag for `validate` and `compile` upgrades schema
  warnings to errors.
- `eventweave pack validate` now checks that event `entity_refs` reference known
  entity types and reports schema warnings from compiled examples.
- Tests in `tests/compiler/test_schema_validator.py` covering warning/strict
  behavior, type checks, enum checks, entity-ref checks, and pack self-validation.

### Changed

- Updated `docs/pack-spec.md` and `docs/scenario-dsl.md` to document schema
  validation, the `--strict-schema` flag, and the distinction between rule
  validation and schema validation.
- Updated `README.md` roadmap to reflect v0.9.7 completion.

## [0.9.6] - 2026-06-30

### Added


- Go HTTP sink SSRF parity with the Python runtime:
  - `runtime-go/internal/sinks/http/http.go` now resolves hostnames and rejects
    URLs where any resolved IP is loopback, link-local, private, multicast,
    reserved, or unspecified.
  - `eventweave-runtime run` and `bench` print a warning when
    `--allow-internal-url` is used.
  - HTTP redirects remain disabled for the Go `http` sink.
- Go HTTP sink tests:
  - `TestHTTPSinkAllowsPublicURL`
  - `TestHTTPSinkRejectsRedirect`
  - `TestRunCmdWarnsOnAllowInternalURL`
  - `TestBenchCmdWarnsOnAllowInternalURL`

### Changed

- Updated `docs/security.md` to document Python/Go HTTP sink parity, DNS
  resolution checks, and the `--allow-internal-url` warning.
- Updated `docs/go-runtime.md` to clarify hostname resolution and the CLI
  warning behavior.
- Updated `README.md` with a security summary and adjusted the v0.9.5/v0.9.6
  roadmap items.

## [0.9.5] - 2026-06-30

### Added

- Core model unit tests in `tests/core/test_models.py` covering entities,
  events, scenarios, timeline, sources, semantic assets, ground truth, noise,
  jitter, sinks, and relations.
- CLI smoke tests in `tests/cli/test_smoke.py` covering `validate`, `compile`,
  `run`, `encode list/inspect/preflight`, `eval prepare`, `benchmark validate`,
  and `pack validate` for all domain packs.
- Regression tests in `tests/encoders/test_registry.py` ensuring every
  registered encoder can be inspected and that encoders relying on base-class
  defaults do not crash.
- Minimal domain packs for `saas`, `iot`, `devops`, and `hospital`, each with
  entities, events, rules, and a runnable example scenario.
- New `docs/security.md` documenting SSRF protection, file-sink path traversal
  prevention, `--allow-internal-url`, `--force`, and runtime server security.

### Fixed

- `eventweave encode inspect <encoder>` no longer crashes when an encoder does
  not override `required_fields`, `optional_fields`, or
  `supported_event_types` (`eventweave/encoders/base.py`).

### Changed

- `eventweave run --sink http --allow-internal-url` now prints a security
  warning at startup.
- `docs/local-runtime.md` clarifies that `--allow-internal-url` triggers a CLI
  warning.

### Removed

- Empty `eventweave/semantic/` directory (semantic implementation lives in
  `eventweave/ai/`).

## [0.9.4] - 2026-06-30

### Added

- Encoder field enrichment / auto-fill profiles:
  - `eventweave/encoders/enrichment.py` provides `EnrichmentProfile`,
    `EnrichmentRegistry`, and `enrich_event()`.
  - `runtime-go/internal/encoder/enrichment.go` provides the Go equivalent
    `ApplyEnrichment()` and `EnrichedEncoder` wrapper.
- Pack-level enrichment configuration in
  `packs/security/encoders/enrichment.yaml`, covering all security encoders.
- `eventweave encode run --enrich` applies enrichment before encoding.
- `eventweave encode preflight --enrich` and `--compare-enrichment` show
  baseline vs enriched encodability.
- `eventweave-runtime run --enrich` and `eventweave-runtime bench --enrich`
  apply enrichment to the configured encoder.
- `eventweave-runtime serve --enrich` and per-endpoint `enrich: true` in
  `server.yaml` apply enrichment to endpoint encoders.

### Changed

- `docs/encoders.md` documents enrichment concepts, profile format, priority
  rules, and CLI usage.
- `docs/multi-source-runtime.md` documents the `enrich` endpoint field and
  `--enrich` flag, and renames Limitations to Current limitations.
- `docs/pack-spec.md` documents `encoders/enrichment.yaml` and updates future
  extensions.

## [0.9.3] - 2026-06-29

### Added

- Go runtime `serve` now supports per-endpoint encoders via the optional
  `encoder` field in `server.yaml`.
- Endpoints can emit vendor-specific formats (e.g., `fortinet-fortigate`,
  `syslog-rfc3164`, `nginx-access`) while other endpoints continue to emit
  canonical JSON.
- Unknown encoder names in `server.yaml` are rejected at config validation time.

### Changed

- `HTTPServer` and `SyslogServer` constructors now accept an encoder instance.
- Syslog endpoints avoid double-wrapping when a syslog encoder is configured.

### Documentation

- Updated `docs/multi-source-runtime.md` with `encoder` examples and encoding
  behavior for HTTP and syslog endpoints.

## [0.9.2] - 2026-06-29

### Added

- Encoder introspection: every encoder now exposes `description`,
  `required_fields`, `optional_fields`, and `supported_event_types`.
- `eventweave encode inspect <encoder>` to display encoder metadata,
  required fields, and Go runtime availability.
- `eventweave encode preflight <plan_dir> --encoder <name>` to check
  encodability, report failures by event type, and list missing fields.
- Pack-level encoder mapping via the optional `encoders:` block in
  `pack.yaml`, plus validation in `eventweave pack validate`.
- `packs/security/pack.yaml` now declares recommended encoders for its
  event types.

### Changed

- `eventweave encode` is now a command group:
  - `eventweave encode run` replaces the old top-level `eventweave encode`.
  - `eventweave encode list` replaces `eventweave encode --list`.

## [0.9.1] - 2026-06-29

### Added

- Security vendor encoders (v0.9.1):
  - International: `fortinet-fortigate`, `paloalto-traffic`, `zeek-conn`,
    `zeek-dns`, `dns-json`
  - Domestic (China): `sangfor-af`, `huawei-usg`, `h3c-secpath`,
    `topsec-ngfw`, `qianxin-ngfw`, `hillstone-ngfw`, `dbappsecurity-waf`,
    `nsfocus-ips`
- Go runtime implementations for all v0.9.1 security encoders under
  `runtime-go/internal/encoder/security/`.
- Tests for Python and Go v0.9.1 encoders.
- Updated `docs/encoders.md` with the new encoder catalog and required fields.

## [0.9.0] - 2026-06-29

### Added

- Vendor/log encoders for EventWeave output:
  - `syslog-rfc3164` and `syslog-rfc5424`
  - `nginx-access`
  - `suricata-eve` (security pack)
  - `windows-event-json` (security pack)
- Python encoder framework under `eventweave/encoders/`:
  - `Encoder` base class, `EncodeResult`, and `EncodeError`
  - `EncoderRegistry` with `@encoder` decorator
  - Pack encoder discovery via `packs/<domain>/encoders/__init__.py`
- Go encoder framework under `runtime-go/internal/encoder/`
  - `Encoder` interface and global registry
  - Security-specific encoders in `runtime-go/internal/encoder/security/`
- New CLI command: `eventweave encode`
- `--encoder` option for `eventweave run`, `eventweave export`, and
  `eventweave-runtime run`/`bench`/`serve`
- Encoder failure handling: visible errors, skipped events with
  `--skip-failed`, and per-sink failure counters
- Documentation: `docs/encoders.md`

## [0.8.5] - 2026-06-29

Same changes as the originally-planned v0.8.4 release; version bumped to
0.8.5 because the v0.8.4 tag already pointed to an earlier commit.

## [0.8.4] - 2026-06-29

### Security

- Added SSRF protection to the Python `http` sink: loopback, link-local,
  private, reserved, and multicast targets are rejected by default.
- Disabled HTTP redirects so a public URL cannot pivot to an internal host.
- Added `--allow-internal-url` opt-in for trusted local/test environments.
- Added path-traversal protection and `--output-dir` restriction to the Python
  `file` sink.
- Added `--force` and `allowed_root` validation to `PlanWriter` so compiled
  output cannot escape the intended directory.

### Evaluation

- Decoupled evaluation from runtime compilation.
- Added `eventweave eval prepare <scenario>` to generate the ground-truth,
  runtime-plan, and event-plan artifacts that `eval task`, `eval run`, and
  `benchmark` consume.
- `EVENTWEAVE_PLAN_DIR` can override the default `dist/` root when resolving
  compiled artifacts.
- Updated `docs/agent-evaluation.md` and `README.md` to document the new
  workflow.

### Runtime

- Split the CLI into a registration hub (`eventweave/cli/main.py`) and
  per-command modules under `eventweave/cli/commands/`.
- Added HTTP retry governance to both Python and Go runtimes:
  `--retries`, `--max-retry-duration`, and `--backoff-factor`, with 429 and
  5xx retry handling.
- Added upper-bound validation to Go runtime tunables (`--workers`,
  `--queue-size`, `--batch-size`, `--retries`, `--timeout`, etc.).
- Switched Go metrics to lazy, idempotent registration instead of `init()`
  `MustRegister`.
- Fixed a Kafka batch close/timer race in `runtime-go/internal/sinks/kafka/batch.go`.
- Added optional UDP client CIDR allowlist and TTL cleanup to the Syslog UDP
  server.
- Fixed a worker-pool send-after-close panic by using an atomic `closed` flag
  and not closing the jobs channel.
- Large event plans are now streamed in Python and read line-by-line in Go to
  avoid memory/token limits.

### AI / Semantic

- Made LLM template render failures visible: `_render_template` now returns
  `(text, ok)`, and failures set `meta.review_status = "pending"`.
- Fixed AI cache key collision by hashing keys with SHA-256 for filenames while
  storing the original key in the wrapper JSON.
- Fixed serialization of `datetime` fields in the semantic asset cache.

### Packs & Demo

- Added minimal `pack.yaml` stubs for `saas`, `iot`, `devops`, and `hospital`
  packs.
- Demo stack (`examples/demo-stack`) now reads its version from
  `pyproject.toml` and generates a random Grafana admin password on first run,
  saved to a Git-ignored `.env` file.

### Dependencies

- Removed the anomalous `go.yaml.in/yaml/v2` dependency from the Go runtime by
  downgrading `github.com/prometheus/client_golang` to `v1.20.5` and
  `github.com/prometheus/common` to `v0.55.0`, then running `go mod tidy`.

[0.8.4]: https://github.com/eventweave/eventweave/releases/tag/v0.8.4
