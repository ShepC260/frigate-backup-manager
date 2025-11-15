import os
import tarfile
from datetime import datetime
from typing import List, Dict

from logger import write_log
from config_manager import load_config

BACKUP_DIR = "/backups"


def _ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _parse_backup_filename(filename: str) -> Dict:
    """
    Parse filenames like:
      frigate_config_2025-11-12_21-46-20.tar.gz
    into {name, timestamp}
    """
    base = filename
    if base.endswith(".tar.gz"):
        base = base[:-7]

    parts = base.split("_")
    if len(parts) < 3:
        return {
            "name": base,
            "timestamp": None,
            "timestamp_str": "",
        }

    name = "_".join(parts[:-2])
    date_part = parts[-2]
    time_part = parts[-1]

    try:
        dt = datetime.strptime(f"{date_part}_{time_part}", "%Y-%m-%d_%H-%M-%S")
        ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        dt = None
        ts_str = ""

    return {
        "name": name,
        "timestamp": dt,
        "timestamp_str": ts_str,
    }


def list_backups() -> List[Dict]:
    """
    Return a list of backup metadata dicts:
      {
        "filename": "...",
        "name": "frigate_config",
        "timestamp": "2025-11-12 21:46:20",
        "size_bytes": 1234567
      }
    Sorted newest first.
    """
    _ensure_backup_dir()
    files = []
    for entry in os.listdir(BACKUP_DIR):
        if not entry.endswith(".tar.gz"):
            continue
        full_path = os.path.join(BACKUP_DIR, entry)
        if not os.path.isfile(full_path):
            continue

        stats = os.stat(full_path)
        size_bytes = stats.st_size
        meta = _parse_backup_filename(entry)
        files.append({
            "filename": entry,
            "name": meta["name"],
            "timestamp": meta["timestamp_str"],
            "size_bytes": size_bytes,
        })

    # Sort by timestamp descending where possible, fallback to filename
    def sort_key(item):
        meta = _parse_backup_filename(item["filename"])
        dt = meta["timestamp"]
        if dt:
            return dt
        return datetime.min

    files.sort(key=sort_key, reverse=True)
    return files


def _cleanup_old_backups():
    """
    Enforce BACKUP_RETENTION by oldest-first removal.
    """
    cfg = load_config()
    retention = int(cfg.get("BACKUP_RETENTION", 10) or 10)

    backups = list_backups()
    if len(backups) <= retention:
        return

    to_delete = backups[retention:]
    for item in to_delete:
        path = os.path.join(BACKUP_DIR, item["filename"])
        try:
            os.remove(path)
            write_log("Backup", f"Removed old backup: {item['filename']}")
        except Exception as e:
            write_log("Backup", f"Failed to remove {item['filename']}: {e}")


def run_backup() -> str | None:
    """
    Create a new backup tarball of BACKUP_PATHS.
    Returns full path to backup file or None on failure.
    """
    cfg = load_config()
    paths = cfg.get("BACKUP_PATHS", ["/config"])
    if not isinstance(paths, list):
        paths = [str(paths)]

    _ensure_backup_dir()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"frigate_config_{timestamp}.tar.gz"
    dest_path = os.path.join(BACKUP_DIR, filename)

    write_log("Backup", f"Starting backup -> {dest_path}")
    try:
        with tarfile.open(dest_path, "w:gz") as tar:
            for path in paths:
                path = str(path)
                if not os.path.exists(path):
                    write_log("Backup", f"Path not found, skipping: {path}")
                    continue
                arcname = os.path.basename(path.rstrip("/")) or path.strip("/")
                write_log("Backup", f"Adding {path} as {arcname}")
                tar.add(path, arcname=arcname)

        write_log("Backup", f"Backup complete: {dest_path}")
        _cleanup_old_backups()
        return dest_path
    except Exception as e:
        write_log("Backup", f"Backup failed: {e}")
        try:
            if os.path.exists(dest_path):
                os.remove(dest_path)
        except Exception:
            pass
        return None


def restore_backup(filename: str) -> bool:
    """
    Restore the specified backup tarball to the root of BACKUP_PATHS[0].
    This does not restart Frigate; caller can mark 'restart required'.
    """
    cfg = load_config()
    paths = cfg.get("BACKUP_PATHS", ["/config"])
    if not isinstance(paths, list):
        paths = [str(paths)]

    if not paths:
        write_log("Backup", "No BACKUP_PATHS configured; cannot restore.")
        return False

    target_root = paths[0]
    backup_path = os.path.join(BACKUP_DIR, filename)

    if not os.path.exists(backup_path):
        write_log("Backup", f"Restore failed: file not found {backup_path}")
        return False

    write_log("Backup", f"Restoring backup {backup_path} -> {target_root}")
    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(target_root)
        write_log("Backup", f"Restore complete from {backup_path}")
        return True
    except Exception as e:
        write_log("Backup", f"Restore failed: {e}")
        return False
