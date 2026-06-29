# Changelog

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
