# Runtime Data

This directory is intentionally outside the tracked game code path.

Use it to persist host-side runtime data that must survive container rebuilds:

- `runtime/conf/secret_settings.py`
- `runtime/evennia.db3`
- `runtime/logs/`
- `runtime/static/`

The container startup script links these files and directories into
`/usr/src/game/server/` at runtime.
