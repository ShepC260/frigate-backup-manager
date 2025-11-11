from cron_descriptor import get_description


def is_valid_cron(expr: str) -> bool:
    """Validate a cron expression format."""
    try:
        parts = expr.split()
        return len(parts) == 5
    except Exception:
        return False


def describe_cron(expr: str) -> str:
    """Return a friendly description of a cron expression."""
    try:
        return get_description(expr, use_24hour_time_format=True)
    except Exception:
        # fallback if cron_descriptor not available
        return f"Cron: {expr}"
