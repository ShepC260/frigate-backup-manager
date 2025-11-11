import os
import tarfile
from datetime import datetime

from logger import write_log
from config_manager import load_config
from gdrive_sync import upload_backup_to_drive

BACKUP_SRC = os.getenv("BACKUP_SRC", "/config")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/backups")
BACKUP_RETENTION = int(os.getenv("BACKUP_RETENTION", "10"))  # number of backups to keep


def ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def list_backups():
    """Return sorted list of backup filenames."""
    ensure_backup_dir()
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz")]
    files.sort()
    return files


def rotate_backups():
    """Keep only the most recent BACKUP_RETENTION backup files."""
    files = list_backups()
    if len(files) <= BACKUP_RETENTION:
        return
    to_remove = files[0: len(files) - BACKUP_RETENTION]
    for fname in to_remove:
        path = os.path.join(BACKUP_DIR, fname)
        try:
            os.remove(path)
            write_log("Backup", f"Removed old backup: {fname}")
        except Exception as e:
            write_log("Backup", f"Failed to remove {fname}: {e}")


def run_backup():
    """Run a configuration backup."""
    ensure_backup_dir()
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = os.path.join(BACKUP_DIR, f"frigate_config_{now}.tar.gz")

    try:
        write_log("Backup", "Starting backup process...")
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(BACKUP_SRC, arcname=os.path.basename(BACKUP_SRC))
        write_log("Backup", f"Backup created successfully: {os.path.basename(backup_path)}")
        rotate_backups()
        write_log("Backup", "Backup rotation check complete.")
    except Exception as e:
        write_log("Backup", f"Backup failed: {e}")
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
        except Exception:
            pass
        return

    # NEW: Optional Google Drive sync
    cfg = load_config()
    if cfg.get("ENABLE_GDRIVE_SYNC"):
        write_log("Backup", "Google Drive sync enabled; uploading backup...")
        upload_backup_to_drive(backup_path)
    else:
        write_log("Backup", "Google Drive sync disabled; skipping upload.")
