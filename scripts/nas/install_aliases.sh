#!/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ALIAS_FILE="$HOME/.profile_mud_aliases"

cat > "$ALIAS_FILE" <<EOF
alias update='sh $SCRIPT_DIR/update.sh'
alias reload='sh $SCRIPT_DIR/reload.sh'
alias start='sh $SCRIPT_DIR/start.sh'
alias stop='sh $SCRIPT_DIR/stop.sh'
alias status='sh $SCRIPT_DIR/status.sh'
EOF

case "${SHELL:-}" in
  */bash)
    RC_FILE="$HOME/.bashrc"
    ;;
  */ash|*/sh)
    RC_FILE="$HOME/.profile"
    ;;
  *)
    RC_FILE="$HOME/.profile"
    ;;
esac

if [ ! -f "$RC_FILE" ]; then
  touch "$RC_FILE"
fi

grep -q "profile_mud_aliases" "$RC_FILE" 2>/dev/null || echo ". \"$ALIAS_FILE\"" >> "$RC_FILE"

echo "Aliases installed. Open a new shell or run:"
echo ". \"$ALIAS_FILE\""
