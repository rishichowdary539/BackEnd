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
    """Job function to trigger monthly expense reports"""
    logger.info("Executing monthly reports job...")
    try:
        result = trigger_monthly_reports()
        if result.get("success"):
            logger.info("Monthly reports job completed successfully")
        else:
            logger.error(f"Monthly reports job failed: {result.get('error')}")
    except Exception as e:
        logger.error(f"Error in monthly reports job: {str(e)}")


def start_scheduler():
    """Start the background scheduler with configured jobs"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler is already running")
        return
    
    scheduler = BackgroundScheduler()
    
    # Get cron schedule from first enabled user, or use defaults
    from app.db import dynamo
    
    # Get all enabled users and use the first one's schedule
    enabled_users = dynamo.get_all_users_with_scheduler_enabled()
    if enabled_users:
        # Use first enabled user's schedule
        db_settings = dynamo.get_scheduler_settings(enabled_users[0])
        if db_settings:
            day = db_settings.get("day", 1)
            hour = db_settings.get("hour", 6)
            minute = db_settings.get("minute", 0)
            logger.info(f"Loaded scheduler settings from first enabled user ({enabled_users[0]}): day={day}, hour={hour}, minute={minute}")
        else:
            # Fallback to defaults
            day, hour, minute = 1, 6, 0
    else:
        # No users have scheduler enabled, use defaults
        # Fallback to environment variable
        cron_schedule = os.getenv("MONTHLY_REPORTS_CRON", "1 6 0")  # day=1, hour=6, minute=0
        
        # Parse schedule
        parts = cron_schedule.split()
        if len(parts) >= 3:
            day = int(parts[0])
            hour = int(parts[1])
            minute = int(parts[2])
        else:
            # Default: 1st of month at 6 AM UTC
            day = 1
            hour = 6
            minute = 0
        logger.info(f"Using environment/default settings: day={day}, hour={hour}, minute={minute}")
    
    # Add monthly job
    scheduler.add_job(
        monthly_reports_job,
        trigger=CronTrigger(
            day=day,      # Day of month (1-31)
            hour=hour,    # Hour (0-23)
            minute=minute # Minute (0-59)
        ),
        id="monthly_expense_reports",
        name="Monthly Expense Reports",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Scheduler started. Monthly reports will run on day {day} at {hour:02d}:{minute:02d} UTC for enabled users.")


def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler stopped")


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

