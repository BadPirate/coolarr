#!/usr/bin/env bash
set -euo pipefail
# Run plugin integration test inside the Unmanic container (see docker/unmanic/scripts/run_plugin_encode_test.py).
#
# Usage (from repo root, stack already up):
#   ./scripts/safari_plugin_encode_test.sh --input /library/sample.mkv --output /library/sample_clip5s.mp4
#
# Override service name if needed:
#   UNMANIC_SERVICE=myunmanic ./scripts/safari_plugin_encode_test.sh -i /library/sample.mkv

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.yaml}"
SERVICE="${UNMANIC_SERVICE:-unmanic}"

exec docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
  /opt/venv/bin/python3 /opt/unmanic-scripts/run_plugin_encode_test.py "$@"
