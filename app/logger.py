import os
import datetime

LOG_DIR = os.getenv("LOG_DIR", "/logs")
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))


def ensure_log_dir():
    """Ensure the log directory exists."""
    os.makedirs(LOG_DIR, exist_ok=True)


def _logfile_path(date: datetime.date | None = None) -> str:
    """Get full path for today's log file."""
    if not date:
        date = datetime.date.today()
    ensure_log_dir()
    return os.path.join(LOG_DIR, f"{date.isoformat()}.log")


def write_log(tag: str, message: str):
    """Append a timestamped message to today's log file."""
    ensure_log_dir()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{tag}] {message}\n"
    try:
        with open(_logfile_path(), "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def rotate_logs():
    """Delete logs older than LOG_RETENTION_DAYS."""
    ensure_log_dir()
    try:
        today = datetime.date.today()
        for fname in os.listdir(LOG_DIR):
            if not fname.endswith(".log"):
                continue
            try:
                date_part = fname.replace(".log", "")
                file_date = datetime.date.fromisoformat(date_part)
                age = (today - file_date).days
                if age > LOG_RETENTION_DAYS:
                    os.remove(os.path.join(LOG_DIR, fname))
                    write_log("Logger", f"Removed old log: {fname}")
            except Exception:
                continue
        write_log("Logger", "Log rotation complete.")
    except Exception as e:
        write_log("Logger", f"Rotation failed: {e}")
