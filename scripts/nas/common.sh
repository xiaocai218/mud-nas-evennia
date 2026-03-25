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

  # QNAP 这套容器环境里，`docker compose up -d` 后偶尔会出现 Portal 已经起来、
  # 但 Server 还没真正挂起的情况。这里先做短轮询，避免把“还在启动中”误判为故障。
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

  # Evennia 在补起过程中可能先报 twistd 已在运行，但实际只是旧进程尚未完全登记完成。
  # 这里不立即视为失败，而是回头重查一次 status，避免产生“4006 Address in use”这类假故障判断。
  if echo "$start_output" | grep -q "Another twistd server is running"; then
    sleep 2
    status_output="$(get_evennia_status)"
    echo "$status_output"
    echo "$status_output" | grep -q "Server: RUNNING" && return 0
  fi

  echo "Failed to ensure Evennia Server is running." >&2
  return 1
}
