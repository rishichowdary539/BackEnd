"""
Scheduler Service
Manages background tasks and cron jobs using APScheduler
"""
import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.utils.lambda_scheduler import trigger_monthly_reports

logger = logging.getLogger(__name__)

# Scheduler instance (exported for use in settings router)
scheduler: BackgroundScheduler = None


def monthly_reports_job():
    """Job function to trigger monthly expense reports for all enabled users"""
    from datetime import datetime
    logger.info("=" * 80)
    logger.info("CRON JOB TRIGGERED!")
    logger.info(f"Triggered at: {datetime.utcnow().isoformat()} UTC")
    logger.info("=" * 80)
    try:
        result = trigger_monthly_reports()
        if result.get("success"):
            logger.info("=" * 80)
            logger.info("Monthly reports job completed successfully")
            logger.info(f"Result: {result.get('message', 'N/A')}")
            logger.info("=" * 80)
        else:
            logger.error("=" * 80)
            logger.error(f"Monthly reports job failed: {result.get('error')}")
            logger.error("=" * 80)
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"Error in monthly reports job: {str(e)}")
        logger.error("=" * 80, exc_info=True)


def start_scheduler():
    """Start the background scheduler with fixed schedule: 1st day of month at 00:00 UTC"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler is already running")
        return
    
    scheduler = BackgroundScheduler()
    
    # ============================================================
    # CRON SCHEDULE CONFIGURATION
    # ============================================================
    # Update these values to change when monthly reports run:
    # - day: Day of month (1-31). Use 1 for 1st of every month
    # - hour: Hour in UTC (0-23). Use 0 for midnight
    # - minute: Minute (0-59). Use 0 for start of hour
    # ============================================================
    
    # Production schedule: 1st day of month at 00:00 UTC
    # day = 1
    # hour = 0
    # minute = 0
    
    # For testing: Set to run today at specific time
    from datetime import datetime
    today = datetime.utcnow()
    day = today.day  # Today's day (19)
    hour = 16  # 4 PM
    minute = 20  # 20 minutes (set to a few minutes from now for testing)
    
    # Add single system-wide job
    job = scheduler.add_job(
        monthly_reports_job,
        trigger=CronTrigger(
            day=day,      # Day of month (1-31)
            hour=hour,    # Hour in UTC (0-23)
            minute=minute # Minute (0-59)
        ),
        id="monthly_expense_reports",
        name="Monthly Expense Reports",
        replace_existing=True
    )
    
    scheduler.start()
    
    # Log detailed information
    logger.info("=" * 80)
    logger.info("SCHEDULER STARTED")
    logger.info(f"Schedule: Day {day} at {hour:02d}:{minute:02d} UTC")
    if job.next_run_time:
        from datetime import timezone
        logger.info(f"Next run: {job.next_run_time.isoformat()} UTC")
        current_time = datetime.now(timezone.utc)
        logger.info(f"Current time: {current_time.isoformat()} UTC")
        time_until_run = (job.next_run_time - current_time).total_seconds()
        logger.info(f"Time until next run: {int(time_until_run / 60)} minutes ({int(time_until_run)} seconds)")
    else:
        logger.warning("No next run time calculated!")
    logger.info("=" * 80)


def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler stopped")


def refresh_scheduler_jobs():
    """
    Refresh scheduler job - not needed for single system-wide job.
    The scheduler uses a fixed schedule, so this function is kept for compatibility.
    """
    # No-op: Single system-wide job doesn't need refreshing
    # The schedule is fixed and users are checked at runtime
    pass


def get_scheduler_status():
    """Get current scheduler status"""
    if scheduler is None:
        return {"running": False}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs
    }

