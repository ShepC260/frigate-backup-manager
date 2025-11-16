import os
import json
import requests
from datetime import datetime, timedelta

from logger import write_log
from config_manager import load_config, save_config

REPO_OWNER = "ShepC260"
REPO_NAME = "frigate-backup-manager"

# Cache state
_LAST_UPDATE_CHECK = None
_CACHED_UPDATE_DATA = None
_CHECK_INTERVAL = timedelta(days=1)  # once per day


def _get_channel_url(channel: str) -> str:
    """
    Determine which GitHub endpoint to query based on update channel.
    - main -> latest commit on main branch
    - releases -> latest GitHub release
    - dev -> latest commit on dev branch
    """
    if channel == "releases":
        return f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    elif channel == "dev":
        return f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/dev"
    else:  # main
        return f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/main"


def _perform_real_update_check() -> dict:
    """
    Actually hit GitHub and get latest version info.
    """
    cfg = load_config()
    channel = cfg.get("UPDATE_CHANNEL", "main")

    url = _get_channel_url(channel)

    write_log("Updater", f"Checking for updates from: {url}")

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception as e:
        write_log("Updater", f"GitHub request error: {e}")
        return {
            "ok": False,
            "error": str(e),
            "channel": channel,
            "checked_at": datetime.utcnow().isoformat(),
        }

    data = r.json()
    remote_version = None

    if channel == "releases":
        remote_version = data.get("tag_name")
    else:
        remote_version = data.get("sha")

    local_version = cfg.get("LOCAL_VERSION", "unknown")

    result = {
        "ok": True,
        "channel": channel,
        "remote_version": remote_version,
        "local_version": local_version,
        "update_available": remote_version != local_version,
        "checked_at": datetime.utcnow().isoformat(),
    }

    return result


def get_update_status() -> dict:
    """
    Return cached update info unless last check >1 day old.
    """
    global _LAST_UPDATE_CHECK, _CACHED_UPDATE_DATA

    now = datetime.utcnow()

    # Serve cached result
    if _LAST_UPDATE_CHECK and _CACHED_UPDATE_DATA:
        if now - _LAST_UPDATE_CHECK < _CHECK_INTERVAL:
            return _CACHED_UPDATE_DATA

    # Otherwise perform real check
    result = _perform_real_update_check()

    # Cache it
    _LAST_UPDATE_CHECK = now
    _CACHED_UPDATE_DATA = result

    return result


def force_update_check() -> dict:
    """
    Manual override for "Check Now" button.
    Bypasses cache and performs real request.
    """
    global _LAST_UPDATE_CHECK, _CACHED_UPDATE_DATA

    result = _perform_real_update_check()

    # Refresh cache completely
    _LAST_UPDATE_CHECK = datetime.utcnow()
    _CACHED_UPDATE_DATA = result

    return result


def get_update_channel() -> str:
    cfg = load_config()
    return cfg.get("UPDATE_CHANNEL", "main")


def set_update_channel(channel: str) -> (bool, str):
    channel = channel.lower().strip()
    if channel not in ["main", "releases", "dev"]:
        return False, "Invalid channel. Use: main, releases, or dev."

    cfg = load_config()
    cfg["UPDATE_CHANNEL"] = channel
    save_config(cfg)

    write_log("Updater", f"Update channel changed to: {channel}")
    return True, f"Update channel set to {channel}."


def download_update() -> dict:
    """
    Downloads repo ZIP for the selected channel into /data/updates/.
    """
    cfg = load_config()
    channel = cfg.get("UPDATE_CHANNEL", "main")

    if channel == "releases":
        zip_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/tags/latest.zip"
    elif channel == "dev":
        zip_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/dev.zip"
    else:
        zip_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/main.zip"

    os.makedirs("/data/updates", exist_ok=True)
    dest = f"/data/updates/update_{channel}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"

    write_log("Updater", f"Downloading update from {zip_url}")

    try:
        r = requests.get(zip_url, timeout=20)
        r.raise_for_status()

        with open(dest, "wb") as f:
            f.write(r.content)

        write_log("Updater", f"Update downloaded to {dest}")

        return {"ok": True, "file": dest, "message": f"Downloaded to {dest}"}

    except Exception as e:
        write_log("Updater", f"Update download failed: {e}")
        return {"ok": False, "error": str(e), "message": f"Download failed: {e}"}
