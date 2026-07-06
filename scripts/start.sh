#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker compose -f "$SCRIPT_DIR/../docker/docker-compose.yml" up --build -d
echo "Aegis Exchange stack started."
echo "  Dashboard:  http://localhost:4000"
echo "  API:        http://localhost:9080"
echo "  Prometheus: http://localhost:9190"
echo "  Grafana:    http://localhost:4001 (admin/aegis)"
