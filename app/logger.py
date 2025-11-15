import os
from datetime import datetime

LOG_DIR = "/logs"
LOG_FILE = os.path.join(LOG_DIR, "manager.log")
MAX_SIZE_BYTES = 512 * 1024  # 512 KB
MAX_BACKUPS = 5


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _rotate_if_needed():
    _ensure_log_dir()
    if not os.path.exists(LOG_FILE):
        return

    size = os.path.getsize(LOG_FILE)
    if size < MAX_SIZE_BYTES:
        return

    # Rotate: manager.log -> manager.log.1 -> manager.log.2 ...
    for i in range(MAX_BACKUPS, 0, -1):
        src = f"{LOG_FILE}.{i}"
        dst = f"{LOG_FILE}.{i+1}"
        if os.path.exists(src):
            if i == MAX_BACKUPS:
                os.remove(src)
            else:
                os.rename(src, dst)

    os.rename(LOG_FILE, f"{LOG_FILE}.1")


def write_log(component: str, message: str):
    _ensure_log_dir()
    _rotate_if_needed()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{component}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
