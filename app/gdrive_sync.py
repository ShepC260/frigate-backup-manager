import os
from typing import Dict, Any, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from logger import write_log
from config_manager import load_config

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _get_token_path() -> str:
    cfg = load_config()
    return cfg.get("GDRIVE_TOKEN_PATH", "/data/drive_token.json")


def _is_enabled() -> bool:
    cfg = load_config()
    return bool(cfg.get("GDRIVE_ENABLED", False))


def _get_drive_service():
    if not _is_enabled():
        raise RuntimeError("Google Drive sync is disabled in config.")

    token_path = _get_token_path()
    if not os.path.exists(token_path):
        raise FileNotFoundError(f"Token file not found: {token_path}")

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return service


def get_drive_status() -> Dict[str, Any]:
    """
    For UI: returns {enabled, configured, email, token_path, message}
    """
    cfg = load_config()
    enabled = _is_enabled()
    token_path = _get_token_path()

    if not enabled:
        return {
            "enabled": False,
            "configured": os.path.exists(token_path),
            "email": None,
            "token_path": token_path,
            "message": "Google Drive disabled",
        }

    if not os.path.exists(token_path):
        return {
            "enabled": True,
            "configured": False,
            "email": None,
            "token_path": token_path,
            "message": "Token file missing",
        }

    try:
        service = _get_drive_service()
        about = service.about().get(fields="user(emailAddress)").execute()
        email = about.get("user", {}).get("emailAddress")
        return {
            "enabled": True,
            "configured": True,
            "email": email,
            "token_path": token_path,
            "message": "Connected",
        }
    except Exception as e:
        write_log("Drive", f"Drive status error: {e}")
        return {
            "enabled": True,
            "configured": False,
            "email": None,
            "token_path": token_path,
            "message": f"Error: {e}",
        }


def upload_backup_to_drive(path: str) -> bool:
    """
    Upload a local backup tar.gz file to Google Drive.
    Returns True on success, False on failure or if disabled.
    """
    if not _is_enabled():
        write_log("Drive", "Upload requested but Drive is disabled.")
        return False

    if not os.path.exists(path):
        write_log("Drive", f"Upload failed: path not found: {path}")
        return False

    filename = os.path.basename(path)
    try:
        service = _get_drive_service()
        file_metadata = {"name": filename}
        media = None
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(path, mimetype="application/gzip", resumable=True)
        write_log("Drive", f"Uploading {filename} to Google Drive...")
        created = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        file_id = created.get("id")
        write_log("Drive", f"Upload complete. File ID: {file_id}")
        return True
    except Exception as e:
        write_log("Drive", f"Upload failed: {e}")
        return False


def save_token_json(token_json: str) -> bool:
    """
    Save raw token JSON string to token_path.
    """
    token_path = _get_token_path()
    os.makedirs(os.path.dirname(token_path), exist_ok=True)
    try:
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(token_json.strip())
        write_log("Drive", f"Token file written to {token_path}")
        return True
    except Exception as e:
        write_log("Drive", f"Failed to write token file: {e}")
        return False


def list_drive_backups(local_filenames: List[str]) -> Dict[str, bool]:
    """
    Given a list of local backup filenames, returns a mapping:
      { "filename.tar.gz": True/False }
    indicating whether a file with that name exists in Drive.

    If Drive is disabled or token invalid, returns {} and logs.
    """
    if not _is_enabled():
        return {}

    token_path = _get_token_path()
    if not os.path.exists(token_path):
        return {}

    try:
        service = _get_drive_service()
        result: Dict[str, bool] = {}
        for name in local_filenames:
            # Query by exact name
            q = f"name = '{name}' and trashed = false"
            try:
                resp = (
                    service.files()
                    .list(q=q, spaces="drive", fields="files(id,name)", pageSize=1)
                    .execute()
                )
                files = resp.get("files", [])
                result[name] = len(files) > 0
            except HttpError as he:
                write_log("Drive", f"Drive query error for {name}: {he}")
                result[name] = False
        return result
    except Exception as e:
        write_log("Drive", f"Drive index error: {e}")
        return {}
