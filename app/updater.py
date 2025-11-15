import subprocess

from logger import write_log


def update_os() -> bool:
    """
    Run an OS update inside the container.
    NOTE: This updates the container image runtime, not Debian on the host.
    """
    try:
        write_log("Update", "Starting OS update (apt-get update && apt-get -y upgrade)...")
        result = subprocess.run(
            ["bash", "-lc", "apt-get update && apt-get -y upgrade"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            write_log("Update", f"OS update failed: {result.stderr}")
            return False
        write_log("Update", "OS update completed successfully.")
        return True
    except Exception as e:
        write_log("Update", f"Exception during OS update: {e}")
        return False
