#!/bin/sh

set -eu

PROJECT_DIR="/share/CACHEDEV1_DATA/Container/mud-nas-evennia"
DOCKER_BIN="/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker"
CONTAINER_NAME="jiuzhou-like-mud"

run_in_project() {
  cd "$PROJECT_DIR"
  "$@"
}

compose_cmd() {
  run_in_project "$DOCKER_BIN" compose "$@"
}

docker_exec() {
  "$DOCKER_BIN" exec "$CONTAINER_NAME" "$@"
}

ensure_server_running() {
  status_output="$(docker_exec evennia status 2>/dev/null || true)"
  echo "$status_output"
  echo "$status_output" | grep -q "Server: RUNNING" && return 0
  echo "Server not running, starting it once..."
  docker_exec sh -lc "cd /usr/src/game && evennia start"
}

