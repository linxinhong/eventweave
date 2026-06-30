# Security Guide

EventWeave is a command-line tool for generating synthetic event streams. By
design it runs with the privileges of the invoking user and does not provide
its own authentication, authorization, or multi-tenant isolation. This guide
covers the built-in safeguards and the options that can weaken them.

## Default protections

### HTTP sink SSRF prevention

The `http` sink POSTs events to a user-supplied URL. By default it rejects:

- Non-HTTP/HTTPS schemes
- Loopback addresses (`127.0.0.1`, `::1`)
- Link-local addresses
- Private/RFC1918 addresses
- Reserved and multicast ranges
- Common internal hostnames such as `localhost` and `metadata.google.internal`

HTTP redirects are also disabled so a public URL cannot pivot to an internal
host.

Both the Python local runtime and the Go high-performance runtime implement
these checks:

- Python: `eventweave/runtime/sinks/http.py`
- Go: `runtime-go/internal/sinks/http/http.go`

The Go runtime additionally resolves hostnames and rejects URLs where any
resolved IP address is internal, so that names like `internal.example.com`
cannot be used to bypass the filters.

### File sink path traversal prevention

The `file` sink resolves `--output` relative to `--output-dir` and rejects any
path that escapes the allowed directory. The default `--output-dir` is the
current working directory.

This is implemented in `eventweave/runtime/sinks/file.py`.

### Output directory control

`eventweave compile` writes to `-o <output_dir>`. By default it refuses to
overwrite a non-empty directory unless `--force` is given. The writer also
validates that output paths stay within the requested root to prevent path
traversal.

## Options that weaken protections

### `--allow-internal-url`

When using the `http` sink, `--allow-internal-url` disables the SSRF filters
and allows POSTs to private/internal hosts. This works for both the Python CLI
(`eventweave run`) and the Go runtime (`eventweave-runtime run`/`bench`).

Only use this option in trusted local or test environments. Both CLIs print a
warning when the flag is set:

```text
WARNING: --allow-internal-url disables SSRF protection and should only be used in trusted local test environments.
```

Examples:

```bash
eventweave run dist/ecommerce_refund_flow_semantic \
  --sink http --url http://127.0.0.1:8080/events \
  --allow-internal-url --no-wait

eventweave-runtime run dist/ecommerce_refund_flow_semantic \
  --sink http --url http://127.0.0.1:8080/events \
  --allow-internal-url --no-wait
```

### `--force`

`--force` allows `eventweave compile` to overwrite an existing non-empty output
directory. Use it deliberately to avoid losing previously compiled plans.

## Secret handling

AI-assisted semantic generation can be configured through environment
variables:

- `EVENTWEAVE_AI_BASE_URL`
- `EVENTWEAVE_AI_API_KEY`
- `EVENTWEAVE_AI_MODEL`

Do not commit real API keys to version control. Example files and test data in
the repository are synthetic and contain no real secrets.

## Runtime server mode (Go)

`eventweave-runtime serve` exposes HTTP and Syslog endpoints without
authentication. Run it only inside a trusted network or behind a reverse proxy
that provides authentication and TLS.

## Reporting security issues

If you discover a security issue, please open a private issue or contact the
maintainers directly. Do not include exploit details in public issues until a
fix has been released.
