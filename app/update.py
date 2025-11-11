import subprocess
from datetime import datetime
from logger import write_log


def run_command(cmd: str):
    """Run a shell command and return (stdout, stderr, returncode)."""
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except Exception as e:
        return "", str(e), 1


def check_for_updates():
    """Check available system updates."""
    write_log("Update", "Checking for OS updates...")
    out, err, code = run_command("apt-get -s upgrade")
    if code != 0:
        write_log("Update", f"Update check failed: {err or out}")
        return False

    updates = []
    for line in out.splitlines():
        if line.startswith("Inst "):
            pkg = line.split()[1]
            updates.append(pkg)
    write_log("Update", f"Updates available: {len(updates)} packages")
    return updates


def run_security_updates():
    """Install only security updates automatically."""
    write_log("Update", "Running automatic security updates...")
    out, err, code = run_command("apt-get update")
    if code != 0:
        write_log("Update", f"Failed to update package list: {err or out}")
        return False

    # Use unattended-upgrades for security packages
    out, err, code = run_command("unattended-upgrade -v")
    if code == 0:
        write_log("Update", "Security updates applied successfully.")
        return True
    else:
        write_log("Update", f"Security update failed: {err or out}")
        return False


def run_full_update():
    """Run a full OS upgrade manually (user-initiated)."""
    write_log("Update", "Performing full system update...")
    out, err, code = run_command("apt-get update && apt-get upgrade -y")
    if code == 0:
        write_log("Update", "System updated successfully.")
        return True
    else:
        write_log("Update", f"Full update failed: {err or out}")
        return False


def update_frigate():
    """Attempt to update the Frigate container."""
    write_log("Update", "Checking for Frigate updates...")
    out, err, code = run_command("docker ps --filter 'name=frigate' --format '{{.Image}}'")
    if code != 0 or not out:
        write_log("Update", "Frigate container not found or Docker unavailable.")
        return False

    image_name = out.strip()
    write_log("Update", f"Found Frigate container image: {image_name}")
    write_log("Update", "Pulling latest image...")
    pull_out, pull_err, pull_code = run_command(f"docker pull {image_name}")
    if pull_code != 0:
        write_log("Update", f"Failed to pull image: {pull_err or pull_out}")
        return False

    write_log("Update", "Restarting Frigate container...")
    _, _, restart_code = run_command("docker restart frigate")
    if restart_code == 0:
        write_log("Update", "Frigate container updated and restarted successfully.")
        return True
    else:
        write_log("Update", "Failed to restart Frigate container.")
        return False
