"""
Scheduler Service
Manages background tasks and cron jobs using APScheduler
"""
import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

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
    
    # For testing: Use IntervalTrigger to run after 2 minutes, then remove job after first run
    from datetime import datetime, timezone, timedelta
    import time
    
    now = datetime.now(timezone.utc)
    future_time = now + timedelta(minutes=2)
    
    logger.info(f"TESTING MODE: Using IntervalTrigger to run in 2 minutes (one-time)")
    logger.info(f"Current time: {now.isoformat()} UTC")
    logger.info(f"Scheduled time: {future_time.isoformat()} UTC")
    
    # Create a wrapper function that runs the job once, then removes itself
    def one_time_job():
        try:
            monthly_reports_job()
        finally:
            # Remove the job after it runs once
            try:
                scheduler.remove_job("monthly_expense_reports")
                logger.info("Test job removed after execution")
            except:
                pass
    
    # Use IntervalTrigger for testing (will run once, then remove itself)
    job = scheduler.add_job(
        one_time_job,
        trigger=IntervalTrigger(minutes=2),
        id="monthly_expense_reports",
        name="Monthly Expense Reports (TEST MODE - ONE TIME)",
        replace_existing=True,
        max_instances=1  # Only allow one instance to run at a time
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
    
    # Start scheduler BEFORE adding job to ensure it's ready
    scheduler.start()
    
    # Small delay to ensure scheduler is fully started
    time.sleep(0.5)
    
    # Log detailed information
    from datetime import timezone
    logger.info("=" * 80)
    logger.info("SCHEDULER STARTED")
    current_time = datetime.now(timezone.utc)
    logger.info(f"Current time: {current_time.isoformat()} UTC")
    
    # Get job again to ensure it's registered
    job = scheduler.get_job("monthly_expense_reports")
    if job:
        if job.next_run_time:
            logger.info(f"Next run: {job.next_run_time.isoformat()}")
            time_until_run = (job.next_run_time - current_time).total_seconds()
            if time_until_run > 0:
                logger.info(f"Time until next run: {int(time_until_run / 60)} minutes ({int(time_until_run)} seconds)")
                logger.info(f"Job will trigger in {int(time_until_run)} seconds")
            else:
                logger.warning(f"Next run time is in the past! ({int(abs(time_until_run) / 60)} minutes ago)")
                logger.warning("Job may not trigger!")
        else:
            logger.error("No next run time calculated! Job may not trigger!")
        
        logger.info(f"Job ID: {job.id}")
        logger.info(f"Job name: {job.name}")
        logger.info(f"Job trigger: {job.trigger}")
    else:
        logger.error("Job 'monthly_expense_reports' not found in scheduler!")
    
    # Verify scheduler is running
    if scheduler.running:
        logger.info(f"Scheduler is RUNNING: {scheduler.running}")
        logger.info(f"Number of jobs: {len(scheduler.get_jobs())}")
        for j in scheduler.get_jobs():
            logger.info(f"  - Job: {j.id} ({j.name}), Next run: {j.next_run_time}")
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

