# Demo Stack / Observability Examples

This directory provides a local, one-command demo stack so you can see EventWeave multi-source event streams, receivers, Prometheus metrics, and a Grafana dashboard without any cloud setup.

## What is included

- `security_demo.yaml` — a multi-source security scenario.
- `security_multi_source.yaml` — Go runtime `serve` config with HTTP and Syslog endpoints.
- `docker-compose.yml` — Redpanda (Kafka-compatible), Prometheus, Grafana, and lightweight receiver containers.
- `prometheus.yml` — scrapes the Go runtime metrics endpoint.
- `grafana/dashboards/eventweave-runtime.json` — a starter dashboard.
- `receivers/` — minimal SSE / Syslog TCP / Syslog UDP consumer scripts.
- `run_demo.sh` — compiles the scenario, builds the runtime, starts Docker, and runs the server.

## Prerequisites

- Docker and Docker Compose
- Go 1.22+ (to build `eventweave-runtime`)
- Python 3.11+ and the EventWeave virtual environment

## Quick start

```bash
make demo-stack
```

Or manually:

```bash
cd examples/demo-stack
./run_demo.sh
```

The script:

1. Compiles `security_demo.yaml` to `dist/security_demo_multi_source`.
2. Builds the Go runtime binary.
3. Starts Redpanda, Prometheus, Grafana, and receiver containers.
4. Starts `eventweave-runtime serve` with the multi-source config and metrics enabled.

## URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://127.0.0.1:3000 | admin / auto-generated password |
| Prometheus | http://127.0.0.1:9090 | — |
| Redpanda Admin | http://127.0.0.1:19644 | — |

The Grafana password is generated on first run and saved to
`examples/demo-stack/.env`. The file is ignored by Git, so each developer gets
a fresh credential.

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Host: eventweave-runtime serve                             │
│  - 0.0.0.0:5514  (firewall  -> syslog_udp)                 │
│  - 0.0.0.0:5515  (edr       -> syslog_tcp)                 │
│  - 0.0.0.0:8081  (waf       -> http sse)                   │
│  - 0.0.0.0:8082  (dns       -> http sse)                   │
│  - 0.0.0.0:9090  (Prometheus metrics)                      │
└────────────┬──────────────────────┬────────────────────┬────┘
             │                      │                    │
    ┌────────▼────────┐    ┌────────▼────────┐   ┌──────▼──────┐
    │ syslog-udp-rcv  │    │ syslog-tcp-rcv  │   │ http-sse-rcv│
    └─────────────────┘    └─────────────────┘   └─────────────┘
             │                      │                    │
             └──────────────────────┼────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │     Prometheus + Grafana      │
                    └───────────────────────────────┘
```

## Optional Kafka sink demo

With Redpanda running, you can also replay the same plan into Kafka:

```bash
cd runtime-go
go run ./cmd/eventweave-runtime run ../dist/security_demo_multi_source \
  --sink kafka \
  --brokers 127.0.0.1:19092 \
  --topic eventweave-events \
  --no-wait
```

## Stopping the demo

Press `Ctrl-C` in the terminal running `run_demo.sh`. The script automatically runs `docker compose down`.

To stop only the containers:

```bash
cd examples/demo-stack
docker compose down
```

## Linux note

If you are on Linux without Docker Desktop, `host.docker.internal` may not resolve inside containers. Start the stack with:

```bash
cd examples/demo-stack
docker compose up -d --add-host host.docker.internal:host-gateway
```

## Files

- `examples/demo-stack/security_demo.yaml`
- `examples/demo-stack/security_multi_source.yaml`
- `examples/demo-stack/docker-compose.yml`
- `examples/demo-stack/prometheus.yml`
- `examples/demo-stack/grafana/dashboards/eventweave-runtime.json`
- `examples/demo-stack/receivers/`
- `examples/demo-stack/run_demo.sh`
