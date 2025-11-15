from logger import write_log


def install_coral_drivers() -> bool:
    """
    Stub for Coral TPU driver installation.

    In your real setup you’ll likely call the community script you used earlier
    on the host. Inside the container we just log that the action was requested
    and return False to indicate 'not actually installed'.
    """
    write_log("Drivers", "Coral driver install requested (stub only in container).")
    return False
