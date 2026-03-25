#!/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/common.sh"

# reload 之前先确认 Server 已在线。
# 否则在 QNAP 上直接 reload，常见结果是命令看似执行了，但实际没有可重载的 Evennia 进程。
ensure_server_running >/dev/null
docker_exec sh -lc "cd /usr/src/game && evennia reload"
