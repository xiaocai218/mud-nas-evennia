#!/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "$SCRIPT_DIR/common.sh"

ensure_server_running >/dev/null
docker_exec sh -lc "cd /usr/src/game && evennia reload"

