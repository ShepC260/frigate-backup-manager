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


def list_log_files():
    """
    Return a list of available log files with index, name, and size.
    index=0 -> manager.log
    index=1 -> manager.log.1, etc.
    """
    _ensure_log_dir()
    files = []

    def _add(idx: int, path: str):
        if os.path.exists(path) and os.path.isfile(path):
            files.append(
                {
                    "index": idx,
                    "name": os.path.basename(path),
                    "size": os.path.getsize(path),
                }
            )

    _add(0, LOG_FILE)
    for i in range(1, MAX_BACKUPS + 1):
        rotated = f"{LOG_FILE}.{i}"
        _add(i, rotated)

    return files


def read_log_file(index: int = 0, max_lines: int = 200):
    """
    Return last max_lines of the selected log file as a list of strings.
    """
    _ensure_log_dir()
    if index == 0:
        path = LOG_FILE
    else:
        path = f"{LOG_FILE}.{index}"

    if not os.path.exists(path) or not os.path.isfile(path):
        return []

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if max_lines <= 0:
            return [line.rstrip("\n") for line in lines]
        return [line.rstrip("\n") for line in lines[-max_lines:]]
    except Exception:
        return []
