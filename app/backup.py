import os
import tarfile
from datetime import datetime
from typing import List, Optional

from logger import write_log
from config_manager import load_config

BACKUP_DIR = "/backups"


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def list_backups() -> List[str]:
    _ensure_dir(BACKUP_DIR)
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz")]
    files.sort(reverse=True)
    return files


def run_backup() -> Optional[str]:
    cfg = load_config()
    _ensure_dir(BACKUP_DIR)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"frigate_config_{ts}.tar.gz"
    full_path = os.path.join(BACKUP_DIR, filename)

    backup_paths = cfg.get("BACKUP_PATHS", ["/config"])
    existing = [p for p in backup_paths if os.path.exists(p)]

    if not existing:
        write_log("Backup", "No existing backup paths found. Backup aborted.")
        return None

    try:
        write_log("Backup", f"Creating backup: {full_path}")
        with tarfile.open(full_path, "w:gz") as tar:
            for path in existing:
                arcname = os.path.basename(path.rstrip("/")) or "config"
                tar.add(path, arcname=arcname)
        write_log("Backup", "Backup created successfully.")
    except Exception as e:
        write_log("Backup", f"Backup failed: {e}")
        return None

    # Retention cleanup
    try:
        retention = int(cfg.get("BACKUP_RETENTION", 10))
    except Exception:
        retention = 10

    files = list_backups()
    if len(files) > retention:
        for old in files[retention:]:
            try:
                os.remove(os.path.join(BACKUP_DIR, old))
                write_log("Backup", f"Removed old backup: {old}")
            except Exception as e:
                write_log("Backup", f"Failed to remove old backup {old}: {e}")

    return full_path


def restore_backup(filename: str) -> bool:
    path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(path):
        write_log("Restore", f"Backup file not found: {path}")
        return False

    try:
        write_log("Restore", f"Restoring backup from: {path}")
        with tarfile.open(path, "r:gz") as tar:
            tar.extractall("/")  # assumes relevant paths are bind-mounted
        write_log("Restore", "Restore completed.")
        return True
    except Exception as e:
        write_log("Restore", f"Restore failed: {e}")
        return False
