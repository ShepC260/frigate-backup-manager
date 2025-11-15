import json
import os
from threading import Lock

CONFIG_PATH = "/data/config.json"

_lock = Lock()

DEFAULT_CONFIG = {
    # Backup settings
    "BACKUP_PATHS": ["/config"],
    "BACKUP_RETENTION": 10,

    # Frigate integration
    "FRIGATE_RESTART_CMD": "systemctl restart frigate",

    # Google Drive
    "GDRIVE_ENABLED": False,
    "GDRIVE_TOKEN_PATH": "/data/drive_token.json",

    # Update / version info
    # Channels: main, releases, dev
    "UPDATE_CHANNEL": "main",
    # Local version string, e.g. dev-main-abc1234 or v1.0.0
    "LOCAL_VERSION": "dev-unknown",

    # GitHub repo info (override if you ever fork)
    "GITHUB_USER": "shepc260",
    "GITHUB_REPO": "frigate-backup-manager",
}


def _ensure_config_exists():
    """
    Ensure config file exists. If not, create with DEFAULT_CONFIG.
    """
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)


def load_config() -> dict:
    """
    Load configuration from disk, merging with DEFAULT_CONFIG for any missing keys.
    """
    with _lock:
        _ensure_config_exists()
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

        # Merge defaults for any missing keys
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v

        return cfg


def save_config(cfg: dict) -> None:
    """
    Save configuration to disk. Unknown keys are preserved.
    """
    with _lock:
        # Ensure at least default keys exist
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)

        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        tmp_path = CONFIG_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
        os.replace(tmp_path, CONFIG_PATH)
