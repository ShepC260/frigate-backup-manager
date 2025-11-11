import os
from typing import Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from logger import write_log
from config_manager import load_config

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_NAME = os.getenv("GDRIVE_FOLDER_NAME", "Frigate-Backups")


def get_token_path() -> str:
    cfg = load_config()
    return cfg.get("GDRIVE_TOKEN_PATH", "/data/drive_token.json")


def get_credentials() -> Optional[Credentials]:
    token_path = get_token_path()
    if not os.path.exists(token_path):
        return None

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            write_log("Backup", "Refreshed Google Drive credentials.")
        except Exception as e:
            write_log("Backup", f"Failed to refresh Drive credentials: {e}")
            return None
    return creds


def get_drive_status():
    token_path = get_token_path()
    if not os.path.exists(token_path):
        return {"configured": False, "email": None, "token_path": token_path}
    creds = get_credentials()
    if not creds:
        return {"configured": False, "email": None, "token_path": token_path}
    try:
        service = build("drive", "v3", credentials=creds)
        about = service.about().get(fields="user(emailAddress)").execute()
        email = about.get("user", {}).get("emailAddress")
        return {"configured": True, "email": email, "token_path": token_path}
    except Exception as e:
        write_log("Backup", f"Failed to fetch Drive status: {e}")
        return {"configured": False, "email": None, "token_path": token_path}


def _get_or_create_folder_id(service, folder_name: str) -> str:
    q = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    res = service.files().list(q=q, spaces="drive", fields="files(id,name)", pageSize=1).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    folder = service.files().create(
        body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder"},
        fields="id",
    ).execute()
    return folder["id"]


def upload_backup_to_drive(file_path: str) -> bool:
    if not os.path.exists(file_path):
        write_log("Backup", f"Drive upload skipped; file not found: {file_path}")
        return False

    creds = get_credentials()
    if not creds:
        write_log("Backup", "Drive upload skipped; not authenticated or invalid token.")
        return False

    try:
        service = build("drive", "v3", credentials=creds)
        folder_id = _get_or_create_folder_id(service, FOLDER_NAME)
        metadata = {"name": os.path.basename(file_path), "parents": [folder_id]}
        media = MediaFileUpload(file_path, mimetype="application/gzip")
        service.files().create(body=metadata, media_body=media, fields="id").execute()
        write_log("Backup", f"Uploaded {os.path.basename(file_path)} to Google Drive.")
        return True
    except Exception as e:
        write_log("Backup", f"Google Drive upload failed: {e}")
        return False
