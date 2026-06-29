#!/usr/bin/env bash
# One-command local demo for EventWeave multi-source runtime + observability.
#
# Usage:
#   cd examples/demo-stack
#   ./run_demo.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PLAN_DIR="${PROJECT_ROOT}/dist/security_demo_multi_source"
RUNTIME="${PROJECT_ROOT}/runtime-go/cmd/eventweave-runtime"

echo "=== EventWeave v0.7.4 Demo Stack ==="
echo

# Compile the demo scenario if needed.
if [[ ! -d "${PLAN_DIR}" ]]; then
  echo "Compiling demo scenario..."
  (cd "${PROJECT_ROOT}" && .venv/bin/eventweave compile "${SCRIPT_DIR}/security_demo.yaml" -o dist)
fi

# Build the Go runtime if needed.
if [[ ! -x "${RUNTIME}/eventweave-runtime" ]]; then
  echo "Building eventweave-runtime..."
  (cd "${RUNTIME}" && go build -o eventweave-runtime .)
fi

# Start observability infrastructure and receivers.
echo "Starting Docker services..."
(cd "${SCRIPT_DIR}" && docker compose up -d)

echo
echo "Services ready:"
echo "  Grafana:       http://127.0.0.1:3000  (admin / admin)"
echo "  Prometheus:    http://127.0.0.1:9090"
echo "  Redpanda:      kafka://127.0.0.1:19092"
echo "  Redpanda UI:   http://127.0.0.1:19644"
echo
echo "Starting EventWeave multi-source runtime (Ctrl-C to stop)..."
echo

# Ensure docker compose is torn down when the runtime exits.
cleanup() {
  echo
  echo "Stopping Docker services..."
  (cd "${SCRIPT_DIR}" && docker compose down)
}
trap cleanup EXIT INT TERM

"${RUNTIME}/eventweave-runtime" serve "${PLAN_DIR}" \
  --server-config "${SCRIPT_DIR}/security_multi_source.yaml" \
  --metrics-addr 0.0.0.0:9090
