import os
import requests
from datetime import datetime
from typing import Tuple, Dict, Any

from logger import write_log
from config_manager import load_config, save_config

GITHUB_API_BASE = "https://api.github.com"


def _get_repo_info() -> Tuple[str, str]:
    cfg = load_config()
    user = cfg.get("GITHUB_USER", "shepc260")
    repo = cfg.get("GITHUB_REPO", "frigate-backup-manager")
    return user, repo


def get_update_channel() -> str:
    cfg = load_config()
    channel = cfg.get("UPDATE_CHANNEL", "main")
    if channel not in ("main", "releases", "dev"):
        channel = "main"
    return channel


def set_update_channel(channel: str) -> Tuple[bool, str]:
    if channel not in ("main", "releases", "dev"):
        return False, "Invalid update channel"
    cfg = load_config()
    cfg["UPDATE_CHANNEL"] = channel
    save_config(cfg)
    write_log("Updater", f"Update channel set to {channel}")
    return True, f"Update channel set to {channel}"


def get_local_version() -> str:
    cfg = load_config()
    v = cfg.get("LOCAL_VERSION") or "dev-unknown"
    return v


def set_local_version(version: str) -> None:
    cfg = load_config()
    cfg["LOCAL_VERSION"] = version
    save_config(cfg)
    write_log("Updater", f"Local version set to {version}")


def _get_latest_release() -> Dict[str, Any]:
    """
    Fetch latest GitHub release for the repo.
    Returns dict with keys: version, download_url
    """
    user, repo = _get_repo_info()
    url = f"{GITHUB_API_BASE}/repos/{user}/{repo}/releases/latest"

    write_log("Updater", f"Checking latest release from {url}")
    r = requests.get(url, timeout=10, headers={"Accept": "application/vnd.github+json"})
    if r.status_code != 200:
        raise RuntimeError(f"GitHub API returned {r.status_code}: {r.text}")

    data = r.json()
    tag = data.get("tag_name") or data.get("name") or "unknown"
    zip_url = data.get("zipball_url")
    if not zip_url:
        # Fallback to GitHub's generic tag zip
        zip_url = f"https://github.com/{user}/{repo}/archive/refs/tags/{tag}.zip"

    return {
        "version": tag,
        "download_url": zip_url,
        "channel": "releases",
    }


def _get_latest_commit(branch: str) -> Dict[str, Any]:
    """
    Fetch latest commit for the given branch (main or dev).
    Returns dict with keys: version, download_url
    """
    user, repo = _get_repo_info()
    api_url = f"{GITHUB_API_BASE}/repos/{user}/{repo}/commits/{branch}"
    write_log("Updater", f"Checking latest commit from {api_url}")

    r = requests.get(api_url, timeout=10, headers={"Accept": "application/vnd.github+json"})
    if r.status_code != 200:
        raise RuntimeError(f"GitHub API returned {r.status_code}: {r.text}")

    data = r.json()
    sha = data.get("sha", "")[:7] or "unknown"
    remote_version = f"dev-{branch}-{sha}"

    # Direct zip of branch
    zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"

    return {
        "version": remote_version,
        "download_url": zip_url,
        "channel": branch if branch in ("main", "dev") else "main",
    }


def get_update_status() -> Dict[str, Any]:
    """
    High-level status for the UI:
    {
      "channel": "main",
      "local_version": "...",
      "remote_version": "...",
      "update_available": true/false,
      "download_url": "...",
      "checked_at": "YYYY-MM-DD HH:MM:SS",
      "error": "...optional..."
    }
    """
    channel = get_update_channel()
    local_version = get_local_version()
    checked_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        if channel == "releases":
            info = _get_latest_release()
        elif channel == "dev":
            info = _get_latest_commit("dev")
        else:
            # default to main
            info = _get_latest_commit("main")

        remote_version = info["version"]
        download_url = info["download_url"]
        update_available = (remote_version != local_version)

        return {
            "ok": True,
            "channel": channel,
            "local_version": local_version,
            "remote_version": remote_version,
            "update_available": update_available,
            "download_url": download_url,
            "checked_at": checked_at,
        }
    except Exception as e:
        msg = f"Update check failed: {e}"
        write_log("Updater", msg)
        return {
            "ok": False,
            "channel": channel,
            "local_version": local_version,
            "remote_version": None,
            "update_available": False,
            "download_url": None,
            "checked_at": checked_at,
            "error": str(e),
        }


def download_update() -> Dict[str, Any]:
    """
    Downloads the latest update zip into /data/updates and returns metadata.
    This does NOT apply the update (container update is handled by update.sh).
    """
    status = get_update_status()
    channel = status.get("channel", "main")

    if not status.get("ok"):
        return {"ok": False, "message": "Update status check failed", "error": status.get("error")}

    download_url = status.get("download_url")
    remote_version = status.get("remote_version") or "unknown"

    if not download_url:
        return {"ok": False, "message": "No download URL for update"}

    updates_dir = "/data/updates"
    os.makedirs(updates_dir, exist_ok=True)

    filename = f"{channel}-{remote_version}.zip".replace("/", "_")
    dest_path = os.path.join(updates_dir, filename)

    try:
        write_log("Updater", f"Downloading update from {download_url} to {dest_path}")
        with requests.get(download_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

        # Update local version record to remote
        set_local_version(remote_version)

        msg = (
            f"Update package downloaded to {dest_path}. "
            f"Run ./update.sh on the host to rebuild and apply."
        )
        write_log("Updater", msg)
        return {
            "ok": True,
            "message": msg,
            "file": dest_path,
            "remote_version": remote_version,
            "channel": channel,
        }
    except Exception as e:
        msg = f"Download failed: {e}"
        write_log("Updater", msg)
        return {
            "ok": False,
            "message": msg,
            "error": str(e),
        }
