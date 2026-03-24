## NAS helper scripts

These scripts are intended to be run directly on the QNAP NAS in:

- `/share/CACHEDEV1_DATA/Container/mud-nas-evennia/scripts/nas/`

They wrap the project-specific Docker and Evennia commands so daily operations
do not require retyping long paths.

Available scripts:

- `update.sh`
  - Run `git pull origin main` in the project directory
- `reload.sh`
  - Ensure the Server is running, then run `evennia reload`
- `start.sh`
  - Run `docker compose up -d`
  - Wait briefly
  - If the known QNAP issue leaves `Server` stopped while `Portal` is running,
    automatically run one `evennia start`
- `stop.sh`
  - Run `docker compose stop`
- `status.sh`
  - Run `evennia status`
- `install_aliases.sh`
  - Install shell aliases:
    - `update`
    - `reload`
    - `start`
    - `stop`
    - `status`

Install aliases:

```sh
cd /share/CACHEDEV1_DATA/Container/mud-nas-evennia
sh scripts/nas/install_aliases.sh
. "$HOME/.profile_mud_aliases"
```

After that, you can use:

```sh
update
reload
start
stop
status
```

Known behavior:

- `start` is safe for normal use.
- Do not manually run `evennia start` after `start` unless `status` shows
  `Server: NOT RUNNING`.
- Repeating `evennia start` while both services are already running can produce
  a misleading `Address in use` error on the internal AMP port.
- The helper scripts already retry `status` and treat `Another twistd server is running`
  as a transitional startup state, then re-check `evennia status`.
