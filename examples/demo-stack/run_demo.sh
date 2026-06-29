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

VERSION="$(grep '^version' "${PROJECT_ROOT}/pyproject.toml" | sed 's/version = "\(.*\)"/\1/')"

# Generate a random Grafana admin password if one is not already present.
ENV_FILE="${SCRIPT_DIR}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
fi
if [[ -z "${GRAFANA_ADMIN_PASSWORD:-}" ]]; then
  if command -v openssl >/dev/null 2>&1; then
    GRAFANA_ADMIN_PASSWORD="$(openssl rand -base64 24)"
  else
    GRAFANA_ADMIN_PASSWORD="$(python3 -c 'import secrets, base64; print(base64.b64encode(secrets.token_bytes(24)).decode())')"
  fi
  echo "GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}" > "${ENV_FILE}"
fi

echo "=== EventWeave v${VERSION:-unknown} Demo Stack ==="
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
echo "  Grafana:       http://127.0.0.1:3000  (admin / ${GRAFANA_ADMIN_PASSWORD})"
echo "  Prometheus:    http://127.0.0.1:9090"
echo "  Redpanda:      kafka://127.0.0.1:19092"
echo "  Redpanda UI:   http://127.0.0.1:19644"
echo "  Password saved to: ${ENV_FILE}"
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
