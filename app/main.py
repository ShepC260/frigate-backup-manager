from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os, datetime

from logger import LOG_DIR, write_log
from backup import run_backup, list_backups
from restore import restore_local, restore_from_drive, _list_drive_backups, list_backups
from update import run_full_update, update_frigate, check_for_updates
from drivers import detect_drivers, install_drivers
from scheduler import reload_scheduler, get_next_run_times, init_scheduler
from config_manager import load_config, save_config
from status import get_status_summary
from gdrive_sync import get_drive_status
from cron_utils import is_valid_cron, describe_cron

app = FastAPI(title="Frigate Backup Manager", docs_url=None, redoc_url=None)

# --- TEMPLATE LOADING ---
templates = Jinja2Templates(directory="/app/templates")

# --- INITIALIZE SCHEDULER ON STARTUP ---
init_scheduler()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard UI."""
    return templates.TemplateResponse("index.html", {"request": request})


# ===========================
# CONFIG / SCHEDULER ENDPOINTS
# ===========================
@app.get("/api/config")
async def api_get_config():
    cfg = load_config()
    next_runs = get_next_run_times()
    friendly = {}
    for k, v in cfg.items():
        if k.endswith("_CRON"):
            friendly[k] = describe_cron(v)
    return {"config": cfg, "next_runs": next_runs, "friendly": friendly}


@app.post("/api/config/update")
async def api_update_config(data: dict):
    cfg = load_config()
    for key, val in data.items():
        if key.endswith("_CRON"):
            if not is_valid_cron(val):
                return JSONResponse({"ok": False, "error": f"Invalid cron expression: {val}"})
            cfg[key] = val
    save_config(cfg)
    reload_scheduler()
    return {"ok": True}


# ===========================
# BACKUP ENDPOINTS
# ===========================
@app.post("/api/backup/run")
async def api_run_backup():
    run_backup()
    return {"ok": True}


@app.get("/api/backups/list")
async def api_list_backups():
    return {"files": list_backups()}


# ===========================
# RESTORE ENDPOINTS
# ===========================
@app.get("/api/restore/list")
async def api_restore_list(source: str = "local"):
    if source == "gdrive":
        return {"files": list_drive_backups()}
    return {"files": list_backups()}


@app.post("/api/restore/run")
async def api_restore(data: dict):
    source = data.get("source", "local")
    name = data.get("name")
    if source == "gdrive":
        file_id = data.get("id")
        ok = restore_drive_backup(file_id, name)
    else:
        ok = restore_local_backup(name)
    return {"ok": ok}


# ===========================
# DRIVER ENDPOINTS
# ===========================
@app.get("/api/drivers/detect")
async def api_detect_drivers():
    return detect_drivers()


@app.post("/api/drivers/install")
async def api_install_drivers():
    result = install_drivers()
    return result


# ===========================
# SYSTEM / UPDATE ENDPOINTS
# ===========================
@app.post("/api/system/update")
async def api_system_update():
    ok = run_full_update()
    return {"ok": ok}


@app.post("/api/system/reboot")
async def api_system_reboot():
    write_log("System", "System reboot triggered via API.")
    os.system("reboot &")
    return {"ok": True}


@app.post("/api/system/restart_frigate")
async def api_restart_frigate():
    ok = update_frigate()
    return {"ok": ok}


@app.get("/api/system/check_updates")
async def api_check_updates():
    updates = check_for_updates()
    return {"updates": updates}


# ===========================
# GOOGLE DRIVE ENDPOINTS
# ===========================
@app.get("/api/gdrive/status")
async def api_gdrive_status():
    status = get_drive_status()
    cfg = load_config()
    return {
        "configured": status["configured"],
        "email": status["email"],
        "enabled": cfg.get("ENABLE_GDRIVE_SYNC", False),
        "token_path": cfg.get("GDRIVE_TOKEN_PATH", "/data/drive_token.json"),
    }


@app.post("/api/gdrive/settings")
async def api_gdrive_settings(data: dict):
    enabled = bool(data.get("enabled", False))
    token_path = data.get("token_path", "/data/drive_token.json")
    cfg = load_config()
    cfg["ENABLE_GDRIVE_SYNC"] = enabled
    cfg["GDRIVE_TOKEN_PATH"] = token_path
    save_config(cfg)
    return {"ok": True, "enabled": enabled, "token_path": token_path}


# ===========================
# LOG ENDPOINTS
# ===========================
@app.get("/api/logs/latest")
async def api_logs_latest(limit: int = 50):
    """Return last N lines from today's log."""
    try:
        log_path = os.path.join(LOG_DIR, f"{datetime.date.today().isoformat()}.log")
        if not os.path.exists(log_path):
            return {"lines": []}
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
        return {"lines": [line.strip() for line in lines]}
    except Exception as e:
        return {"lines": [f"Error reading log: {e}"]}


# ===========================
# STATUS ENDPOINT
# ===========================
@app.get("/api/status")
async def api_status():
    """Return system and task status for the dashboard."""
    summary = get_status_summary()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "timestamp": now,
        "system": summary["system"],
        "backup": {"time": now, "state": "ok", "color": "#18b09f"},
        "update": {"time": now, "state": "ok", "color": "#a1c349"},
        "rotation": {"time": now, "state": "ok", "color": "#3cb8ff"},
    }
