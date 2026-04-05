#!/usr/bin/env bash
set -euo pipefail
#
# Run the safari_h264_mp4 plugin encode test: starts Unmanic via compose, copies a local sample in,
# runs the real plugin + ffmpeg, copies sample-encoded.mp4 to the current directory, then stops Unmanic.
#
# Usage:
#   ./test_mp4_plugin.sh
#   ./test_mp4_plugin.sh /path/to/sample.mkv
#
# Environment:
#   COMPOSE_FILE              — default: <repo>/docker-compose.yaml
#   UNMANIC_SERVICE           — default: unmanic
#   UNMANIC_COMPOSE_BUILD=1   — run `docker compose up --build` when starting
#   KEEP_UNMANIC_RUNNING=1    — do not stop the service on exit (leave it running)
#

ROOT="$(cd "$(dirname "$0")" && pwd)"
export COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.yaml}"
SERVICE="${UNMANIC_SERVICE:-unmanic}"
PROJECT_DIR="${COMPOSE_PROJECT_DIR:-$ROOT}"

INPUT_LOCAL="${1:-sample.mkv}"
[[ "$INPUT_LOCAL" != /* ]] && INPUT_LOCAL="${PWD}/${INPUT_LOCAL}"
OUT_LOCAL="${PWD}/sample-encoded.mp4"
IN_REMOTE="/tmp/test_mp4_plugin_in.mkv"
OUT_REMOTE="/tmp/test_mp4_plugin_out.mp4"

compose() {
  docker compose -f "$COMPOSE_FILE" --project-directory "$PROJECT_DIR" "$@"
}

stop_unmanic() {
  if [[ "${KEEP_UNMANIC_RUNNING:-0}" == "1" ]]; then
    echo "==> Leaving $SERVICE running (KEEP_UNMANIC_RUNNING=1)"
    return 0
  fi
  echo "==> Stopping $SERVICE"
  compose stop "$SERVICE" || true
}

if [[ ! -f "$INPUT_LOCAL" ]]; then
  echo "error: input not found: $INPUT_LOCAL" >&2
  echo "  Place sample.mkv in this directory or pass a path: ./test_mp4_plugin.sh /path/to/file.mkv" >&2
  exit 1
fi

trap stop_unmanic EXIT

echo "==> Starting $SERVICE"
if [[ "${UNMANIC_COMPOSE_BUILD:-}" == "1" ]]; then
  compose up -d --build "$SERVICE"
else
  compose up -d "$SERVICE"
fi

echo "==> Copying into container: $INPUT_LOCAL -> $SERVICE:$IN_REMOTE"
compose cp "$INPUT_LOCAL" "$SERVICE:$IN_REMOTE"

echo "==> Running plugin + ffmpeg inside $SERVICE"
compose exec -T "$SERVICE" \
  /opt/venv/bin/python3 /opt/unmanic-scripts/run_plugin_encode_test.py \
  --input "$IN_REMOTE" \
  --output "$OUT_REMOTE"

echo "==> Copying result to: $OUT_LOCAL"
compose cp "$SERVICE:$OUT_REMOTE" "$OUT_LOCAL"

echo "==> Cleaning temp files in container"
compose exec -T "$SERVICE" rm -f "$IN_REMOTE" "$OUT_REMOTE" || true

echo "Done. Open: $OUT_LOCAL"
