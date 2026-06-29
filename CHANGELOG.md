# Changelog

All notable changes to this project will be documented in this file.

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
