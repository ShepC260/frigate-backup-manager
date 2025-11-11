import os
import tarfile
import tempfile
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from logger import write_log
from gdrive_sync import get_credentials, get_token_path
from config_manager import load_config

BACKUP_DIR = os.getenv("BACKUP_DIR", "/backups")
CONFIG_DIR = os.getenv("CONFIG_DIR", "/config")


def _list_local_backups():
    """List local .tar.gz backup files."""
    try:
        files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz")]
        files.sort(reverse=True)
        return files
    except Exception as e:
        write_log("Restore", f"Failed to list local backups: {e}")
        return []


def _list_drive_backups():
    """List backup files from Google Drive backup folder."""
    try:
        creds = get_credentials()
        if not creds:
            return []
        service = build("drive", "v3", credentials=creds)
        query = "name contains 'frigate_config_' and trashed = false"
        result = service.files().list(q=query, fields="files(id, name, modifiedTime)").execute()
        files = sorted(result.get("files", []), key=lambda x: x["modifiedTime"], reverse=True)
        return [f["name"] for f in files]
    except Exception as e:
        write_log("Restore", f"Failed to list Drive backups: {e}")
        return []


def list_backups(source: str = "local"):
    """Return list of backups based on source."""
    if source == "gdrive":
        return _list_drive_backups()
    return _list_local_backups()


def restore_local(filename: str):
    """Restore from a local backup file."""
    path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(path):
        return {"ok": False, "message": "Backup file not found."}

    try:
        write_log("Restore", f"Restoring local backup: {filename}")
        with tarfile.open(path, "r:gz") as tar:
            tar.extractall(CONFIG_DIR)
        write_log("Restore", "Local restore complete.")
        return {"ok": True, "message": f"Restored {filename}"}
    except Exception as e:
        write_log("Restore", f"Restore failed: {e}")
        return {"ok": False, "message": str(e)}


def restore_from_drive(filename: str):
    """Restore backup directly from Google Drive."""
    try:
        creds = get_credentials()
        if not creds:
            return {"ok": False, "message": "Drive not configured."}

        service = build("drive", "v3", credentials=creds)
        query = f"name='{filename}' and trashed=false"
        result = service.files().list(q=query, fields="files(id, name)").execute()
        files = result.get("files", [])
        if not files:
            return {"ok": False, "message": "File not found on Drive."}

        file_id = files[0]["id"]
        request = service.files().get_media(fileId=file_id)

        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        downloader = MediaIoBaseDownload(tmpfile, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        tmpfile.close()

        write_log("Restore", f"Downloaded {filename} from Drive; restoring...")
        with tarfile.open(tmpfile.name, "r:gz") as tar:
            tar.extractall(CONFIG_DIR)
        os.unlink(tmpfile.name)
        write_log("Restore", "Drive restore complete.")
        return {"ok": True, "message": f"Restored {filename} from Google Drive"}
    except Exception as e:
        write_log("Restore", f"Drive restore failed: {e}")
        return {"ok": False, "message": str(e)}
