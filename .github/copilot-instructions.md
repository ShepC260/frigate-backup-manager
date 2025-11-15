Short summary to help an AI agent get productive in this repository.

Focus: the app is a small FastAPI service (UVicorn) that manages Frigate backups, optional
Google Drive sync, driver detection/installation, and simple system/update actions.

Key architecture & components
- **Web API / UI**: `app/main.py` — FastAPI routes, Jinja2 templates in `app/templates`, static files in `app/static`.
- **Backups**: `app/backup.py` (create/list/restore local tar.gz files in `/backups`). Filenames use pattern `frigate_config_{YYYY-MM-DD_HH-MM-SS}.tar.gz`.
- **Google Drive integration**: `app/gdrive_sync.py` — enabled by `GDRIVE_ENABLED` and token at `GDRIVE_TOKEN_PATH` (default `/data/drive_token.json`). Drive upload/list uses Google API clients declared in `requirements.txt`.
- **Config**: `app/config_manager.py` — single JSON config at `/data/config.json`. Defaults live in `DEFAULT_CONFIG`. Use `load_config()` / `save_config()` to read/write.
- **Scheduler**: `app/scheduler.py` — uses `apscheduler` and expects cron expressions stored in config keys like `BACKUP_CRON`, `SECURITY_UPDATE_CRON`, `LOG_ROTATION_CRON`.
- **Drivers**: `app/drivers.py` and `app/driver_installer.py` — driver detection and (host-level) install helpers. Container often stubs driver install; see `install_coral_drivers()` differences between files.
- **Updates**: `app/updater.py` / `app/self_updater.py` — checks GitHub, downloads update packages to `/data/updates` but does not apply host-level update; `update.sh` on host is referenced by the code/workflow.
- **Logging**: `app/logger.py` — writes to `/logs/manager.log`, rotates at 512KB with 5 backups. Use `write_log(...)` for consistent entries.

Important runtime facts & developer workflows
- Run locally / in container: Dockerfile creates a venv and runs `uvicorn main:app --host 0.0.0.0 --port 8082` (see `Dockerfile`).
- Compose: `docker-compose.yml` maps ports and volumes and sets `privileged: true` because some actions (reboot, hostnamectl) require host privileges.
- Build & run (common):
  - `docker compose build && docker compose up -d`
  - `docker compose logs -f frigate-backup-manager`
- Config editing: edit `/data/config.json` or use the API endpoints (e.g. `POST /api/gdrive/config`). The app merges missing keys from `DEFAULT_CONFIG` on load.
- Backup dev/test: create files under `backups/` and follow naming pattern; `app/backup.py` contains the exact parsing logic in `_parse_backup_filename()`.

Patterns & conventions to follow when changing code
- Always use `load_config()` / `save_config()` when reading or writing config; `load_config()` merges `DEFAULT_CONFIG`.
- Use `write_log(component, message)` for all operational logs to preserve rotation and location (`/logs/manager.log`).
- Calls that use `subprocess` or system commands (e.g. `apt-get`, `systemctl`, `reboot`, `hostnamectl`, `docker`) are host-sensitive — running them inside the container often requires `privileged` or will be intentionally stubbed. Check `driver_installer.py` vs `drivers.py` for how container vs host behavior is handled.
- Background jobs are scheduled with `apscheduler` in `app/scheduler.py` — config must contain cron keys used there (`BACKUP_CRON`, etc.). If these keys are missing the scheduler will raise KeyError; ensure the config contains valid cron strings (5 fields). `cron_utils.describe_cron()` uses `cron_descriptor` to produce human-friendly descriptions.

Integration points & external dependencies
- Google Drive: requires OAuth token JSON (saved via UI or `POST /api/gdrive/upload_token`). Token path default: `/data/drive_token.json`.
- Docker and host: many features expect access to `systemctl`, `reboot`, `hostnamectl`, or the Docker socket; CI/dev agents should not run those operations unless running against a privileged test host or a mock.
- Network: service listens on port `8082` inside container; UI expects a browser to reach that port.

Quick references (where to look)
- REST + templates: `app/main.py` and `app/templates/index.html`
- Backup logic & filename rules: `app/backup.py` (`_parse_backup_filename`, `run_backup`, `restore_backup`).
- Drive sync: `app/gdrive_sync.py` (`get_drive_status`, `upload_backup_to_drive`, `list_drive_backups`, `save_token_json`).
- Config load/save: `app/config_manager.py` (`DEFAULT_CONFIG`, `CONFIG_PATH=/data/config.json`).
- Logging & rotation: `app/logger.py` (`write_log`, `list_log_files`, `read_log_file`).
- Scheduler & cron: `app/scheduler.py` and `app/cron_utils.py`.
- Host-level commands & updater: `app/update.py`, `app/self_updater.py` (note: download vs apply separation).

When proposing code changes
- Explicitly state whether code will run in-container vs on-host; prefer to add clear `if in_container():` guards or document required privileges.
- For features that touch system state (reboot/hostname/package installs), add unit-testable boundaries and/or mockable wrappers — see `update.run_command()` as an example wrapper around `subprocess`.
- Keep API behavior backward compatible: `app/main.py` routes are used by the UI; changing response shape may break the front-end templates.

If anything here is ambiguous or you want the doc to include more examples (API request/response samples, config.json example, or development run commands), tell me which section to expand.
