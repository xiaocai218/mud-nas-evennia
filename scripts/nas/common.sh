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

get_evennia_status() {
  docker_exec evennia status 2>/dev/null || true
}

server_running() {
  status_output="$(get_evennia_status)"
  echo "$status_output" | grep -q "Server: RUNNING"
}

ensure_server_running() {
  status_output="$(get_evennia_status)"
  echo "$status_output"
  echo "$status_output" | grep -q "Server: RUNNING" && return 0

  tries=0
  while [ "$tries" -lt 3 ]; do
    sleep 2
    status_output="$(get_evennia_status)"
    echo "$status_output" | grep -q "Server: RUNNING" && return 0
    tries=$((tries + 1))
  done

  echo "Server not running, starting it once..."
  start_output="$(docker_exec sh -lc "cd /usr/src/game && evennia start" 2>&1 || true)"
  echo "$start_output"

  echo "$start_output" | grep -q "Server: RUNNING" && return 0
  echo "$start_output" | grep -q "Server started." && return 0

  if echo "$start_output" | grep -q "Another twistd server is running"; then
    sleep 2
    status_output="$(get_evennia_status)"
    echo "$status_output"
    echo "$status_output" | grep -q "Server: RUNNING" && return 0
  fi

  echo "Failed to ensure Evennia Server is running." >&2
  return 1
}
