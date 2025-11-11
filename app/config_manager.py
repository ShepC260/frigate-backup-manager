import json
import os
from logger import write_log

CONFIG_FILE = os.getenv("CONFIG_FILE", "/data/config.json")

DEFAULT_CONFIG = {
    "BACKUP_CRON": "0 3 * * *",
    "SECURITY_UPDATE_CRON": "0 4 * * *",
    "LOG_ROTATION_CRON": "0 5 * * *",
    "ENABLE_GDRIVE_SYNC": False,
    "GDRIVE_TOKEN_PATH": "/data/drive_token.json",  # path to user-supplied Google Drive token
}


def load_config():
    """Load configuration from JSON file, create defaults if missing."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # merge with defaults so new keys appear automatically
            return {**DEFAULT_CONFIG, **data}
    except Exception as e:
        write_log("Config", f"Failed to load config: {e}")
        return DEFAULT_CONFIG


def save_config(data):
    """Save configuration to JSON file."""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        write_log("Config", f"Configuration saved: {data}")
    except Exception as e:
        write_log("Config", f"Failed to save config: {e}")
