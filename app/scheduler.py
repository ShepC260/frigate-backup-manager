from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from logger import write_log
from backup import run_backup
from update import check_for_updates, run_security_updates
from logger import rotate_logs
from config_manager import load_config
from cron_utils import describe_cron

scheduler = BackgroundScheduler()
jobs = {}


def add_job(name: str, cron_expr: str, func):
    """Register or update a scheduled job."""
    try:
        if name in jobs:
            scheduler.remove_job(jobs[name].id)

        trigger = CronTrigger.from_crontab(cron_expr)
        job = scheduler.add_job(func, trigger, id=name, replace_existing=True)
        jobs[name] = job
        write_log("Scheduler", f"Added job '{name}' ({cron_expr})")
    except Exception as e:
        write_log("Scheduler", f"Failed to add job '{name}': {e}")


def init_scheduler():
    """Initialise scheduler with current configuration."""
    cfg = load_config()
    add_job("backup", cfg["BACKUP_CRON"], run_backup)
    add_job("security_updates", cfg["SECURITY_UPDATE_CRON"], run_security_updates)
    add_job("log_rotation", cfg["LOG_ROTATION_CRON"], rotate_logs)

    if not scheduler.running:
        scheduler.start()
        write_log("Scheduler", "Background scheduler started.")


def reload_scheduler():
    """Reload scheduler when config is updated."""
    write_log("Scheduler", "Reloading scheduler...")
    for job_id in list(jobs.keys()):
        try:
            scheduler.remove_job(jobs[job_id].id)
            del jobs[job_id]
        except Exception:
            pass
    init_scheduler()


def get_next_run_times():
    """Return dictionary of next run times and descriptions."""
    out = {}
    for name, job in jobs.items():
        next_run = job.next_run_time
        out[name] = {
            "next": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "—",
            "in": describe_cron(job.trigger),
        }
    return out
