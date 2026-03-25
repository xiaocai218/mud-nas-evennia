#!/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/common.sh"

# 先拉起 compose，再交给 common.sh 补齐 Evennia Server。
# 这样 start.sh 和 reload.sh 能共用同一套 QNAP 环境兜底逻辑。
compose_cmd up -d
sleep 5
ensure_server_running
