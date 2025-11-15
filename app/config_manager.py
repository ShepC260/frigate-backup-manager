import os
import json

CONFIG_PATH = "/data/config.json"

DEFAULT_CONFIG = {
    "BACKUP_PATHS": ["/config"],                # volume-mounted frigate config
    "BACKUP_RETENTION": 10,                     # number of backup files to keep
    "GDRIVE_ENABLED": False,
    "GDRIVE_TOKEN_PATH": "/data/drive_token.json",
    "FRIGATE_RESTART_CMD": "systemctl restart frigate",
}


def load_config() -> dict:
    """Load config from JSON, falling back to defaults."""
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # corrupted config: fall back to default
        return DEFAULT_CONFIG.copy()

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(data)
    return cfg


def save_config(cfg: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
