import subprocess
import platform
from datetime import datetime
from logger import write_log


def get_os_version():
    """Return OS version string."""
    try:
        out = subprocess.getoutput("lsb_release -ds")
        return out.strip().replace('"', "")
    except Exception:
        return platform.platform()


def get_frigate_version():
    """Detect Frigate version via Docker image or CLI."""
    try:
        out = subprocess.getoutput("docker ps --filter 'name=frigate' --format '{{.Image}}'")
        if not out:
            return "Not running"
        image = out.strip()
        if ":" in image:
            return image.split(":")[-1]
        return image
    except Exception:
        return "Unknown"


def get_coral_status():
    """Detect if Coral TPU is available."""
    try:
        out = subprocess.getoutput("ls /dev/apex* 2>/dev/null")
        if out.strip():
            return "Detected"
        return "Not detected"
    except Exception:
        return "Unknown"


def get_status_summary():
    """Return structured system status for the dashboard."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        os_version = get_os_version()
        frigate_version = get_frigate_version()
        coral = get_coral_status()

        return {
            "timestamp": now,
            "system": {
                "os": os_version,
                "frigate": frigate_version,
                "coral": coral,
            },
        }
    except Exception as e:
        write_log("Status", f"Failed to collect system info: {e}")
        return {
            "timestamp": now,
            "system": {
                "os": "Unknown",
                "frigate": "Unknown",
                "coral": "Unknown",
            },
        }
