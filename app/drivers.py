import os
import subprocess
from logger import write_log
from update import run_command


def detect_drivers():
    """Detect presence of Coral TPU and common GPU devices."""
    info = {}

    # Coral Edge TPU (PCI / M.2 / USB)
    apex_detected = False
    try:
        out = subprocess.run("ls /dev/apex* 2>/dev/null", shell=True, capture_output=True, text=True)
        if out.stdout.strip():
            apex_detected = True
    except Exception:
        pass
    info["coral"] = {
        "detected": apex_detected,
        "recommended_method": "community_installer",
    }

    # Intel GPU (VAAPI)
    intel_gpu = False
    lspci = subprocess.getoutput("lspci")
    if "Intel Corporation" in lspci and "Graphics" in lspci:
        intel_gpu = True
    info["intel_gpu"] = {
        "detected": intel_gpu,
        "recommended_packages": [
            "intel-media-va-driver-non-free",
            "i965-va-driver-shaders",
        ],
    }

    # NVIDIA GPU
    nvidia_gpu = "NVIDIA" in lspci
    info["nvidia_gpu"] = {
        "detected": nvidia_gpu,
        "recommended_packages": [
            "nvidia-driver",
            "firmware-misc-nonfree",
        ],
    }

    # AMD GPU
    amd_gpu = "AMD" in lspci or "ATI" in lspci
    info["amd_gpu"] = {
        "detected": amd_gpu,
        "recommended_packages": ["firmware-amd-graphics"],
    }

    write_log(
        "Drivers",
        f"Detection result: coral={apex_detected}, intel={intel_gpu}, nvidia={nvidia_gpu}, amd={amd_gpu}",
    )
    return info


def install_coral_drivers():
    """Install Coral Edge TPU drivers using the community script."""
    try:
        write_log("Drivers", "Installing Coral TPU drivers via community installer...")
        # Download the official Coral community install script
        script_url = "https://coral.googlesource.com/edgetpu/+/refs/heads/release/install.sh?format=TEXT"
        local_script = "/tmp/coral_install.sh"

        # Retrieve and decode the script
        subprocess.run(
            f"curl -sL {script_url} | base64 -d > {local_script}",
            shell=True,
            check=True,
        )
        os.chmod(local_script, 0o755)

        # Run the script non-interactively
        proc = subprocess.run(
            f"bash {local_script}",
            shell=True,
            capture_output=True,
            text=True,
        )

        if proc.returncode == 0:
            write_log("Drivers", "Coral TPU driver installation completed successfully.")
            return True
        else:
            write_log(
                "Drivers",
                f"Coral driver installation failed with code {proc.returncode}: {proc.stderr or proc.stdout}",
            )
            return False

    except Exception as e:
        write_log("Drivers", f"Coral driver installation failed: {e}")
        return False


def install_drivers():
    """Install recommended drivers for detected hardware."""
    info = detect_drivers()
    installed = []

    # --- Coral TPU ---
    if info["coral"]["detected"]:
        ok = install_coral_drivers()
        if ok:
            installed.append("Coral TPU drivers (community installer)")
        else:
            write_log("Drivers", "Coral TPU installation failed or skipped.")

    # --- Intel GPU ---
    if info["intel_gpu"]["detected"]:
        pkgs = info["intel_gpu"]["recommended_packages"]
        write_log("Drivers", f"Installing Intel GPU packages: {', '.join(pkgs)}")
        run_command("apt-get update")
        for pkg in pkgs:
            out, err, code = run_command(f"apt-get install -y {pkg}")
            if code == 0:
                write_log("Drivers", f"Installed {pkg} successfully.")
                installed.append(pkg)
            else:
                write_log("Drivers", f"Failed to install {pkg}: {err or out}")

    # --- NVIDIA GPU ---
    if info["nvidia_gpu"]["detected"]:
        pkgs = info["nvidia_gpu"]["recommended_packages"]
        write_log("Drivers", f"Installing NVIDIA GPU packages: {', '.join(pkgs)}")
        run_command("apt-get update")
        for pkg in pkgs:
            out, err, code = run_command(f"apt-get install -y {pkg}")
            if code == 0:
                write_log("Drivers", f"Installed {pkg} successfully.")
                installed.append(pkg)
            else:
                write_log("Drivers", f"Failed to install {pkg}: {err or out}")

    # --- AMD GPU ---
    if info["amd_gpu"]["detected"]:
        pkgs = info["amd_gpu"]["recommended_packages"]
        write_log("Drivers", f"Installing AMD GPU packages: {', '.join(pkgs)}")
        run_command("apt-get update")
        for pkg in pkgs:
            out, err, code = run_command(f"apt-get install -y {pkg}")
            if code == 0:
                write_log("Drivers", f"Installed {pkg} successfully.")
                installed.append(pkg)
            else:
                write_log("Drivers", f"Failed to install {pkg}: {err or out}")

    if installed:
        return {"ok": True, "installed": installed}
    else:
        write_log("Drivers", "No compatible hardware detected or installation failed.")
        return {"ok": False, "installed": []}
