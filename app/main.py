import os
import subprocess
from datetime import datetime

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from logger import write_log, list_log_files, read_log_file
from config_manager import load_config, save_config
from backup import list_backups, run_backup, restore_backup
from updater import update_os
from driver_installer import install_coral_drivers
from gdrive_sync import (
    get_drive_status,
    upload_backup_to_drive,
    list_drive_backups,
    save_token_json,
)

from self_updater import (
    get_update_status,
    set_update_channel,
    get_update_channel,
    download_update,
    force_update_check,
)

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

RESTART_FLAG = "/data/restart_required"


def get_system_hostname() -> str:
    try:
        result = subprocess.run(
            ["hostnamectl", "--static"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    # Fallback to container hostname
    try:
        return os.uname().nodename
    except Exception:
        return "unknown"


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


def get_frigate_status() -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "frigate"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def get_coral_status() -> bool:
    return os.path.exists("/dev/apex_0")


def is_restart_required() -> bool:
    return os.path.exists(RESTART_FLAG)


def set_restart_required(flag: bool):
    try:
        if flag:
            os.makedirs(os.path.dirname(RESTART_FLAG), exist_ok=True)
            with open(RESTART_FLAG, "w", encoding="utf-8") as f:
                f.write(datetime.now().isoformat())
        else:
            if os.path.exists(RESTART_FLAG):
                os.remove(RESTART_FLAG)
    except Exception as e:
        write_log("System", f"Failed to set restart flag: {e}")


@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/logs")
async def logs_page(request: Request):
    """Full log viewer page."""
    return templates.TemplateResponse("logs.html", {"request": request})


@app.get("/api/status")
async def api_status():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    system = {
        "hostname": get_system_hostname(),
        "os": get_os_version(),
        "frigate_ok": get_frigate_status(),
        "coral_ok": get_coral_status(),
        "restart_required": is_restart_required(),
    }

    cfg = load_config()
    drive_status = get_drive_status()

    update_info = get_update_status()
    update_available = bool(update_info.get("update_available"))
    update_channel = update_info.get("channel")
    update_remote = update_info.get("remote_version")
    update_local = update_info.get("local_version")

    return {
        "timestamp": timestamp,
        "system": system,
        "drive": drive_status,
        "update": {
            "available": update_available,
            "channel": update_channel,
            "remote_version": update_remote,
            "local_version": update_local,
        },
    }


# --------- Backup APIs ---------


@app.get("/api/backups")
async def api_list_backups():
    """
    Return structured backup info with optional Drive presence:
    {
      "files": [
        {
          "filename": "...",
          "name": "frigate_config",
          "timestamp": "2025-11-12 21:46:20",
          "size_bytes": 123456,
          "local": true,
          "drive": true/false/"na"
        }
      ]
    }
    """
    backups = list_backups()
    cfg = load_config()
    drive_enabled = bool(cfg.get("GDRIVE_ENABLED", False))

    if drive_enabled and backups:
        filenames = [b["filename"] for b in backups]
        drive_index = list_drive_backups(filenames)
    else:
        drive_index = {}

    for b in backups:
        b["local"] = True
        if not drive_enabled:
            b["drive"] = "na"
        else:
            b["drive"] = bool(drive_index.get(b["filename"], False))

    return {"files": backups}


@app.get("/api/backups/download")
async def api_download_backup(file: str):
    """
    Download a backup tar.gz by filename.
    """
    from pathlib import Path

    safe_name = os.path.basename(file)
    backup_path = os.path.join("/backups", safe_name)

    if not os.path.exists(backup_path):
        return JSONResponse(
            {"ok": False, "message": "File not found"},
            status_code=404,
        )

    return FileResponse(
        backup_path,
        media_type="application/gzip",
        filename=safe_name,
    )


@app.post("/api/backup/run")
async def api_run_backup():
    cfg = load_config()
    path = run_backup()
    if not path:
        msg = "Backup failed. See logs for details."
        return JSONResponse({"ok": False, "error": msg, "message": msg}, status_code=500)

    drive_msg = ""
    if cfg.get("GDRIVE_ENABLED", False):
        uploaded = upload_backup_to_drive(path)
        drive_msg = " and uploaded to Google Drive" if uploaded else " (Drive upload failed or disabled)"

    msg = f"Backup completed: {path}{drive_msg}"
    return {"ok": True, "path": path, "message": msg}


@app.post("/api/restore")
async def api_restore(request: Request):
    body = await request.json()
    filename = body.get("filename")
    if not filename:
        msg = "No filename provided."
        return JSONResponse({"ok": False, "error": msg, "message": msg}, status_code=400)

    success = restore_backup(filename)
    if success:
        set_restart_required(True)
    msg = (
        "Restore completed. Restart Frigate is recommended."
        if success
        else "Restore failed. Check logs."
    )
    return {"ok": success, "message": msg}


# --------- Google Drive config APIs ---------


@app.get("/api/gdrive/status")
async def api_gdrive_status():
    status = get_drive_status()
    return status


@app.post("/api/gdrive/config")
async def api_gdrive_config(request: Request):
    """
    Configure Google Drive:
    body: {
      "enabled": bool,
      "token_json": "..."
    }
    """
    body = await request.json()
    enabled = bool(body.get("enabled", False))
    token_json = body.get("token_json")

    cfg = load_config()
    cfg["GDRIVE_ENABLED"] = enabled

    if token_json:
        ok = save_token_json(token_json)
        if not ok:
            return JSONResponse(
                {"ok": False, "message": "Failed to save token JSON."},
                status_code=500,
            )

    save_config(cfg)
    return {"ok": True, "message": "Google Drive configuration updated."}


@app.post("/api/gdrive/upload_token")
async def api_gdrive_upload_token(file: UploadFile = File(...)):
    """
    Upload a token.json file via multipart/form-data.
    """
    content = await file.read()
    token_str = content.decode("utf-8")
    ok = save_token_json(token_str)
    if not ok:
        return JSONResponse(
            {"ok": False, "message": "Failed to save uploaded token file."},
            status_code=500,
        )

    cfg = load_config()
    cfg["GDRIVE_ENABLED"] = True
    save_config(cfg)

    return {"ok": True, "message": "Token uploaded and Drive enabled."}


# --------- System / OS / Hostname / Drivers ---------


@app.post("/api/system/update_os")
async def api_update_os():
    ok = update_os()
    msg = "OS update completed." if ok else "OS update failed. Check logs."
    return {"ok": ok, "message": msg}


@app.post("/api/system/install_drivers")
async def api_install_drivers():
    ok = install_coral_drivers()
    msg = (
        "Coral driver installation requested (stub only in container)."
        if ok
        else "Coral driver install not implemented inside container."
    )
    return {"ok": ok, "message": msg}


@app.post("/api/system/restart_frigate")
async def api_restart_frigate():
    cfg = load_config()
    cmd = cfg.get("FRIGATE_RESTART_CMD", "systemctl restart frigate")
    try:
        write_log("System", f"Restarting Frigate with command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            write_log("System", f"Frigate restart failed: {result.stderr}")
            msg = f"Frigate restart failed: {result.stderr}"
            return {"ok": False, "error": result.stderr, "message": msg}
        write_log("System", "Frigate restart command completed.")
        # Clear restart-required flag on success
        set_restart_required(False)
        return {"ok": True, "message": "Frigate restart command completed."}
    except Exception as e:
        write_log("System", f"Frigate restart exception: {e}")
        msg = f"Frigate restart exception: {e}"
        return {"ok": False, "error": str(e), "message": msg}


@app.post("/api/system/reboot")
async def api_reboot():
    try:
        write_log("System", "Reboot requested via API.")
        subprocess.Popen(["reboot"])
        return {"ok": True, "message": "Reboot command issued."}
    except Exception as e:
        write_log("System", f"Reboot failed: {e}")
        msg = f"Reboot failed: {e}"
        return {"ok": False, "error": str(e), "message": msg}


@app.post("/api/system/set_hostname")
async def api_set_hostname(request: Request):
    try:
        body = await request.json()
        new_name = body.get("hostname", "").strip()

        if not new_name:
            msg = "Hostname cannot be empty."
            return {"ok": False, "error": msg, "message": msg}

        if len(new_name) > 60 or not new_name.replace("-", "").isalnum():
            msg = "Invalid hostname format. Use letters, numbers, and hyphens only."
            return {"ok": False, "error": msg, "message": msg}

        os.system(f"hostnamectl set-hostname {new_name}")

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
        msg = f"Hostname changed to {new_name}. Reboot required."
        return {"ok": True, "hostname": new_name, "reboot_required": True, "message": msg}
    except Exception as e:
        write_log("System", f"Hostname change failed: {e}")
        msg = f"Hostname change failed: {e}"
        return {"ok": False, "error": str(e), "message": msg}


# --------- Log viewer APIs ---------


@app.get("/api/logs/list")
async def api_logs_list():
    """Return list of available log files."""
    files = list_log_files()
    return {"files": files}


@app.get("/api/logs/content")
async def api_logs_content(file: int = 0, max_lines: int = 200):
    """
    Return last N lines of the selected log file.
    file=0 -> manager.log, file=1 -> manager.log.1, etc.
    """
    lines = read_log_file(index=file, max_lines=max_lines)
    return {"lines": lines}


# --------- Self-updater APIs ---------


@app.get("/api/update/status")
async def api_update_status():
    """
    Check update status against GitHub.
    """
    status = get_update_status()
    status["channel"] = get_update_channel()
    return status


@app.post("/api/update/channel")
async def api_update_channel(request: Request):
    """
    Change update channel: main, releases, dev
    """
    body = await request.json()
    channel = str(body.get("channel", "")).strip()
    ok, msg = set_update_channel(channel)
    if not ok:
        return JSONResponse({"ok": False, "message": msg}, status_code=400)

    status = get_update_status()
    status["message"] = msg
    return status


@app.post("/api/update/download")
async def api_update_download():
    """
    Download the latest update zip into /data/updates.
    Does NOT apply the update; use update.sh on the host.
    """
    result = download_update()
    code = 200 if result.get("ok") else 500
    return JSONResponse(result, status_code=code)


@app.post("/api/update/check_now")
async def api_update_check_now():
    """
    Force a GitHub update check immediately (bypasses cache).
    """
    result = force_update_check()
    code = 200 if result.get("ok") else 500
    return JSONResponse(result, status_code=code)
