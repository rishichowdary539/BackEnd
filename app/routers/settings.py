"""
Settings Router
Provides endpoints to control scheduler and manage application settings
"""
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel

from app.core.security import decode_access_token
from app.db import dynamo
from app.utils.scheduler import (
    get_scheduler_status,
    start_scheduler,
    stop_scheduler,
    scheduler
)
from apscheduler.triggers.cron import CronTrigger
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract user_id from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token required")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user_id


class SchedulerScheduleUpdate(BaseModel):
    day: int  # Day of month (1-31)
    hour: int  # Hour (0-23)
    minute: int  # Minute (0-59)


class BudgetThresholdsUpdate(BaseModel):
    thresholds: Dict[str, float]  # Category name -> amount


@router.get("/scheduler")
def get_scheduler_settings(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Get current scheduler status and configuration for the current user.
    Loads settings from DynamoDB.
    """
    # Get system-wide scheduler status (is the scheduler service running?)
    status_info = get_scheduler_status()
    
    # Get user's personal scheduler settings from DynamoDB
    db_settings = dynamo.get_scheduler_settings(user_id)
    if db_settings:
        current_schedule = {
            "day": db_settings.get("day", 1),
            "hour": db_settings.get("hour", 6),
            "minute": db_settings.get("minute", 0),
            "enabled": db_settings.get("enabled", False),
        }
    else:
        # Fallback to defaults if not in DB
        current_schedule = {
            "day": 1,
            "hour": 6,
            "minute": 0,
            "enabled": False,
        }
    
    # Get next run time from running scheduler if available (for this specific user)
    if scheduler and scheduler.running:
        job_id = f"monthly_expense_reports_{user_id}"
        job = scheduler.get_job(job_id)
        if job and job.next_run_time:
            current_schedule["next_run"] = job.next_run_time.isoformat()
    
    return {
        "service_running": status_info.get("running", False),  # System-wide scheduler service status
        "enabled": current_schedule.get("enabled", False),  # User's personal enable/disable
        "jobs": status_info.get("jobs", []),
        "schedule": current_schedule,
    }


@router.post("/scheduler/start")
def start_scheduler_endpoint(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Enable scheduler for the current user and ensure system scheduler is running.
    """
    try:
        # Get user's current settings
        db_settings = dynamo.get_scheduler_settings(user_id)
        if not db_settings:
            # Initialize defaults
            dynamo.initialize_default_scheduler_settings(user_id)
            db_settings = dynamo.get_scheduler_settings(user_id)
        
        day = db_settings.get("day", 1)
        hour = db_settings.get("hour", 6)
        minute = db_settings.get("minute", 0)
        
        # Enable scheduler for this user
        dynamo.save_scheduler_settings(user_id, day, hour, minute, enabled=True)
        
        # Ensure system-wide scheduler service is running
        if scheduler is None or not scheduler.running:
            start_scheduler()
        else:
            # Scheduler is already running, add or update job for this user
            from app.utils.scheduler import monthly_reports_job_for_user
            from apscheduler.triggers.cron import CronTrigger
            
            job_id = f"monthly_expense_reports_{user_id}"
            new_trigger = CronTrigger(day=day, hour=hour, minute=minute)
            
            try:
                existing_job = scheduler.get_job(job_id)
                if existing_job:
                    # Job exists, reschedule it
                    scheduler.reschedule_job(job_id, trigger=new_trigger)
                    logger.info(f"Rescheduled job for user {user_id}: day={day}, hour={hour}, minute={minute}")
                else:
                    # Job doesn't exist, add it
                    scheduler.add_job(
                        monthly_reports_job_for_user,
                        args=[user_id],
                        trigger=new_trigger,
                        id=job_id,
                        name=f"Monthly Expense Reports - {user_id}",
                        replace_existing=True
                    )
                    logger.info(f"Added scheduler job for user {user_id}: day={day}, hour={hour}, minute={minute}")
            except Exception as e:
                logger.error(f"Failed to add/update job for user {user_id}: {str(e)}", exc_info=True)
        
        return {
            "success": True,
            "message": "Scheduler enabled for your account. Monthly reports will be generated automatically.",
            "status": get_scheduler_status()
        }
    except Exception as e:
        logger.error(f"Error enabling scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to enable scheduler: {str(e)}")


@router.post("/scheduler/stop")
def stop_scheduler_endpoint(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Disable scheduler for the current user (doesn't stop system scheduler for other users).
    """
    try:
        # Get user's current settings
        db_settings = dynamo.get_scheduler_settings(user_id)
        if not db_settings:
            # Initialize defaults
            dynamo.initialize_default_scheduler_settings(user_id)
            db_settings = dynamo.get_scheduler_settings(user_id)
        
        day = db_settings.get("day", 1)
        hour = db_settings.get("hour", 6)
        minute = db_settings.get("minute", 0)
        
        # Disable scheduler for this user only
        dynamo.save_scheduler_settings(user_id, day, hour, minute, enabled=False)
        
        # Remove this user's job from the scheduler
        if scheduler and scheduler.running:
            job_id = f"monthly_expense_reports_{user_id}"
            try:
                scheduler.remove_job(job_id)
                logger.info(f"Removed scheduler job for user {user_id}")
            except:
                pass  # Job doesn't exist, that's fine
        
        # Note: We don't stop the system scheduler as other users might have it enabled
        
        return {
            "success": True,
            "message": "Scheduler disabled for your account. Monthly reports will not be generated automatically.",
            "status": get_scheduler_status()
        }
    except Exception as e:
        logger.error(f"Error disabling scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to disable scheduler: {str(e)}")


@router.put("/scheduler/schedule")
def update_scheduler_schedule(
    schedule: SchedulerScheduleUpdate,
    user_id: str = Depends(get_current_user_id)
) -> Dict:
    """
    Update the scheduler cron schedule.
    Requires scheduler to be restarted to take effect.
    """
    # Validate inputs
    if not (1 <= schedule.day <= 31):
        raise HTTPException(status_code=400, detail="Day must be between 1 and 31")
    if not (0 <= schedule.hour <= 23):
        raise HTTPException(status_code=400, detail="Hour must be between 0 and 23")
    if not (0 <= schedule.minute <= 59):
        raise HTTPException(status_code=400, detail="Minute must be between 0 and 59")
    
    try:
        logger.info(f"Updating schedule for user {user_id}: day={schedule.day}, hour={schedule.hour}, minute={schedule.minute}")
        
        # Get user's current enabled state
        db_settings = dynamo.get_scheduler_settings(user_id)
        enabled = db_settings.get("enabled", False) if db_settings else False
        logger.info(f"User {user_id} scheduler enabled status: {enabled}")
        
        # Save user's schedule preference to DB
        dynamo.save_scheduler_settings(user_id, schedule.day, schedule.hour, schedule.minute, enabled=enabled)
        logger.info(f"Saved schedule to database for user {user_id}")
        
        # If this user has scheduler enabled and system scheduler is running, update their job
        if enabled and scheduler and scheduler.running:
            from app.utils.scheduler import monthly_reports_job_for_user
            from apscheduler.triggers.cron import CronTrigger
            
            job_id = f"monthly_expense_reports_{user_id}"
            new_trigger = CronTrigger(
                day=schedule.day,
                hour=schedule.hour,
                minute=schedule.minute
            )
            
            try:
                existing_job = scheduler.get_job(job_id)
                if existing_job:
                    # Job exists, reschedule it with new trigger
                    scheduler.reschedule_job(job_id, trigger=new_trigger)
                    logger.info(f"Rescheduled existing job for user {user_id}: day={schedule.day}, hour={schedule.hour}, minute={schedule.minute}")
                else:
                    # Job doesn't exist, add it
                    scheduler.add_job(
                        monthly_reports_job_for_user,
                        args=[user_id],
                        trigger=new_trigger,
                        id=job_id,
                        name=f"Monthly Expense Reports - {user_id}",
                        replace_existing=True
                    )
                    logger.info(f"Added new job for user {user_id}: day={schedule.day}, hour={schedule.hour}, minute={schedule.minute}")
                
                # Verify the job was updated
                import time
                time.sleep(0.2)  # Small delay to ensure job is registered
                verify_job = scheduler.get_job(job_id)
                if verify_job:
                    logger.info(f"Job verified: {verify_job.id}, next_run={verify_job.next_run_time}, trigger={verify_job.trigger}")
                else:
                    logger.error(f"Job verification failed: job {job_id} not found after update")
                    raise HTTPException(status_code=500, detail="Job update failed: job not found after update")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to update job for user {user_id}: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to update scheduler job: {str(e)}")
        
        # Get next run time if scheduler is running (for this specific user)
        next_run = None
        if scheduler and scheduler.running:
            job_id = f"monthly_expense_reports_{user_id}"
            job = scheduler.get_job(job_id)
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()
                logger.info(f"Next run time for user {user_id}: {next_run}")
            else:
                logger.warning(f"No next_run time found for job {job_id}")
        
        return {
            "success": True,
            "message": f"Schedule updated and saved. Your reports will run on day {schedule.day} at {schedule.hour:02d}:{schedule.minute:02d} UTC.",
            "schedule": {
                "day": schedule.day,
                "hour": schedule.hour,
                "minute": schedule.minute,
                "next_run": next_run
            }
        }
    except Exception as e:
        logger.error(f"Error updating scheduler schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.get("/thresholds")
def get_budget_thresholds(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Get current budget thresholds from DynamoDB for the current user.
    """
    thresholds = dynamo.get_budget_thresholds(user_id)
    if thresholds is None:
        # Return empty dict if not found
        return {"thresholds": {}}
    
    return {"thresholds": thresholds}


@router.put("/thresholds")
def update_budget_thresholds(
    update: BudgetThresholdsUpdate,
    user_id: str = Depends(get_current_user_id)
) -> Dict:
    """
    Update budget thresholds in DynamoDB.
    These thresholds are used for notifications when spending crosses limits.
    """
    # Validate thresholds (all values must be positive)
    for category, amount in update.thresholds.items():
        if amount < 0:
            raise HTTPException(status_code=400, detail=f"Threshold for {category} must be positive")
    
    try:
        success = dynamo.save_budget_thresholds(user_id, update.thresholds)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save budget thresholds")
        
        return {
            "success": True,
            "message": "Budget thresholds updated successfully",
            "thresholds": update.thresholds
        }
    except Exception as e:
        logger.error(f"Error updating budget thresholds: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update thresholds: {str(e)}")

