import os
import subprocess
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from logger import write_log
from config_manager import load_config, save_config
from backup import list_backups, run_backup, restore_backup
from updater import update_os
from driver_installer import install_coral_drivers
from gdrive_sync import get_drive_status, upload_backup_to_drive

app = FastAPI(title="Frigate Backup Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="/app/static"), name="static")
templates = Jinja2Templates(directory="/app/templates")


def get_os_version() -> str:
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith("PRETTY_NAME"):
                return line.strip().split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return "Unknown OS"


def get_frigate_version() -> str:
    # Placeholder — could be extended to query Frigate's API
    return "not found"


def get_coral_status() -> str:
    if os.path.exists("/dev/apex_0"):
        return "Detected"
    return "Not detected"


@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def api_status():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = os.uname().nodename

    system = {
        "os": get_os_version(),
        "frigate": get_frigate_version(),
        "coral": get_coral_status(),
        "hostname": hostname,
    }

    # These can be made smarter later (e.g. track last success, etc.)
    backup_state = {
        "time": timestamp,
        "state": "ok",
        "color": "#18b09f",
    }
    update_state = {
        "time": timestamp,
        "state": "ok",
        "color": "#a1c349",
    }
    rotation_state = {
        "time": timestamp,
        "state": "ok",
        "color": "#3cb8ff",
    }

    return {
        "timestamp": timestamp,
        "system": system,
        "backup": backup_state,
        "update": update_state,
        "rotation": rotation_state,
    }


@app.get("/api/backups")
async def api_list_backups():
    files = list_backups()
    return {"files": files}


@app.post("/api/backup/run")
async def api_run_backup():
    cfg = load_config()
    path = run_backup()
    if not path:
        return JSONResponse({"ok": False, "error": "Backup failed"}, status_code=500)

    if cfg.get("GDRIVE_ENABLED", False):
        upload_backup_to_drive(path)

    return {"ok": True, "path": path}


@app.post("/api/restore")
async def api_restore(request: Request):
    body = await request.json()
    filename = body.get("filename")
    if not filename:
        return JSONResponse({"ok": False, "error": "No filename provided"}, status_code=400)

    success = restore_backup(filename)
    return {"ok": success}


@app.get("/api/gdrive/status")
async def api_gdrive_status():
    cfg = load_config()
    status = get_drive_status()
    status["enabled"] = cfg.get("GDRIVE_ENABLED", False)
    return status


@app.get("/api/config")
async def api_get_config():
    cfg = load_config()
    # Only expose safe keys
    public = {
        "BACKUP_PATHS": cfg.get("BACKUP_PATHS"),
        "BACKUP_RETENTION": cfg.get("BACKUP_RETENTION"),
        "GDRIVE_ENABLED": cfg.get("GDRIVE_ENABLED"),
        "GDRIVE_TOKEN_PATH": cfg.get("GDRIVE_TOKEN_PATH"),
    }
    return public


@app.post("/api/config")
async def api_set_config(request: Request):
    body = await request.json()
    cfg = load_config()

    if "GDRIVE_ENABLED" in body:
        cfg["GDRIVE_ENABLED"] = bool(body["GDRIVE_ENABLED"])
    if "GDRIVE_TOKEN_PATH" in body:
        cfg["GDRIVE_TOKEN_PATH"] = str(body["GDRIVE_TOKEN_PATH"])
    if "BACKUP_RETENTION" in body:
        try:
            cfg["BACKUP_RETENTION"] = int(body["BACKUP_RETENTION"])
        except Exception:
            pass

    save_config(cfg)
    return {"ok": True}


@app.post("/api/system/update_os")
async def api_update_os():
    ok = update_os()
    return {"ok": ok}


@app.post("/api/system/install_drivers")
async def api_install_drivers():
    ok = install_coral_drivers()
    return {"ok": ok}


@app.post("/api/system/restart_frigate")
async def api_restart_frigate():
    cfg = load_config()
    cmd = cfg.get("FRIGATE_RESTART_CMD", "systemctl restart frigate")
    try:
        write_log("System", f"Restarting Frigate with command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            write_log("System", f"Frigate restart failed: {result.stderr}")
            return {"ok": False, "error": result.stderr}
        write_log("System", "Frigate restart command completed.")
        return {"ok": True}
    except Exception as e:
        write_log("System", f"Frigate restart exception: {e}")
        return {"ok": False, "error": str(e)}


@app.post("/api/system/reboot")
async def api_reboot():
    try:
        write_log("System", "Reboot requested via API.")
        subprocess.Popen(["reboot"])
        return {"ok": True}
    except Exception as e:
        write_log("System", f"Reboot failed: {e}")
        return {"ok": False, "error": str(e)}


@app.post("/api/system/set_hostname")
async def api_set_hostname(request: Request):
    try:
        body = await request.json()
        new_name = body.get("hostname", "").strip()

        if not new_name:
            return {"ok": False, "error": "Hostname cannot be empty"}

        if len(new_name) > 60 or not new_name.replace("-", "").isalnum():
            return {"ok": False, "error": "Invalid hostname format"}

        # Change in runtime
        os.system(f"hostnamectl set-hostname {new_name}")

        # Update /etc/hosts so 127.0.1.1 points at the new hostname
        try:
            with open("/etc/hosts", "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open("/etc/hosts", "w", encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("127.0.1.1"):
                        f.write(f"127.0.1.1   {new_name}\n")
                    else:
                        f.write(line)
        except Exception as e:
            write_log("System", f"Failed to update /etc/hosts: {e}")

        write_log("System", f"Hostname changed to: {new_name}")
        return {"ok": True, "hostname": new_name, "reboot_required": True}
    except Exception as e:
        write_log("System", f"Hostname change failed: {e}")
        return {"ok": False, "error": str(e)}
