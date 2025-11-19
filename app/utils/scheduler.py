"""
Scheduler Service
Manages background tasks and cron jobs using APScheduler
"""
import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

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
    
    # For testing: Use DateTrigger to run at a specific datetime (2 minutes from now)
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    future_time = now + timedelta(minutes=2)
    
    logger.info(f"TESTING MODE: Using DateTrigger to run at {future_time.isoformat()} UTC (in 2 minutes)")
    
    # Use DateTrigger for testing (runs once at specific time)
    job = scheduler.add_job(
        monthly_reports_job,
        trigger=DateTrigger(run_date=future_time),
        id="monthly_expense_reports",
        name="Monthly Expense Reports (TEST MODE)",
        replace_existing=True
    )
    
    # For production, uncomment this and comment out the DateTrigger above:
    # job = scheduler.add_job(
    #     monthly_reports_job,
    #     trigger=CronTrigger(
    #         day=1,      # 1st day of month
    #         hour=0,     # 00:00 UTC
    #         minute=0    # Start of hour
    #     ),
    #     id="monthly_expense_reports",
    #     name="Monthly Expense Reports",
    #     replace_existing=True
    # )
    
    scheduler.start()
    
    # Log detailed information
    from datetime import timezone
    logger.info("=" * 80)
    logger.info("SCHEDULER STARTED")
    current_time = datetime.now(timezone.utc)
    logger.info(f"Current time: {current_time.isoformat()} UTC")
    
    if job.next_run_time:
        logger.info(f"Next run: {job.next_run_time.isoformat()}")
        time_until_run = (job.next_run_time - current_time).total_seconds()
        if time_until_run > 0:
            logger.info(f"Time until next run: {int(time_until_run / 60)} minutes ({int(time_until_run)} seconds)")
        else:
            logger.warning(f"Next run time is in the past! ({int(abs(time_until_run) / 60)} minutes ago)")
            logger.warning("Job may not trigger!")
    else:
        logger.error("No next run time calculated! Job may not trigger!")
    
    # Verify scheduler is running
    if scheduler.running:
        logger.info(f"Scheduler is RUNNING: {scheduler.running}")
        logger.info(f"Number of jobs: {len(scheduler.get_jobs())}")
    else:
        logger.error("Scheduler is NOT running!")
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

