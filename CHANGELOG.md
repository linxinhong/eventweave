# Changelog

## v0.8.4 — P1 technical debt and robustness

### CLI
- Split `eventweave/cli/main.py` into per-command modules under
  `eventweave/cli/commands/`; `main.py` now only registers commands.

### Rules
- `NotImplementedRule` placeholders now emit explicit warnings during
  validation instead of silently passing.
- Implemented `event_before` and `field_lte_ref` declarative rules.

### Evaluation
- `GroundTruth` gained `expected_timeline_stages`, auto-derived from
  `expected_findings` when not declared.
- `Evaluator` now compares `AgentOutput.timeline_stages` and reports
  `timeline_stage_recall`, `timeline_stage_precision`,
  `timeline_event_recall`, and `timeline_event_precision`.

### AI provider
- Added configurable `timeout`, `max_retries`, `max_tokens`, and
  `temperature` for the AI provider.
- Implemented exponential-backoff retry for transient HTTP errors.
- Validated Chat Completions response shape and `finish_reason`.
- Empty API keys now omit the `Authorization` header for local servers.

### Go runtime
- `LocalRuntime` supports `RunWithContext` and graceful shutdown on
  `SIGINT`/`SIGTERM`.
- Worker pool uses context cancellation, drains queued events on close,
  and removes per-loop `time.After` allocations.
- Rate limiter and runtime clock wait in a context-aware way.

## v0.8.3 — Security hardening for HTTP and file sinks

### Security
- Python `HTTPSink` now rejects internal/private/reserved hosts and non-http(s)
  schemes by default, and disables HTTP redirects to prevent SSRF pivoting.
- Python `FileSink` now requires an `output_dir` and rejects paths that escape
  it, preventing path traversal / arbitrary file writes.
- Go HTTP sink mirrors the same URL safety checks and disables redirects.
- Go file sink enforces an `--output-dir` boundary.

### CLI
- `eventweave run` gained `--output-dir` and `--allow-internal-url`.
- `eventweave export` gained `--output-dir`.
- `eventweave-runtime run` / `bench` gained `--output-dir` and
  `--allow-internal-url`.

### Tests
- Added security tests for forbidden HTTP URLs and file path traversal in both
  Python and Go.
- Existing sink/runtime tests updated to opt-in to internal URLs/paths where
  needed for local test servers.
